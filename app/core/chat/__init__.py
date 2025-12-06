# app/core/chat/__init__.py
from app.core.chat.service import ChatService
from app.core.chat.service import ChatService


def create_chat_service() -> ChatService:
    """Создать сервис провайдеров"""

    factory = ProviderFactory(registry, api_keys)
    return ProviderService(registry, factory)


__all__ = ["ChatService"]