
"""
Выбор лучшей модели из оцененных кандидатов.
"""
import logging 
from typing import List ,Dict ,Any ,Optional 

from .types import ModelScore ,DecisionResult 

logger =logging .getLogger (__name__ )


class ModelSelector :
    """
    Выбирает лучшую модель из оцененных кандидатов.
    """

    def __init__ (self ,min_score_threshold :float =0.3 ):
        """
        Args:
            min_score_threshold: Минимальный порог оценки
        """
        self .min_score_threshold =min_score_threshold 

    def select_best_model (
    self ,
    model_scores :List [ModelScore ]
    )->Optional [DecisionResult ]:
        """
        Выбирает лучшую модель.

        Args:
            model_scores: Список оценок моделей

        Returns:
            Результат выбора или None
        """
        if not model_scores :
            return None 


        filtered_scores =[
        score for score in model_scores 
        if score .final_score >=self .min_score_threshold 
        ]

        if not filtered_scores :
            logger .warning (f"No models above threshold {self .min_score_threshold }")
            return None 


        sorted_scores =sorted (
        filtered_scores ,
        key =lambda x :x .final_score ,
        reverse =True 
        )


        best_score =sorted_scores [0 ]


        self ._log_top_candidates (sorted_scores )

        return self ._create_decision_result (best_score ,sorted_scores )

    def _create_decision_result (
    self ,
    best_score :ModelScore ,
    all_scores :List [ModelScore ]
    )->DecisionResult :
        """Создает результат выбора"""

        all_candidates =[]
        for i ,score in enumerate (all_scores [:10 ]):
            all_candidates .append ({
            'rank':i +1 ,
            'model':score .model_name ,
            'provider':score .provider_name ,
            'score':round (score .final_score ,3 ),
            'cost':round (score .estimated_cost ,6 ),
            'reasoning_summary':self ._summarize_reasoning (score .reasoning )
            })

        return DecisionResult (
        model_name =best_score .model_name ,
        provider_name =best_score .provider_name ,
        score =best_score .final_score ,
        estimated_cost =best_score .estimated_cost ,
        reasoning =best_score .reasoning ,
        is_default =False ,
        all_candidates =all_candidates 
        )

    def _summarize_reasoning (self ,reasoning :List [str ])->str :
        """Создает краткое резюме из reasoning"""
        if not reasoning :
            return ""


        summary_items =[]
        for item in reasoning [:3 ]:
            if item .startswith (('✓','✗','~')):
                summary_items .append (item )

        return "; ".join (summary_items )

    def _log_top_candidates (self ,sorted_scores :List [ModelScore ]):
        """Логирует топ кандидатов"""
        if not logger .isEnabledFor (logging .DEBUG ):
            return 

        logger .debug ("Top model candidates:")
        for i ,score in enumerate (sorted_scores [:5 ]):
            logger .debug (
            f"  {i +1 }. {score .model_name } ({score .provider_name }): "
            f"score={score .final_score :.3f}, "
            f"cost=${score .estimated_cost :.6f}"
            )

    def select_fallback_model (
    self ,
    available_models :List [Dict [str ,Any ]]
    )->DecisionResult :
        """
        Выбирает резервную модель по умолчанию.

        Args:
            available_models: Список доступных моделей

        Returns:
            Результат выбора резервной модели
        """


        fallback_model =None 
        max_context =0 

        for model_info in available_models :
            context =model_info .get ('context_window',0 )
            if context >max_context :
                max_context =context 
                fallback_model =model_info 

        if not fallback_model :

            return DecisionResult (
            model_name ='gpt-4o',
            provider_name ='OpenAI',
            score =0.0 ,
            estimated_cost =0.0 ,
            reasoning =['Using default fallback model'],
            is_default =True 
            )

        return DecisionResult (
        model_name =fallback_model .get ('name','gpt-4o'),
        provider_name =fallback_model .get ('provider','OpenAI'),
        score =0.0 ,
        estimated_cost =0.0 ,
        reasoning =['Selected as fallback (largest context window)'],
        is_default =True 
        )

    def update_threshold (self ,new_threshold :float ):
        """Обновляет минимальный порог оценки"""
        if 0 <=new_threshold <=1.0 :
            self .min_score_threshold =new_threshold 
            logger .info (f"Updated minimum score threshold to {new_threshold }")
        else :
            raise ValueError ("Threshold must be between 0 and 1")



def create_model_selector (min_score_threshold :float =0.3 )->ModelSelector :
    return ModelSelector (min_score_threshold )


__all__ =['ModelSelector','create_model_selector']