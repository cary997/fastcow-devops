from fastapi import APIRouter

from .execution import execution_api
from .scheduled import scheduled_api
from .templates import templates_api

tasksRouters = APIRouter()
tasksRouters.include_router(templates_api.router, prefix="/templates")
tasksRouters.include_router(scheduled_api.router, prefix="/scheduled")
tasksRouters.include_router(execution_api.router, prefix="/execution")
