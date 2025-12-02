from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


# Базовые схемы
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    user_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Provider схемы
class ProviderBase(BaseModel):
    provider_name: str
    api_base_url: Optional[str] = None


class ProviderCreate(ProviderBase):
    pass


class ProviderUpdate(BaseModel):
    provider_name: Optional[str] = None
    api_base_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProviderInDB(ProviderBase):
    provider_id: UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# AI Model схемы
class ModelBase(BaseModel):
    model_name: str
    max_tokens: Optional[int] = None
    cost_per_input_token: Optional[float] = None
    cost_per_output_token: Optional[float] = None


class ModelCreate(ModelBase):
    provider_id: UUID


class ModelUpdate(BaseModel):
    model_name: Optional[str] = None
    max_tokens: Optional[int] = None
    cost_per_input_token: Optional[float] = None
    cost_per_output_token: Optional[float] = None
    is_available: Optional[bool] = None


class ModelInDB(ModelBase):
    model_id: UUID
    provider_id: UUID
    is_available: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Request схемы
class RequestBase(BaseModel):
    input_text: str
    model_id: UUID


class RequestCreate(RequestBase):
    user_id: Optional[UUID] = None


class RequestUpdate(BaseModel):
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_cost: Optional[float] = None
    status: Optional[str] = None
    response_timestamp: Optional[datetime] = None


class RequestInDB(RequestBase):
    request_id: UUID
    user_id: Optional[UUID]
    input_tokens: int
    output_tokens: int
    total_cost: float
    status: str
    request_timestamp: datetime
    response_timestamp: Optional[datetime]

    class Config:
        from_attributes = True


# Ответы API
class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


class DatabaseHealthResponse(BaseModel):
    status: str
    database: str
    check: bool
    error: Optional[str] = None