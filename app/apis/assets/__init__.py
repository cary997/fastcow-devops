from fastapi import APIRouter

from .fields import fields_api
from .groups import groups_api
from .hosts import hosts_api

assetsRouter = APIRouter()

assetsRouter.include_router(fields_api.router, prefix="/fields")
assetsRouter.include_router(groups_api.router, prefix="/groups")
assetsRouter.include_router(hosts_api.router, prefix="/hosts")
