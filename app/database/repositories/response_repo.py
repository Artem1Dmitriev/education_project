from app.database.models import Response
from app.schemas import ResponseCreate, ResponseUpdate
from .base import BaseRepository


class ResponseRepository(BaseRepository[Response, ResponseCreate, ResponseUpdate]):
    """Репозиторий для работы с ответами"""

    async def get_by_request_id(self, request_id: str):
        """Получить ответ по ID запроса"""
        return await self.get(request_id=request_id)

    async def get_cached_responses(self, limit: int = 100):
        """Получить кешированные ответы"""
        return await self.get_all(is_cached=True, limit=limit)

    async def mark_as_cached(self, response_id: str) -> bool:
        """Пометить ответ как кешированный"""
        sql = """
        UPDATE ai_framework.responses
        SET is_cached = true
        WHERE response_id = :response_id
        """
        try:
            await self.session.execute(text(sql), {"response_id": response_id})
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            return False