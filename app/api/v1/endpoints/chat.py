# app/api/v1/endpoints/chat.py
from datetime import datetime

from fastapi import APIRouter, Depends, BackgroundTasks
import logging

from app.database.session import get_db
from app.schemas import ChatRequest, ChatResponse, SuccessResponse
from app.application.deps import get_chat_service
from app.core.chat.service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(
        request: ChatRequest,
        background_tasks: BackgroundTasks,
        chat_service: ChatService = Depends(get_chat_service),
        db=Depends(get_db)
):
    """
    Основной chat endpoint

    Args:
        request: Запрос чата
        background_tasks: Фоновые задачи FastAPI
        chat_service: Сервис обработки чата
        db: Сессия БД

    Returns:
        ChatResponse
    """
    logger.info(f"Processing chat request for model: {request.model}")

    # Можно вынести сохранение в фоновую задачу для ускорения ответа
    response = await chat_service.process_chat_request(
        request=request,
        db=db,
        user_id=request.user_id
    )

    logger.info(f"Chat request completed: {response.request_id}")
    return response


@router.get("/providers", response_model=SuccessResponse)
async def list_providers(
        chat_service: ChatService = Depends(get_chat_service)
):
    """Получить список провайдеров"""
    from app.core.providers.registry import registry

    providers = registry.list_providers()
    models = registry.list_models()

    # Получаем статус провайдеров
    provider_status = {}
    if hasattr(chat_service.provider_service, 'get_provider_status'):
        provider_status = chat_service.provider_service.get_provider_status()

    return SuccessResponse(
        success=True,
        message="Providers retrieved successfully",
        data={
            "providers": providers,
            "models": models,
            "status": provider_status,
            "counts": {
                "total_providers": len(providers),
                "total_models": len(models),
                "available_models": len([m for m in models if m.get("is_available", True)])
            }
        }
    )


@router.get("/models", response_model=SuccessResponse)
async def list_models():
    """Получить список моделей"""
    from app.core.providers.registry import registry

    models = registry.list_models()
    available_models = [
        model for model in models
        if model.get("is_available", True)
    ]

    return SuccessResponse(
        success=True,
        message="Models retrieved successfully",
        data={
            "total_models": len(models),
            "available_models": len(available_models),
            "models": models,
            "available": available_models
        }
    )


@router.get("/health")
async def chat_health_check(
        chat_service: ChatService = Depends(get_chat_service)
):
    """Проверка здоровья системы чата"""
    try:
        # Проверяем различные компоненты системы
        health_checks = {}

        # Проверка провайдеров
        if hasattr(chat_service.provider_service, 'health_check'):
            provider_health = await chat_service.provider_service.health_check()
            health_checks["providers"] = provider_health

        # Проверка репозиториев
        health_checks["repositories"] = {
            "request_repo": chat_service.request_repo is not None,
            "user_repo": chat_service.user_repo is not None
        }

        # Агрегируем статус
        all_healthy = all(
            all(v.values()) if isinstance(v, dict) else v
            for v in health_checks.values()
        )

        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": health_checks
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/available-models", response_model=SuccessResponse)
async def get_available_models():
    """Получить только доступные модели"""
    from app.core.providers.registry import registry

    models = registry.list_models()
    available_models = [
        {
            "name": model["name"],
            "provider": model["provider"],
            "context_window": model.get("context_window", 8192),
            "type": model.get("type", "text"),
            "supports_streaming": model.get("supports_streaming", False),
            "pricing": {
                "input": model.get("input_price_per_1k", 0.0),
                "output": model.get("output_price_per_1k", 0.0)
            } if "input_price_per_1k" in model else None,
            "rate_limits": model.get("rate_limits", {})
        }
        for model in models if model.get("is_available", True)
    ]

    return SuccessResponse(
        success=True,
        message="Available models retrieved successfully",
        data={
            "count": len(available_models),
            "models": available_models
        }
    )