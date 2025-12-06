# app/core/exceptions/middleware.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging
import traceback

from app.core.exceptions.base import BaseAPIException

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next):
    """
    Middleware для обработки ошибок
    """
    try:
        response = await call_next(request)
        return response

    except BaseAPIException as exc:
        # Обработка наших кастомных исключений
        logger.warning(f"API Exception: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.detail,
                    "details": exc.extra
                }
            }
        )

    except HTTPException as exc:
        # Обработка стандартных HTTP исключений FastAPI
        logger.warning(f"HTTP Exception: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"message": exc.detail}}
        )

    except Exception as exc:
        # Обработка неожиданных ошибок
        logger.error(f"Unexpected error: {str(exc)}")
        logger.error(traceback.format_exc())

        # В продакшене скрываем детали ошибок
        if request.app.debug:
            detail = f"{type(exc).__name__}: {str(exc)}"
        else:
            detail = "Internal server error"

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": detail
                }
            }
        )