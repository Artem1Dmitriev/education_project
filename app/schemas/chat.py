"""
Схемы для работы с чатом
"""
from typing import List, Optional
from uuid import UUID
from pydantic import Field, ConfigDict
from datetime import datetime

from .base import BaseDTO


class ChatMessage(BaseDTO):
    """Сообщение в чате"""
    role: str = Field(
        ...,
        pattern="^(system|user|assistant)$",
        description="Роль отправителя"
    )
    content: str = Field(
        ...,
        description="Содержание сообщения"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "user",
                "content": "Привет! Как дела?"
            }
        }
    )


class ChatRequest(BaseDTO):
    """Запрос на обработку чата"""
    messages: List[ChatMessage] = Field(
        ...,
        min_items=1,
        description="Список сообщений"
    )
    model: str = Field(
        "gpt-4o",
        description="Модель для использования"
    )
    temperature: float = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Креативность ответа"
    )
    max_tokens: Optional[int] = Field(
        None,
        gt=0,
        description="Максимальное количество токенов в ответе"
    )
    stream: bool = Field(
        False,
        description="Использовать streaming"
    )
    user_id: Optional[UUID] = Field(
        None,
        description="ID пользователя (если авторизован)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "messages": [
                    {"role": "user", "content": "Привет!"}
                ],
                "model": "gpt-4o",
                "temperature": 0.7
            }
        }
    )


class ChatResponse(BaseDTO):
    """Ответ от чата"""
    response_id: UUID = Field(
        ...,
        description="ID ответа"
    )
    request_id: UUID = Field(
        ...,
        description="ID запроса"
    )
    content: str = Field(
        ...,
        description="Текст ответа"
    )
    model_used: str = Field(
        ...,
        description="Использованная модель"
    )
    provider_used: str = Field(
        ...,
        description="Использованный провайдер"
    )
    input_tokens: int = Field(
        ...,
        ge=0,
        description="Потрачено токенов на вход"
    )
    output_tokens: int = Field(
        ...,
        ge=0,
        description="Потрачено токенов на выход"
    )
    total_cost: float = Field(
        ...,
        ge=0,
        description="Общая стоимость в USD"
    )
    processing_time_ms: int = Field(
        ...,
        ge=0,
        description="Время обработки в миллисекундах"
    )
    timestamp: datetime = Field(
        ...,
        description="Время создания ответа"
    )
    finish_reason: Optional[str] = Field(
        None,
        description="Причина завершения"
    )
    is_cached: bool = Field(
        False,
        description="Был ли ответ получен из кэша"
    )