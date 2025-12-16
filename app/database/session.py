
from sqlalchemy .ext .asyncio import AsyncSession ,create_async_engine ,async_sessionmaker 
from sqlalchemy .orm import declarative_base 
from sqlalchemy .pool import NullPool 
from app .application .config import settings 


Base =declarative_base ()


engine_args ={
"echo":settings .APP_DEBUG ,
"pool_pre_ping":True ,
"connect_args":{
"server_settings":{
"jit":"off",
"application_name":"ai_gateway_framework"
}
}
}


if not settings .APP_DEBUG :
    engine_args .update ({
    "pool_size":20 ,
    "max_overflow":30 ,
    })
else :
    engine_args ["poolclass"]=NullPool 


engine =create_async_engine (str (settings .DATABASE_URL ),**engine_args )


AsyncSessionLocal =async_sessionmaker (
engine ,
class_ =AsyncSession ,
expire_on_commit =False ,
autocommit =False ,
autoflush =False ,
)


async def get_db ()->AsyncSession :
    """Dependency для получения асинхронной сессии БД"""
    async with AsyncSessionLocal ()as session :
        try :
            yield session 
        finally :
            await session .close ()


async def check_db_connection ():
    """Проверка подключения к БД"""
    try :
        from sqlalchemy import text 
        async with engine .connect ()as conn :
            result =await conn .execute (text ("""
                                SELECT EXISTS(
                                    SELECT 1 FROM information_schema.schemata 
                                    WHERE schema_name = 'ai_framework'
                                )
                            """))
            schema_exists =result .scalar ()

            if not schema_exists :
                print (
                "⚠️  Schema 'ai_framework' not found. You need to run: python scripts/create_database_structure.py")
            else :
                print ("✅ Schema 'ai_framework' exists")


                result =await conn .execute (
                text ("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'ai_framework'"))
                table_count =result .scalar ()
                print (f"📊 Found {table_count } tables in ai_framework schema")
        return True 
    except Exception as e :
        print (f"❌ Error checking database: {e }")
        return False 