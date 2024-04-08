from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.base import ResponseBase
from app.core.config import settings
from app.core.security import get_client_ip, verify_client_ip


def register_middleware(app: FastAPI) -> None:
    """
    添加中间件
    """
    app.add_middleware(RequestIpCheckMiddleware)
    # 跨域
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )


class RequestIpCheckMiddleware(BaseHTTPMiddleware):
    """
    判断IP地址是否允许访问实现IP拦截
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:

        client_ip = await get_client_ip(request)
        state = await verify_client_ip(client_ip)
        if not state:
            logger.warning(
                f"非法IP {client_ip} 已拦截! - {request.method} 403 {request.url}"
            )
            return ResponseBase(message=f"非法IP {client_ip}").fail(status_code=403)
        response = await call_next(request)
        return response
