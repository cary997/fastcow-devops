from fastapi import APIRouter

from .scheduled import scheduled_api
from .templates import templates_api

tasksRouters = APIRouter()
tasksRouters.include_router(templates_api.router, prefix="/templates")
tasksRouters.include_router(scheduled_api.router, prefix="/scheduled")
