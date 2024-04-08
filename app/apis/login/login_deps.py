from typing import Optional, Sequence
from fastapi import Depends
from pydantic import BaseModel, Field
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.depends import AsyncSessionDep
from app.core.exeption import AuthError
from app.ext.ldap.ldap_auth import LdapAuthMixin
from app.models.auth_model import Menus, RolesMenusLink, Users
from app.utils.cache_tools import get_redis_data
from app.utils.password_tools import verify_password
from . import login_schema as schema


class LoginVerifyDepends(BaseModel):
    """
    登录依赖项返回内容
    """

    user: Users
    password: str
    totp_code: Optional[str] = Field(default=None, min_length=6, max_length=6)
    totp_enable: Optional[bool] = False


def user_login_by_ldap(user: Users, password: str, ldap_conf: dict) -> None:
    """
    ldap用户名密码验证
    """
    if not ldap_conf.get("enable"):
        raise AuthError(message="管理员未开启LDAP登录!", status_code=400)
    ldap_conn = LdapAuthMixin(**ldap_conf)
    search_res = ldap_conn.search_user(username=user.username)
    _code = search_res.get("code")
    search_data = search_res.get("data")
    if _code and len(search_data) == 0:
        raise AuthError(message="未查询到LDAP用户", status_code=404)
    if not search_res.get("code"):
        raise AuthError(message=f"{search_res.get('message')}", status_code=400)
    verify_user = ldap_conn.verify_user(
        user=search_data[0].get("dn"), password=password
    )
    if not verify_user.get("code"):
        raise AuthError(message=f"{verify_user.get('message')}", status_code=400)


async def user_login(
        session: AsyncSessionDep, post: schema.LoginRequestForm = Depends()
) -> LoginVerifyDepends:
    """
    登录验证
    """
    user = (
        await session.exec(select(Users).where(Users.username == post.username))
    ).one_or_none()
    if not user:
        raise AuthError(message="用户不存在!", status_code=404)
    verify_info = LoginVerifyDepends(
        user=user, password=post.password, totp_code=post.totp_code
    )
    if not user.password:
        raise AuthError(message="用户密码验证失败!", status_code=400)
    if not user.user_status:
        raise AuthError(message="用户已被禁用!", status_code=403)
    if user.user_type == 1:
        if not verify_password(post.password, user.password):
            raise AuthError(message="用户密码不正确!", status_code=400)
    # 获取系统配置
    sys_conf = await get_redis_data("sys:settings")
    verify_info.totp_enable = sys_conf["security"]["totp"] if sys_conf else False
    if user.user_type == 2:
        # 获取ldap配置
        ldap_conf = sys_conf["ldap"]["config"]
        # ldap验证
        user_login_by_ldap(user=user, password=post.password, ldap_conf=ldap_conf)
    return verify_info


async def get_user_link_menus(session: AsyncSession, user: Users) -> Sequence[Menus]:
    # 平台设置的用户默认权限
    default_roles: list[int] = await get_redis_data(
        "sys:settings", "general.user_default_roles"
    )
    # 当前用户关联的所有角色ID
    roles_id =[]
    if default_roles:
        roles_id: list[int] = [*default_roles]
    for role in user.roles:
        if role.role_status:
            roles_id.append(role.id)

    # 判断是否为超级管理员
    if 1 in roles_id:
        routers = (await session.exec(select(Menus))).all()
        return routers
    # 角色ID关联的所有菜单ID 去重
    menus_id = (
        await session.exec(
            select(RolesMenusLink.auth_menus_id)
            .distinct()
            .where(col(RolesMenusLink.auth_roles_id).in_(roles_id))
        )
    ).all()

    # menus_id对应的所有菜单
    routers = (
        await session.exec(select(Menus).where(col(Menus.id).in_(menus_id)))
    ).all()
    return routers
