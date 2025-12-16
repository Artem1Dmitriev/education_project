import asyncio 
import time 
import logging 
import uuid 
from datetime import datetime 
from typing import List ,Dict ,Optional ,Any 
from uuid import UUID 

from sqlalchemy .ext .asyncio import AsyncSession 
from fastapi import HTTPException 


from app .database .repositories import get_repository 
from app .schemas import ChatRequest ,ChatResponse ,ChatMessage 
from app .core .providers import registry 
from app .core .providers .service import ProviderService 
from app .core .providers .base import ProviderResponse 


from app .core .routing import create_decision_engine ,DecisionResult 

logger =logging .getLogger (__name__ )


class ChatService :
    """
    Сервис для обработки чат-запросов.
    Инкапсулирует бизнес-логику работы с чатом и интеллектуальный выбор моделей.
    """

    def __init__ (self ,db :AsyncSession ,provider_service :ProviderService ):
        """
        Инициализация сервиса.
        """
        self .db =db 
        self .provider_service =provider_service 
        self .decision_engine =None 



    async def _init_decision_engine (self ):
        """Ленивая инициализация Decision Engine"""
        if self .decision_engine is None :

            self .decision_engine =create_decision_engine (self .db )

    async def _get_model_candidates (self ,chat_request :ChatRequest )->List [Dict [str ,Any ]]:
        """
        Получает основной и резервные модели для обработки запроса.

        Возвращает: Список кандидатов: [{'model_name': str, 'score': float}, ...]
        """

        if chat_request .model and chat_request .model !="auto":
            return [{"model_name":chat_request .model ,"score":1.0 }]


        try :
            await self ._init_decision_engine ()



            decision_result =await self .decision_engine .select_model (
            chat_request ,
            self .provider_service .factory .registry 
            )


            candidates =[{'model_name':decision_result .model_name ,'score':decision_result .score }]


            if decision_result .all_candidates :

                fallback_pool =[
                c for c in decision_result .all_candidates 
                if c ['model_name']!=decision_result .model_name 
                ]

                candidates .extend (fallback_pool [:3 ])

            return candidates 

        except Exception as e :
            logger .error (f"Decision Engine failed, falling back to default model (if configured): {e }")

            default_model ="gpt-3.5-turbo"
            if registry .get_model_config (default_model ):
                return [{"model_name":default_model ,"score":0.0 }]


            raise HTTPException (status_code =503 ,detail ="Decision Engine failed and no default model is available.")


    def _log_decision_result (self ,decision_result :DecisionResult ,requested_model :str ):
        """Логирует результат выбора модели"""

        if decision_result .is_default :
            logger .info (f"⚠️  Using default model: {decision_result .model_name }")
        else :
            logger .info (f"🎯 Selected model: {decision_result .model_name } "
            f"(score: {decision_result .score :.3f}, "
            f"cost: ${decision_result .estimated_cost :.6f})")

            if decision_result .model_name !=requested_model :
                logger .info (f"   Changed from requested: {requested_model }")


            for reason in decision_result .reasoning [:3 ]:
                logger .debug (f"   {reason }")



    async def process_chat_request (
    self ,
    chat_request :ChatRequest ,
    endpoint :str ="/api/v1/chat"
    )->ChatResponse :
        """
        Основной метод обработки чат-запроса с механизмом Failover.
        """
        start_time =time .time ()


        self ._validate_chat_request (chat_request )


        selected_candidates =await self ._get_model_candidates (chat_request )

        provider_response =None 
        selected_model =None 


        for i ,candidate in enumerate (selected_candidates ):
            model_name =candidate ['model_name']
            is_fallback =i >0 

            if is_fallback :
                logger .warning (f"⚠️ Failover: Attempting backup model {model_name } after failure.")

            try :

                self ._get_model_config (model_name )


                provider =self ._get_provider_for_model (model_name )


                messages =self ._convert_messages (chat_request .messages )


                provider_response =await self ._send_to_provider (
                provider =provider ,
                messages =messages ,
                model =model_name ,
                temperature =chat_request .temperature ,
                max_tokens =chat_request .max_tokens ,
                stream =chat_request .stream 
                )


                selected_model =model_name 
                break 

            except HTTPException as e :

                logger .error (
                f"Request failed for model {model_name } ({e .status_code } {e .detail }). Trying next candidate.")
                if i ==len (selected_candidates )-1 :

                    raise e 
            except Exception as e :
                logger .error (f"Unexpected error for model {model_name }: {e }. Trying next candidate.")
                if i ==len (selected_candidates )-1 :
                    raise HTTPException (status_code =500 ,detail =f"All models failed: {str (e )}")



        if not selected_model or not provider_response :

            raise HTTPException (status_code =500 ,detail ="Failed to get response from any provider.")


        save_result =await self ._save_chat_to_database (
        messages =messages ,
        model_name =selected_model ,
        temperature =chat_request .temperature ,
        provider_response =provider_response ,
        user_id =chat_request .user_id ,
        max_tokens =chat_request .max_tokens ,
        endpoint =endpoint 
        )

        total_time =int ((time .time ()-start_time )*1000 )


        return self ._build_chat_response (
        save_result =save_result ,
        provider_response =provider_response ,
        total_time =total_time 
        )

    async def get_model_recommendation (
    self ,
    chat_request :ChatRequest ,
    detailed :bool =False 
    )->Dict [str ,Any ]:
        """
        Получить рекомендацию по выбору модели без выполнения запроса.
        """
        try :
            await self ._init_decision_engine ()

            decision_result =await self .decision_engine .select_model (
            chat_request ,
            self .provider_service .factory .registry 
            )


            response ={
            "recommended_model":decision_result .model_name ,
            "provider":decision_result .provider_name ,
            "score":decision_result .score ,
            "estimated_cost":decision_result .estimated_cost ,
            "reasoning":decision_result .reasoning ,
            "is_default":decision_result .is_default ,
            "requested_model":chat_request .model ,
            "models_considered":len (decision_result .all_candidates )
            if decision_result .all_candidates else 0 ,
            }

            if detailed and decision_result .all_candidates :

                response ["all_candidates"]=decision_result .all_candidates [:5 ]

            return response 

        except Exception as e :
            logger .error (f"Error getting model recommendation: {e }")
            raise 

    async def get_decision_stats (self )->Dict [str ,Any ]:
        """
        Получить статистику работы Decision Engine.
        """
        try :
            if self .decision_engine is None :
                await self ._init_decision_engine ()

            return await self .decision_engine .get_performance_stats ()

        except Exception as e :
            logger .error (f"Error getting decision stats: {e }")
            return {"error":str (e )}

    async def get_chat_statistics (
    self ,
    user_id :Optional [UUID ]=None ,
    days :int =30 
    )->Dict [str ,Any ]:
        """
        Получение статистики по чат-запросам. (Взят из первой версии)
        """

        try :
            request_repo =get_repository ("request",self .db )

            if user_id :

                total_cost =await request_repo .get_total_cost_by_user (user_id )
                request_count =await request_repo .count (user_id =user_id )
                recent_requests =await request_repo .get_user_requests (
                user_id ,limit =10 
                )

                return {
                "user_id":user_id ,
                "total_cost":total_cost ,
                "request_count":request_count ,
                "recent_requests":[
                {
                "request_id":str (req .request_id ),
                "model_id":str (req .model_id ),
                "status":req .status ,
                "total_cost":float (req .total_cost ),
                "timestamp":req .request_timestamp .isoformat (),
                }
                for req in recent_requests 
                ]
                }
            else :







                if not isinstance (days ,int )or days <=0 :
                    days =30 

                sql ="""
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(total_cost) as total_cost,
                    AVG(processing_time) as avg_processing_time_ms
                FROM requests
                WHERE timestamp >= NOW() - INTERVAL '1 day' * :days
                """


                result =await request_repo .raw_query (
                sql ,{"days":days }
                )

                return result [0 ]if result and result [0 ]else {
                "total_requests":0 ,
                "total_cost":0.0 ,
                "avg_processing_time_ms":0.0 
                }

        except Exception as e :
            logger .error (f"Error getting chat statistics: {e }")
            raise HTTPException (status_code =500 ,detail =f"Error retrieving statistics: {str (e )}")

    async def cleanup_old_requests (self ,days :int =90 )->int :
        """
        Очистка старых запросов. (Взят из первой версии)
        """
        try :
            request_repo =get_repository ("request",self .db )

            if not isinstance (days ,int )or days <=0 :
                days =90 

            sql ="""
            DELETE FROM requests
            WHERE timestamp < NOW() - INTERVAL '1 day' * :days
            """


            result =await self .db .execute (sql ,{"days":days })
            await self .db .commit ()


            return result .rowcount 

        except Exception as e :
            logger .error (f"Error cleaning up old requests: {e }")
            raise 



    def _validate_chat_request (self ,chat_request :ChatRequest )->None :
        """Валидация чат-запроса."""
        if not chat_request .messages :
            raise HTTPException (status_code =400 ,detail ="Messages cannot be empty")


    def _get_model_config (self ,model_name :str )->Any :
        """Получение конфигурации модели из реестра."""
        model_config =registry .get_model_config (model_name )
        if not model_config :
            raise HTTPException (
            status_code =404 ,
            detail =f"Model '{model_name }' not found."
            )
        return model_config 

    def _get_provider_for_model (self ,model_name :str )->Any :
        """Получение провайдера для указанной модели."""
        provider =self .provider_service .factory .get_provider_for_model (model_name )
        if not provider :
            raise HTTPException (
            status_code =503 ,
            detail =f"Provider for model '{model_name }' is not available."
            )
        return provider 

    def _convert_messages (self ,messages :List [ChatMessage ])->List [Dict [str ,str ]]:
        """Конвертация сообщений из схемы Pydantic в словарь."""
        return [{"role":msg .role ,"content":msg .content }for msg in messages ]

    async def _send_to_provider (
    self ,
    provider :Any ,
    messages :List [Dict [str ,str ]],
    model :str ,
    temperature :float ,
    max_tokens :Optional [int ],
    stream :bool =False 
    )->ProviderResponse :
        """Отправка запроса провайдеру."""
        timeout_seconds =getattr (provider ,'timeout',30 )

        try :
            return await asyncio .wait_for (
            provider .chat_completion (
            messages =messages ,
            model =model ,
            temperature =temperature ,
            max_tokens =max_tokens ,
            stream =stream 
            ),
            timeout =timeout_seconds 
            )
        except asyncio .TimeoutError :
            logger .error (f"Timeout for provider {provider .provider_name }")
            raise HTTPException (
            status_code =504 ,
            detail =f"Provider {provider .provider_name } "
            f"timeout after {timeout_seconds } seconds"
            )
        except Exception as e :
            logger .error (f"Provider error: {e }",exc_info =True )
            raise HTTPException (
            status_code =500 ,
            detail =f"Provider error: {str (e )}"
            )

    async def _save_chat_to_database (
    self ,
    messages :List [Dict [str ,str ]],
    model_name :str ,
    temperature :float ,
    provider_response :ProviderResponse ,
    user_id :Optional [UUID ]=None ,
    max_tokens :Optional [int ]=None ,
    endpoint :str ="/api/v1/chat"
    )->Dict [str ,Any ]:
        """Сохранение чат-запроса и ответа в базу данных. (Упрощена работа с репозиторием)"""

        try :
            start_time =time .time ()


            model_config =registry .get_model_config (model_name )
            if not model_config :
                raise ValueError (f"Model {model_name } not found in registry")



            def get_price (key ,default =0.0 ):
                return getattr (model_config ,key ,model_config .get (key ,default ))


            user_id_to_save =None 
            if user_id :
                user_repo =get_repository ("user",self .db )

                user =await user_repo .get_by_id (user_id )
                if user :
                    user_id_to_save =user_id 
                else :
                    logger .warning (f"User with ID {user_id } not found. Saving request without user_id.")


            input_price_per_1k =get_price ("input_price_per_1k")
            output_price_per_1k =get_price ("output_price_per_1k")

            input_cost =provider_response .input_tokens *input_price_per_1k /1000 
            output_cost =provider_response .output_tokens *output_price_per_1k /1000 
            total_cost =input_cost +output_cost 


            input_text ="\n".join (
            [f"{msg .get ('role','user')}: {msg .get ('content','')}"
            for msg in messages ]
            )


            prompt_hash =self ._calculate_prompt_hash (messages )


            request_repo =get_repository ("request",self .db )


            request_data ={
            "request_id":uuid .uuid4 (),
            "user_id":user_id_to_save ,
            "model_id":getattr (model_config ,'model_id',str (uuid .uuid4 ())),
            "prompt_hash":prompt_hash ,
            "input_text":input_text ,
            "input_tokens":provider_response .input_tokens ,
            "output_tokens":provider_response .output_tokens ,
            "total_cost":total_cost ,
            "temperature":temperature ,
            "max_tokens":max_tokens ,
            "timestamp":datetime .utcnow (),
            "processing_time":int ((time .time ()-start_time )*1000 ),
            "endpoint":endpoint ,
            "status":"success",
            }

            response_data ={
            "response_id":uuid .uuid4 (),
            "content":provider_response .content ,
            "finish_reason":provider_response .finish_reason ,
            "model_used":provider_response .model_used ,
            "provider_used":provider_response .provider_name ,
            "timestamp":datetime .utcnow ()
            }


            result =await request_repo .create_with_response (
            request_data ,response_data 
            )

            logger .info (f"Chat request saved via repository: {result ['request_id']}")

            return result 

        except Exception as e :

            await self .db .rollback ()
            logger .error (f"Database save error: {e }",exc_info =True )


            return {
            "request_id":None ,
            "response_id":None ,
            "total_cost":total_cost if 'total_cost'in locals ()else 0.0 
            }

    def _calculate_prompt_hash (self ,messages :list )->str :
        """Вычисляем хеш промпта с нормализацией и версионированием."""

        import hashlib 
        import json 


        if messages and isinstance (messages [0 ],ChatMessage ):
            messages =[{"role":msg .role ,"content":msg .content }for msg in messages ]

        normalized_messages =[]
        for msg in messages :
            normalized_msg ={
            "role":msg .get ("role","").strip ().lower (),
            "content":msg .get ("content","").strip (),
            }
            normalized_messages .append (
            json .dumps (normalized_msg ,sort_keys =True ,separators =(',',':'))
            )


        normalized_messages .sort ()
        text_repr =f"v1:{':'.join (normalized_messages )}"

        return hashlib .blake2s (
        text_repr .encode (),
        digest_size =16 
        ).hexdigest ()

    def _build_chat_response (
    self ,
    save_result :Dict [str ,Any ],
    provider_response :ProviderResponse ,
    total_time :int 
    )->ChatResponse :
        """Формирование ответа на чат-запрос."""
        return ChatResponse (
        response_id =save_result ["response_id"]or uuid .uuid4 (),
        request_id =save_result ["request_id"]or uuid .uuid4 (),
        content =provider_response .content ,
        model_used =provider_response .model_used ,
        provider_used =provider_response .provider_name ,
        input_tokens =provider_response .input_tokens ,
        output_tokens =provider_response .output_tokens ,
        total_cost =save_result ["total_cost"],
        processing_time_ms =total_time ,
        timestamp =datetime .utcnow (),
        finish_reason =provider_response .finish_reason ,
        is_cached =False 
        )