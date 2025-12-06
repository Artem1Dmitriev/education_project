"""
Providers module - clean exports and facade
"""
from .base import BaseProvider, ProviderResponse
from .registry import create_registry
from .factory import ProviderFactory
from .service import ProviderService


def create_provider_service(registry, api_keys: dict = None) -> ProviderService:
    """Создать сервис провайдеров"""
    factory = ProviderFactory(registry, api_keys)
    return ProviderService(registry, factory)


# Экспорт классов провайдеров
from .mock_client import MockProvider
from .openai_client import OpenAIProvider
from .gemini_client import GeminiProvider
from .ollama_client import OllamaProvider

__all__ = [
    # Core
    'BaseProvider',
    'ProviderResponse',
    # Components
    'ProviderService',
    # Global instances
    'create_registry',
    'create_provider_service',
    # Provider implementations
    'MockProvider',
    'OpenAIProvider',
    'GeminiProvider',
    'OllamaProvider',
]