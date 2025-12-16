
"""
Менеджер нагрузки для отслеживания и управления нагрузкой на провайдеров.
"""
import logging 
from typing import Dict ,Optional 
from datetime import datetime 
from dataclasses import dataclass 

from sqlalchemy .ext .asyncio import AsyncSession 
from sqlalchemy import text 

from .types import ProviderLoad 

logger =logging .getLogger (__name__ )


@dataclass 
class LoadCacheEntry :
    """Запись в кэше нагрузки"""
    loads :Dict [str ,float ]
    timestamp :datetime 


class ProviderLoadManager :
    """
    Управляет данными о нагрузке на провайдеров.
    """

    def __init__ (self ,db :AsyncSession ,cache_ttl :int =300 ):
        """
        Args:
            db: Асинхронная сессия БД
            cache_ttl: Время жизни кэша в секундах
        """
        self .db =db 
        self .cache_ttl =cache_ttl 
        self ._cache :Optional [LoadCacheEntry ]=None 

    async def get_provider_loads (self )->Dict [str ,float ]:
        """
        Получает данные о нагрузке на провайдеров.

        Returns:
            Словарь с нагрузкой на провайдеров (0-1)
        """

        if self ._cache_is_valid ():
            return self ._cache .loads .copy ()

        try :
            loads =await self ._fetch_loads_from_db ()


            self ._cache =LoadCacheEntry (
            loads =loads ,
            timestamp =datetime .now ()
            )

            return loads 

        except Exception as e :
            logger .error (f"Error fetching provider loads: {e }")
            return {}

    async def _fetch_loads_from_db (self )->Dict [str ,float ]:
        """
        Получает данные о нагрузке из базы данных.

        Returns:
            Словарь с нагрузкой на провайдеров
        """
        sql ="""
        SELECT 
            p.provider_name,
            COUNT(r.request_id) as request_count,
            p.max_requests_per_minute
        FROM ai_framework.providers p
        LEFT JOIN ai_framework.ai_models m ON p.provider_id = m.provider_id
        LEFT JOIN ai_framework.requests r ON m.model_id = r.model_id
            AND r.request_timestamp >= NOW() - INTERVAL '1 hour'
        WHERE p.is_active = true
        GROUP BY p.provider_id, p.provider_name, p.max_requests_per_minute
        """

        result =await self .db .execute (text (sql ))
        rows =result .fetchall ()

        loads ={}
        for row in rows :
            provider_name =row .provider_name 
            request_count =row .request_count or 0 
            max_requests =row .max_requests_per_minute or 60 


            requests_per_minute =request_count /60 
            load =min (requests_per_minute /max_requests ,1.0 )

            loads [provider_name ]=load 

        return loads 

    def _cache_is_valid (self )->bool :
        """Проверяет, действителен ли кэш"""
        if not self ._cache :
            return False 

        cache_age =datetime .now ()-self ._cache .timestamp 
        return cache_age .total_seconds ()<self .cache_ttl 

    async def get_detailed_loads (self )->Dict [str ,ProviderLoad ]:
        """
        Получает детальную информацию о нагрузке.

        Returns:
            Детальная информация о нагрузке
        """
        try :
            sql ="""
            SELECT 
                p.provider_name,
                COUNT(r.request_id) as request_count,
                p.max_requests_per_minute,
                AVG(r.processing_time_ms) as avg_processing_time
            FROM ai_framework.providers p
            LEFT JOIN ai_framework.ai_models m ON p.provider_id = m.provider_id
            LEFT JOIN ai_framework.requests r ON m.model_id = r.model_id
                AND r.request_timestamp >= NOW() - INTERVAL '1 hour'
            WHERE p.is_active = true
            GROUP BY p.provider_id, p.provider_name, p.max_requests_per_minute
            """

            result =await self .db .execute (text (sql ))
            rows =result .fetchall ()

            detailed_loads ={}
            for row in rows :
                provider_name =row .provider_name 
                request_count =row .request_count or 0 
                max_requests =row .max_requests_per_minute or 60 
                avg_processing_time =row .avg_processing_time or 0 


                requests_per_minute =request_count /60 
                load_percentage =min ((requests_per_minute /max_requests )*100 ,100.0 )

                detailed_loads [provider_name ]=ProviderLoad (
                provider_name =provider_name ,
                load_percentage =load_percentage ,
                requests_per_minute =requests_per_minute ,
                max_requests_per_minute =max_requests ,
                last_updated =datetime .now ()
                )

            return detailed_loads 

        except Exception as e :
            logger .error (f"Error fetching detailed loads: {e }")
            return {}

    async def update_provider_max_requests (
    self ,
    provider_name :str ,
    max_requests_per_minute :int 
    )->bool :
        """
        Обновляет максимальное количество запросов для провайдера.

        Args:
            provider_name: Имя провайдера
            max_requests_per_minute: Новое максимальное количество запросов

        Returns:
            True если успешно
        """
        try :
            sql ="""
            UPDATE ai_framework.providers
            SET max_requests_per_minute = :max_requests
            WHERE provider_name = :provider_name
            """

            await self .db .execute (
            text (sql ),
            {
            'provider_name':provider_name ,
            'max_requests':max_requests_per_minute 
            }
            )

            await self .db .commit ()


            self ._cache =None 

            logger .info (
            f"Updated max requests for {provider_name } to {max_requests_per_minute }"
            )

            return True 

        except Exception as e :
            logger .error (f"Error updating provider max requests: {e }")
            await self .db .rollback ()
            return False 

    def clear_cache (self ):
        """Очищает кэш"""
        self ._cache =None 
        logger .debug ("Provider load cache cleared")



def create_load_manager (
db :AsyncSession ,
cache_ttl :int =300 
)->ProviderLoadManager :
    return ProviderLoadManager (db ,cache_ttl )


__all__ =['ProviderLoadManager','create_load_manager']