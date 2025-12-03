# app/database/repositories/__init__.py
from .base import BaseRepository
from app.database.models import User, Provider, AIModel, Request
from app.api.v1.schemas import (
    UserCreate, UserUpdate,
    ProviderCreate, ProviderUpdate,
    ModelCreate, ModelUpdate,
    RequestCreate, RequestUpdate
)


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """Репозиторий для пользователей"""
    pass


class ProviderRepository(BaseRepository[Provider, ProviderCreate, ProviderUpdate]):
    """Репозиторий для провайдеров"""
    pass


class ModelRepository(BaseRepository[AIModel, ModelCreate, ModelUpdate]):
    """Репозиторий для AI моделей"""
    pass


class RequestRepository(BaseRepository[Request, RequestCreate, RequestUpdate]):
    """Репозиторий для запросов"""

    async def get_user_requests(self, user_id: str, limit: int = 50):
        """Получить запросы пользователя"""
        return await self.get_all(
            user_id=user_id,
            limit=limit,
            order_by="request_timestamp",
            desc=True
        )

    async def get_total_cost_by_user(self, user_id: str) -> float:
        """Получить общую стоимость запросов пользователя"""
        sql = """
        SELECT COALESCE(SUM(total_cost), 0) as total
        FROM ai_framework.requests
        WHERE user_id = :user_id
        """
        result = await self.raw_query(sql, {"user_id": user_id})
        return float(result[0]["total"]) if result else 0.0


# Фабрика для создания репозиториев
def get_repository(
        model_type: str,
        session
):
    """Фабрика для получения репозитория по типу модели"""
    repositories = {
        "user": UserRepository,
        "provider": ProviderRepository,
        "model": ModelRepository,
        "request": RequestRepository,
    }

    models = {
        "user": User,
        "provider": Provider,
        "model": AIModel,
        "request": Request,
    }

    if model_type not in repositories:
        raise ValueError(f"Unknown model type: {model_type}")

    return repositories[model_type](models[model_type], session)