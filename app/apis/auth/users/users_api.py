import math
from typing import Any, Dict, List

from fastapi import APIRouter, Query, Request
from redis import Redis
from sqlalchemy import func
from sqlmodel import col, select

from app.depends import AsyncSessionDep
from app.ext.channels.tasks import send_email
from app.models.auth_model import Users, UsersRolesLink
from app.utils.cache_tools import get_redis_data

from . import users_crud as crud
from . import users_schema as schema

router = APIRouter()


@router.get(
    "/get", summary="查询当前用户", response_model=schema.UserReadWithRolesResponse
)
async def auth_users_get(request: Request, session: AsyncSessionDep) -> Any:
    """
    查询当前用户
    """
    response = schema.UserReadWithRolesResponse
    result = await session.get(Users, request.state.user_id)
    if not result:
        return response(message="用户不存在").fail()
    return response(message="查询成功", data=result).success()


@router.post("/add", summary="创建用户", response_model=schema.UserCreateResponse)
async def auth_users_add(
    session: AsyncSessionDep, user_create: schema.UserCreate
) -> Any:
    """
    创建用户
    """
    response = schema.UserCreateResponse
    user = await crud.get_user_name_or_phone(
        session=session, username=user_create.username, phone=user_create.phone
    )
    if user:
        return response(message="用户名或手机号冲突").fail()
    add_res = await crud.create_user(session=session, user_create=user_create)
    if not add_res:
        return response(message="创建失败").fail()
    return response(message="创建成功", data=add_res).success()


@router.delete(
    "/del/{user_id}", summary="删除用户", response_model=schema.UserDeleteResponse
)
async def auth_users_del(
    request: Request, session: AsyncSessionDep, user_id: int
) -> Any:
    """
    删除单用户
    """
    response = schema.UserDeleteResponse
    if request.state.user_id == user_id:
        return response(message="您不能将自己删除").fail()
    user = await session.get(Users, user_id)
    if not user:
        return response(message="用户不存在").fail()
    session.delete(user)
    await session.commit()
    # 删除redis中的token 强制下线
    cache: Redis = request.app.state.cache
    await cache.delete(f"jwt:{user_id}")
    return response(message="删除成功", data={"id": user_id}).success()


@router.delete(
    "/bulkdel", summary="批量删除用户", response_model=schema.UserBulkDeleteResponse
)
async def auth_users_bulkdel(
    request: Request, session: AsyncSessionDep, data: schema.UserBulkDelete
) -> Any:
    """
    批量删除用户
    """
    response = schema.UserBulkDeleteResponse
    user_id_list = data.user_list
    if request.state.user_id in user_id_list:
        return response(message="您不能将自己删除").fail()
    user_list = (
        await session.exec(select(Users).where(col(Users.id).in_(user_id_list)))
    ).all()
    if len(user_list) == 0:
        return response(message="未查询到用户").fail()
    res_list = []
    cache_kyes = []
    for user in user_list:
        await session.delete(user)
        res_list.append(user.id)
        cache_kyes.append(f"jwt:{user.id}")
    await session.commit()
    # redis中批量删除token
    cache: Redis = request.app.state.cache
    p_cache = cache.pipeline()
    p_cache.delete(*cache_kyes)
    await p_cache.execute()
    return response(message="删除成功", data=res_list).success()


@router.patch(
    "/set/{user_id}", summary="更新用户", response_model=schema.UserUpdateResponse
)
async def auth_users_set(
    request: Request,
    session: AsyncSessionDep,
    user_id: int,
    user_update: schema.UserUpdate,
) -> Any:
    """
    更新用户
    """
    response = schema.UserUpdateResponse
    if (
        request.state.user_id == user_id
        and isinstance(user_update.user_status, bool)
        and not user_update.user_status
    ):
        return response(message="您不能将自己禁用").fail()
    db_user = await session.get(Users, user_id)
    if not db_user:
        return response(message="用户不存在").fail()

    result = await crud.update_user(
        session=session, db_user=db_user, user_update=user_update
    )
    if result.user_status is False:
        # 删除redis中的token 强制下线
        cache: Redis = request.app.state.cache
        await cache.delete(f"jwt:{user_id}")
    return response(message="更新成功", data=result).success()


@router.patch(
    "/bulkset", summary="批量更新用户", response_model=schema.UserBulkUpdateResponse
)
async def auth_users_bulkset(
    request: Request, session: AsyncSessionDep, update_content: schema.UserBulkUpdate
) -> Any:
    """
    批量更新用户
    """
    response = schema.UserBulkUpdateResponse

    # 获取要更新的字段
    update_fields = update_content.model_dump(
        exclude={"user_list", "update_roles"}, exclude_none=True
    )

    if len(update_fields) == 0:
        return response(
            message="未获取到支持的更新字段 user_type | user_status | roles "
        ).fail()

    # 要更新的用户ID列表
    user_id_list = update_content.user_list
    if (
        request.state.user_id in user_id_list
        and isinstance(update_content.user_status, bool)
        and not update_content.user_status
    ):
        return response(message="您不能将自己禁用").fail()

    db_users = (
        await session.exec(
            select(Users).where(
                col(Users.id).in_(user_id_list)  # pylint: disable=no-member
            )
        )
    ).all()

    res_list: List[int] = []
    if len(db_users) == 0:
        return response(message="未查询到用户", data=res_list).fail()
    # 判断是否更新角色
    update_roles = update_content.update_roles
    # redis中缓存的kye 如果禁用要删除
    cache_kye = []
    for user in db_users:
        if "roles" in update_fields and update_roles:
            roles = update_content.roles
            # 先将角色清空
            user.roles.clear()
            if roles:
                user = await crud.update_roles_by_id(
                    session=session, user=user, roles_id_list=roles
                )
        if "user_status" in update_fields:
            user.user_status = update_content.user_status
            if update_content.user_status is False:
                cache_kye.append(f"jwt:{user.id}")
        if "user_type" in update_fields:
            user.user_type = update_content.user_type
        res_list.append(user.id)
        session.add(user)
    # 提交更改
    await session.commit()

    if update_content.user_status is False:
        # redis中批量删除token
        cache: Redis = request.app.state.cache
        p_cache = cache.pipeline()
        p_cache.delete(*cache_kye)
        await p_cache.execute()
    return response(message="更新完成", data=res_list).success()


@router.get("/query", summary="过滤用户列表", response_model=schema.UserQueryResponse)
async def auth_users_query(
    session: AsyncSessionDep,
    username: str = Query(None),
    nickname: str = Query(None),
    phone: str = Query(None),
    email: str = Query(None),
    user_type: int = Query(None),
    user_status: bool = Query(None),
    roles: int = Query(None),
    limit: int = 10,
    page: int = 1,
) -> Any:
    """
    过滤用户
    """
    response = schema.UserQueryResponse
    # 序列化查询参数
    query: Dict[str, Any] = {}
    if username:
        query.setdefault("username", username)
    if nickname:
        query.setdefault("nickname", nickname)
    if phone:
        query.setdefault("phone", phone)
    if email:
        query.setdefault("email", email)
    if user_type:
        query.setdefault("user_type", user_type)
    if user_status is not None:
        query.setdefault("user_status", user_status)
    if roles:
        query.setdefault("roles", roles)
    # 查询结果
    stmt = select(Users).filter_by(**query).limit(limit).offset(limit * (page - 1))
    query_data = (await session.exec(stmt)).all()
    # 用户总数
    query_total = (
        await session.exec(
            select(func.count()).select_from(Users)  # pylint: disable=not-callable
        )
    ).one()
    if not query_total:
        return response(message="查询结果为空!").success()
    # 分页总数
    page_total = math.ceil(query_total / limit)
    if page > page_total:
        return response(message="输入页数大于分页总数!").fail()
    # 过滤角色使user['roles']中只包含关联角色的id
    result = []
    for user in query_data:
        roles_id_list = (
            await session.exec(
                select(UsersRolesLink.auth_roles_id).where(
                    UsersRolesLink.auth_users_id == user.id
                )
            )
        ).all()
        format_user = user.model_dump()
        format_user["roles"] = roles_id_list
        result.append(format_user)
    # 序列化查询结果
    result = schema.UserQueryResult(
        result=result, total=query_total, page_total=page_total, page=page, limit=limit
    )

    return response(message="查询成功", data=result).success()


@router.post("/pwdset", summary="修改密码", response_model=schema.ResponseBase)
async def auth_users_pwdset(
    request: Request, session: AsyncSessionDep, req_data: schema.UserUpdatePassword
) -> Any:
    """
    修改密码

    `
    如果is_reset为true则自动生成并重置用户密码
    避免管理员权限过大任意修改用户密码
    `
    """
    response = schema.ResponseBase
    user_id = req_data.user_id
    user = await session.get(Users, user_id)
    if not user:
        return response(message="用户不存在").fail()
    if req_data.is_reset:
        new_password = await crud.reset_password(session=session, user=user)
        if user.email:
            send_email.delay(
                recipients=user.email,
                subject="密码重置通知",
                body={"username": user.nickname, "password": new_password},
                template_name="reset-password.html",
            )
        return response(
            message="重置成功", data={"new_password": new_password}
        ).success()

    if user_id != request.state.user_id:
        return response(message="您不能修改别人的密码").fail()
    password = req_data.password
    repassword = req_data.repassword
    if password != repassword:
        return response(message="两次密码不一致").fail()
    await crud.reset_password(session=session, user=user, password=password)
    return response(message="修改成功").success()


@router.post(
    "/otpreset/{user_id}", summary="重置TOTP", response_model=schema.ResponseBase
)
async def auth_users_otpreset(user_id: int, session: AsyncSessionDep) -> Any:
    """
    重置TOTP
    """
    response = schema.ResponseBase
    _totp = await get_redis_data("sys:settings", "security.totp")
    if not _totp:
        return response(message="系统未开启MFA登录").fail()
    user = await session.get(Users, user_id)
    if not user:
        return response(message="用户不存在").fail()
    user.totp = None
    session.add(user)
    await session.commit()
    if user.email:
        send_email.delay(
            recipients=user.email,
            subject="TOTP重置成功",
            body={"username": user.nickname},
            template_name="reset-totp.html",
            )
    return response(message="重置成功").success()
