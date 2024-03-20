from typing import Annotated, Any
from fastapi import APIRouter, Depends

from app.apis.deps import SessionDep
from .settings_deps import get_or_create_settings, set_settings_depends
from app.utils.cache_tools import get_redis_data, redis_exists_key, set_redis_data
from . import settings_schema as schema

router = APIRouter()


@router.get("/get", summary="获取系统配置", response_model=schema.SettingsResponse)
async def get_settings(session: SessionDep) -> Any:
    """
    获取系统配置
    """
    response = schema.SettingsResponse
    cache_state = await redis_exists_key("sys:settings")
    if not cache_state:
        data = get_or_create_settings(session=session)
        await set_redis_data("sys:settings", value=data.model_dump())
    else:
        data = await get_redis_data("sys:settings")
    return response(message="查询成功", data=data).success()


@router.patch("/set", summary="更新系统配置", response_model=schema.SettingsResponse)
async def set_settings(
    session: SessionDep, update_content: Annotated[dict, Depends(set_settings_depends)]
)-> Any:
    """
    更新系统配置
    """
    response = schema.SettingsResponse
    # 查询结果
    db_settings = get_or_create_settings(session=session)

    # 更新并缓存
    settings = db_settings.sqlmodel_update(update_content)
    session.add(settings)
    session.commit()
    session.refresh(settings)
    await set_redis_data("sys:settings", value=settings.model_dump())
    return response(message="更新成功", data=settings).success()
