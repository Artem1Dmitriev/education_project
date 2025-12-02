from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database.session import get_db, check_db_connection
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """Проверка работоспособности приложения"""
    return {
        "status": "healthy",
        "service": "ai-gateway-framework",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@router.get("/health/db")
async def health_check_db():
    """Проверка подключения к базе данных"""
    try:
        db_connected = await check_db_connection()
        return {
            "status": "healthy" if db_connected else "unhealthy",
            "database": "connected" if db_connected else "disconnected",
            "check": db_connected,
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
        "users",
        "providers",
        "ai_models",
        "api_keys",
        "requests",
        "files",
        "responses",
        "cache",
        "error_logs",
        "usage_statistics",
        "system_settings"
    ]

    results = []

    for table_name in tables_to_check:
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
async def check_sample_data():
    """Проверка наличия тестовых данных"""
    return {
        "status": "info",
        "message": "Use /health/tables for detailed table information"
    }