from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Security
from jose import ExpiredSignatureError, JWTError
from pydantic import ValidationError

from app.apis.deps import (
    CheckTokenDep,
    SessionDep,
    jwt_expires_error,
    jwt_validation_error,
)
from app.core.config import settings
from app.core.security import format_token, generate_totp, verify_totp
from app.models.auth_model import Users
from app.utils.cache_tools import set_redis_data
from app.utils.format_tools import ToTree
from app.utils.password_tools import (
    aes_decrypt_password,
    aes_hash_password,
    jwt_decode,
    verify_password,
)

from . import login_schema as schema
from .login_deps import get_user_link_menus, user_login, LoginVerifyDepends

router = APIRouter()


@router.post(
    settings.SYS_ROUTER_AUTH2,
    response_model=schema.AccessResponse,
    response_model_exclude_unset=True,
    summary="用户登录",
)
async def access_token(
    session: SessionDep, verify_info: Annotated[LoginVerifyDepends, Depends(user_login)]
) -> Any:
    """
    用户登陆
    """
    response = schema.AccessResponse
    # 判断是否开启totp验证
    user: Users = verify_info.user
    totp_code = verify_info.totp_code
    totp_enable = verify_info.totp_enable
    if totp_enable:
        # 验证tot
        if totp_code is None:
            if not user.totp:
                new_totp = generate_totp(user.username)
                user.totp = aes_hash_password(new_totp.get("key"))
                session.commit()
                session.refresh(user)
                return response(
                    data=schema.totpResult(
                        totp=totp_enable, new=True, new_totp=new_totp.get("data")
                    )
                ).success()
            return response(
                data=schema.totpResult(totp=totp_enable, new=False)
            ).success()
        # 如果开启了Totp也传了code则验证totp
        user_totp = aes_decrypt_password(user.totp)
        if not verify_totp(user_totp, totp_code):
            return response(message="MFA验证失败!").fail()
    # 如果totp没开启则直接返回token
    # jwt签发成功写入redis
    user_jwt = format_token(user)
    await set_redis_data(
        f"jwt:{user.id}",
        value=user_jwt.get("access_token"),
        ex=settings.SECRET_JWT_EXP * 60,
    )
    return response(
        message="登录成功",
        data=user_jwt,
    ).success(
        access_token=user_jwt["access_token"],
        token_type=user_jwt["token_type"],
    )


@router.post(
    settings.SYS_ROUTER_REFRESH,
    response_model=schema.RefreshResponse,
    response_model_exclude_unset=True,
    summary="令牌刷新",
)
async def refresh_token(session: SessionDep, post: schema.RefreshToken) -> Any:
    """
    刷新jwt
    :param post:
    :return: jwt token
    """
    response = schema.RefreshResponse
    try:
        access_payload = jwt_decode(post.access_token, verify_exp=False)
        ref_payload = jwt_decode(post.refresh_token)

        if verify_password(
            f"{access_payload.get('user_id')}{access_payload.get('jid')}{access_payload.get('username')}",
            ref_payload.get("refresh_key"),
        ):
            user = session.get(Users, access_payload.get("user_id"))
            if not user:
                return response(http_code=403, message="用户不存在或已删除!").fail()
            if not user.user_status:
                return response(http_code=403, message="用户已被禁用!").fail()
            user_jwt = format_token(user)
            # jwt签发成功写入redis
            await set_redis_data(
                f"jwt:{user.id}",
                value=user_jwt.get("access_token"),
                ex=settings.SECRET_JWT_EXP * 60,
            )
            return response(message="刷新成功", data=user_jwt).success()
        return jwt_validation_error
    except ExpiredSignatureError:
        raise jwt_expires_error
    except (JWTError, ValidationError):
        raise jwt_validation_error


@router.get(
    settings.SYS_ROUTER_SYNCROUTES,
    summary="同步后端路由菜单",
    response_model=schema.MenusTreeResponse,
    dependencies=[Security(CheckTokenDep)],
)
async def async_routes(session: SessionDep, request: Request) -> Any:
    """
    同步动态路由
    """
    response = schema.MenusTreeResponse
    # 当前用户ID
    user_id: int = request.state.user_id
    user = session.get(Users, user_id)
    menus_list = await get_user_link_menus(session=session, user=user)
    routers = ToTree(menus_list, True, "meta.rank").list_to_tree()
    return response(message="同步菜单成功", data=routers).success()
