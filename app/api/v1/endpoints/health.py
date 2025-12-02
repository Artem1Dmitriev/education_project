from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database.session import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """Проверка работоспособности приложения"""
    return {
        "status": "healthy",
        "service": "ai-gateway-framework",
    }


@router.get("/health/db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """Проверка подключения к базе данных"""
    try:
        result = await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "result": result.scalar(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }