# app/api/v1/schemas/chat.py
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str

class ChatRequest(BaseModel):
    """Запрос для chat endpoint"""
    messages: List[ChatMessage] = Field(..., min_items=1)
    model: Optional[str] = Field("gpt-4o", description="Модель для использования")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    user_id: Optional[UUID] = None
    stream: bool = Field(False, description="Использовать streaming")

class ChatResponse(BaseModel):
    """Ответ от chat endpoint"""
    response_id: UUID
    content: str
    model_used: str
    input_tokens: int
    output_tokens: int
    total_cost: float
    processing_time_ms: int
    timestamp: datetime