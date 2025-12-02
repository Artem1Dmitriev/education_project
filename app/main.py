from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import uvicorn

from app.core.config import settings
from app.api.v1.endpoints import health
from app.database.session import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan контекст для управления жизненным циклом приложения"""
    # При запуске
    print("🚀 Starting AI Gateway Framework...")

    # Проверяем подключение к БД
    try:
        async with engine.connect() as conn:
            # Используем text() для SQL-запросов в SQLAlchemy 2.0
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

    yield

    # При остановке
    print("👋 Shutting down AI Gateway Framework...")
    await engine.dispose()


# Создаем экземпляр FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Фреймворк для управления нейросетевыми моделями",
    docs_url="/docs" if settings.APP_DEBUG else None,
    redoc_url="/redoc" if settings.APP_DEBUG else None,
    lifespan=lifespan,
)

# Настраиваем CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Подключаем роутеры
app.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["health"])


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "Welcome to AI Gateway Framework",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else None,
    }


def run():
    """Функция для запуска через poetry scripts"""
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    run()