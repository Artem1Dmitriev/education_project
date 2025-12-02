from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


# Асинхронный движок для работы с БД
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.APP_DEBUG,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """Dependency для получения асинхронной сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()