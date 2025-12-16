"""
Providers module - clean exports and facade
"""
from .base import BaseProvider ,ProviderResponse 
from .registry import ProviderRegistry ,registry 
from .factory import ProviderFactory 
from .service import ProviderService 


def create_provider_factory (api_keys :dict =None )->ProviderFactory :
    """Создать фабрику провайдеров с внедренным реестром"""
    return ProviderFactory (registry ,api_keys )


def create_provider_service (api_keys :dict =None )->ProviderService :
    """Создать сервис провайдеров"""
    factory =create_provider_factory (api_keys )
    return ProviderService (registry ,factory )



from .mock_client import MockProvider 
from .openai_client import OpenAIProvider 
from .gemini_client import GeminiProvider 
from .ollama_client import OllamaProvider 

__all__ =[

'BaseProvider',
'ProviderResponse',

'ProviderRegistry',
'ProviderFactory',
'ProviderService',

'registry',
'create_provider_factory',
'create_provider_service',

'MockProvider',
'OpenAIProvider',
'GeminiProvider',
'OllamaProvider',
]