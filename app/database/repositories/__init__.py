# app/database/repositories/__init__.py
from .base import BaseRepository
from app.database.models import User, Provider, AIModel, Request, Response
from app.schemas import (
    UserCreate, UserUpdate,
    ProviderCreate, ProviderUpdate,
    ModelCreate, ModelUpdate,
    RequestCreate, RequestUpdate,
    ResponseCreate, ResponseUpdate
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

    async def create_with_response(
            self,
            request_data: dict,
            response_data: dict
    ) -> dict:
        """
        Создать запрос и ответ вместе в одной транзакции
        Возвращает dict с request_id, response_id и другими данными
        """
        from sqlalchemy import text

        try:
            # Используем прямой SQL для вставки обоих записей
            # Это позволяет избежать лишних ORM операций
            request_id = request_data.get('request_id')
            response_id = request_data.get('response_id', None)

            if not response_id:
                import uuid
                response_id = uuid.uuid4()

            # Вставляем запрос
            request_sql = """
            INSERT INTO ai_framework.requests 
            (request_id, user_id, model_id, prompt_hash, input_text,
             input_tokens, output_tokens, total_cost, temperature,
             max_tokens, status, request_timestamp, processing_time_ms,
             endpoint_called)
            VALUES 
            (:request_id, :user_id, :model_id, :prompt_hash, :input_text,
             :input_tokens, :output_tokens, :total_cost, :temperature,
             :max_tokens, 'completed', :timestamp, :processing_time, :endpoint)
            RETURNING request_id
            """

            request_result = await self.session.execute(
                text(request_sql),
                request_data
            )
            request_id = request_result.scalar()

            # Вставляем ответ
            response_sql = """
            INSERT INTO ai_framework.responses 
            (response_id, request_id, content, finish_reason,
             model_used, provider_used, response_timestamp, is_cached)
            VALUES 
            (:response_id, :request_id, :content, :finish_reason,
             :model_used, :provider_used, :timestamp, false)
            RETURNING response_id
            """

            response_data['request_id'] = request_id
            response_data['response_id'] = response_id

            response_result = await self.session.execute(
                text(response_sql),
                response_data
            )
            response_id = response_result.scalar()

            await self.session.commit()

            return {
                "request_id": request_id,
                "response_id": response_id,
                "processing_time_ms": request_data.get('processing_time_ms', 0),
                "total_cost": request_data.get('total_cost', 0)
            }

        except Exception as e:
            await self.session.rollback()
            raise e

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


class ResponseRepository(BaseRepository[Response, ResponseCreate, ResponseUpdate]):
    """Репозиторий для ответов"""

    async def get_by_request_id(self, request_id: str):
        """Получить ответ по ID запроса"""
        return await self.get(request_id=request_id)


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
        "response": ResponseRepository,
    }

    models = {
        "user": User,
        "provider": Provider,
        "model": AIModel,
        "request": Request,
        "response": Response,
    }

    if model_type not in repositories:
        raise ValueError(f"Unknown model type: {model_type}")

    return repositories[model_type](models[model_type], session)