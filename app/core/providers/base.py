# app/core/providers/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ProviderResponse(BaseModel):
    """Стандартизированный ответ от провайдера"""
    content: str
    model_used: str
    provider_name: str
    input_tokens: int
    output_tokens: int
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict] = None


class BaseProvider(ABC):
    """Базовый класс для всех провайдеров AI"""

    def __init__(
            self,
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            timeout: int = 30,
            **kwargs
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.config = kwargs

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Название провайдера"""
        pass

    @abstractmethod
    async def chat_completion(
            self,
            messages: List[Dict[str, str]],
            model: str,
            temperature: float = 0.7,
            max_tokens: Optional[int] = None,
            **kwargs
    ) -> ProviderResponse:
        """Отправка запроса к API провайдера"""
        pass

    async def health_check(self) -> bool:
        """Проверка доступности провайдера"""
        try:
            # Простой тестовый запрос
            test_messages = [{"role": "user", "content": "ping"}]
            await self.chat_completion(
                messages=test_messages,
                model=self._get_test_model(),
                temperature=0.1,
                max_tokens=1
            )
            return True
        except Exception as e:
            print(f"Health check failed for {self.provider_name}: {e}")
            return False

    def _get_test_model(self) -> str:
        """Получить тестовую модель (переопределить в наследниках)"""
        # По умолчанию берем первую доступную модель из реестра
        from .registry import registry
        for model_name in registry.models.keys():
            if self.provider_name.lower() in model_name.lower():
                return model_name
        return "mock-model"