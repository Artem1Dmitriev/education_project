
from fastapi import APIRouter 
from .endpoints import chat_router ,health_router ,users_router ,decision 

router =APIRouter ()
router .include_router (health_router )
router .include_router (users_router )
router .include_router (chat_router )