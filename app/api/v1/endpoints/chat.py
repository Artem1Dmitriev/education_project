# # app/api/v1/endpoints/chat.py
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from typing import List
# import uuid
# from datetime import datetime
# import time
#
# from app.database.session import get_db
# from app.api.v1.schemas.chat import ChatRequest, ChatResponse
# # from app.core.providers.openai_client import openai_client
# from app.core.providers.mock_client import mock_client as ai_client
#
# from app.database.repositories import get_repository
# from app.database.models import Request, Response
#
# router = APIRouter(prefix="/chat", tags=["chat"])
#
#
# @router.post("", response_model=ChatResponse)
# async def chat(
#         request: ChatRequest,
#         db: AsyncSession = Depends(get_db)
# ):
#     """Основной endpoint для запросов к нейросетям"""
#     start_time = time.time()
#
#     try:
#         # 1. Получаем репозитории
#         request_repo = get_repository("request", db)
#         response_repo = get_repository("response", db)
#
#         # 2. Отправляем запрос в OpenAI
#         openai_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
#
#         result = await ai_client.chat_completion(
#             messages=openai_messages,
#             model=request.model,
#             temperature=request.temperature,
#             max_tokens=request.max_tokens
#         )
#
#         # 3. Рассчитываем стоимость (пока заглушка)
#         # TODO: Реализовать расчет на основе реальных цен
#         input_cost = result["input_tokens"] * 0.000005  # $0.005 за 1K токенов
#         output_cost = result["output_tokens"] * 0.000015  # $0.015 за 1K токенов
#         total_cost = input_cost + output_cost
#
#         # 4. Сохраняем запрос в БД
#         db_request = Request(
#             request_id=uuid.uuid4(),
#             user_id=request.user_id,
#             model_id=await _get_model_id(db, request.model),  # Получаем model_id по названию
#             prompt_hash=_calculate_hash(str(request.messages)),
#             input_text="\n".join([f"{m.role}: {m.content}" for m in request.messages]),
#             input_tokens=result["input_tokens"],
#             output_tokens=result["output_tokens"],
#             total_cost=total_cost,
#             temperature=request.temperature,
#             max_tokens=request.max_tokens,
#             status="completed",
#             processing_time_ms=int((time.time() - start_time) * 1000)
#         )
#
#         db.add(db_request)
#         await db.flush()  # Получаем request_id без коммита
#
#         # 5. Сохраняем ответ в БД
#         db_response = Response(
#             response_id=uuid.uuid4(),
#             request_id=db_request.request_id,
#             content=result["content"],
#             finish_reason=result["finish_reason"],
#             model_used=result["model_used"],
#             response_timestamp=datetime.utcnow(),
#             is_cached=False
#         )
#
#         db.add(db_response)
#         await db.commit()
#
#         # 6. Возвращаем ответ
#         return ChatResponse(
#             response_id=db_response.response_id,
#             content=result["content"],
#             model_used=result["model_used"],
#             input_tokens=result["input_tokens"],
#             output_tokens=result["output_tokens"],
#             total_cost=total_cost,
#             processing_time_ms=db_request.processing_time_ms,
#             timestamp=datetime.utcnow()
#         )
#
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
#
# @router.post("/simple")
# async def chat_simple(
#     message: str = "Привет, как дела?",
#     model: str = "gpt-4o"
# ):
#     """Простейший endpoint для быстрого тестирования"""
#     try:
#         messages = [{"role": "user", "content": message}]
#         result = await ai_client.chat_completion(
#             messages=messages,
#             model=model
#         )
#         return {
#             "status": "success",
#             "response": result["content"],
#             "model": result["model_used"],
#             "tokens": {
#                 "input": result["input_tokens"],
#                 "output": result["output_tokens"],
#                 "total": result["total_tokens"]
#             }
#         }
#     except Exception as e:
#         return {
#             "status": "error",
#             "error": str(e)
#         }
#
#
# async def _get_model_id(db: AsyncSession, model_name: str) -> uuid.UUID:
#     """Получить model_id по названию модели"""
#     model_repo = get_repository("model", db)
#     model = await model_repo.get(model_name=model_name)
#     if not model:
#         # Если модели нет в БД, создаем запись с дефолтными значениями
#         # TODO: Реализовать получение provider_id
#         pass
#     return model.model_id
#
#
# def _calculate_hash(text: str) -> str:
#     """Вычисляем хеш промпта для кеширования"""
#     import hashlib
#     return hashlib.sha256(text.encode()).hexdigest()
#
