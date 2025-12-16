
from fastapi import APIRouter ,Depends 
from sqlalchemy .ext .asyncio import AsyncSession 
from sqlalchemy import text 
from datetime import datetime 
import logging 
import re 

from app .database .session import get_db ,check_db_connection 
from app .schemas import (
HealthCheckResponse ,
DatabaseHealthResponse ,
TableHealthResponse ,
SystemHealthResponse 
)

logger =logging .getLogger (__name__ )
router =APIRouter ()


@router .get ("/health",response_model =HealthCheckResponse )
async def health_check ():
    """Проверка работоспособности приложения"""
    return HealthCheckResponse (
    status ="healthy",
    service ="ai-gateway-framework",
    version ="0.1.0",
    timestamp =datetime .utcnow ().isoformat (),
    uptime =None ,
    dependencies =None 
    )


@router .get ("/health/db",response_model =DatabaseHealthResponse )
async def health_check_db ():
    """Проверка подключения к базе данных"""
    try :
        db_connected =await check_db_connection ()
        return DatabaseHealthResponse (
        status ="healthy"if db_connected else "unhealthy",
        database ="ai_framework_db",
        check =db_connected ,
        error =None if db_connected else "Database connection failed",
        connection_time_ms =None 
        )
    except Exception as e :
        logger .error (f"Database health check failed: {e }")
        return DatabaseHealthResponse (
        status ="unhealthy",
        database ="ai_framework_db",
        check =False ,
        error =str (e ),
        connection_time_ms =None 
        )


@router .get ("/health/tables",response_model =SystemHealthResponse )
async def check_tables (db :AsyncSession =Depends (get_db )):
    """Проверка существования и доступности таблиц"""
    tables_to_check =[
    "users",
    "providers",
    "ai_models",
    "api_keys",
    "requests",
    "files",
    "responses",
    "cache",
    "error_logs",
    "usage_statistics",
    "system_settings"
    ]

    results =[]
    safe_tables =[]
    for table_name in tables_to_check :

        import re 
        if not re .match (r'^[a-z_][a-z0-9_]*$',table_name ,re .IGNORECASE ):
            logger .warning (f"Skipping potentially unsafe table name: {table_name }")
            continue 
        safe_tables .append (table_name )

    for table_name in safe_tables :
        try :

            query =text (f"SELECT COUNT(*) as count FROM ai_framework.{table_name } LIMIT 1")
            result =await db .execute (query )
            count =result .scalar ()or 0 

            results .append (
            TableHealthResponse (
            table =table_name ,
            exists =True ,
            accessible =True ,
            row_count =count ,
            error =None 
            )
            )
        except Exception as e :
            results .append (
            TableHealthResponse (
            table =table_name ,
            exists =False ,
            accessible =False ,
            row_count =None ,
            error =str (e )
            )
            )

    all_accessible =all (r .accessible for r in results )

    return SystemHealthResponse (
    overall_status ="healthy"if all_accessible else "partial",
    api_status =HealthCheckResponse (
    status ="healthy",
    service ="ai-gateway-framework",
    version ="0.1.0",
    timestamp =datetime .utcnow ().isoformat ()
    ),
    database_status =DatabaseHealthResponse (
    status ="healthy"if all_accessible else "partial",
    database ="ai_framework_db",
    check =all_accessible ,
    error =None 
    ),
    tables_status =results ,
    providers_status =None ,
    cache_status =None 
    )
