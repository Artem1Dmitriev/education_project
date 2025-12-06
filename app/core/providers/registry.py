# app/core/providers/registry.py
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
from sqlalchemy import text

from app.core.exceptions.chat import ModelNotFoundException

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Конфигурация провайдера из БД"""
    provider_id: uuid.UUID
    name: str
    base_url: str
    auth_type: str
    max_requests_per_minute: int = 60
    retry_count: int = 3
    timeout_seconds: int = 30
    is_active: bool = True


@dataclass
class ModelConfig:
    """Конфигурация модели из БД"""
    model_id: uuid.UUID
    provider_id: uuid.UUID
    name: str
    context_window: int = 8192
    max_output_tokens: Optional[int] = None
    input_price_per_1k: float = 0.0
    output_price_per_1k: float = 0.0
    is_available: bool = True
    model_type: str = "text"
    priority: int = 5


class ProviderRegistry:
    """
    Registry - только для хранения конфигурации (без бизнес-логики)
    Single Responsibility: управление данными о провайдерах и моделях
    """

    def __init__(self):
        self.providers: Dict[str, ProviderConfig] = {}
        self.models: Dict[str, ModelConfig] = {}
        self.provider_models: Dict[str, List[str]] = {}
        self._initialized = False

    async def load_from_database(self, db):
        """Загрузить конфигурацию из БД"""

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

            self.providers.clear()
            self.provider_models.clear()

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

            self.models.clear()
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
        """Получить конфигурацию провайдера"""
        return self.providers.get(provider_name)

    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Получить конфигурацию модели"""
        model_config = self.models.get(model_name)
        if not model_config:
            raise ModelNotFoundException(model_name)
        return model_config

    def get_provider_name_for_model(self, model_name: str) -> Optional[str]:
        """Получить имя провайдера для модели"""
        model_config = self.models.get(model_name)
        if not model_config:
            return None

        for provider_name, provider in self.providers.items():
            if provider.provider_id == model_config.provider_id:
                return provider_name
        return None

    def list_providers(self) -> List[Dict]:
        """Список всех провайдеров с моделями (только данные)"""
        return [
            {
                "name": provider_name,
                "models": self.provider_models.get(provider_name, []),
                "model_count": len(self.provider_models.get(provider_name, [])),
                "is_active": provider.is_active
            }
            for provider_name, provider in self.providers.items()
        ]

    def list_models(self) -> List[Dict]:
        """Список всех моделей (только данные)"""
        return [
            {
                "name": model_name,
                "provider": self.get_provider_name_for_model(model_name) or "Unknown",
                "context_window": model.context_window,
                "is_available": model.is_available
            }
            for model_name, model in self.models.items()
        ]

    def is_loaded(self) -> bool:
        """Проверить, загружены ли данные"""
        return self._initialized

    def clear(self):
        """Очистить реестр (для тестов)"""
        self.providers.clear()
        self.models.clear()
        self.provider_models.clear()
        self._initialized = False


def create_registry() -> ProviderRegistry:
    return ProviderRegistry()
