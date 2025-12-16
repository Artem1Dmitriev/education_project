
"""
Типы данных для движка принятия решений.
"""
from dataclasses import dataclass 
from enum import Enum 
from typing import Dict ,List ,Optional ,Any ,TypedDict 
from datetime import datetime 
from uuid import UUID 


class PromptComplexity (Enum ):
    """Уровень сложности промпта"""
    SIMPLE ="simple"
    STANDARD ="standard"
    COMPLEX ="complex"
    ADVANCED ="advanced"


@dataclass 
class PromptAnalysis :
    """Результат анализа промпта"""
    token_estimate :int 
    complexity :PromptComplexity 
    prompt_type :str 
    has_specific_instructions :bool 
    text_length :int 
    message_count :int 
    preview :str 


@dataclass 
class ModelScore :
    """Оценка модели для принятия решения"""
    model_name :str 
    provider_name :str 
    score :float 
    cost_score :float 
    complexity_score :float 
    context_score :float 
    priority_score :float 
    load_score :float 
    final_score :float 
    estimated_cost :float 
    reasoning :List [str ]


@dataclass 
class ScoreWeights :
    """Веса критериев оценки"""
    cost :float =0.30 
    complexity :float =0.25 
    context :float =0.20 
    priority :float =0.15 
    load :float =0.10 

    def validate (self )->bool :
        """Проверяет, что сумма весов = 1.0"""
        total =sum ([
        self .cost ,
        self .complexity ,
        self .context ,
        self .priority ,
        self .load 
        ])
        return abs (total -1.0 )<0.001 


@dataclass 
class ModelRequirements :
    """Минимальные требования к модели"""
    context_window :int =1024 
    priority :int =1 


@dataclass 
class ProviderLoad :
    """Нагрузка на провайдера"""
    provider_name :str 
    load_percentage :float 
    requests_per_minute :float 
    max_requests_per_minute :int 
    last_updated :datetime 


@dataclass 
class DecisionResult :
    """Результат выбора модели"""
    model_name :str 
    provider_name :str 
    score :float 
    estimated_cost :float 
    reasoning :List [str ]
    is_default :bool =False 
    all_candidates :Optional [List [Dict [str ,Any ]]]=None 


@dataclass 
class ModelCandidate :
    """Кандидат для оценки"""
    name :str 
    config :Any 
    provider_name :str 
    provider_config :Any 
    context_window :int 
    input_price :float 
    output_price :float 
    priority :int 
    model_type :str 


class PerformanceStats (TypedDict ):
    """Статистика производительности"""
    total_decisions :int 
    avg_processing_time_ms :float 
    min_processing_time_ms :int 
    max_processing_time_ms :int 
    success_rate :float 


__all__ =[
'PromptComplexity',
'PromptAnalysis',
'ModelScore',
'ScoreWeights',
'ModelRequirements',
'ProviderLoad',
'DecisionResult',
'ModelCandidate',
'PerformanceStats',
]