
from app .database .models import User 
from app .schemas import UserCreate ,UserUpdate 
from .base import BaseRepository 


class UserRepository (BaseRepository [User ,UserCreate ,UserUpdate ]):
    """Репозиторий для работы с пользователями"""

    async def get_by_email (self ,email :str ):
        """Получить пользователя по email"""
        return await self .get (email =email )

    async def get_active_users (self ):
        """Получить всех активных пользователей"""
        return await self .get_all (is_active =True )