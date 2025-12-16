
import openai 
from openai import AsyncOpenAI 
from typing import List ,Dict ,Any ,Optional 
import logging 
from .base import BaseProvider ,ProviderResponse 

logger =logging .getLogger (__name__ )


class OpenAIProvider (BaseProvider ):
    """Провайдер для OpenAI API"""

    @property 
    def provider_name (self )->str :
        return "OpenAI"

    def __init__ (self ,**kwargs ):
        super ().__init__ (**kwargs )
        if self .api_key :
            self .client =AsyncOpenAI (
            api_key =self .api_key ,
            base_url =self .base_url ,
            timeout =self .timeout 
            )
        else :
            self .client =None 
            logger .warning ("OpenAI API key not configured")

    async def chat_completion (
    self ,
    messages :List [Dict [str ,str ]],
    model :str ,
    temperature :float =0.7 ,
    max_tokens :Optional [int ]=None ,
    **kwargs 
    )->ProviderResponse :
        if not self .client :
            raise ValueError ("OpenAI API key not configured")

        try :
            response =await self .client .chat .completions .create (
            model =model ,
            messages =messages ,
            temperature =temperature ,
            max_tokens =max_tokens ,
            **kwargs 
            )

            return ProviderResponse (
            content =response .choices [0 ].message .content ,
            model_used =response .model ,
            provider_name =self .provider_name ,
            input_tokens =response .usage .prompt_tokens ,
            output_tokens =response .usage .completion_tokens ,
            finish_reason =response .choices [0 ].finish_reason ,
            raw_response =response .dict ()
            )

        except Exception as e :
            logger .error (f"OpenAI API error: {e }")
            raise Exception (f"OpenAI API error: {str (e )}")