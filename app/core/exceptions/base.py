# app/core/exceptions/base.py
from fastapi import HTTPException
from typing import Any, Dict, Optional

class BaseAPIException(HTTPException):
    """Базовое исключение API"""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.extra = extra or {}