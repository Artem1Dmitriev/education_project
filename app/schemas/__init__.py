"""
Экспорт всех схем (DTO) приложения
"""
from .base import (
    BaseDTO,
    TimestampMixin,
    StatusMixin,
    PaginationParams,
    PaginatedResponse,
    SuccessResponse,
    ErrorResponse,
)
from .users import *
from .chat import *
from .providers import *
from .requests import *
from .health import *
from .responses import *
# Для обратной совместимости - экспорт всех классов
__all__ = [
    # Базовые
    'BaseDTO',
    'TimestampMixin', 
    'StatusMixin',
    'PaginationParams',
    'PaginatedResponse',
    'SuccessResponse',
    'ErrorResponse',
    # Users
    'UserCreate',
    'UserUpdate', 
    'UserResponse',
    'UserListResponse',
    # Chat
    'ChatMessage',
    'ChatRequest',
    'ChatResponse',
    # Providers
    'ProviderCreate',
    'ProviderUpdate',
    'ProviderResponse',
    'ModelCreate',
    'ModelUpdate', 
    'ModelResponse',
    # Requests
    'RequestCreate',
    'RequestUpdate',
    'RequestResponse',
    'RequestStats',
    # Health
    'HealthCheckResponse',
    'DatabaseHealthResponse',
    'TableHealthResponse',
    # Responses
    'ResponseBase',
    'ResponseCreate',
    'ResponseUpdate',
    'ResponseResponse'
]