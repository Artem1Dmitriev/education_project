# app/api/v1/endpoints/chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uuid
from datetime import datetime
import time
import hashlib
import logging

from app.database.session import get_db
from app.schemas import ChatRequest, ChatResponse, SuccessResponse, ErrorResponse
from app.core.providers.factory import provider_factory
from app.core.providers.registry import registry

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


def calculate_prompt_hash(messages: list) -> str:
    """Вычисляем хеш промпта для кеширования"""
    text_repr = str(sorted([(m.get("role"), m.get("content")) for m in messages]))
    return hashlib.sha256(text_repr.encode()).hexdigest()


async def save_chat_to_database(
        db: AsyncSession,
        messages: list,
        model_name: str,
        temperature: float,
        provider_response,
        user_id: uuid.UUID = None,
        max_tokens: int = None,
        endpoint: str = "/api/v1/chat"
) -> dict:
    """Сохранить chat запрос и ответ в БД"""
    try:
        start_time = time.time()

        # 1. Генерируем ID
        request_id = uuid.uuid4()
        response_id = uuid.uuid4()

        # 2. Хеш промпта
        prompt_hash = calculate_prompt_hash(messages)

        # 3. Получаем данные модели из реестра
        model_config = registry.get_model_config(model_name)
        if not model_config:
            raise ValueError(f"Model {model_name} not found in registry")

        # 4. Проверяем user_id
        user_id_to_save = None
        if user_id:
            user_check = await db.execute(
                text("SELECT 1 FROM ai_framework.users WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            if user_check.scalar():
                user_id_to_save = user_id

        # 5. Рассчитываем стоимость (используем цены из реестра)
        input_cost = provider_response.input_tokens * model_config.input_price_per_1k / 1000
        output_cost = provider_response.output_tokens * model_config.output_price_per_1k / 1000
        total_cost = input_cost + output_cost

        # 6. Подготавливаем текст запроса
        input_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in messages])

        # 7. Сохраняем запрос
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
             :max_tokens, 'completed', :timestamp, :processing_time, :endpoint)
            """),
            {
                "request_id": request_id,
                "user_id": user_id_to_save,
                "model_id": model_config.model_id,
                "prompt_hash": prompt_hash,
                "input_text": input_text,
                "input_tokens": provider_response.input_tokens,
                "output_tokens": provider_response.output_tokens,
                "total_cost": total_cost,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timestamp": datetime.utcnow(),
                "processing_time": processing_time,
                "endpoint": endpoint
            }
        )

        # 8. Сохраняем ответ
        await db.execute(
            text("""
            INSERT INTO ai_framework.responses 
            (response_id, request_id, content, finish_reason,
             model_used, provider_used, response_timestamp, is_cached)
            VALUES 
            (:response_id, :request_id, :content, :finish_reason,
             :model_used, :provider_used, :timestamp, false)
            """),
            {
                "response_id": response_id,
                "request_id": request_id,
                "content": provider_response.content,
                "finish_reason": provider_response.finish_reason,
                "model_used": provider_response.model_used,
                "provider_used": provider_response.provider_name,
                "timestamp": datetime.utcnow()
            }
        )

        await db.commit()

        logger.info(f"Chat request saved: {request_id}")

        return {
            "request_id": request_id,
            "response_id": response_id,
            "processing_time_ms": processing_time,
            "total_cost": total_cost
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Database save error: {e}")
        raise


@router.post("", response_model=ChatResponse)
async def chat(
        request: ChatRequest,
        db: AsyncSession = Depends(get_db)
):
    """Основной chat endpoint"""
    start_time = time.time()

    try:
        # 1. Проверяем, есть ли модель в реестре
        model_config = registry.get_model_config(request.model)
        if not model_config:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{request.model}' not found. Available models: {list(registry.models.keys())}"
            )

        # 2. Получаем провайдера для модели
        provider = provider_factory.get_provider_for_model(request.model)
        if not provider:
            raise HTTPException(
                status_code=503,
                detail=f"Provider for model '{request.model}' is not available"
            )

        # 3. Конвертируем сообщения
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # 4. Отправляем запрос
        logger.info(f"Sending request to {provider.provider_name}, model: {request.model}")

        provider_response = await provider.chat_completion(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream
        )

        # 5. Сохраняем в БД
        save_result = await save_chat_to_database(
            db=db,
            messages=messages,
            model_name=request.model,
            temperature=request.temperature,
            provider_response=provider_response,
            user_id=request.user_id,
            max_tokens=request.max_tokens
        )

        total_time = int((time.time() - start_time) * 1000)

        # 6. Возвращаем ответ
        return ChatResponse(
            response_id=save_result["response_id"],
            content=provider_response.content,
            model_used=provider_response.model_used,
            provider_used=provider_response.provider_name,
            input_tokens=provider_response.input_tokens,
            output_tokens=provider_response.output_tokens,
            total_cost=save_result["total_cost"],
            processing_time_ms=total_time,
            timestamp=datetime.utcnow(),
            finish_reason=provider_response.finish_reason,
            is_cached=False
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/providers")
async def list_providers():
    """Получить список провайдеров и моделей"""
    return SuccessResponse(
        success=True,
        message="Providers list retrieved successfully",
        data={
            "providers": registry.list_providers(),
            "models": registry.list_models(),
            "counts": {
                "providers": len(registry.providers),
                "models": len(registry.models)
            }
        }
    )


@router.get("/models")
async def list_models():
    """Получить список моделей"""
    models = registry.list_models()
    return SuccessResponse(
        success=True,
        message="Models list retrieved successfully",
        data={
            "models": models,
            "count": len(models)
        }
    )