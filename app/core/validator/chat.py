# app/core/validator/chat.py
import logging
from typing import Optional, Dict, Any
from uuid import UUID

from app.application.config import chat_settings
from app.core.exceptions.chat import ValidationError
from app.schemas import ChatRequest

logger = logging.getLogger(__name__)


class ChatValidator:
    """Сервис для работы с промптами"""

    def __init__(
            self,
            request_repo,
            user_repo,
    ):
        self.request_repo = request_repo
        self.user_repo = user_repo

    async def validate_user(
            self,
            user_id: Optional[UUID],
    ) -> Optional[Dict[str, Any]]:
        """Валидация пользователя"""
        if not user_id:
            return None

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"User {user_id} not found, but continuing without user")
            return None

        # Здесь можно добавить проверку лимитов пользователя

        return user.to_dict() if hasattr(user, 'to_dict') else dict(user)

    def validate_request(self, request: ChatRequest) -> None:
        """Валидация входящего запроса"""
        if not request.messages:
            raise ValidationError("Messages cannot be empty")

        if len(request.messages) > chat_settings.MAX_MESSAGES:
            raise ValidationError(
                f"Too many messages (max {chat_settings.MAX_MESSAGES})"
            )

        for i, msg in enumerate(request.messages):
            if len(msg.content) > chat_settings.MAX_MESSAGE_LENGTH:
                raise ValidationError(
                    f"Message {i + 1} too long (max {chat_settings.MAX_MESSAGE_LENGTH} chars)",
                    field=f"messages[{i}].content"
                )

        if request.temperature is not None:
            if not (chat_settings.MIN_TEMPERATURE <= request.temperature <= chat_settings.MAX_TEMPERATURE):
                raise ValidationError(
                    f"Temperature must be between {chat_settings.MIN_TEMPERATURE} and {chat_settings.MAX_TEMPERATURE}"
                )
