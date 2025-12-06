# app/application/deps.py
from typing import AsyncGenerator
from fastapi import Depends, Request as FastAPIRequest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chat.factory import ChatServiceFactory
from app.core.chat.prompt.service import PromptService
from app.core.chat.service import ChatService
from app.core.providers import ProviderService
from app.database.repositories import RequestRepository, UserRepository
from app.core.chat.calculation import CostCalculator
from app.core.chat.calculation import TokenizerService


async def get_db(request: FastAPIRequest) -> AsyncGenerator[AsyncSession, None]:
    """
    Получение сессии БД для запроса.
    Использует фабрику сессий из app.state.
    """
    async_session_maker = request.app.state.async_session_maker

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_provider_service(request: FastAPIRequest):
    return request.app.state.provider_service


async def get_chat_service(
        request: FastAPIRequest,
        db: AsyncSession = Depends(get_db)
) -> ChatService:

    factory = getattr(request.app.state, 'chat_service_factory', None)
    if not factory:
        factory = ChatServiceFactory()
        setattr(request.app.state, 'chat_service_factory', factory)

    provider_service = await get_provider_service(request)

    return factory.create_service(
        provider_service=provider_service,
        session=db
    )
