import asyncio
import time
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import get_repository
from app.schemas import ChatRequest, ChatResponse
from app.core.providers import registry
from app.core.providers.service import ProviderService
from app.core.providers.base import ProviderResponse

logger = logging.getLogger(__name__)


class ChatService:
    """
    Сервис для обработки чат-запросов.
    Инкапсулирует бизнес-логику работы с чатом.
    """

    def __init__(self, db: AsyncSession, provider_service: ProviderService):
        """
        Инициализация сервиса.

        Args:
            db: Асинхронная сессия БД
            provider_service: Сервис провайдеров
        """
        self.db = db
        self.provider_service = provider_service

    async def process_chat_request(
            self,
            chat_request: ChatRequest,
            endpoint: str = "/api/v1/chat"
    ) -> ChatResponse:
        """
        Основной метод обработки чат-запроса.

        Args:
            chat_request: Запрос на обработку чата
            endpoint: Конечная точка API (для логирования)

        Returns:
            ChatResponse: Ответ на чат-запрос
        """
        start_time = time.time()

        try:
            # 1. Валидация входных данных
            self._validate_chat_request(chat_request)

            # 2. Проверка модели в реестре
            model_config = self._get_model_config(chat_request.model)

            # 3. Получение провайдера для модели
            provider = self._get_provider_for_model(chat_request.model)

            # 4. Конвертация сообщений
            messages = self._convert_messages(chat_request.messages)

            # 5. Отправка запроса провайдеру
            provider_response = await self._send_to_provider(
                provider=provider,
                messages=messages,
                model=chat_request.model,
                temperature=chat_request.temperature,
                max_tokens=chat_request.max_tokens,
                stream=chat_request.stream
            )

            # 6. Сохранение в базу данных
            save_result = await self._save_chat_to_database(
                messages=messages,
                model_name=chat_request.model,
                temperature=chat_request.temperature,
                provider_response=provider_response,
                user_id=chat_request.user_id,
                max_tokens=chat_request.max_tokens,
                endpoint=endpoint
            )

            total_time = int((time.time() - start_time) * 1000)

            # 7. Формирование ответа
            return self._build_chat_response(
                save_result=save_result,
                provider_response=provider_response,
                total_time=total_time
            )

        except Exception as e:
            logger.error(f"Chat processing error: {e}", exc_info=True)
            raise

    def _validate_chat_request(self, chat_request: ChatRequest) -> None:
        """
        Валидация чат-запроса.

        Args:
            chat_request: Запрос на валидацию

        Raises:
            HTTPException: Если валидация не пройдена
        """
        from fastapi import HTTPException

        if not chat_request.messages:
            raise HTTPException(status_code=400, detail="Messages cannot be empty")

        if len(chat_request.messages) > 100:
            raise HTTPException(status_code=400, detail="Too many messages (max 100)")

        for msg in chat_request.messages:
            if len(msg.content) > 10000:
                raise HTTPException(
                    status_code=400,
                    detail="Message too long (max 10000 chars)"
                )

        if chat_request.temperature is not None:
            if chat_request.temperature < 0 or chat_request.temperature > 2:
                raise HTTPException(
                    status_code=400,
                    detail="Temperature must be between 0 and 2"
                )

    def _get_model_config(self, model_name: str) -> Any:
        """
        Получение конфигурации модели из реестра.

        Args:
            model_name: Название модели

        Returns:
            Конфигурация модели

        Raises:
            HTTPException: Если модель не найдена
        """
        from fastapi import HTTPException

        model_config = registry.get_model_config(model_name)
        if not model_config:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model_name}' not found. "
                       f"Available models: {list(registry.models.keys())}"
            )
        return model_config

    def _get_provider_for_model(self, model_name: str) -> Any:
        """
        Получение провайдера для указанной модели.

        Args:
            model_name: Название модели

        Returns:
            Провайдер

        Raises:
            HTTPException: Если провайдер не найден
        """
        from fastapi import HTTPException

        provider = self.provider_service.factory.get_provider_for_model(model_name)
        if not provider:
            raise HTTPException(
                status_code=503,
                detail=f"Provider for model '{model_name}' is not available. "
                       f"Possible reasons: API key not configured, "
                       f"provider is inactive, or network issue."
            )
        return provider

    def _convert_messages(self, messages: List[Any]) -> List[Dict[str, str]]:
        """
        Конвертация сообщений из схемы Pydantic в словарь.

        Args:
            messages: Список сообщений в формате Pydantic

        Returns:
            Список сообщений в формате словаря
        """
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def _send_to_provider(
            self,
            provider: Any,
            messages: List[Dict[str, str]],
            model: str,
            temperature: float,
            max_tokens: Optional[int],
            stream: bool = False
    ) -> ProviderResponse:
        """
        Отправка запроса провайдеру.

        Args:
            provider: Экземпляр провайдера
            messages: Сообщения
            model: Название модели
            temperature: Температура
            max_tokens: Максимальное количество токенов
            stream: Использовать ли streaming

        Returns:
            Ответ от провайдера

        Raises:
            HTTPException: При таймауте или ошибке провайдера
        """
        from fastapi import HTTPException

        timeout_seconds = getattr(provider, 'timeout', 30)

        try:
            return await asyncio.wait_for(
                provider.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream
                ),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout for provider {provider.provider_name}")
            raise HTTPException(
                status_code=504,
                detail=f"Provider {provider.provider_name} "
                       f"timeout after {timeout_seconds} seconds"
            )
        except Exception as e:
            logger.error(f"Provider error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Provider error: {str(e)}"
            )

    async def _save_chat_to_database(
            self,
            messages: List[Dict[str, str]],
            model_name: str,
            temperature: float,
            provider_response: ProviderResponse,
            user_id: Optional[UUID] = None,
            max_tokens: Optional[int] = None,
            endpoint: str = "/api/v1/chat"
    ) -> Dict[str, Any]:
        """
        Сохранение чат-запроса и ответа в базу данных.

        Args:
            messages: Сообщения
            model_name: Название модели
            temperature: Температура
            provider_response: Ответ от провайдера
            user_id: ID пользователя
            max_tokens: Максимальное количество токенов
            endpoint: Конечная точка API

        Returns:
            Результат сохранения
        """
        try:
            start_time = time.time()

            # 1. Получаем данные модели из реестра
            model_config = registry.get_model_config(model_name)
            if not model_config:
                raise ValueError(f"Model {model_name} not found in registry")

            # 2. Проверяем user_id
            user_id_to_save = None
            if user_id:
                user_repo = get_repository("user", self.db)
                user = await user_repo.get_by_id(user_id)
                if user:
                    user_id_to_save = user_id

            # 3. Рассчитываем стоимость
            input_cost = provider_response.input_tokens * model_config.input_price_per_1k / 1000
            output_cost = provider_response.output_tokens * model_config.output_price_per_1k / 1000
            total_cost = input_cost + output_cost

            # 4. Подготавливаем текст запроса
            input_text = "\n".join(
                [f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                 for msg in messages]
            )

            # 5. Хеш промпта
            prompt_hash = self._calculate_prompt_hash(messages)

            # 6. Получаем репозиторий запросов
            request_repo = get_repository("request", self.db)

            # 7. Подготавливаем данные для сохранения
            request_data = {
                "request_id": uuid.uuid4(),
                "user_id": user_id_to_save,
                "model_id": model_config.model_id,
                "prompt_hash": prompt_hash,
                "input_text": input_text,
                "input_tokens": provider_response.input_tokens,
                "output_tokens": provider_response.output_tokens,
                "total_cost": total_cost,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timestamp": datetime.utcnow(),
                "processing_time": int((time.time() - start_time) * 1000),
                "endpoint": endpoint
            }

            response_data = {
                "response_id": uuid.uuid4(),
                "content": provider_response.content,
                "finish_reason": provider_response.finish_reason,
                "model_used": provider_response.model_used,
                "provider_used": provider_response.provider_name,
                "timestamp": datetime.utcnow()
            }

            # 8. Используем репозиторий для сохранения
            result = await request_repo.create_with_response(
                request_data, response_data
            )

            logger.info(f"Chat request saved via repository: {result['request_id']}")

            return result

        except Exception as e:
            logger.error(f"Database save error: {e}")
            raise

    def _calculate_prompt_hash(self, messages: list) -> str:
        """
        Вычисляем хеш промпта с нормализацией и версионированием.

        Args:
            messages: Список сообщений

        Returns:
            Хеш промпта
        """
        import hashlib
        import json

        normalized_messages = []
        for msg in messages:
            normalized_msg = {
                "role": msg.get("role", "").strip().lower(),
                "content": msg.get("content", "").strip(),
            }
            normalized_messages.append(
                json.dumps(normalized_msg, sort_keys=True, separators=(',', ':'))
            )

        normalized_messages.sort()
        text_repr = f"v1:{':'.join(normalized_messages)}"

        return hashlib.blake2s(
            text_repr.encode(),
            digest_size=16
        ).hexdigest()

    def _build_chat_response(
            self,
            save_result: Dict[str, Any],
            provider_response: ProviderResponse,
            total_time: int
    ) -> ChatResponse:
        """
        Формирование ответа на чат-запрос.

        Args:
            save_result: Результат сохранения в БД
            provider_response: Ответ от провайдера
            total_time: Общее время обработки

        Returns:
            ChatResponse
        """
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

    async def get_chat_statistics(
            self,
            user_id: Optional[UUID] = None,
            days: int = 30
    ) -> Dict[str, Any]:
        """
        Получение статистики по чат-запросам.

        Args:
            user_id: ID пользователя (опционально)
            days: Количество дней для статистики

        Returns:
            Статистика
        """
        try:
            request_repo = get_repository("request", self.db)

            if user_id:
                # Статистика для конкретного пользователя
                total_cost = await request_repo.get_total_cost_by_user(user_id)
                request_count = await request_repo.count(user_id=user_id)
                recent_requests = await request_repo.get_user_requests(
                    user_id, limit=10
                )

                return {
                    "user_id": user_id,
                    "total_cost": total_cost,
                    "request_count": request_count,
                    "recent_requests": [
                        {
                            "request_id": str(req.request_id),
                            "model_id": str(req.model_id),
                            "status": req.status,
                            "total_cost": float(req.total_cost),
                            "timestamp": req.request_timestamp.isoformat(),
                        }
                        for req in recent_requests
                    ]
                }
            else:
                # Общая статистика
                sql = """
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(total_cost) as total_cost,
                    AVG(processing_time_ms) as avg_processing_time
                FROM ai_framework.requests
                WHERE request_timestamp >= NOW() - INTERVAL ':days days'
                """

                result = await request_repo.raw_query(
                    sql, {"days": days}
                )

                return result[0] if result else {}

        except Exception as e:
            logger.error(f"Error getting chat statistics: {e}")
            return {}

    async def cleanup_old_requests(self, days: int = 90) -> int:
        """
        Очистка старых запросов.

        Args:
            days: Удалить запросы старше этого количества дней

        Returns:
            Количество удаленных запросов
        """
        try:
            request_repo = get_repository("request", self.db)

            sql = """
            DELETE FROM ai_framework.requests
            WHERE request_timestamp < NOW() - INTERVAL ':days days'
            """

            result = await request_repo.raw_query(sql, {"days": days})
            return result[0].get("count", 0) if result else 0

        except Exception as e:
            logger.error(f"Error cleaning up old requests: {e}")
            return 0