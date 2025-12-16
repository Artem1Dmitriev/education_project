
from fastapi import APIRouter ,Depends ,HTTPException ,Query 
from typing import Optional ,Dict ,Any 
import logging 

from app .api .deps import get_chat_service 
from app .core .chat import ChatService 
from app .schemas import ChatRequest ,ChatMessage ,SuccessResponse 
from app .core .routing import PromptComplexity 

logger =logging .getLogger (__name__ )
router =APIRouter (prefix ="/decision",tags =["decision-engine"])


@router .post ("/recommend-model")
async def recommend_model (
messages :list [Dict [str ,str ]],
temperature :float =Query (0.7 ,ge =0.0 ,le =2.0 ),
max_tokens :Optional [int ]=Query (None ,gt =0 ),
detailed :bool =Query (False ,description ="Show detailed analysis"),
chat_service :ChatService =Depends (get_chat_service )
):
    """
    Получить рекомендацию по выбору модели для промпта.

    Args:
        messages: Список сообщений в формате [{"role": "user", "content": "text"}]
        temperature: Температура для генерации
        max_tokens: Максимальное количество токенов
        detailed: Показать детальный анализ

    Returns:
        Рекомендация по выбору модели
    """
    try :

        chat_messages =[
        ChatMessage (role =msg ["role"],content =msg ["content"])
        for msg in messages 
        ]


        chat_request =ChatRequest (
        messages =chat_messages ,
        model ="auto",
        temperature =temperature ,
        max_tokens =max_tokens 
        )


        recommendation =await chat_service .get_model_recommendation (
        chat_request ,
        detailed =detailed 
        )

        return SuccessResponse (
        success =True ,
        message ="Model recommendation generated",
        data =recommendation 
        )

    except Exception as e :
        logger .error (f"Recommendation error: {e }",exc_info =True )
        raise HTTPException (
        status_code =500 ,
        detail =f"Error generating recommendation: {str (e )}"
        )


@router .get ("/analyze-prompt")
async def analyze_prompt (
prompt :str =Query (...,description ="Prompt to analyze"),
chat_service :ChatService =Depends (get_chat_service )
):
    """
    Проанализировать промпт и определить его характеристики.

    Args:
        prompt: Текст промпта для анализа

    Returns:
        Анализ промпта
    """
    try :
        from app .core .routing import PromptAnalyzer 

        analyzer =PromptAnalyzer ()
        messages =[ChatMessage (role ="user",content =prompt )]
        analysis =analyzer .analyze (messages )


        complexity_map ={
        "simple":"Простой",
        "standard":"Стандартный",
        "complex":"Сложный",
        "advanced":"Очень сложный"
        }

        return SuccessResponse (
        success =True ,
        message ="Prompt analysis completed",
        data ={
        "token_estimate":analysis .token_estimate ,
        "complexity":{
        "value":analysis .complexity .value ,
        "label":complexity_map .get (analysis .complexity .value ,"Неизвестно")
        },
        "prompt_type":analysis .prompt_type ,
        "has_specific_instructions":analysis .has_specific_instructions ,
        "text_length":analysis .text_length ,
        "preview":analysis .preview [:200 ]+"..."if len (analysis .preview )>200 else analysis .preview 
        }
        )

    except Exception as e :
        logger .error (f"Prompt analysis error: {e }")
        raise HTTPException (
        status_code =500 ,
        detail =f"Error analyzing prompt: {str (e )}"
        )


@router .get ("/stats")
async def get_decision_stats (
chat_service :ChatService =Depends (get_chat_service )
):
    """
    Получить статистику работы Decision Engine.

    Returns:
        Статистика Decision Engine
    """
    try :
        stats =await chat_service .get_decision_stats ()

        return SuccessResponse (
        success =True ,
        message ="Decision Engine statistics",
        data =stats 
        )

    except Exception as e :
        logger .error (f"Stats error: {e }")
        raise HTTPException (
        status_code =500 ,
        detail =f"Error getting stats: {str (e )}"
        )


@router .get ("/available-strategies")
async def get_available_strategies ():
    """
    Получить список доступных стратегий выбора моделей.

    Returns:
        Список стратегий
    """
    strategies =[
    {
    "id":"auto",
    "name":"Автоматический выбор",
    "description":"Intelligent model selection based on cost, complexity, and load",
    "enabled":True 
    },
    {
    "id":"cost_optimized",
    "name":"Оптимизация по стоимости",
    "description":"Select the cheapest model that can handle the prompt",
    "enabled":True 
    },
    {
    "id":"performance",
    "name":"Максимальная производительность",
    "description":"Select the most powerful model regardless of cost",
    "enabled":True 
    },
    {
    "id":"balanced",
    "name":"Сбалансированный подход",
    "description":"Balance between cost and performance",
    "enabled":True 
    }
    ]

    return SuccessResponse (
    success =True ,
    message ="Available selection strategies",
    data ={"strategies":strategies }
    )