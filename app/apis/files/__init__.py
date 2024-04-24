from fastapi import APIRouter

from . import files_api

filesRouters = APIRouter()
filesRouters.include_router(files_api.router)