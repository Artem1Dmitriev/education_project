"""
Схемы для работы с пользователями
"""
from datetime import datetime 
from typing import Optional 
from uuid import UUID 
from pydantic import EmailStr ,Field ,ConfigDict 
from decimal import Decimal 

from .base import BaseDTO ,TimestampMixin ,StatusMixin 


class UserBase (BaseDTO ):
    """Базовая схема пользователя"""
    username :str =Field (
    ...,
    min_length =3 ,
    max_length =50 ,
    description ="Имя пользователя"
    )
    email :EmailStr =Field (
    ...,
    description ="Email пользователя"
    )
    model_config =ConfigDict (
    from_attributes =True ,
    json_schema_extra ={
    "example":{
    "username":"john_doe",
    "email":"john@example.com",
    }
    }
    )


class UserCreate (UserBase ):
    """Создание пользователя"""
    pass 


class UserUpdate (BaseDTO ):
    """Обновление пользователя"""
    username :Optional [str ]=Field (
    None ,
    min_length =3 ,
    max_length =50 ,
    description ="Имя пользователя"
    )
    email :Optional [EmailStr ]=Field (
    None ,
    description ="Email пользователя"
    )
    is_active :Optional [bool ]=Field (
    None ,
    description ="Активен ли пользователь"
    )
    daily_limit :Optional [Decimal ]=Field (
    None ,
    ge =0 ,
    description ="Дневной лимит в USD"
    )
    monthly_limit :Optional [Decimal ]=Field (
    None ,
    ge =0 ,
    description ="Месячный лимит в USD"
    )


class UserResponse (UserBase ,TimestampMixin ,StatusMixin ):
    """Полная информация о пользователе"""
    user_id :UUID =Field (
    ...,
    description ="ID пользователя"
    )
    current_daily_usage :Decimal =Field (
    ...,
    ge =0 ,
    description ="Текущее дневное использование"
    )
    current_monthly_usage :Decimal =Field (
    ...,
    ge =0 ,
    description ="Текущее месячное использование"
    )
    daily_limit :Decimal =Field (
    ...,
    ge =0 ,
    description ="Дневной лимит в USD"
    )
    monthly_limit :Decimal =Field (
    ...,
    ge =0 ,
    description ="Месячный лимит в USD"
    )
    api_key_hash :Optional [str ]=Field (
    None ,
    description ="Хеш API ключа (только для чтения)"
    )


class UserListResponse (BaseDTO ):
    """Сокращенная информация о пользователе для списков"""
    user_id :UUID =Field (
    ...,
    description ="ID пользователя"
    )
    username :str =Field (
    ...,
    description ="Имя пользователя"
    )
    email :EmailStr =Field (
    ...,
    description ="Email пользователя"
    )
    is_active :bool =Field (
    ...,
    description ="Активен ли пользователь"
    )
    total_requests :int =Field (
    ...,
    description ="Общее количество запросов"
    )
    total_cost :Decimal =Field (
    ...,
    description ="Общая стоимость запросов"
    )
    last_request :Optional [datetime ]=Field (
    None ,
    description ="Дата последнего запроса"
    )