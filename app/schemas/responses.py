"""
Схемы для работы с ответами
"""
from typing import Optional 
from uuid import UUID 
from pydantic import Field ,ConfigDict 
from datetime import datetime 

from .base import BaseDTO 


class ResponseBase (BaseDTO ):
    """Базовая схема ответа"""
    content :str =Field (...,description ="Текст ответа")
    finish_reason :Optional [str ]=Field (
    None ,
    description ="Причина завершения генерации"
    )
    model_config =ConfigDict (
    from_attributes =True ,
    json_schema_extra ={
    "example":{
    "content":"Это тестовый ответ",
    "finish_reason":"stop"
    }
    }
    )


class ResponseCreate (ResponseBase ):
    """Создание ответа"""
    request_id :UUID =Field (
    ...,
    description ="ID связанного запроса"
    )
    model_used :Optional [str ]=Field (
    None ,
    description ="Использованная модель"
    )
    provider_used :Optional [str ]=Field (
    None ,
    description ="Использованный провайдер"
    )
    summary :Optional [str ]=Field (
    None ,
    description ="Краткое содержание ответа"
    )
    is_cached :bool =Field (
    False ,
    description ="Был ли ответ получен из кэша"
    )
    embedding_vector :Optional [str ]=Field (
    None ,
    description ="Векторное представление ответа"
    )


class ResponseUpdate (BaseDTO ):
    """Обновление ответа"""
    content :Optional [str ]=Field (
    None ,
    description ="Текст ответа"
    )
    summary :Optional [str ]=Field (
    None ,
    description ="Краткое содержание"
    )
    finish_reason :Optional [str ]=Field (
    None ,
    description ="Причина завершения"
    )
    is_cached :Optional [bool ]=Field (
    None ,
    description ="Флаг кэширования"
    )


class ResponseResponse (ResponseBase ):
    """Полная информация об ответе"""
    response_id :UUID =Field (
    ...,
    description ="ID ответа"
    )
    request_id :UUID =Field (
    ...,
    description ="ID запроса"
    )
    model_used :Optional [str ]=Field (
    None ,
    description ="Использованная модель"
    )
    provider_used :Optional [str ]=Field (
    None ,
    description ="Использованный провайдер"
    )
    summary :Optional [str ]=Field (
    None ,
    description ="Краткое содержание"
    )
    response_timestamp :datetime =Field (
    ...,
    description ="Время создания ответа"
    )
    is_cached :bool =Field (
    False ,
    description ="Был ли ответ получен из кэша"
    )
    embedding_vector :Optional [str ]=Field (
    None ,
    description ="Векторное представление"
    )