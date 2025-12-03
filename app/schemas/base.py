"""
Базовые схемы для всех DTO в приложении
"""
from datetime import datetime
from typing import Optional, Generic, TypeVar
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from pydantic.generics import GenericModel


# Типы для generic схем
T = TypeVar('T')


class BaseDTO(BaseModel):
    """Базовый DTO с общими полями"""
    model_config = ConfigDict(
        from_attributes=True,          # Поддержка ORM
        populate_by_name=True,         # Разрешить alias
        arbitrary_types_allowed=True,
    )

    id: Optional[UUID] = Field(None, alias="id", description="Уникальный идентификатор")


class TimestampMixin(BaseModel):
    """Миксин для временных меток"""
    created_at: Optional[datetime] = Field(
        None, 
        description="Дата создания"
    )
    updated_at: Optional[datetime] = Field(
        None, 
        description="Дата последнего обновления"
    )
    deleted_at: Optional[datetime] = Field(
        None, 
        description="Дата удаления (soft delete)"
    )


class StatusMixin(BaseModel):
    """Миксин для статусов"""
    is_active: bool = Field(
        True, 
        description="Активен ли объект"
    )
    status: Optional[str] = Field(
        None, 
        description="Дополнительный статус"
    )


class PaginationParams(BaseModel):
    """Параметры пагинации"""
    skip: int = Field(0, ge=0, description="Сколько записей пропустить")
    limit: int = Field(100, ge=1, le=1000, description="Сколько записей вернуть")


class PaginatedResponse(GenericModel, Generic[T]):
    """Пагинированный ответ"""
    items: list[T] = Field(..., description="Список элементов")
    total: int = Field(..., description="Общее количество элементов")
    page: int = Field(..., description="Текущая страница")
    pages: int = Field(..., description="Всего страниц")
    has_next: bool = Field(..., description="Есть следующая страница")
    has_prev: bool = Field(..., description="Есть предыдущая страница")


class SuccessResponse(BaseModel):
    """Успешный ответ API"""
    success: bool = Field(True, description="Успешность операции")
    message: Optional[str] = Field(None, description="Сообщение")
    data: Optional[dict] = Field(None, description="Данные ответа")


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    success: bool = Field(False, description="Успешность операции")
    error_code: str = Field(..., description="Код ошибки")
    error_message: str = Field(..., description="Сообщение об ошибке")
    details: Optional[dict] = Field(None, description="Детали ошибки")