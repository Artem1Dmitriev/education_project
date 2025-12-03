# app/api/v1/schemas/base.py
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class BaseSchema(BaseModel):
    """Базовая схема с общими полями"""
    id: Optional[UUID] = Field(None, alias="id")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class StatusMixin(BaseModel):
    """Миксин для статусных полей"""
    is_active: bool = True
    status: Optional[str] = None


class TimestampMixin(BaseModel):
    """Миксин для временных меток"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None