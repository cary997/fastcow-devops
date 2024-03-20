from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError
from pydantic import ValidationError
from sqlmodel import Session

from app.core.cache import redisCache
from app.core.config import settings
from app.core.database import engine
from app.core.exeption import AuthError
from app.utils.password_tools import jwt_decode


def get_session() -> Generator[Session, None, None]:
    """
    获取数据库连接
    """
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

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


async def CheckTokenDep(req: Request, token: TokenDep) -> None:
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
            cache: redisCache = req.app.state.cache
            cache_token = await cache.get(f"jwt:{user_id}")
            # 如果和reids中的key不一致则前端请求刷新
            if cache_token != token:
                raise jwt_expires_error
            # 缓存用户ID至request
            req.state.user_id = user_id
        else:
            raise jwt_validation_error
    except ExpiredSignatureError:
        raise jwt_expires_error
    except (JWTError, ValidationError):
        raise jwt_validation_error
