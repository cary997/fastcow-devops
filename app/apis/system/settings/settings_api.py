from typing import Annotated, Any

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Request
from sqlmodel import select

from app.depends import AsyncSessionDep
from app.ext.ldap_tsk.tasks import ldap_sync
from app.models.tasks_model import TaskMeta
from app.utils.cache_tools import get_redis_data, redis_exists_key, set_redis_data
from app.utils.datetime_tools import utc_to_local

from . import settings_schema as schema
from .settings_deps import (
    add_ldap_sync_interval_task,
    get_or_create_settings,
    set_settings_depends,
)

router = APIRouter()


@router.get("/get", summary="获取系统配置", response_model=schema.SettingsResponse)
async def get_settings(session: AsyncSessionDep) -> Any:
    """
    获取系统配置
    """
    response = schema.SettingsResponse
    cache_state = await redis_exists_key("sys:settings")
    if not cache_state:
        data = await get_or_create_settings(session=session)
        await set_redis_data("sys:settings", value=data.model_dump())
    else:
        data = await get_redis_data("sys:settings")
    return response(message="查询成功", data=data).success()


@router.patch("/set", summary="更新系统配置", response_model=schema.SettingsResponse)
async def set_settings(
    session: AsyncSessionDep,
    req: Request,
    update_content: Annotated[dict, Depends(set_settings_depends)],
) -> Any:
    """
    更新系统配置
    """
    response = schema.SettingsResponse
    # 查询结果
    db_settings = await get_or_create_settings(session=session)

    # 更新并缓存
    settings = db_settings.sqlmodel_update(update_content)
    session.add(settings)
    await session.commit()
    await session.refresh(settings)
    await set_redis_data(
        "sys:settings",
        value=settings.model_dump(exclude={"ansible_model_list", "system_path"}),
    )
    if "ldap" in update_content:
        # 更新ldap定时同步
        await add_ldap_sync_interval_task(session=session, username=req.state.username)
    return response(message="更新成功", data=settings).success()


@router.post("/syncldap", summary="ldap触发同步", response_model=schema.ResponseBase)
async def syncldap():
    response = schema.ResponseBase
    ldap_sync.delay()
    return response(message="任务已开始执行").success()


@router.get(
    "/syncldap_result",
    summary="ldap同步结果",
    response_model=schema.LdapSyncResultResponse,
)
async def sync_ldap_result(session: AsyncSessionDep):
    response = schema.LdapSyncResultResponse
    task_id_list = (
        await session.exec(
            select(TaskMeta.task_id)
            .where(TaskMeta.name == "tasks.ldap_sync")
            .order_by(-TaskMeta.date_done)  # pylint: disable=invalid-unary-operand-type
        )
    ).all()
    if not task_id_list:
        return response(message="查询成功", data=[])
    results = []
    for task_id in task_id_list:
        task_result = AsyncResult(task_id)
        sync_result = task_result.result
        dete_done = task_result.date_done
        result = sync_result.get("data")
        if not result:
            result = {}
        result["code"] = sync_result.get("code")
        result["message"] = f"{sync_result.get('message')}"
        result["date_done"] = utc_to_local(dete_done).strftime("%Y-%m-%d %H:%M:%S")
        results.append(result)
    return response(message="查询成功", data=results).success()
