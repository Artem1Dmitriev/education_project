
from typing import Dict ,Optional 
import logging 

from .base import BaseProvider 
from .mock_client import MockProvider 
from .openai_client import OpenAIProvider 
from .gemini_client import GeminiProvider 
from .ollama_client import OllamaProvider 
from .registry import ProviderRegistry ,ProviderConfig 

logger =logging .getLogger (__name__ )


class ProviderFactory :
    """
    Factory - создает и кэширует экземпляры провайдеров
    Single Responsibility: создание объектов провайдеров
    """


    PROVIDER_CLASSES ={
    "MockAI":MockProvider ,
    "OpenAI":OpenAIProvider ,
    "Google Gemini":GeminiProvider ,
    "Ollama":OllamaProvider ,
    }

    def __init__ (
    self ,
    registry :ProviderRegistry ,
    api_keys :Optional [Dict [str ,str ]]=None 
    ):
        """
        Инициализация с инъекцией зависимостей

        Args:
            registry: Экземпляр ProviderRegistry
            api_keys: Словарь API ключей {provider_name: api_key}
        """
        self .registry =registry 
        self .api_keys =api_keys or {}
        self ._cache :Dict [str ,BaseProvider ]={}

    def get_provider (self ,provider_name :str )->Optional [BaseProvider ]:
        """Получить экземпляр провайдера по имени"""

        if provider_name in self ._cache :
            return self ._cache [provider_name ]


        provider_config =self .registry .get_provider_config (provider_name )
        if not provider_config :
            logger .error (f"Provider {provider_name } not found in registry")
            return None 


        provider =self ._create_provider (provider_config )
        if provider :
            self ._cache [provider_name ]=provider 

        return provider 

    def get_provider_for_model (self ,model_name :str )->Optional [BaseProvider ]:
        """Получить провайдера для конкретной модели"""
        provider_name =self .registry .get_provider_name_for_model (model_name )
        if not provider_name :
            logger .error (f"No provider found for model {model_name }")
            return None 

        return self .get_provider (provider_name )

    def _create_provider (self ,config :ProviderConfig )->Optional [BaseProvider ]:
        """Создать экземпляр провайдера на основе конфигурации"""
        provider_class =self .PROVIDER_CLASSES .get (config .name )
        if not provider_class :
            logger .error (f"No class found for provider {config .name }")
            return None 

        api_key =self .api_keys .get (config .name )

        try :
            provider =provider_class (
            api_key =api_key ,
            base_url =config .base_url ,
            timeout =config .timeout_seconds 
            )
            logger .info (f"Created provider instance: {config .name }")
            return provider 
        except Exception as e :
            logger .error (f"Failed to create provider {config .name }: {e }")
            return None 

    def clear_cache (self ):
        """Очистить кэш экземпляров провайдеров"""
        self ._cache .clear ()
        logger .info ("Provider cache cleared")

    def get_cached_providers (self )->list :
        """Получить список закэшированных провайдеров"""
        return list (self ._cache .keys ())