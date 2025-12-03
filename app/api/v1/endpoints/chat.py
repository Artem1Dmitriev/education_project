from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime
import time
import hashlib
import logging

from app.database.session import get_db
from app.database.repositories import get_repository
from app.schemas import ChatRequest, ChatResponse, SuccessResponse, ErrorResponse
from app.core.providers import registry
from app.core.providers.service import ProviderService

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


# Dependency для получения сервиса провайдеров
async def get_provider_service(request: Request) -> ProviderService:
    """Получить сервис провайдеров из состояния приложения"""
    service = request.app.state.provider_service
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Provider service not initialized. Please check if database is connected and providers are loaded."
        )
    return service


def calculate_prompt_hash(messages: list) -> str:
    """Вычисляем хеш промпта для кеширования"""
    text_repr = str(sorted([(m.get("role"), m.get("content")) for m in messages]))
    return hashlib.sha256(text_repr.encode()).hexdigest()


async def save_chat_to_database(
        db: AsyncSession,
        messages: list,
        model_name: str,
        temperature: float,
        provider_response,
        user_id: uuid.UUID = None,
        max_tokens: int = None,
        endpoint: str = "/api/v1/chat"
) -> dict:
    """Сохранить chat запрос и ответ в БД через репозитории"""
    try:
        start_time = time.time()

        # 1. Получаем данные модели из реестра
        model_config = registry.get_model_config(model_name)
        if not model_config:
            raise ValueError(f"Model {model_name} not found in registry")

        # 2. Проверяем user_id
        user_id_to_save = None
        if user_id:
            user_repo = get_repository("user", db)
            user = await user_repo.get_by_id(user_id)
            if user:
                user_id_to_save = user_id

        # 3. Рассчитываем стоимость
        input_cost = provider_response.input_tokens * model_config.input_price_per_1k / 1000
        output_cost = provider_response.output_tokens * model_config.output_price_per_1k / 1000
        total_cost = input_cost + output_cost

        # 4. Подготавливаем текст запроса
        input_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in messages])

        # 5. Хеш промпта
        prompt_hash = calculate_prompt_hash(messages)

        # 6. Получаем репозиторий запросов
        request_repo = get_repository("request", db)

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
        result = await request_repo.create_with_response(request_data, response_data)

        logger.info(f"Chat request saved via repository: {result['request_id']}")

        return result

    except Exception as e:
        logger.error(f"Database save error: {e}")
        raise


@router.post("", response_model=ChatResponse)
async def chat(
        request: ChatRequest,
        db: AsyncSession = Depends(get_db),
        provider_service: ProviderService = Depends(get_provider_service)
):
    """Основной chat endpoint с использованием ProviderService"""
    start_time = time.time()

    try:
        # 1. Проверяем, есть ли модель в реестре
        model_config = registry.get_model_config(request.model)
        if not model_config:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{request.model}' not found. Available models: {list(registry.models.keys())}"
            )

        # 2. Получаем провайдера для модели через фабрику из сервиса
        provider = provider_service.factory.get_provider_for_model(request.model)
        if not provider:
            raise HTTPException(
                status_code=503,
                detail=f"Provider for model '{request.model}' is not available. "
                       f"Possible reasons: API key not configured, provider is inactive, or network issue."
            )

        # 3. Конвертируем сообщения
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # 4. Отправляем запрос
        logger.info(f"Sending request to {provider.provider_name}, model: {request.model}")

        provider_response = await provider.chat_completion(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream
        )

        # 5. Сохраняем в БД
        save_result = await save_chat_to_database(
            db=db,
            messages=messages,
            model_name=request.model,
            temperature=request.temperature,
            provider_response=provider_response,
            user_id=request.user_id,
            max_tokens=request.max_tokens
        )

        total_time = int((time.time() - start_time) * 1000)

        # 6. Возвращаем ответ
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/providers")
async def list_providers(request: Request):
    """Получить список провайдеров и моделей"""
    # Проверяем, инициализирован ли сервис
    if not hasattr(request.app.state, 'provider_service') or not request.app.state.provider_service:
        raise HTTPException(
            status_code=503,
            detail="Provider service not initialized"
        )

    provider_service = request.app.state.provider_service
    status = provider_service.get_provider_status()

    return SuccessResponse(
        success=True,
        message="Providers list retrieved successfully",
        data={
            "providers": registry.list_providers(),
            "models": registry.list_models(),
            "status": status,
            "counts": {
                "providers": len(registry.providers),
                "models": len(registry.models),
                "cached_instances": len(provider_service.factory.get_cached_providers())
            }
        }
    )


@router.get("/models")
async def list_models():
    """Получить список моделей"""
    models = registry.list_models()
    return SuccessResponse(
        success=True,
        message="Models list retrieved successfully",
        data={
            "models": models,
            "count": len(models),
            "available_models": [model["name"] for model in models if model.get("is_available", True)]
        }
    )


@router.get("/health")
async def chat_health_check(request: Request):
    """Проверка здоровья системы чата"""
    try:
        # Проверяем, инициализирован ли сервис
        if not hasattr(request.app.state, 'provider_service') or not request.app.state.provider_service:
            return {
                "status": "degraded",
                "chat_service": "not_initialized",
                "database": "unknown",
                "providers": "not_loaded",
                "message": "Provider service not initialized. Database might be unavailable."
            }

        # Проверяем реестр
        registry_loaded = registry.is_loaded() if hasattr(registry, 'is_loaded') else True

        # Проверяем здоровье провайдеров (асинхронно)
        provider_service = request.app.state.provider_service
        health_results = await provider_service.health_check()

        healthy_count = sum(1 for v in health_results.values() if v)
        unhealthy_providers = [name for name, healthy in health_results.items() if not healthy]

        overall_status = "healthy" if healthy_count == len(health_results) else "degraded"

        return {
            "status": overall_status,
            "chat_service": "operational",
            "database": "connected" if registry_loaded else "disconnected",
            "providers": {
                "total": len(health_results),
                "healthy": healthy_count,
                "unhealthy": len(unhealthy_providers),
                "unhealthy_list": unhealthy_providers,
                "details": health_results
            },
            "cache_status": {
                "cached_providers": provider_service.factory.get_cached_providers(),
                "cache_size": len(provider_service.factory.get_cached_providers())
            }
        }

    except Exception as e:
        logger.error(f"Chat health check failed: {e}")
        return {
            "status": "unhealthy",
            "chat_service": "error",
            "database": "unknown",
            "providers": "error",
            "error": str(e)
        }


@router.get("/available-models")
async def get_available_models():
    """Получить только доступные модели"""
    models = registry.list_models()
    available_models = [
        {
            "name": model["name"],
            "provider": model["provider"],
            "context_window": model.get("context_window", 8192),
            "type": model.get("type", "text"),
            "pricing": {
                "input": model.get("input_price_per_1k", 0.0),
                "output": model.get("output_price_per_1k", 0.0)
            } if "input_price_per_1k" in model else None
        }
        for model in models if model.get("is_available", True)
    ]

    return {
        "success": True,
        "count": len(available_models),
        "models": available_models
    }