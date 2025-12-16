
from fastapi import APIRouter ,Depends ,HTTPException ,Request 
import logging 

from app .api .deps import get_chat_service 
from app .core .chat import ChatService 
from app .schemas import ChatRequest ,ChatResponse ,SuccessResponse 
from app .core .providers import registry 

router =APIRouter (prefix ="/chat",tags =["chat"])
logger =logging .getLogger (__name__ )


@router .post ("",response_model =ChatResponse )
async def chat (
request :ChatRequest ,
chat_service :ChatService =Depends (get_chat_service )
):
    """
    Основной chat endpoint с использованием ChatService.

    Эндпоинт теперь тонкий - только валидация зависимостей и вызов сервиса.
    """
    try :
        return await chat_service .process_chat_request (request )

    except HTTPException :
        raise 
    except Exception as e :
        logger .error (f"Chat error: {e }",exc_info =True )
        raise HTTPException (status_code =500 ,detail =f"Internal server error: {str (e )}")


@router .get ("/providers")
async def list_providers (request :Request ):
    """Получить список провайдеров и моделей"""
    if not hasattr (request .app .state ,'provider_service')or not request .app .state .provider_service :
        raise HTTPException (
        status_code =503 ,
        detail ="Provider service not initialized"
        )

    provider_service =request .app .state .provider_service 
    status =provider_service .get_provider_status ()

    return SuccessResponse (
    success =True ,
    message ="Providers list retrieved successfully",
    data ={
    "providers":registry .list_providers (),
    "models":registry .list_models (),
    "status":status ,
    "counts":{
    "providers":len (registry .providers ),
    "models":len (registry .models ),
    "cached_instances":len (provider_service .factory .get_cached_providers ())
    }
    }
    )


@router .get ("/health")
async def chat_health_check (request :Request ):
    """Проверка здоровья системы чата"""
    try :
        if not hasattr (request .app .state ,'provider_service')or not request .app .state .provider_service :
            return {
            "status":"degraded",
            "chat_service":"not_initialized",
            "database":"unknown",
            "providers":"not_loaded",
            "message":"Provider service not initialized. Database might be unavailable."
            }

        registry_loaded =registry .is_loaded ()if hasattr (registry ,'is_loaded')else True 

        provider_service =request .app .state .provider_service 
        health_results =await provider_service .health_check ()

        healthy_count =sum (1 for v in health_results .values ()if v )
        unhealthy_providers =[name for name ,healthy in health_results .items ()if not healthy ]

        overall_status ="healthy"if healthy_count ==len (health_results )else "degraded"

        return {
        "status":overall_status ,
        "chat_service":"operational",
        "database":"connected"if registry_loaded else "disconnected",
        "providers":{
        "total":len (health_results ),
        "healthy":healthy_count ,
        "unhealthy":len (unhealthy_providers ),
        "unhealthy_list":unhealthy_providers ,
        "details":health_results 
        },
        "cache_status":{
        "cached_providers":provider_service .factory .get_cached_providers (),
        "cache_size":len (provider_service .factory .get_cached_providers ())
        }
        }

    except Exception as e :
        logger .error (f"Chat health check failed: {e }")
        return {
        "status":"unhealthy",
        "chat_service":"error",
        "database":"unknown",
        "providers":"error",
        "error":str (e )
        }


@router .get ("/available-models")
async def get_available_models ():
    """Получить только доступные модели"""
    models =registry .list_models ()
    available_models =[
    {
    "name":model ["name"],
    "provider":model ["provider"],
    "context_window":model .get ("context_window",8192 ),
    "type":model .get ("type","text"),
    "pricing":{
    "input":model .get ("input_price_per_1k",0.0 ),
    "output":model .get ("output_price_per_1k",0.0 )
    }if "input_price_per_1k"in model else None 
    }
    for model in models if model .get ("is_available",True )
    ]

    return {
    "success":True ,
    "count":len (available_models ),
    "models":available_models 
    }


@router .get ("/stats/{user_id}")
async def get_chat_stats (
user_id :str ,
chat_service :ChatService =Depends (get_chat_service )
):
    """Получить статистику чата для пользователя"""
    try :
        from uuid import UUID 
        user_uuid =UUID (user_id )
        stats =await chat_service .get_chat_statistics (user_uuid )
        return SuccessResponse (
        success =True ,
        message ="Chat statistics retrieved",
        data =stats 
        )
    except ValueError :
        raise HTTPException (status_code =400 ,detail ="Invalid user ID format")
    except Exception as e :
        logger .error (f"Error getting chat stats: {e }")
        raise HTTPException (status_code =500 ,detail ="Error retrieving statistics")