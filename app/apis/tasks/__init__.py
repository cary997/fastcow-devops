from fastapi import APIRouter

from .scheduled import scheduled_api

tasksRouters = APIRouter()

tasksRouters.include_router(scheduled_api.router, prefix="/scheduled")
