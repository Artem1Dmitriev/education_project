"""
Схемы для работы с провайдерами и моделями
"""
from typing import Optional
from uuid import UUID
from pydantic import Field, ConfigDict
from decimal import Decimal

from .base import BaseDTO, TimestampMixin, StatusMixin


# ============== PROVIDERS ==============
class ProviderBase(BaseDTO):
    """Базовая схема провайдера"""
    provider_name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Название провайдера"
    )
    base_url: str = Field(
        ...,
        description="Базовый URL API"
    )
    auth_type: str = Field(
        ...,
        description="Тип аутентификации"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider_name": "OpenAI",
                "base_url": "https://api.openai.com/v1",
                "auth_type": "Bearer"
            }
        }
    )


class ProviderCreate(ProviderBase):
    """Создание провайдера"""
    pass


class ProviderUpdate(BaseDTO):
    """Обновление провайдера"""
    provider_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        description="Название провайдера"
    )
    base_url: Optional[str] = Field(
        None,
        description="Базовый URL API"
    )
    auth_type: Optional[str] = Field(
        None,
        description="Тип аутентификации"
    )
    max_requests_per_minute: Optional[int] = Field(
        None,
        ge=1,
        description="Максимум запросов в минуту"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Активен ли провайдер"
    )


class ProviderResponse(ProviderBase, TimestampMixin, StatusMixin):
    """Полная информация о провайдере"""
    provider_id: UUID = Field(
        ...,
        description="ID провайдера"
    )
    max_requests_per_minute: int = Field(
        ...,
        description="Максимум запросов в минуту"
    )
    retry_count: int = Field(
        ...,
        description="Количество повторных попыток"
    )
    timeout_seconds: int = Field(
        ...,
        description="Таймаут в секундах"
    )
    model_count: Optional[int] = Field(
        None,
        description="Количество доступных моделей (вычисляемое поле)"
    )


# ============== MODELS ==============
class ModelBase(BaseDTO):
    """Базовая схема модели"""
    model_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Название модели"
    )
    model_type: str = Field(
        "text",
        description="Тип модели (text, vision, audio, multimodal)"
    )
    context_window: int = Field(
        ...,
        gt=0,
        description="Размер контекстного окна"
    )
    max_output_tokens: Optional[int] = Field(
        None,
        gt=0,
        description="Максимум токенов в ответе"
    )
    input_price_per_1k: Decimal = Field(
        ...,
        ge=0,
        description="Цена за 1000 входных токенов в USD"
    )
    output_price_per_1k: Decimal = Field(
        ...,
        ge=0,
        description="Цена за 1000 выходных токенов в USD"
    )
    supports_json_mode: bool = Field(
        False,
        description="Поддерживает ли JSON режим"
    )
    supports_function_calling: bool = Field(
        False,
        description="Поддерживает ли вызов функций"
    )


class ModelCreate(ModelBase):
    """Создание модели"""
    provider_id: UUID = Field(
        ...,
        description="ID провайдера"
    )


class ModelUpdate(BaseDTO):
    """Обновление модели"""
    model_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Название модели"
    )
    is_available: Optional[bool] = Field(
        None,
        description="Доступна ли модель"
    )
    input_price_per_1k: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Цена за 1000 входных токенов"
    )
    output_price_per_1k: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Цена за 1000 выходных токенов"
    )
    priority: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="Приоритет модели (1-10)"
    )


class ModelResponse(ModelBase, TimestampMixin, StatusMixin):
    """Полная информация о модели"""
    model_id: UUID = Field(
        ...,
        description="ID модели"
    )
    provider_id: UUID = Field(
        ...,
        description="ID провайдера"
    )
    provider_name: str = Field(
        ...,
        description="Название провайдера"
    )
    priority: int = Field(
        ...,
        description="Приоритет модели (1-10)"
    )