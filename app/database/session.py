# app/database/session.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.application.config import settings

# Базовый класс для моделей
Base = declarative_base()


# Создаем engine и фабрику сессий
def create_db_engine_and_sessionmaker():
    """Создание engine и фабрики сессий (вызывается в lifespan)"""

    engine_args = {
        "echo": settings.APP_DEBUG,
        "pool_pre_ping": True,
        "connect_args": {
            "server_settings": {
                "jit": "off",
                "application_name": "ai_gateway_framework"
            }
        }
    }

    if not settings.APP_DEBUG:
        engine_args.update({
            "pool_size": 20,
            "max_overflow": 30,
        })
    else:
        engine_args["poolclass"] = NullPool

    engine = create_async_engine(str(settings.DATABASE_URL), **engine_args)

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    return engine, async_session_maker


async def check_db_connection(engine):
    """Проверка подключения к БД"""
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.schemata 
                    WHERE schema_name = 'ai_framework'
                )
            """))
            schema_exists = result.scalar()

            if not schema_exists:
                print("⚠️  Schema 'ai_framework' not found")
                return False
            else:
                print("✅ Schema 'ai_framework' exists")
                return True
    except Exception as e:
        print(f"⚠️  Database connection failed: {e}")
        return False