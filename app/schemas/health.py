"""
Схемы для health checks
"""
from typing import List ,Optional 
from pydantic import Field 


from .base import BaseDTO 


class HealthCheckResponse (BaseDTO ):
    """Ответ health check"""
    status :str =Field (
    ...,
    description ="Статус сервиса"
    )
    service :str =Field (
    ...,
    description ="Название сервиса"
    )
    version :str =Field (
    ...,
    description ="Версия сервиса"
    )
    timestamp :str =Field (
    ...,
    description ="Время проверки"
    )
    uptime :Optional [float ]=Field (
    None ,
    description ="Время работы в секундах"
    )
    dependencies :Optional [dict ]=Field (
    None ,
    description ="Статус зависимостей"
    )


class DatabaseHealthResponse (BaseDTO ):
    """Статус базы данных"""
    status :str =Field (
    ...,
    description ="Статус БД"
    )
    database :str =Field (
    ...,
    description ="Название БД"
    )
    check :bool =Field (
    ...,
    description ="Результат проверки"
    )
    error :Optional [str ]=Field (
    None ,
    description ="Ошибка (если есть)"
    )
    connection_time_ms :Optional [float ]=Field (
    None ,
    description ="Время подключения в мс"
    )


class TableHealthResponse (BaseDTO ):
    """Статус таблицы"""
    table :str =Field (
    ...,
    description ="Название таблицы"
    )
    exists :bool =Field (
    ...,
    description ="Существует ли таблица"
    )
    accessible :bool =Field (
    ...,
    description ="Доступна ли таблица"
    )
    row_count :Optional [int ]=Field (
    None ,
    description ="Количество строк"
    )
    error :Optional [str ]=Field (
    None ,
    description ="Ошибка (если есть)"
    )


class SystemHealthResponse (BaseDTO ):
    """Полный статус системы"""
    overall_status :str =Field (
    ...,
    description ="Общий статус"
    )
    api_status :HealthCheckResponse =Field (
    ...,
    description ="Статус API"
    )
    database_status :DatabaseHealthResponse =Field (
    ...,
    description ="Статус БД"
    )
    tables_status :List [TableHealthResponse ]=Field (
    ...,
    description ="Статус таблиц"
    )
    providers_status :Optional [dict ]=Field (
    None ,
    description ="Статус провайдеров"
    )
    cache_status :Optional [dict ]=Field (
    None ,
    description ="Статус кэша"
    )