from fastapi import APIRouter
from .settings import settings_api
from .apicheck import check_api

systemRouter = APIRouter()

systemRouter.include_router(settings_api.router, prefix="/settings")
systemRouter.include_router(check_api.router, prefix="/apicheck")
