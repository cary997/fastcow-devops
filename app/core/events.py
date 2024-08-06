from typing import Callable

from fastapi import FastAPI
from loguru import logger

from app.core.cache import register_redis
from app.core.config import init_path, settings
from app.core.database import register_db
from app.core.exeption import register_exception_handlers
from app.core.logs import init_logs
from app.core.middleware import register_middleware
from app.core.routers import register_routers


def startup(app: FastAPI) -> Callable:
    """
    FastApi 启动完成事件
    :return: start_app
    """
    # 日志初始化
    init_logs()
    logger.info("Application Start Event Handler")
    # 检查数据目录是否存在
    init_path()
    logger.info(f"Data Path - {settings.base_data_path}")
    # 注册中间件
    register_middleware(app)
    logger.success("Middleware Registration Complete")
    # 注册异常处理器
    register_exception_handlers(app)
    logger.success("Exception Handler Registration Complete")

    async def app_start() -> None:
        """
        启动后触发
        """

        # 注册数据库
        logger.info(
            f"Mysql URI {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?{settings.DB_QUERY}"
        )
        await register_db()
        logger.success("Mysql Registration Complete")

        # 注册redis
        logger.info(
            f"Redis Mode {settings.REDIS_MODE} Redis Address {settings.REDIS_ADDRESS}"
        )
        await register_redis(app)
        logger.success("Redis Registration Complete")

        # 注册路由
        await register_routers(app)
        logger.success("Routers Registration Complete")

    return app_start


def stopping(app: FastAPI) -> Callable:
    """
    FastApi 停止事件
    :return: stop_app
    """

    async def stop_app() -> None:
        # APP停止时触发
        logger.info("Application Stop Event Handler")

        await app.state.cache.close()
        logger.success("Redis Close connection")

    return stop_app
