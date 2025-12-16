
from fastapi import FastAPI 
from app .application .config import settings 
from app .api .v1 .endpoints import health ,users ,chat ,decision 
from app .application .handlers import root 


def register_routers (app :FastAPI ):
    """Регистрация всех роутеров в приложении"""
    app .include_router (health .router ,prefix =settings .API_V1_PREFIX ,tags =["health"])
    app .include_router (users .router ,prefix =settings .API_V1_PREFIX ,tags =["users"])
    app .include_router (chat .router ,prefix =settings .API_V1_PREFIX ,tags =["chat"])
    app .include_router (decision .router ,prefix =settings .API_V1_PREFIX ,tags =["decision-engine"])

    app .include_router (root .router )
