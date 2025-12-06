# app/core/exceptions/chat.py
from typing import Any, Dict, Optional
from fastapi import HTTPException
from app.core.exceptions.base import BaseAPIException


class ChatException(BaseAPIException):
    """Исключения, связанные с чатом"""
    pass


class ValidationError(ChatException):
    """Ошибка валидации"""
    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="VALIDATION_ERROR",
            extra={"field": field} if field else {}
        )


class ModelNotFoundException(ChatException):
    """Модель не найдена"""
    def __init__(self, model_name: str):
        super().__init__(
            status_code=404,
            detail=f"Model '{model_name}' not found",
            error_code="MODEL_NOT_FOUND",
            extra={"model_name": model_name}
        )


class ProviderUnavailableException(ChatException):
    """Провайдер недоступен"""
    def __init__(self, provider_name: str, model_name: str, reason: str = ""):
        detail = f"Provider '{provider_name}' for model '{model_name}' is unavailable"
        if reason:
            detail += f": {reason}"
        super().__init__(
            status_code=503,
            detail=detail,
            error_code="PROVIDER_UNAVAILABLE",
            extra={"provider": provider_name, "model": model_name}
        )


class RateLimitException(ChatException):
    """Превышен лимит запросов"""
    def __init__(self, provider_name: str, retry_after: Optional[int] = None):
        extra = {"provider": provider_name}
        if retry_after:
            extra["retry_after"] = retry_after
        super().__init__(
            status_code=429,
            detail=f"Rate limit exceeded for provider '{provider_name}'",
            error_code="RATE_LIMIT_EXCEEDED",
            extra=extra
        )


class ContextLengthExceededException(ChatException):
    """Превышена длина контекста"""
    def __init__(self, model_name: str, max_tokens: int, requested: int):
        super().__init__(
            status_code=400,
            detail=f"Context length exceeded for model '{model_name}'. "
                   f"Max: {max_tokens}, Requested: {requested}",
            error_code="CONTEXT_LENGTH_EXCEEDED",
            extra={
                "model": model_name,
                "max_tokens": max_tokens,
                "requested_tokens": requested
            }
        )