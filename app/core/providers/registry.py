# app/core/providers/registry.py
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Конфигурация провайдера из БД"""
    provider_id: uuid.UUID
    name: str  # "OpenAI", "MockAI", etc
    base_url: str
    auth_type: str
    api_key: Optional[str] = None  # Будем получать из настроек или api_keys таблицы
    max_requests_per_minute: int = 60
    retry_count: int = 3
    timeout_seconds: int = 30
    is_active: bool = True


@dataclass
class ModelConfig:
    """Конфигурация модели из БД"""
    model_id: uuid.UUID
    provider_id: uuid.UUID
    name: str  # "gpt-4o", "mock-model", etc
    context_window: int = 8192
    max_output_tokens: Optional[int] = None
    input_price_per_1k: float = 0.0
    output_price_per_1k: float = 0.0
    is_available: bool = True
    model_type: str = "text"
    priority: int = 5


class ProviderRegistry:
    """Реестр провайдеров и моделей (кэш в памяти)"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.providers: Dict[str, ProviderConfig] = {}  # name -> config
            self.models: Dict[str, ModelConfig] = {}  # model_name -> config
            self.provider_models: Dict[str, List[str]] = {}  # provider_name -> [model_names]
            self._initialized = False

    async def load_from_database(self, db):
        """Загрузить все данные из БД один раз"""
        from sqlalchemy import text

        try:
            # 1. Загружаем провайдеров
            result = await db.execute(
                text("""
                SELECT 
                    provider_id, provider_name, base_url, auth_type,
                    max_requests_per_minute, retry_count, timeout_seconds, is_active
                FROM ai_framework.providers
                WHERE is_active = true
                """)
            )

            for row in result:
                provider = ProviderConfig(
                    provider_id=row.provider_id,
                    name=row.provider_name,
                    base_url=row.base_url,
                    auth_type=row.auth_type,
                    max_requests_per_minute=row.max_requests_per_minute or 60,
                    retry_count=row.retry_count or 3,
                    timeout_seconds=row.timeout_seconds or 30,
                    is_active=row.is_active
                )
                self.providers[provider.name] = provider
                self.provider_models[provider.name] = []

            # 2. Загружаем модели
            result = await db.execute(
                text("""
                SELECT 
                    m.model_id, m.provider_id, m.model_name, m.context_window,
                    m.max_output_tokens, m.input_price_per_1k, m.output_price_per_1k,
                    m.is_available, m.model_type, m.priority,
                    p.provider_name
                FROM ai_framework.ai_models m
                JOIN ai_framework.providers p ON m.provider_id = p.provider_id
                WHERE m.is_available = true AND p.is_active = true
                """)
            )

            for row in result:
                model = ModelConfig(
                    model_id=row.model_id,
                    provider_id=row.provider_id,
                    name=row.model_name,
                    context_window=row.context_window or 8192,
                    max_output_tokens=row.max_output_tokens,
                    input_price_per_1k=row.input_price_per_1k or 0.0,
                    output_price_per_1k=row.output_price_per_1k or 0.0,
                    is_available=row.is_available,
                    model_type=row.model_type or "text",
                    priority=row.priority or 5
                )
                self.models[model.name] = model
                self.provider_models[row.provider_name].append(model.name)

            logger.info(f"✅ ProviderRegistry loaded: {len(self.providers)} providers, {len(self.models)} models")
            self._initialized = True

        except Exception as e:
            logger.error(f"❌ Failed to load ProviderRegistry: {e}")
            raise

    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """Получить конфиг провайдера по имени"""
        return self.providers.get(provider_name)

    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Получить конфиг модели по имени"""
        return self.models.get(model_name)

    def get_provider_for_model(self, model_name: str) -> Optional[ProviderConfig]:
        """Найти провайдера для модели"""
        model_config = self.get_model_config(model_name)
        if not model_config:
            return None

        # Находим провайдера по provider_id
        for provider in self.providers.values():
            if provider.provider_id == model_config.provider_id:
                return provider
        return None

    def list_providers(self) -> List[Dict]:
        """Список всех провайдеров с моделями"""
        result = []
        for provider_name, provider in self.providers.items():
            result.append({
                "name": provider_name,
                "models": self.provider_models.get(provider_name, []),
                "model_count": len(self.provider_models.get(provider_name, [])),
                "is_active": provider.is_active
            })
        return result

    def list_models(self) -> List[Dict]:
        """Список всех моделей"""
        result = []
        for model_name, model in self.models.items():
            provider = self.get_provider_for_model(model_name)
            result.append({
                "name": model_name,
                "provider": provider.name if provider else "Unknown",
                "context_window": model.context_window,
                "is_available": model.is_available
            })
        return result


# Глобальный экземпляр реестра
registry = ProviderRegistry()