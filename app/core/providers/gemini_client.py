
import google .generativeai as genai 
from typing import List ,Dict ,Any ,Optional 
import asyncio 
from concurrent .futures import ThreadPoolExecutor 
import logging 
from .base import BaseProvider ,ProviderResponse 

logger =logging .getLogger (__name__ )


class GeminiProvider (BaseProvider ):
    """Провайдер для Google Gemini API"""

    @property 
    def provider_name (self )->str :
        return "Google Gemini"

    def __init__ (self ,**kwargs ):
        super ().__init__ (**kwargs )
        if self .api_key :
            genai .configure (api_key =self .api_key )
            self .client =genai 
        else :
            self .client =None 
            logger .warning ("Gemini API key not configured")

    async def chat_completion (
    self ,
    messages :List [Dict [str ,str ]],
    model :str ,
    temperature :float =0.7 ,
    max_tokens :Optional [int ]=None ,
    **kwargs 
    )->ProviderResponse :
        """Отправка запроса в Gemini API"""
        if not self .client :
            raise ValueError ("Gemini API key not configured")

        try :

            formatted_messages =[]
            for msg in messages :
                formatted_messages .append ({
                "role":"user"if msg ["role"]=="user"else "model",
                "parts":[msg ["content"]]
                })

            model_obj =self .client .GenerativeModel (model )
            generation_config ={
            "temperature":temperature ,
            "max_output_tokens":max_tokens or 2048 ,
            }


            def generate_sync ():
                return model_obj .generate_content (
                formatted_messages [-1 ]["parts"][0 ]if formatted_messages else "",
                generation_config =generation_config 
                )

            with ThreadPoolExecutor ()as executor :
                response =await asyncio .get_event_loop ().run_in_executor (
                executor ,generate_sync 
                )


            estimated_tokens =len (response .text .split ())*1.3 

            return ProviderResponse (
            content =response .text ,
            model_used =model ,
            provider_name =self .provider_name ,
            input_tokens =int (estimated_tokens *0.3 ),
            output_tokens =int (estimated_tokens *0.7 ),
            finish_reason ="stop",
            raw_response =response .__dict__ 
            )

        except Exception as e :
            logger .error (f"Gemini API error: {e }")
            raise Exception (f"Gemini API error: {str (e )}")