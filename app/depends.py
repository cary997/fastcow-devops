from collections.abc import AsyncGenerator, Generator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError
from pydantic import ValidationError
from redis import Redis
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import async_engine, engine
from app.core.exeption import AuthError
from app.utils.password_tools import jwt_decode


def get_session() -> Generator[Session, None, None]:
    """
    获取数据库连接
    """
    with Session(bind=engine, expire_on_commit=False) as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None, None]:
    """
    获取异步数据库连接
    """
    async with AsyncSession(bind=async_engine, expire_on_commit=False) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.SYS_ROUTER_PREFIX}{settings.SYS_ROUTER_AUTH2}"
)
TokenDep = Annotated[str, Depends(reusable_oauth2)]


jwt_validation_error = AuthError(
    headers={"WWW-Authenticate": f"Bearer {TokenDep}"},
    message="无效凭证!",
)
jwt_expires_error = AuthError(
    headers={"WWW-Authenticate": f"Bearer {TokenDep}"},
    message="凭证已过期!",
)


async def check_token_dep(req: Request, token: TokenDep) -> None:
    """
    检查JWT Token
    """
    try:
        # token解密
        payload = jwt_decode(token)
        if payload:
            # 用户ID
            user_id = payload.get("user_id", None)
            # 用户名
            username = payload.get("username", None)
            # 无效用户信息
            if user_id is None or username is None:
                raise jwt_validation_error
            # 查询redis是否存在jwt
            cache: Redis = req.app.state.cache
            cache_token = await cache.get(f"jwt:{user_id}")
            # 如果和redis中的key不一致则前端请求刷新
            if cache_token != token:
                raise jwt_expires_error
            # 缓存用户ID至request
            req.state.user_id = user_id
            req.state.username = username
        else:
            raise jwt_validation_error
    except ExpiredSignatureError:
        raise jwt_expires_error
    except (JWTError, ValidationError):
        raise jwt_validation_error
