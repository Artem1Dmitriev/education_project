# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.database.session import get_db
from app.database.repositories import get_repository
from app.schemas import (
    UserCreate, UserUpdate, UserResponse,
    PaginationParams, PaginatedResponse,
    RequestCreate, RequestResponse,
    SuccessResponse, ErrorResponse
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
async def get_users(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        is_active: Optional[bool] = None,
        db: AsyncSession = Depends(get_db)
):
    """Получить список пользователей"""
    repo = get_repository("user", db)

    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active

    users = await repo.get_all(skip=skip, limit=limit, **filters)
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Получить пользователя по ID"""
    repo = get_repository("user", db)

    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.post("/", response_model=UserResponse)
async def create_user(
        user_data: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    """Создать нового пользователя"""
    repo = get_repository("user", db)

    # Проверяем, нет ли уже пользователя с таким email
    existing = await repo.get(email=user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Создаем пользователя
    user = await repo.create(user_data)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")

    return user


@router.get("/{user_id}/requests", response_model=List[RequestResponse])
async def get_user_requests(
        user_id: str,
        limit: int = Query(50, ge=1, le=100),
        db: AsyncSession = Depends(get_db)
):
    """Получить запросы пользователя"""
    request_repo = get_repository("request", db)

    requests = await request_repo.get_user_requests(user_id, limit)
    return requests


@router.get("/{user_id}/stats")
async def get_user_stats(user_id: str, db: AsyncSession = Depends(get_db)):
    """Получить статистику пользователя"""
    request_repo = get_repository("request", db)

    # Общая стоимость
    total_cost = await request_repo.get_total_cost_by_user(user_id)

    # Количество запросов
    request_count = await request_repo.count(user_id=user_id)

    # Последние 10 запросов
    recent_requests = await request_repo.get_user_requests(user_id, limit=10)

    return {
        "user_id": user_id,
        "total_cost": total_cost,
        "request_count": request_count,
        "recent_requests": [
            {
                "request_id": str(req.request_id),
                "model_id": str(req.model_id),
                "status": req.status,
                "total_cost": float(req.total_cost),
                "timestamp": req.request_timestamp.isoformat(),
            }
            for req in recent_requests
        ]
    }