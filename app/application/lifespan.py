# app/application/lifespan.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any
import logging
from app.database.session import create_db_engine_and_sessionmaker, check_db_connection
from fastapi import FastAPI

from app.application.config import settings
from app.core.providers import create_provider_service, create_registry
from app.core.chat import create_chat_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan контекст для управления жизненным циклом приложения"""
    logger.info("🚀 Starting AI Gateway Framework...")

    # 1. Создаем engine и фабрику сессий
    engine, async_session_maker = create_db_engine_and_sessionmaker()

    # 2. Проверяем подключение к БД
    await check_db_connection(engine)

    # Загружаем реестр из БД
    registry = create_registry()
    async with AsyncSession(engine) as db:
        await registry.load_from_database(db)

    app.state.engine = engine
    app.state.async_session_maker = async_session_maker

    await _initialize_providers(app, registry)
    await _initialize_chat()

    yield  # Приложение работает

    # При остановке
    logger.info("👋 Shutting down AI Gateway Framework...")
    await engine.dispose()
    if hasattr(app.state.provider_service, 'close'):
        await app.state.provider_service.close()
    if hasattr(app.state.chat_service, 'close'):
        await app.state.chat_service.close()


async def _initialize_providers(app: FastAPI, registry):
    """Инициализация системы провайдеров"""
    try:
        # Создаем сервис провайдеров с API ключами из настроек
        api_keys = {
            "OpenAI": settings.OPENAI_API_KEY,
            "Google Gemini": settings.GEMINI_API_KEY,
            "Anthropic": settings.ANTHROPIC_API_KEY,
            "HuggingFace": settings.HUGGINGFACE_API_KEY,
            "Cohere": settings.COHERE_API_KEY,
        }

        provider_service = create_provider_service(registry, api_keys)

        # Сохраняем сервис в состоянии приложения
        app.state.provider_service = provider_service

        # Проверяем доступность провайдеров (опционально)
        if settings.APP_DEBUG:
            await _check_provider_health(provider_service, api_keys)

    except Exception as e:
        logger.info(f"⚠️  Failed to initialize providers: {e}")
        logger.info("ℹ️  Continuing with basic functionality...")
        app.state.provider_service = None


async def _initialize_chat(app: FastAPI):
    """Инициализация системы чата"""
    try:
        chat_service = create_chat_service()

        # Сохраняем сервис в состоянии приложения
        app.state.chat_service = chat_service

    except Exception as e:
        logger.info(f"⚠️  Failed to initialize chat: {e}")
        logger.info("ℹ️  Continuing with basic functionality...")
        app.state.chat_service = None


async def _check_provider_health(provider_service, api_keys):
    """Проверка здоровья провайдеров (только в режиме отладки)"""
    print("🔍 Checking provider health (debug mode)...")
    health_results = await provider_service.health_check()

    for provider_name, is_healthy in health_results.items():
        status = "✅" if is_healthy else "❌"
        health_status = "healthy" if is_healthy else "unhealthy"
        print(f"   {status} {provider_name}: {health_status}")

        if not is_healthy:
            if api_keys.get(provider_name):
                print(f"     ⚠️  API key present but provider is unhealthy")
            else:
                print(f"     ⚠️  No API key configured")
