# app/api/handlers/root.py
from fastapi import APIRouter, Request
from app.application.config import settings
from app.database.session import check_db_connection

router = APIRouter(tags=["root"])


@router.get("/")
async def root(request: Request):
    """Корневой endpoint"""
    db_connected = await check_db_connection()

    # Проверяем состояние провайдеров
    providers_status = "not_initialized"
    if hasattr(request.app.state, 'provider_registry') and request.app.state.provider_registry:
        providers_status = f"loaded ({len(request.app.state.provider_registry.providers)} providers)"

    return {
        "message": "Welcome to AI Gateway Framework",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "database": {
            "schema": "ai_framework",
            "status": "connected" if db_connected else "disconnected",
            "connection": "healthy" if db_connected else "unhealthy"
        },
        "providers": {
            "status": providers_status,
            "api": f"{settings.API_V1_PREFIX}/chat/providers"
        },
        "documentation": {
            "swagger": "/docs" if settings.APP_DEBUG else "disabled",
            "redoc": "/redoc" if settings.APP_DEBUG else "disabled",
            "api_spec": "/openapi.json"
        },
        "endpoints": [
            f"{settings.API_V1_PREFIX}/health",
            f"{settings.API_V1_PREFIX}/chat",
            f"{settings.API_V1_PREFIX}/users",
        ]
    }


@router.get("/api")
async def api_info(request: Request):
    """Информация о API"""
    return {
        "api_version": "v1",
        "prefix": settings.API_V1_PREFIX,
        "available_endpoints": {
            "health": [
                "GET /api/v1/health",
                "GET /api/v1/health/db",
                "GET /api/v1/health/tables",
                "GET /api/v1/health/providers" if hasattr(request.app.state,
                                                          'provider_service') and request.app.state.provider_service else None,
            ],
            "users": [
                "GET /api/v1/users",
                "POST /api/v1/users",
                "GET /api/v1/users/{user_id}",
                "GET /api/v1/users/{user_id}/requests",
                "GET /api/v1/users/{user_id}/stats",
            ],
            "chat": [
                "POST /api/v1/chat",
                "GET /api/v1/chat/providers",
                "GET /api/v1/chat/models",
            ]
        }
    }