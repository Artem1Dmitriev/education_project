from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData
from app.core.config import settings

# Базовый класс для моделей (если будем использовать ORM)
Base = declarative_base()

# Метаданные для явного указания схемы
metadata = MetaData(schema="ai_framework")

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


# Утилита для проверки соединения
async def check_db_connection():
    """Проверка подключения к БД"""
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False