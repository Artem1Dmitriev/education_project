from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import uvicorn

from app.core.config import settings
from app.database.session import engine, check_db_connection, AsyncSessionLocal
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan контекст для управления жизненным циклом приложения"""
    # При запуске
    print("🚀 Starting AI Gateway Framework...")

    try:
        # 1. Проверяем подключение к БД
        if not await check_db_connection():
            print("⚠️  Database connection failed. Some features may be unavailable.")
        else:
            print("✅ Database connection successful")

        # 2. Инициализируем систему провайдеров (если есть подключение к БД)
        try:
            from app.core.providers import registry, create_provider_service

            # Загружаем реестр из БД
            async with AsyncSessionLocal() as db:
                await registry.load_from_database(db)

            # Выводим статистику реестра
            print(f"✅ ProviderRegistry loaded:")

            # 3. Создаем сервис провайдеров с API ключами из настроек
            api_keys = {
                "OpenAI": settings.OPENAI_API_KEY,
                "Google Gemini": settings.GEMINI_API_KEY,
                "Anthropic": settings.ANTHROPIC_API_KEY,
                "HuggingFace": settings.HUGGINGFACE_API_KEY,
                "Cohere": settings.COHERE_API_KEY,
            }

            provider_service = create_provider_service(api_keys)

            # Сохраняем сервис в состоянии приложения для доступа в эндпоинтах
            app.state.provider_service = provider_service
            app.state.provider_registry = registry

            # 4. Проверяем доступность провайдеров (опционально, можно отключить для ускорения)
            if settings.APP_DEBUG:  # Проверяем только в режиме отладки
                print("🔍 Checking provider health (debug mode)...")
                health_results = await provider_service.health_check()

                for provider_name, is_healthy in health_results.items():
                    status = "✅" if is_healthy else "❌"
                    health_status = "healthy" if is_healthy else "unhealthy"
                    print(f"   {status} {provider_name}: {health_status}")

                    if not is_healthy:
                        # Для отладки: выводим причину если есть API ключ
                        if api_keys.get(provider_name):
                            print(f"     ⚠️  API key present but provider is unhealthy")
                        else:
                            print(f"     ⚠️  No API key configured")

        except Exception as e:
            print(f"⚠️  Failed to initialize providers: {e}")
            print("ℹ️  Continuing with basic functionality...")
            # Инициализируем пустые атрибуты, чтобы избежать ошибок
            app.state.provider_service = None
            app.state.provider_registry = None

    except Exception as e:
        print(f"❌ Error during startup: {e}")
        # Все равно продолжаем, чтобы приложение могло работать в ограниченном режиме
        app.state.provider_service = None
        app.state.provider_registry = None

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
app.include_router(users_router, prefix=settings.API_V1_PREFIX, tags=["users"])
app.include_router(chat_router, prefix=settings.API_V1_PREFIX, tags=["chat"])


@app.get("/")
async def root():
    """Корневой endpoint"""
    db_connected = await check_db_connection()

    # Проверяем состояние провайдеров
    providers_status = "not_initialized"
    if hasattr(app.state, 'provider_registry') and app.state.provider_registry:
        providers_status = f"loaded ({len(app.state.provider_registry.providers)} providers)"

    return {
        "message": "Welcome to AI Gateway Framework",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "database": {
            "schema": "ai_framework",
            "status": "connected" if db_connected else "disconnected",
            "connection": "healthy" if db_connected else "unhealthy"
        },
        "providers": {
            "status": providers_status,
            "api": f"{settings.API_V1_PREFIX}/chat/providers"
        },
        "documentation": {
            "swagger": "/docs" if settings.APP_DEBUG else "disabled",
            "redoc": "/redoc" if settings.APP_DEBUG else "disabled",
            "api_spec": "/openapi.json"
        },
        "endpoints": [
            f"{settings.API_V1_PREFIX}/health",
            f"{settings.API_V1_PREFIX}/chat",
            f"{settings.API_V1_PREFIX}/users",
        ]
    }


@app.get("/api")
async def api_info():
    """Информация о API"""
    return {
        "api_version": "v1",
        "prefix": settings.API_V1_PREFIX,
        "available_endpoints": {
            "health": [
                "GET /api/v1/health",
                "GET /api/v1/health/db",
                "GET /api/v1/health/tables",
                "GET /api/v1/health/providers" if hasattr(app.state,
                                                          'provider_service') and app.state.provider_service else None,
            ],
            "users": [
                "GET /api/v1/users",
                "POST /api/v1/users",
                "GET /api/v1/users/{user_id}",
                "GET /api/v1/users/{user_id}/requests",
                "GET /api/v1/users/{user_id}/stats",
            ],
            "chat": [
                "POST /api/v1/chat",
                "GET /api/v1/chat/providers",
                "GET /api/v1/chat/models",
            ]
        }
    }


@app.get("/database/status")
async def database_status():
    """Статус базы данных"""
    try:
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

            # Проверяем функции и триггеры
            result = await conn.execute(text("""
                SELECT COUNT(*) as function_count
                FROM information_schema.routines
                WHERE routine_schema = 'ai_framework'
            """))
            function_count = result.scalar()

            return {
                "status": "healthy",
                "schema": "ai_framework",
                "tables": len(tables),
                "indexes": index_count,
                "views": view_count,
                "functions": function_count,
                "table_list": tables[:10] if len(tables) > 10 else tables,  # Ограничиваем вывод
                "has_more_tables": len(tables) > 10
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "schema": "ai_framework",
            "message": "Database schema might not be initialized. Run scripts/init_db.py"
        }


@app.get("/system/status")
async def system_status():
    """Полный статус системы"""
    db_connected = await check_db_connection()

    # Статус провайдеров
    providers_status = {}
    if hasattr(app.state, 'provider_service') and app.state.provider_service:
        providers_status = app.state.provider_service.get_provider_status()

    return {
        "application": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "debug": settings.APP_DEBUG,
        },
        "database": {
            "connected": db_connected,
            "schema": "ai_framework",
            "url": str(engine.url).split('@')[1] if db_connected else "unknown",  # Без логина/пароля
        },
        "providers": providers_status,
        "api": {
            "host": settings.APP_HOST,
            "port": settings.APP_PORT,
            "prefix": settings.API_V1_PREFIX,
        },
        "timestamp": "2024-01-01T00:00:00Z"  # Можно заменить на реальное время
    }


def run():
    """Функция для запуска через poetry scripts"""
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.APP_DEBUG else "warning",
    )


if __name__ == "__main__":
    run()