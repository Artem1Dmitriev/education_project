from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import uvicorn
from app.core.config import settings
from app.database.session import engine, check_db_connection
from app.api.v1.endpoints import health, users
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan контекст для управления жизненным циклом приложения"""
    # При запуске
    print("🚀 Starting AI Gateway Framework...")

    # Проверяем подключение к БД
    try:
        if not await check_db_connection():
            print("⚠️  Database connection failed. Please check your database configuration.")
        else:
            print("✅ Database connection successful")

            # Проверяем существование схемы
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
                    print(
                        "⚠️  Schema 'ai_framework' not found. You need to run: python scripts/create_database_structure.py")
                else:
                    print("✅ Schema 'ai_framework' exists")

                    # Проверяем основные таблицы
                    result = await conn.execute(
                        text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'ai_framework'"))
                    table_count = result.scalar()
                    print(f"📊 Found {table_count} tables in ai_framework schema")

    except Exception as e:
        print(f"❌ Error checking database: {e}")

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
app.include_router(health_router, prefix=settings.API_V1_PREFIX, tags=["health"])
app.include_router(users_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "Welcome to AI Gateway Framework",
        "version": settings.APP_VERSION,
        "database": {
            "schema": "ai_framework",
            "tables": 11,
            "status": "connected" if await check_db_connection() else "disconnected"
        },
        "docs": "/docs" if settings.DEBUG else None,
        "api": f"{settings.API_V1_PREFIX}/health",
    }


@app.get("/api")
async def api_info():
    """Информация о API"""
    return {
        "api_version": "v1",
        "prefix": settings.API_V1_PREFIX,
        "available_endpoints": [
            "GET /api/v1/health",
            "GET /api/v1/health/db",
            "GET /api/v1/health/tables",
            "GET /api/v1/users",
            "POST /api/v1/users",
            "GET /api/v1/users/{user_id}",
            "GET /api/v1/users/{user_id}/requests",
            "GET /api/v1/users/{user_id}/stats",
        ]
    }


@app.get("/database/status")
async def database_status():
    """Статус базы данных"""
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            # Проверяем таблицы
            result = await conn.execute(text("""
                SELECT table_name, COUNT(*) as column_count
                FROM information_schema.columns
                WHERE table_schema = 'ai_framework'
                GROUP BY table_name
                ORDER BY table_name
            """))

            tables = []
            for row in result:
                tables.append({
                    "table": row.table_name,
                    "columns": row.column_count
                })

            # Проверяем индексы
            result = await conn.execute(text("""
                SELECT COUNT(*) as index_count
                FROM pg_indexes
                WHERE schemaname = 'ai_framework'
            """))
            index_count = result.scalar()

            # Проверяем представления
            result = await conn.execute(text("""
                SELECT COUNT(*) as view_count
                FROM information_schema.views
                WHERE table_schema = 'ai_framework'
            """))
            view_count = result.scalar()

            return {
                "status": "healthy",
                "schema": "ai_framework",
                "tables": len(tables),
                "indexes": index_count,
                "views": view_count,
                "table_list": tables
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def run():
    """Функция для запуска через poetry scripts"""
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.APP_DEBUG else "warning",  # Добавлено
    )


if __name__ == "__main__":
    run()
