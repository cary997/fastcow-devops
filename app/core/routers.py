from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from loguru import logger

from app.apis import loginRouter,apiRouter
from app.core.config import settings

Routers = APIRouter(prefix=settings.SYS_ROUTER_PREFIX)
Routers.include_router(loginRouter)
Routers.include_router(apiRouter)


async def register_routers(app: FastAPI) -> None:
    """
    注册路由
    :param app: FastAPI 实例对象 或者 APIRouter对象
    :return: 默认None
    """
    app.include_router(Routers)
    for route in app.routes:
        try:
            # 为所有route添加ID
            if isinstance(route, APIRoute):
                route.operation_id = route.name
        except AttributeError as e:
            logger.error(f" {e} ")
