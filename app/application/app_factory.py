
from fastapi import FastAPI 
from fastapi .middleware .cors import CORSMiddleware 
from app .application .config import settings 
from app .application .lifespan import lifespan 
from app .application .routes import register_routers 


def create_app ()->FastAPI :
    """Фабрика для создания приложения FastAPI"""
    app =FastAPI (
    title =settings .APP_NAME ,
    version =settings .APP_VERSION ,
    description ="Фреймворк для управления нейросетевыми моделями",
    docs_url ="/docs"if settings .APP_DEBUG else None ,
    redoc_url ="/redoc"if settings .APP_DEBUG else None ,
    lifespan =lifespan ,
    )


    _configure_cors (app )


    register_routers (app )

    return app 


def _configure_cors (app :FastAPI ):
    """Настройка CORS middleware"""
    if settings .BACKEND_CORS_ORIGINS :
        app .add_middleware (
        CORSMiddleware ,
        allow_origins =settings .BACKEND_CORS_ORIGINS ,
        allow_credentials =True ,
        allow_methods =["*"],
        allow_headers =["*"],
        )