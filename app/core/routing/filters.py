
"""
Фильтры для отбора моделей по базовым критериям.
"""
import logging 
from typing import List ,Dict ,Any ,Optional 

from .types import ModelRequirements ,PromptAnalysis ,ModelCandidate 

logger =logging .getLogger (__name__ )


class ModelFilter :
    """
    Фильтрует модели по базовым критериям.
    """

    def __init__ (self ,requirements :ModelRequirements ):
        """
        Args:
            requirements: Минимальные требования к модели
        """
        self .requirements =requirements 

    def filter_models (
    self ,
    available_models :List [Dict [str ,Any ]],
    prompt_analysis :PromptAnalysis ,
    registry 
    )->List [ModelCandidate ]:
        """
        Фильтрует модели по базовым критериям.

        Args:
            available_models: Список доступных моделей
            prompt_analysis: Анализ промпта
            registry: Реестр провайдеров

        Returns:
            Отфильтрованный список моделей-кандидатов
        """
        candidates =[]


        required_context =prompt_analysis .token_estimate *1.5 

        for model_info in available_models :
            try :
                candidate =self ._create_candidate (
                model_info ,registry ,required_context 
                )

                if candidate :
                    candidates .append (candidate )

            except Exception as e :
                logger .warning (f"Error creating candidate: {e }")
                continue 

        return candidates 

    def _create_candidate (
    self ,
    model_info :Dict [str ,Any ],
    registry ,
    required_context :float 
    )->Optional [ModelCandidate ]:
        """Создает кандидата из информации о модели"""
        model_name =model_info ['name']


        model_config =registry .get_model_config (model_name )
        if not model_config :
            logger .debug (f"Model config not found: {model_name }")
            return None 


        if not model_config .is_available :
            logger .debug (f"Model not available: {model_name }")
            return None 


        if model_config .context_window <required_context :
            logger .debug (
            f"Model {model_name } filtered: context window "
            f"{model_config .context_window } < required {required_context }"
            )
            return None 


        if model_config .context_window <self .requirements .context_window :
            logger .debug (
            f"Model {model_name } filtered: context window "
            f"{model_config .context_window } < min {self .requirements .context_window }"
            )
            return None 

        if model_config .priority <self .requirements .priority :
            logger .debug (
            f"Model {model_name } filtered: priority "
            f"{model_config .priority } < min {self .requirements .priority }"
            )
            return None 


        provider_name =registry .get_provider_name_for_model (model_name )
        provider_config =registry .get_provider_config (provider_name )

        if not provider_config :
            logger .debug (f"Provider config not found: {provider_name }")
            return None 

        if not provider_config .is_active :
            logger .debug (f"Provider not active: {provider_name }")
            return None 


        return ModelCandidate (
        name =model_name ,
        config =model_config ,
        provider_name =provider_name ,
        provider_config =provider_config ,
        context_window =model_config .context_window ,
        input_price =float (model_config .input_price_per_1k ),
        output_price =float (model_config .output_price_per_1k ),
        priority =model_config .priority ,
        model_type =model_config .model_type 
        )

    def quick_filter (
    self ,
    candidate :ModelCandidate ,
    prompt_analysis :PromptAnalysis 
    )->bool :
        """
        Быстрая проверка кандидата.

        Args:
            candidate: Кандидат
            prompt_analysis: Анализ промпта

        Returns:
            True если кандидат проходит базовые проверки
        """

        if prompt_analysis .prompt_type =='code_generation':

            if candidate .model_type not in ['text','code']:
                return False 



        return True 



def create_model_filter (
context_window :int =1024 ,
priority :int =1 
)->ModelFilter :
    requirements =ModelRequirements (
    context_window =context_window ,
    priority =priority 
    )
    return ModelFilter (requirements )


__all__ =['ModelFilter','create_model_filter']