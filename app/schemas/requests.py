"""
Схемы для работы с запросами
"""
from typing import Optional 
from uuid import UUID 
from pydantic import Field ,ConfigDict 
from datetime import datetime 
from decimal import Decimal 

from .base import BaseDTO ,TimestampMixin 


class RequestBase (BaseDTO ):
    """Базовая схема запроса"""
    model_config =ConfigDict (
    from_attributes =True ,
    json_schema_extra ={
    "example":{
    "input_text":"Привет, как дела?",
    "model_id":"123e4567-e89b-12d3-a456-426614174000"
    }
    }
    )


class RequestCreate (RequestBase ):
    """Создание запроса"""
    input_text :str =Field (
    ...,
    min_length =1 ,
    description ="Текст запроса"
    )
    model_id :UUID =Field (
    ...,
    description ="ID модели"
    )
    user_id :Optional [UUID ]=Field (
    None ,
    description ="ID пользователя"
    )
    temperature :float =Field (
    0.7 ,
    ge =0.0 ,
    le =2.0 ,
    description ="Температура"
    )
    max_tokens :Optional [int ]=Field (
    None ,
    gt =0 ,
    description ="Максимум токенов"
    )


class RequestUpdate (BaseDTO ):
    """Обновление запроса (в основном для статуса)"""
    input_tokens :Optional [int ]=Field (
    None ,
    ge =0 ,
    description ="Количество входных токенов"
    )
    output_tokens :Optional [int ]=Field (
    None ,
    ge =0 ,
    description ="Количество выходных токенов"
    )
    total_cost :Optional [Decimal ]=Field (
    None ,
    ge =0 ,
    description ="Общая стоимость"
    )
    status :Optional [str ]=Field (
    None ,
    description ="Статус запроса"
    )
    processing_time_ms :Optional [int ]=Field (
    None ,
    ge =0 ,
    description ="Время обработки в мс"
    )


class RequestResponse (RequestBase ,TimestampMixin ):
    """Полная информация о запросе"""
    request_id :UUID =Field (
    ...,
    description ="ID запроса"
    )
    user_id :Optional [UUID ]=Field (
    None ,
    description ="ID пользователя"
    )
    model_id :UUID =Field (
    ...,
    description ="ID модели"
    )
    model_name :str =Field (
    ...,
    description ="Название модели"
    )
    provider_name :str =Field (
    ...,
    description ="Название провайдера"
    )
    input_text :str =Field (
    ...,
    description ="Текст запроса"
    )
    input_tokens :int =Field (
    ...,
    ge =0 ,
    description ="Входные токены"
    )
    output_tokens :int =Field (
    ...,
    ge =0 ,
    description ="Выходные токены"
    )
    total_cost :Decimal =Field (
    ...,
    ge =0 ,
    description ="Общая стоимость"
    )
    status :str =Field (
    ...,
    description ="Статус"
    )
    request_timestamp :datetime =Field (
    ...,
    description ="Время создания запроса"
    )
    response_timestamp :Optional [datetime ]=Field (
    None ,
    description ="Время получения ответа"
    )
    has_response :bool =Field (
    ...,
    description ="Есть ли ответ"
    )
    has_errors :bool =Field (
    ...,
    description ="Были ли ошибки"
    )


class RequestStats (BaseDTO ):
    """Статистика по запросам"""
    total_requests :int =Field (
    ...,
    description ="Всего запросов"
    )
    successful_requests :int =Field (
    ...,
    description ="Успешных запросов"
    )
    failed_requests :int =Field (
    ...,
    description ="Неудачных запросов"
    )
    total_input_tokens :int =Field (
    ...,
    description ="Всего входных токенов"
    )
    total_output_tokens :int =Field (
    ...,
    description ="Всего выходных токенов"
    )
    total_cost :Decimal =Field (
    ...,
    description ="Общая стоимость"
    )
    avg_processing_time_ms :float =Field (
    ...,
    description ="Среднее время обработки"
    )
    cache_hit_rate :float =Field (
    ...,
    description ="Процент попаданий в кэш"
    )
    top_models :list [dict ]=Field (
    ...,
    description ="Топ используемых моделей"
    )