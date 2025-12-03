# app/core/providers/__init__.py
"""
Провайдеры AI моделей для AI Gateway Framework

Экспортирует:
- provider_factory: Фабрика для создания экземпляров провайдеров
- registry: Реестр провайдеров и моделей из БД
- BaseProvider, ProviderResponse: Базовые классы
"""

from .base import BaseProvider, ProviderResponse
from .factory import provider_factory
from .registry import registry

# Экспорт классов провайдеров (для тестов или расширения)
from .mock_client import MockProvider
from .openai_client import OpenAIProvider
from .gemini_client import GeminiProvider
from .ollama_client import OllamaProvider

__all__ = [
    'BaseProvider',
    'ProviderResponse',
    'provider_factory',
    'registry',
    'MockProvider',
    'OpenAIProvider',
    'GeminiProvider',
    'OllamaProvider',
]