# app/core/chat/service.py
import uuid
from datetime import datetime
import time
import logging
import asyncio
from typing import Dict, Any, Optional
from uuid import UUID
from app.application.config import chat_settings

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chat.calculation import CostCalculator
from app.core.chat.calculation import TokenizerService
from app.core.exceptions.chat import (
    ValidationError,
    ProviderUnavailableException,
    ContextLengthExceededException
)

from app.core.providers.service import ProviderService
from app.core.providers.registry import registry
from app.schemas import ChatRequest, ChatResponse
from app.core.chat.prompt.service import PromptService
from app.core.validator.chat import ChatValidator

logger = logging.getLogger(__name__)


class ChatService:
    """Сервис для обработки чат-запросов"""

    def __init__(
            self,
            provider_service: ProviderService,
            request_repo,
            user_repo,
            prompt_service: PromptService,
            tokenizer: TokenizerService,
            cost_calculator: CostCalculator,
            validator: ChatValidator,
            db_session : AsyncSession
    ):
        self.provider_service = provider_service
        self.request_repo = request_repo
        self.user_repo = user_repo
        self.prompt_service = prompt_service
        self.tokenizer = tokenizer
        self.cost_calculator = cost_calculator
        self.validator = validator
        self.db_session = db_session

    async def process_chat_request(
            self,
            request: ChatRequest,
            user_id: Optional[UUID] = None
    ) -> ChatResponse:
        """
        Обработать чат-запрос

        Args:
            request: Запрос чата
            db: Асинхронная сессия БД
            user_id: ID пользователя (опционально)

        Returns:
            ChatResponse
        """
        start_time = time.time()

        # 1. Валидация запроса
        self._validate_request(request)

        # 2. Получение конфигурации модели
        model_config = registry.get_model_config(request.model)

        # 3. Проверка пользователя
        user = await self._validate_user(user_id)

        # 4. Расчет токенов и проверка лимитов
        await self._check_context_length(request, model_config)

        # 5. Получение провайдера
        provider = self.provider_service.factory.get_provider_for_model(request.model)

        # 6. Отправка запроса к провайдеру
        provider_response = await self._call_provider(provider, request, model_config)

        # 7. Сохранение в БД
        save_result = await self._save_request_to_db(
            db=self.db_session,
            request=request,
            provider_response=provider_response,
            model_config=model_config,
            user=user,
            start_time=start_time
        )

        # 8. Формирование ответа
        return self._build_response(
            save_result=save_result,
            provider_response=provider_response,
            start_time=start_time
        )

    async def _check_context_length(
            self,
            request: ChatRequest,
            model_config: Dict[str, Any]
    ) -> None:
        """Проверка длины контекста"""
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        max_tokens = model_config.get("context_window", 8192)

        estimated_tokens = self.tokenizer.estimate_tokens(
            messages_dict,
            request.model
        )
        self.tokenizer.check_context_limit(messages_dict, max_tokens)
        if estimated_tokens > max_tokens:
            raise ContextLengthExceededException(
                model_name=request.model,
                max_tokens=max_tokens,
                requested=estimated_tokens
            )

    def _get_provider(self, model_name: str):
        """Получить провайдера для модели"""
        provider = self.provider_service.factory.get_provider_for_model(model_name)
        if not provider:
            raise ProviderUnavailableException(
                provider_name="unknown",
                model_name=model_name,
                reason="Provider not configured or inactive"
            )
        return provider

    async def _call_provider(self, provider, request: ChatRequest, model_config: Dict[str, Any]):
        """Вызов провайдера с обработкой ошибок"""
        timeout = getattr(provider, 'timeout', chat_settings.DEFAULT_TIMEOUT)

        try:
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

            return await asyncio.wait_for(
                provider.chat_completion(
                    messages=messages,
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    stream=request.stream
                ),
                timeout=timeout
            )

        except asyncio.TimeoutError:
            logger.error(f"Provider {provider.provider_name} timeout after {timeout} seconds")
            raise ProviderUnavailableException(
                provider_name=provider.provider_name,
                model_name=request.model,
                reason=f"Timeout after {timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Provider {provider.provider_name} error: {str(e)}")
            # Здесь можно добавить специфичные проверки разных типов ошибок
            raise ProviderUnavailableException(
                provider_name=provider.provider_name,
                model_name=request.model,
                reason=str(e)
            )

    async def _save_request_to_db(
            self,
            db: AsyncSession,
            request: ChatRequest,
            provider_response,
            model_config: Dict[str, Any],
            user: Optional[Dict[str, Any]],
            start_time: float
    ) -> Dict[str, Any]:
        """Сохранение запроса в БД"""
        try:
            # Расчет стоимости через калькулятор
            cost_data = self.cost_calculator.calculate_cost_for_provider_response(
                provider_response,
                model_config
            )

            # Хеш промпта
            prompt_hash = self.prompt_service.calculate_hash(
                [{"role": msg.role, "content": msg.content} for msg in request.messages]
            )

            # Подготовка данных
            request_data = {
                "request_id": getattr(provider_response, 'request_id', uuid.uuid4()),
                "user_id": user["id"] if user else None,
                "model_id": model_config.get("model_id"),
                "prompt_hash": prompt_hash,
                "input_text": self._prepare_input_text(request.messages),
                "input_tokens": provider_response.input_tokens,
                "output_tokens": provider_response.output_tokens,
                "total_cost": cost_data["total_cost"],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "timestamp": datetime.utcnow(),
                "processing_time": int((time.time() - start_time) * 1000),
                "endpoint": "/api/v1/chat"
            }

            response_data = {
                "response_id": provider_response.response_id,
                "content": provider_response.content,
                "finish_reason": provider_response.finish_reason,
                "model_used": provider_response.model_used,
                "provider_used": provider_response.provider_name,
                "timestamp": datetime.utcnow()
            }

            return await self.request_repo.create_with_response(request_data, response_data)

        except Exception as e:
            logger.error(f"Failed to save request to database: {e}")
            # Не прерываем выполнение, просто логируем
            return {
                "request_id": provider_response.request_id,
                "response_id": provider_response.response_id,
                "total_cost": 0.0
            }

    def _build_response(
            self,
            save_result: Dict[str, Any],
            provider_response,
            start_time: float
    ) -> ChatResponse:
        """Построение ответа"""
        total_time = int((time.time() - start_time) * 1000)

        return ChatResponse(
            response_id=save_result["response_id"],
            request_id=save_result["request_id"],
            content=provider_response.content,
            model_used=provider_response.model_used,
            provider_used=provider_response.provider_name,
            input_tokens=provider_response.input_tokens,
            output_tokens=provider_response.output_tokens,
            total_cost=save_result["total_cost"],
            processing_time_ms=total_time,
            timestamp=datetime.utcnow(),
            finish_reason=provider_response.finish_reason,
            is_cached=False
        )


    def _prepare_input_text(self, messages) -> str:
        """Подготовка текста запроса для сохранения"""
        return "\n".join(
            f"{msg.role}: {msg.content[:500]}..." if len(msg.content) > 500
            else f"{msg.role}: {msg.content}"
            for msg in messages
        )