
"""
Основной движок принятия решений.
Координирует работу всех компонентов.
"""
import logging 
from typing import Dict ,Any ,Optional 
from datetime import datetime 

from sqlalchemy .ext .asyncio import AsyncSession 

from app .schemas import ChatRequest 
from .types import DecisionResult 
from .analyzer import create_prompt_analyzer 
from .filters import create_model_filter 
from .load_manager import create_load_manager 
from .scorer import create_model_scorer 
from .selector import create_model_selector 

logger =logging .getLogger (__name__ )


class DecisionEngine :
    """
    Основной движок принятия решений.
    Координирует работу всех компонентов.
    """

    def __init__ (
    self ,
    db :AsyncSession ,
    weights :Optional [Dict [str ,float ]]=None ,
    min_score_threshold :float =0.3 
    ):
        """
        Args:
            db: Асинхронная сессия БД
            weights: Веса критериев
            min_score_threshold: Минимальный порог оценки
        """
        self .db =db 


        self .prompt_analyzer =create_prompt_analyzer ()
        self .model_filter =create_model_filter ()
        self .load_manager =create_load_manager (db )


        weights_dict =weights or {
        'cost':0.30 ,
        'complexity':0.25 ,
        'context':0.20 ,
        'priority':0.15 ,
        'load':0.10 
        }

        self .model_scorer =create_model_scorer (**weights_dict )
        self .model_selector =create_model_selector (min_score_threshold )


        self .stats ={
        'total_decisions':0 ,
        'successful_decisions':0 ,
        'fallback_decisions':0 ,
        'avg_processing_time_ms':0 ,
        'last_decision_time':None 
        }

    async def select_model (
    self ,
    chat_request :ChatRequest ,
    registry 
    )->DecisionResult :
        """
        Выбирает оптимальную модель для обработки запроса.

        Args:
            chat_request: Запрос чата
            registry: Реестр провайдеров

        Returns:
            DecisionResult: Результат выбора
        """
        start_time =datetime .now ()

        try :

            prompt_analysis =self .prompt_analyzer .analyze (
            chat_request .messages 
            )


            available_models =registry .list_models ()


            candidates =self .model_filter .filter_models (
            available_models ,prompt_analysis ,registry 
            )

            if not candidates :
                logger .warning ("No suitable models found after filtering")
                return await self ._get_fallback_result (available_models )


            provider_loads =await self .load_manager .get_provider_loads ()


            model_scores =self .model_scorer .score_candidates (
            candidates ,prompt_analysis ,provider_loads 
            )

            if not model_scores :
                logger .warning ("No models scored successfully")
                return await self ._get_fallback_result (available_models )


            decision_result =self .model_selector .select_best_model (model_scores )

            if not decision_result :
                logger .warning ("No model selected by selector")
                return await self ._get_fallback_result (available_models )


            self ._update_stats (True ,False ,start_time )


            self ._log_decision (decision_result ,prompt_analysis )

            return decision_result 

        except Exception as e :
            logger .error (f"Error in decision engine: {e }",exc_info =True )


            try :
                available_models =registry .list_models ()
                fallback_result =await self ._get_fallback_result (available_models )
                self ._update_stats (False ,True ,start_time )
                return fallback_result 
            except Exception as fallback_error :
                logger .error (f"Fallback also failed: {fallback_error }")
                return self ._get_hardcoded_fallback ()

    async def _get_fallback_result (
    self ,
    available_models :list 
    )->DecisionResult :
        """Получает резервный результат"""
        fallback_result =self .model_selector .select_fallback_model (
        available_models 
        )
        logger .info (f"Using fallback model: {fallback_result .model_name }")
        return fallback_result 

    def _get_hardcoded_fallback (self )->DecisionResult :
        """Возвращает жестко заданный резервный вариант"""
        return DecisionResult (
        model_name ='gpt-4o',
        provider_name ='OpenAI',
        score =0.0 ,
        estimated_cost =0.0 ,
        reasoning =['Hardcoded fallback due to system error'],
        is_default =True 
        )

    def _update_stats (
    self ,
    success :bool ,
    fallback :bool ,
    start_time :datetime 
    ):
        """Обновляет статистику"""
        processing_time =(datetime .now ()-start_time ).total_seconds ()*1000 

        self .stats ['total_decisions']+=1 

        if success :
            self .stats ['successful_decisions']+=1 
        elif fallback :
            self .stats ['fallback_decisions']+=1 


        current_avg =self .stats ['avg_processing_time_ms']
        count =self .stats ['total_decisions']

        if count ==1 :
            new_avg =processing_time 
        else :
            new_avg =((current_avg *(count -1 ))+processing_time )/count 

        self .stats ['avg_processing_time_ms']=new_avg 
        self .stats ['last_decision_time']=datetime .now ()

    def _log_decision (
    self ,
    decision_result :DecisionResult ,
    prompt_analysis 
    ):
        """Логирует принятое решение"""
        logger .info (
        f"Selected model: {decision_result .model_name } "
        f"({decision_result .provider_name }) with score {decision_result .score :.3f}"
        )

        logger .debug (
        f"Prompt analysis: complexity={prompt_analysis .complexity .value }, "
        f"tokens={prompt_analysis .token_estimate }, "
        f"type={prompt_analysis .prompt_type }"
        )

    async def update_weights (self ,new_weights :Dict [str ,float ])->bool :
        """
        Обновляет веса критериев.

        Args:
            new_weights: Новые веса

        Returns:
            True если успешно
        """
        try :

            self .model_scorer =create_model_scorer (**new_weights )
            logger .info (f"Updated decision weights: {new_weights }")
            return True 
        except Exception as e :
            logger .error (f"Error updating weights: {e }")
            return False 

    async def get_performance_stats (self )->Dict [str ,Any ]:
        """
        Получает статистику производительности.

        Returns:
            Статистика
        """

        detailed_loads =await self .load_manager .get_detailed_loads ()

        return {
        'stats':self .stats .copy (),
        'weights':self .model_scorer .weights .__dict__ ,
        'threshold':self .model_selector .min_score_threshold ,
        'provider_loads':{
        name :load .__dict__ 
        for name ,load in detailed_loads .items ()
        },
        'success_rate':(
        self .stats ['successful_decisions']/
        max (self .stats ['total_decisions'],1 )
        )*100 ,
        'fallback_rate':(
        self .stats ['fallback_decisions']/
        max (self .stats ['total_decisions'],1 )
        )*100 ,
        }

    def clear_cache (self ):
        """Очищает все кэши"""
        self .load_manager .clear_cache ()
        logger .info ("Decision engine cache cleared")



def create_decision_engine (
db :AsyncSession ,
weights :Optional [Dict [str ,float ]]=None ,
min_score_threshold :float =0.3 
)->DecisionEngine :
    return DecisionEngine (db ,weights ,min_score_threshold )


__all__ =['DecisionEngine','create_decision_engine']