# app/core/providers/service.py
from typing import Dict, Optional
import logging

from .factory import ProviderFactory
from .registry import ProviderRegistry

logger = logging.getLogger(__name__)


class ProviderService:
    """
    Service layer - бизнес-логика работы с провайдерами
    Single Responsibility: orchestration, health checks, etc.
    """

    def __init__(
            self,
            registry: ProviderRegistry,
            factory: ProviderFactory
    ):
        """
        Инициализация с инъекцией зависимостей

        Args:
            registry: Экземпляр ProviderRegistry
            factory: Экземпляр ProviderFactory
        """
        self.registry = registry
        self.factory = factory

    async def health_check(self, provider_name: str = None) -> Dict[str, bool]:
        """Проверка здоровья провайдеров"""
        results = {}

        if provider_name:
            # Проверка конкретного провайдера
            provider = self.factory.get_provider(provider_name)
            if provider:
                try:
                    results[provider_name] = await provider.health_check()
                except Exception as e:
                    logger.error(f"Health check failed for {provider_name}: {e}")
                    results[provider_name] = False
            else:
                results[provider_name] = False
        else:
            # Проверка всех провайдеров
            for name in self.registry.providers.keys():
                provider = self.factory.get_provider(name)
                if provider:
                    try:
                        results[name] = await provider.health_check()
                    except Exception as e:
                        logger.error(f"Health check failed for {name}: {e}")
                        results[name] = False
                else:
                    results[name] = False

        return results

    def get_provider_status(self) -> Dict:
        """Получить статус всех провайдеров"""
        return {
            "providers": self.registry.list_providers(),
            "models": self.registry.list_models(),
            "cached_instances": self.factory.get_cached_providers(),
            "counts": {
                "providers": len(self.registry.providers),
                "models": len(self.registry.models),
                "cached": len(self.factory._cache)
            }
        }

    def reload_registry(self, db):
        """Перезагрузить реестр из БД"""
        import asyncio
        return asyncio.run(self.registry.load_from_database(db))