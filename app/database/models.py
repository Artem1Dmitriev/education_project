from sqlalchemy import UUID, Boolean, DateTime, Integer, String, Text, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database.session import Base
import uuid


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    __table_args__ = {"schema": "ai_framework"}

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Связи
    requests = relationship("Request", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.user_id}, username={self.username})>"


class Request(Base):
    """Модель запроса к нейросети"""
    __tablename__ = "requests"
    __table_args__ = {"schema": "ai_framework"}

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_framework.users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_framework.ai_models.model_id"), nullable=False
    )
    input_text: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float] = mapped_column(Numeric(10, 6), default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    request_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Связи
    user = relationship("User", back_populates="requests")

    def __repr__(self):
        return f"<Request(id={self.request_id}, user={self.user_id}, status={self.status})>"