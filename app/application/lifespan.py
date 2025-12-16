
from contextlib import asynccontextmanager 
from fastapi import FastAPI 
from app .application .config import settings 
from app .database .session import engine ,check_db_connection ,AsyncSessionLocal 


@asynccontextmanager 
async def lifespan (app :FastAPI ):
    """Lifespan контекст для управления жизненным циклом приложения"""
    print ("🚀 Starting AI Gateway Framework...")

    try :

        if not await check_db_connection ():
            print ("⚠️  Database connection failed. Some features may be unavailable.")
        else :
            print ("✅ Database connection successful")


        await _initialize_providers (app )

    except Exception as e :
        print (f"❌ Error during startup: {e }")
        app .state .provider_service =None 
        app .state .provider_registry =None 

    yield 


    print ("👋 Shutting down AI Gateway Framework...")
    await engine .dispose ()


async def _initialize_providers (app :FastAPI ):
    """Инициализация системы провайдеров"""
    try :
        from app .core .providers import registry ,create_provider_service 


        async with AsyncSessionLocal ()as db :
            await registry .load_from_database (db )

        print (f"✅ ProviderRegistry loaded")


        api_keys ={
        "OpenAI":settings .OPENAI_API_KEY ,
        "Google Gemini":settings .GEMINI_API_KEY ,
        "Anthropic":settings .ANTHROPIC_API_KEY ,
        "HuggingFace":settings .HUGGINGFACE_API_KEY ,
        "Cohere":settings .COHERE_API_KEY ,
        }

        provider_service =create_provider_service (api_keys )


        app .state .provider_service =provider_service 
        app .state .provider_registry =registry 


        if settings .APP_DEBUG :
            await _check_provider_health (provider_service ,api_keys )

    except Exception as e :
        print (f"⚠️  Failed to initialize providers: {e }")
        print ("ℹ️  Continuing with basic functionality...")
        app .state .provider_service =None 
        app .state .provider_registry =None 


async def _check_provider_health (provider_service ,api_keys ):
    """Проверка здоровья провайдеров (только в режиме отладки)"""
    print ("🔍 Checking provider health (debug mode)...")
    health_results =await provider_service .health_check ()

    for provider_name ,is_healthy in health_results .items ():
        status ="✅"if is_healthy else "❌"
        health_status ="healthy"if is_healthy else "unhealthy"
        print (f"   {status } {provider_name }: {health_status }")

        if not is_healthy :
            if api_keys .get (provider_name ):
                print (f"     ⚠️  API key present but provider is unhealthy")
            else :
                print (f"     ⚠️  No API key configured")