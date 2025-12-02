from sqlalchemy import Column, String, DateTime, Boolean, Integer, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.database.session import Base, metadata


# Обязательно указываем метаданные для каждой модели
class User(Base):
    """Модель пользователя (соответствует существующей таблице)"""
    __tablename__ = "users"
    __table_args__ = {"schema": "ai_framework"}

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50))
    email = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.user_id}, username={self.username})>"


class Provider(Base):
    """Модель провайдера"""
    __tablename__ = "providers"
    __table_args__ = {"schema": "ai_framework"}

    provider_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_name = Column(String(50), nullable=False)
    api_base_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Provider(id={self.provider_id}, name={self.provider_name})>"


class AIModel(Base):
    """Модель AI"""
    __tablename__ = "ai_models"
    __table_args__ = {"schema": "ai_framework"}

    model_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("ai_framework.providers.provider_id"))
    model_name = Column(String(100), nullable=False)
    max_tokens = Column(Integer)
    cost_per_input_token = Column(Numeric(10, 8))
    cost_per_output_token = Column(Numeric(10, 8))
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AIModel(id={self.model_id}, name={self.model_name})>"


class Request(Base):
    """Модель запроса"""
    __tablename__ = "requests"
    __table_args__ = {"schema": "ai_framework"}

    request_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("ai_framework.users.user_id", ondelete="SET NULL"))
    model_id = Column(UUID(as_uuid=True), ForeignKey("ai_framework.ai_models.model_id"), nullable=False)
    input_text = Column(Text)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_cost = Column(Numeric(10, 6), default=0.0)
    status = Column(String(20), default="pending")
    request_timestamp = Column(DateTime, default=datetime.utcnow)
    response_timestamp = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Request(id={self.request_id}, status={self.status})>"


# Утилита для получения модели по названию таблицы
def get_model_by_table_name(table_name: str):
    """Получить класс модели по названию таблицы"""
    models = {
        "users": User,
        "providers": Provider,
        "ai_models": AIModel,
        "requests": Request,
    }
    return models.get(table_name)