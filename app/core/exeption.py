from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from typing import Optional, Union
from fastapi.exceptions import RequestValidationError, ValidationException
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field, ValidationError
from loguru import logger


def register_exception_handlers(app: FastAPI) -> None:
    """
    全局异常错误处理注册
    """
    app.add_exception_handler(
        RequestValidationError, handler=request_validation_error_handler
    )
    app.add_exception_handler(StarletteHTTPException, handler=http_error_handler)
    app.add_exception_handler(ValidationException, handler=validation_error_handler)
    app.add_exception_handler(ValidationError, handler=validation_error_handler)
    app.add_exception_handler(Exception, handler=server_error_handler)
    app.add_exception_handler(AuthError, auth_error_handler)


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    http异常处理
    :param _:
    :param exc:
    :return:
    """

    # logger.error(f"HTTPException - {exc}")
    return JSONResponse(
        {"code": 0, "message": exc.detail, "data": {}},
        status_code=exc.status_code,
        headers=exc.headers,
    )


async def request_validation_error_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    参数校验错误处理
    :param _:
    :param exc:
    :return:
    """
    # logger.warning(f"RequestValidationError - {exc}")

    return JSONResponse(
        {"code": 0, "message": "参数错误", "data": exc.errors(), "body": exc.body},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


class Http422ErrorResponse(BaseModel):
    """
    api文档422响应格式
    """

    code: int = Field(title="状态码")
    message: str = Field(title="提示信息")
    data: list[dict] = Field(
        title="错误信息",
        default=[{"loc": ["string", "string"], "msg": "string", "type": "string"}],
    )


async def validation_error_handler(
    _: Request, exc: Union[ValidationException, ValidationError]
) -> JSONResponse:
    # logger.warning(f"ValidationError - {exc}")
    return JSONResponse(
        {"code": 0, "message": "数据校验异常", "data": exc.errors()},
        status_code=status.HTTP_417_EXPECTATION_FAILED,
    )


async def server_error_handler(_: Request, exc: Exception) -> JSONResponse:

    logger.critical(f"ServerException - {exc}")
    return JSONResponse(
        {"code": 0, "message": "服务器内部异常", "data": {}},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class AuthError(Exception):
    """
    身份认证错误
    """

    def __init__(
        self,
        message: str,
        headers: Optional[dict] | None = None,
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        data: Optional[dict] | None = None,
    ):
        self.message = message
        self.headers = headers
        self.data = data
        self.status_code = status_code


async def auth_error_handler(
    _: Request,
    exc: AuthError,
) -> JSONResponse:
    """
    参数校验错误处理
    :param _:
    :param exc:
    :return:
    """
    if exc.data is None:
        exc.data = {}
    return JSONResponse(
        {"code": 0, "message": exc.message, "data": exc.data},
        status_code=exc.status_code,
        headers=exc.headers,
    )
