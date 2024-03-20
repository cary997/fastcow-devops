from fastapi import APIRouter

from .menus import menus_api
from .roles import roles_api
from .users import users_api

authRouters = APIRouter()

authRouters.include_router(users_api.router, prefix="/users")

authRouters.include_router(roles_api.router, prefix="/roles")

authRouters.include_router(menus_api.router, prefix="/menus")
