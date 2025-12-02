from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database.session import get_db, check_db_connection
from app.database.models import get_model_by_table_name
from app.database.repositories import get_repository
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """Проверка работоспособности приложения"""
    return {
        "status": "healthy",
        "service": "ai-gateway-framework",
        "timestamp": "2024-01-01T00:00:00Z"  # В реальном коде используйте datetime.utcnow()
    }


@router.get("/health/db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """Проверка подключения к базе данных"""
    try:
        result = await db.execute(text("SELECT 1"))
        db_status = result.scalar() == 1

        return {
            "status": "healthy" if db_status else "unhealthy",
            "database": "connected" if db_status else "disconnected",
            "check": db_status,
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }


@router.get("/health/tables")
async def check_tables(db: AsyncSession = Depends(get_db)):
    """Проверка существования и доступности таблиц"""
    tables_to_check = [
        ("users", "user_id"),
        ("providers", "provider_id"),
        ("ai_models", "model_id"),
        ("requests", "request_id"),
    ]

    results = []

    for table_name, id_column in tables_to_check:
        try:
            # Пробуем прочитать одну запись
            query = text(f"SELECT COUNT(*) as count FROM ai_framework.{table_name} LIMIT 1")
            result = await db.execute(query)
            count = result.scalar() or 0

            results.append({
                "table": table_name,
                "exists": True,
                "accessible": True,
                "row_count": count,
            })
        except Exception as e:
            results.append({
                "table": table_name,
                "exists": False,
                "accessible": False,
                "error": str(e),
            })

    all_accessible = all(r["accessible"] for r in results)

    return {
        "status": "healthy" if all_accessible else "partial",
        "tables": results,
        "all_tables_accessible": all_accessible,
    }


@router.get("/health/data")
async def check_sample_data(db: AsyncSession = Depends(get_db)):
    """Проверка наличия тестовых данных"""
    try:
        # Проверяем наличие хотя бы одного провайдера
        provider_repo = get_repository("provider", db)
        providers = await provider_repo.get_all(limit=1)

        # Проверяем наличие хотя бы одной модели
        model_repo = get_repository("model", db)
        models = await model_repo.get_all(limit=1)

        return {
            "status": "ok",
            "has_providers": len(providers) > 0,
            "provider_count": len(providers),
            "has_models": len(models) > 0,
            "model_count": len(models),
            "message": "Data check completed successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "has_providers": False,
            "has_models": False,
        }