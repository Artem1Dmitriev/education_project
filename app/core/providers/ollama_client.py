
import httpx 
from typing import List ,Dict ,Optional 
import json 
import logging 
from .base import BaseProvider ,ProviderResponse 

logger =logging .getLogger (__name__ )


class OllamaProvider (BaseProvider ):
    """Провайдер для Ollama (локальные модели)"""

    @property 
    def provider_name (self )->str :
        return "Ollama"

    def __init__ (self ,**kwargs ):
        super ().__init__ (**kwargs )
        self .client =httpx .AsyncClient (
        base_url =self .base_url or "http://localhost:11434",
        timeout =self .timeout 
        )

    async def chat_completion (
    self ,
    messages :List [Dict [str ,str ]],
    model :str ="llama3.2:latest",
    temperature :float =0.7 ,
    max_tokens :Optional [int ]=None ,
    **kwargs 
    )->ProviderResponse :
        """Отправка запроса в Ollama API"""
        try :

            prompt =self ._format_messages (messages )

            payload ={
            "model":model ,
            "prompt":prompt ,
            "stream":False ,
            "options":{
            "temperature":temperature ,
            "num_predict":max_tokens or 1024 ,
            }
            }

            response =await self .client .post ("/api/generate",json =payload )
            response .raise_for_status ()

            result =response .json ()

            return ProviderResponse (
            content =result .get ("response",""),
            model_used =model ,
            provider_name =self .provider_name ,
            input_tokens =result .get ("prompt_eval_count",0 ),
            output_tokens =result .get ("eval_count",0 ),
            finish_reason ="stop",
            raw_response =result 
            )

        except Exception as e :
            logger .error (f"Ollama API error: {e }")
            raise Exception (f"Ollama API error: {str (e )}")

    def _format_messages (self ,messages :List [Dict [str ,str ]])->str :
        """Конвертируем OpenAI формат сообщений в промпт для Ollama"""
        formatted =[]
        for msg in messages :
            role =msg ["role"]
            content =msg ["content"]
            if role =="system":
                formatted .append (f"System: {content }")
            elif role =="user":
                formatted .append (f"User: {content }")
            elif role =="assistant":
                formatted .append (f"Assistant: {content }")

        return "\n".join (formatted )

    async def list_models (self )->List [str ]:
        """Получить список доступных моделей"""
        try :
            response =await self .client .get ("/api/tags")
            if response .status_code ==200 :
                data =response .json ()
                return [model ["name"]for model in data .get ("models",[])]
            return []
        except Exception as e :
            logger .error (f"Failed to list Ollama models: {e }")
            return []

    async def health_check (self )->bool :
        """Проверка доступности Ollama"""
        try :
            response =await self .client .get ("/api/tags",timeout =5.0 )
            return response .status_code ==200 
        except Exception :
            return False 