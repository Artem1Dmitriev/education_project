# app/api/v1/endpoints/chat_simple.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uuid
from datetime import datetime
import time
import hashlib
import logging

from app.database.session import get_db
from app.core.providers.mock_client import mock_client

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.get("/test")
async def chat_test():
    """Простейший тестовый endpoint"""
    return {
        "message": "AI Gateway Framework работает!",
        "endpoints": {
            "simple_chat_get": "GET /api/v1/chat/simple?message=ваш_текст",
            "simple_chat_post": "POST /api/v1/chat/simple",
            "full_chat": "POST /api/v1/chat (со схемой)",
            "health": "/api/v1/health",
            "docs": "/docs"
        }
    }


async def save_to_database(
        db: AsyncSession,
        messages: list,
        model_name: str,
        temperature: float,
        result: dict,
        user_id: str = None,
        max_tokens: int = None
) -> dict:
    """Сохранить запрос и ответ в БД"""
    try:
        start_time = time.time()

        # 1. Генерируем ID
        request_id = uuid.uuid4()
        response_id = uuid.uuid4()

        # 2. Хеш промпта
        prompt_hash = hashlib.sha256(str(messages).encode()).hexdigest()

        # 3. Ищем или создаем модель в БД
        model_result = await db.execute(
            text("""
            SELECT model_id 
            FROM ai_framework.ai_models 
            WHERE model_name = :model_name 
            LIMIT 1
            """),
            {"model_name": model_name}
        )
        model_row = model_result.fetchone()

        if not model_row:
            # Создаем модель если нет
            model_id = uuid.uuid4()
            provider_result = await db.execute(
                text("SELECT provider_id FROM ai_framework.providers WHERE provider_name = 'MockAI' LIMIT 1")
            )
            provider_row = provider_result.fetchone()

            if not provider_row:
                # Создаем провайдера MockAI
                provider_id = uuid.uuid4()
                await db.execute(
                    text("""
                    INSERT INTO ai_framework.providers 
                    (provider_id, provider_name, base_url, auth_type, is_active)
                    VALUES (:provider_id, 'MockAI', 'http://mock.ai', 'Bearer', true)
                    """),
                    {"provider_id": provider_id}
                )
                provider_id_to_use = provider_id
            else:
                provider_id_to_use = provider_row[0]

            await db.execute(
                text("""
                INSERT INTO ai_framework.ai_models 
                (model_id, provider_id, model_name, model_type, context_window,
                 max_output_tokens, input_price_per_1k, output_price_per_1k,
                 is_available, priority)
                VALUES 
                (:model_id, :provider_id, :model_name, 'text', 8192,
                 2048, 0.0, 0.0, true, 1)
                """),
                {
                    "model_id": model_id,
                    "provider_id": provider_id_to_use,
                    "model_name": model_name
                }
            )
            model_id_to_use = model_id
        else:
            model_id_to_use = model_row[0]

        # 4. Проверяем user_id (если передан)
        user_id_to_save = None
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id)
                user_check = await db.execute(
                    text("SELECT 1 FROM ai_framework.users WHERE user_id = :user_id"),
                    {"user_id": user_uuid}
                )
                if user_check.scalar():
                    user_id_to_save = user_uuid
                else:
                    logger.warning(f"User {user_id} not found, saving without user_id")
            except ValueError:
                logger.warning(f"Invalid user_id format: {user_id}")

        # 5. Подготавливаем текст запроса
        input_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in messages])

        # 6. Сохраняем запрос в таблицу requests
        processing_time = int((time.time() - start_time) * 1000)

        await db.execute(
            text("""
            INSERT INTO ai_framework.requests 
            (request_id, user_id, model_id, prompt_hash, input_text,
             input_tokens, output_tokens, total_cost, temperature,
             max_tokens, status, request_timestamp, processing_time_ms,
             endpoint_called)
            VALUES 
            (:request_id, :user_id, :model_id, :prompt_hash, :input_text,
             :input_tokens, :output_tokens, :total_cost, :temperature,
             :max_tokens, 'completed', :request_timestamp, :processing_time_ms,
             :endpoint_called)
            """),
            {
                "request_id": request_id,
                "user_id": user_id_to_save,
                "model_id": model_id_to_use,
                "prompt_hash": prompt_hash,
                "input_text": input_text,
                "input_tokens": result.get("input_tokens", 0),
                "output_tokens": result.get("output_tokens", 0),
                "total_cost": 0.0,  # Mock модели бесплатные
                "temperature": temperature,
                "max_tokens": max_tokens,
                "request_timestamp": datetime.utcnow(),
                "processing_time_ms": processing_time,
                "endpoint_called": "/api/v1/chat/simple"
            }
        )

        # 7. Сохраняем ответ в таблицу responses
        await db.execute(
            text("""
            INSERT INTO ai_framework.responses 
            (response_id, request_id, content, finish_reason,
             model_used, provider_used, response_timestamp, is_cached)
            VALUES 
            (:response_id, :request_id, :content, :finish_reason,
             :model_used, 'MockAI', :response_timestamp, false)
            """),
            {
                "response_id": response_id,
                "request_id": request_id,
                "content": result["content"],
                "finish_reason": result.get("finish_reason", "stop"),
                "model_used": result["model_used"],
                "response_timestamp": datetime.utcnow()
            }
        )

        await db.commit()

        return {
            "request_id": str(request_id),
            "response_id": str(response_id),
            "processing_time_ms": processing_time,
            "success": True
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error saving to database: {e}")
        raise


@router.get("/simple", summary="GET запрос с сохранением в БД")
async def chat_simple_get(
        message: str = "Привет, как работает система?",
        model: str = "mock-model",
        temperature: float = 0.7,
        max_tokens: int = None,
        user_id: str = None,
        db: AsyncSession = Depends(get_db)
):
    """GET версия простого чата с сохранением в БД"""
    try:
        start_time = time.time()

        # 1. Подготавливаем сообщения
        messages = [{"role": "user", "content": message}]

        # 2. Отправляем запрос к mock клиенту
        result = await mock_client.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # 3. Сохраняем в БД
        save_result = await save_to_database(
            db=db,
            messages=messages,
            model_name=model,
            temperature=temperature,
            result=result,
            user_id=user_id,
            max_tokens=max_tokens
        )

        total_time = int((time.time() - start_time) * 1000)

        # 4. Возвращаем ответ
        return {
            "status": "success",
            "request": message,
            "response": result["content"],
            "model": result["model_used"],
            "tokens": {
                "input": result["input_tokens"],
                "output": result["output_tokens"],
                "total": result["total_tokens"]
            },
            "database": {
                "saved": True,
                "request_id": save_result["request_id"],
                "response_id": save_result["response_id"]
            },
            "timing": {
                "total_ms": total_time,
                "db_save_ms": save_result["processing_time_ms"]
            },
            "cost": 0.0,
            "note": "Mock response saved to database"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/simple", summary="POST запрос с сохранением в БД")
async def chat_simple_post(
        message: str = "Привет!",
        model: str = "mock-model",
        temperature: float = 0.7,
        max_tokens: int = None,
        user_id: str = None,
        db: AsyncSession = Depends(get_db)
):
    """POST версия простого чата с сохранением в БД"""
    return await chat_simple_get(message, model, temperature, max_tokens, user_id, db)


@router.get("/simple/stats")
async def get_simple_stats(db: AsyncSession = Depends(get_db)):
    """Получить статистику по сохраненным simple запросам"""
    try:
        # Общая статистика
        result = await db.execute(
            text("""
            SELECT 
                COUNT(*) as total_requests,
                COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                AVG(processing_time_ms) as avg_processing_time
            FROM ai_framework.requests
            WHERE endpoint_called = '/api/v1/chat/simple'
            """)
        )

        stats_row = result.fetchone()

        # Последние 5 запросов
        recent_result = await db.execute(
            text("""
            SELECT 
                r.request_id,
                r.request_timestamp,
                LEFT(r.input_text, 100) as input_preview,
                LEFT(res.content, 100) as response_preview,
                r.input_tokens,
                r.output_tokens
            FROM ai_framework.requests r
            LEFT JOIN ai_framework.responses res ON r.request_id = res.request_id
            WHERE r.endpoint_called = '/api/v1/chat/simple'
            ORDER BY r.request_timestamp DESC
            LIMIT 5
            """)
        )

        recent_requests = []
        for row in recent_result:
            recent_requests.append({
                "request_id": str(row.request_id),
                "timestamp": row.request_timestamp.isoformat() if row.request_timestamp else None,
                "input_preview": row.input_preview,
                "response_preview": row.response_preview,
                "tokens": {
                    "input": row.input_tokens,
                    "output": row.output_tokens
                }
            })

        return {
            "status": "success",
            "stats": {
                "total_requests": stats_row.total_requests,
                "total_input_tokens": stats_row.total_input_tokens,
                "total_output_tokens": stats_row.total_output_tokens,
                "avg_processing_time_ms": float(stats_row.avg_processing_time) if stats_row.avg_processing_time else 0.0
            },
            "recent_requests": recent_requests
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/simple/check-db")
async def check_database_connection(db: AsyncSession = Depends(get_db)):
    """Проверить подключение к БД и существование таблиц"""
    try:
        # Проверяем таблицу requests
        requests_count = await db.execute(
            text("SELECT COUNT(*) FROM ai_framework.requests")
        )
        requests_total = requests_count.scalar()

        # Проверяем таблицу responses
        responses_count = await db.execute(
            text("SELECT COUNT(*) FROM ai_framework.responses")
        )
        responses_total = responses_count.scalar()

        # Проверяем последний запрос
        last_request = await db.execute(
            text("""
            SELECT request_timestamp 
            FROM ai_framework.requests 
            ORDER BY request_timestamp DESC 
            LIMIT 1
            """)
        )
        last_timestamp_row = last_request.fetchone()

        return {
            "status": "success",
            "database": {
                "connected": True,
                "requests_table": {
                    "exists": True,
                    "total_records": requests_total
                },
                "responses_table": {
                    "exists": True,
                    "total_records": responses_total
                },
                "last_request_time": last_timestamp_row[0].isoformat() if last_timestamp_row else None
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "database": {
                "connected": False,
                "error": str(e)
            }
        }