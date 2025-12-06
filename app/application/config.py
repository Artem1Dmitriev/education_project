# app/application/config.py
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, validator, field_validator
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()


class Settings(BaseSettings):
    """Конфигурация приложения"""

    # App
    APP_NAME: str = "AI Gateway Framework"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    APP_DEBUG: bool = True

    # API
    API_V1_PREFIX: str = "/api/v1"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Database
    DATABASE_URL: Optional[PostgresDsn] = None
    SYNC_DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: Optional[str]) -> str:
        if v is not None:
            return v
        # Пробуем получить из переменных окружения
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url
        # Или используем значение по умолчанию для разработки
        return "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_framework_db"

    @field_validator("SYNC_DATABASE_URL", mode="after")
    @classmethod
    def assemble_sync_database_url(cls, v: Optional[str], info) -> str:
        values = info.data
        if isinstance(v, str) and v:
            return v
        # Конвертируем asyncpg в psycopg2 для синхронного подключения
        db_url = str(values.get("DATABASE_URL"))
        return db_url.replace("postgresql+asyncpg://", "postgresql://")

    # AI Providers API Keys
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Разрешает дополнительные поля


class ChatSettings(BaseSettings):
    """Настройки чата"""

    # Лимиты
    MAX_MESSAGES: int = 100
    MAX_MESSAGE_LENGTH: int = 10000
    MIN_TEMPERATURE: float = 0.0
    MAX_TEMPERATURE: float = 2.0

    # Таймауты
    PROVIDER_TIMEOUT: int = 30
    DATABASE_TIMEOUT: int = 10

    # Кэширование
    ENABLE_CACHING: bool = True
    CACHE_TTL: int = 300  # 5 минут

    class Config:
        env_prefix = "CHAT_"


chat_settings = ChatSettings()
settings = Settings()