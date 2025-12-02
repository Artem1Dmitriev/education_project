from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Базовый класс для моделей
Base = declarative_base()

# Параметры для create_async_engine
engine_args = {
    "echo": settings.APP_DEBUG,
    "pool_pre_ping": True,
    "connect_args": {
        "server_settings": {
            "jit": "off",  # Выключаем JIT для лучшей производительности
            "application_name": "ai_gateway_framework"
        }
    }
}

# Если не в режиме отладки, добавляем параметры пула
if not settings.APP_DEBUG:
    engine_args.update({
        "pool_size": 20,
        "max_overflow": 30,
    })
else:
    engine_args["poolclass"] = NullPool

# Асинхронный движок для работы с БД
engine = create_async_engine(str(settings.DATABASE_URL), **engine_args)

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


async def check_db_connection():
    """Проверка подключения к БД"""
    try:
        from sqlalchemy import text  # Локальный импорт
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False