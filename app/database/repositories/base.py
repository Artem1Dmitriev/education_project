# app/database/repositories/base.py
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.sql import text
from pydantic import BaseModel
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Базовый репозиторий с CRUD операциями"""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get(self, **filters) -> Optional[ModelType]:
        """Получить одну запись по фильтрам"""
        try:
            query = select(self.model)

            conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    column = getattr(self.model, key)
                    conditions.append(column == value)

            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error in get: {e}")
            return None

    async def get_by_id(self, id: Union[int, str, UUID]) -> Optional[ModelType]:
        """Получить запись по первичному ключу"""
        try:
            primary_key = None
            for column in self.model.__table__.columns:
                if column.primary_key:
                    primary_key = column.name
                    break

            if not primary_key:
                raise ValueError(f"Model {self.model.__name__} has no primary key")

            return await self.get(**{primary_key: id})
        except Exception as e:
            logger.error(f"Error in get_by_id: {e}")
            return None

    async def get_all(
            self,
            skip: int = 0,
            limit: int = 100,
            order_by: str = None,
            desc: bool = False,
            **filters
    ) -> List[ModelType]:
        """Получить все записи с фильтрацией"""
        try:
            query = select(self.model)

            for key, value in filters.items():
                if hasattr(self.model, key):
                    column = getattr(self.model, key)
                    if isinstance(value, (list, tuple)):
                        query = query.where(column.in_(value))
                    else:
                        query = query.where(column == value)

            if order_by and hasattr(self.model, order_by):
                column = getattr(self.model, order_by)
                query = query.order_by(column.desc() if desc else column.asc())

            if limit:
                query = query.limit(limit)
            if skip:
                query = query.offset(skip)

            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error in get_all: {e}")
            return []

    async def count(self, **filters) -> int:
        """Посчитать количество записей по фильтрам"""
        try:
            query = select(self.model)

            for key, value in filters.items():
                if hasattr(self.model, key):
                    column = getattr(self.model, key)
                    query = query.where(column == value)

            result = await self.session.execute(query)
            return len(result.scalars().all())
        except Exception as e:
            logger.error(f"Error in count: {e}")
            return 0

    async def create(self, obj_in: CreateSchemaType) -> Optional[ModelType]:
        """Создать новую запись"""
        try:
            db_obj = self.model(**obj_in.dict())
            self.session.add(db_obj)
            await self.session.commit()
            await self.session.refresh(db_obj)
            return db_obj
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in create: {e}")
            return None

    async def create_many(self, objects: List[CreateSchemaType]) -> List[ModelType]:
        """Создать несколько записей"""
        try:
            db_objs = [self.model(**obj.dict()) for obj in objects]
            self.session.add_all(db_objs)
            await self.session.commit()

            for obj in db_objs:
                await self.session.refresh(obj)

            return db_objs
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in create_many: {e}")
            return []

    async def update(
            self,
            obj_id: Union[int, str, UUID],
            obj_in: UpdateSchemaType
    ) -> Optional[ModelType]:
        """Обновить запись"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                return None

            update_data = obj_in.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(obj, field):
                    setattr(obj, field, value)

            await self.session.commit()
            await self.session.refresh(obj)
            return obj
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in update: {e}")
            return None

    async def delete(self, obj_id: Union[int, str, UUID]) -> bool:
        """Удалить запись"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                return False

            await self.session.delete(obj)
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in delete: {e}")
            return False

    async def delete_many(self, **filters) -> int:
        """Удалить несколько записей по фильтрам"""
        try:
            query = delete(self.model)

            conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    column = getattr(self.model, key)
                    conditions.append(column == value)

            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            await self.session.commit()
            return result.rowcount
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in delete_many: {e}")
            return 0

    async def raw_query(self, sql: str, params: Dict = None) -> List[Dict]:
        """Выполнить сырой SQL запрос"""
        try:
            result = await self.session.execute(text(sql), params or {})
            return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Error in raw_query: {e}")
            return []

    async def exists(self, **filters) -> bool:
        """Проверить существование записи"""
        obj = await self.get(**filters)
        return obj is not None

    async def begin_transaction(self):
        """Начать транзакцию"""
        await self.session.begin()

    async def commit_transaction(self):
        """Зафиксировать транзакцию"""
        await self.session.commit()

    async def rollback_transaction(self):
        """Откатить транзакцию"""
        await self.session.rollback()