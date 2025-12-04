# app/database/repositories/request.py
from sqlalchemy import text
from app.database.models import Request, Response
from app.schemas import RequestCreate, RequestUpdate
from .base import BaseRepository
import uuid


class RequestRepository(BaseRepository[Request, RequestCreate, RequestUpdate]):
    """Репозиторий для работы с запросами"""

    async def create_with_response(
            self,
            request_data: dict,
            response_data: dict
    ) -> dict:
        """
        Создать запрос и ответ вместе в одной транзакции
        """
        try:
            request_id = request_data.get('request_id')
            if not request_id:
                request_id = uuid.uuid4()
                request_data['request_id'] = request_id

            response_id = response_data.get('response_id')
            if not response_id:
                response_id = uuid.uuid4()
                response_data['response_id'] = response_id

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
                "processing_time_ms": request_data.get('processing_time', 0),
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

    async def get_requests_with_responses(self, limit: int = 100):
        """Получить запросы с ответами"""
        sql = """
        SELECT 
            r.request_id,
            r.user_id,
            r.model_id,
            r.input_tokens,
            r.output_tokens,
            r.total_cost,
            r.request_timestamp,
            resp.content as response_content,
            resp.model_used,
            resp.provider_used
        FROM ai_framework.requests r
        JOIN ai_framework.responses resp ON r.request_id = resp.request_id
        ORDER BY r.request_timestamp DESC
        LIMIT :limit
        """
        return await self.raw_query(sql, {"limit": limit})