# app/api/v1/endpoints/__init__.py
# from .chat import router as chat_router
from .health import router as health_router
from .users import router as users_router
from .chat_simple import router as chat_router


__all__ = ["chat_router", "health_router", "users_router"]