# app/api/deps.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, FastAPI, HTTPException, Request

from app.core.chat import ChatService
from app.core.providers import ProviderService
from app.database.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения асинхронной сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Dependency для получения сервиса провайдеров
async def get_provider_service(request: Request) -> ProviderService:
    """Получить сервис провайдеров из состояния приложения"""
    service = request.app.state.provider_service
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Provider service not initialized. "
                   "Please check if database is connected and providers are loaded."
        )
    return service


# Dependency для получения ChatService
async def get_chat_service(
    db: AsyncSession = Depends(get_db),
    provider_service: ProviderService = Depends(get_provider_service)
) -> ChatService:
    """Получить ChatService с инъекцией зависимостей"""
    return ChatService(db=db, provider_service=provider_service)