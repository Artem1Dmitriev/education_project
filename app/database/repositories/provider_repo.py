# app/database/repositories/provider.py
from app.database.models import Provider
from app.schemas import ProviderCreate, ProviderUpdate
from .base import BaseRepository


class ProviderRepository(BaseRepository[Provider, ProviderCreate, ProviderUpdate]):
    """Репозиторий для работы с провайдерами"""

    async def get_active_providers(self):
        """Получить всех активных провайдеров"""
        return await self.get_all(is_active=True)

    async def get_by_name(self, name: str):
        """Получить провайдера по имени"""
        return await self.get(provider_name=name)