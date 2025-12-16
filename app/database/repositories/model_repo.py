
from app .database .models import AIModel 
from app .schemas import ModelCreate ,ModelUpdate 
from .base import BaseRepository 


class ModelRepository (BaseRepository [AIModel ,ModelCreate ,ModelUpdate ]):
    """Репозиторий для работы с AI моделями"""

    async def get_by_provider (self ,provider_id :str ):
        """Получить модели по ID провайдера"""
        return await self .get_all (provider_id =provider_id )

    async def get_available_models (self ):
        """Получить все доступные модели"""
        return await self .get_all (is_available =True )

    async def get_by_name (self ,model_name :str ):
        """Получить модель по имени"""
        return await self .get (model_name =model_name )