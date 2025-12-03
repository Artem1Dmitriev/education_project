# app/core/providers/factory.py
from typing import Dict, Optional
from .base import BaseProvider
from .mock_client import MockProvider
from .openai_client import OpenAIProvider
from .gemini_client import GeminiProvider
from .ollama_client import OllamaProvider
from .registry import registry
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Упрощенная фабрика, использующая реестр"""

    # Маппинг названий провайдеров на классы
    _provider_classes = {
        "MockAI": MockProvider,
        "OpenAI": OpenAIProvider,
        "Google Gemini": GeminiProvider,
        "Ollama": OllamaProvider,
    }

    def __init__(self):
        self._cache: Dict[str, BaseProvider] = {}  # provider_name -> instance
        self._api_keys = self._load_api_keys()

    def _load_api_keys(self) -> Dict[str, Optional[str]]:
        """Загрузить API ключи из настроек"""
        return {
            "OpenAI": settings.OPENAI_API_KEY,
            "Google Gemini": settings.GEMINI_API_KEY,
            "Anthropic": settings.ANTHROPIC_API_KEY,
            "HuggingFace": settings.HUGGINGFACE_API_KEY,
            "Cohere": settings.COHERE_API_KEY,
            "Ollama": None,  # Ollama не требует API ключа
            "MockAI": None,  # Mock не требует API ключа
        }

    def get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """Получить экземпляр провайдера по имени"""
        # Проверяем кэш
        if provider_name in self._cache:
            return self._cache[provider_name]

        # Проверяем, есть ли провайдер в реестре
        provider_config = registry.get_provider_config(provider_name)
        if not provider_config:
            logger.error(f"Provider {provider_name} not found in registry")
            return None

        # Находим класс провайдера
        provider_class = self._provider_classes.get(provider_name)
        if not provider_class:
            logger.error(f"No class found for provider {provider_name}")
            return None

        # Получаем API ключ
        api_key = self._api_keys.get(provider_name)

        try:
            # Создаем экземпляр провайдера
            provider = provider_class(
                api_key=api_key,
                base_url=provider_config.base_url,
                timeout=provider_config.timeout_seconds
            )

            # Сохраняем в кэш
            self._cache[provider_name] = provider
            logger.info(f"Created provider instance: {provider_name}")

            return provider

        except Exception as e:
            logger.error(f"Failed to create provider {provider_name}: {e}")
            return None

    def get_provider_for_model(self, model_name: str) -> Optional[BaseProvider]:
        """Получить провайдера для конкретной модели"""
        # Находим провайдера модели в реестре
        provider_config = registry.get_provider_for_model(model_name)
        if not provider_config:
            logger.error(f"No provider found for model {model_name}")
            return None

        return self.get_provider(provider_config.name)

    def get_model_config(self, model_name: str):
        """Получить конфигурацию модели"""
        return registry.get_model_config(model_name)

    def list_available_providers(self) -> Dict:
        """Список доступных провайдеров"""
        providers = []
        for provider_name in registry.providers.keys():
            if provider_name in self._provider_classes:
                providers.append({
                    "name": provider_name,
                    "has_api_key": bool(self._api_keys.get(provider_name)),
                    "cached": provider_name in self._cache,
                    "class": self._provider_classes[provider_name].__name__
                })
        return {"providers": providers}


# Глобальная фабрика
provider_factory = ProviderFactory()
