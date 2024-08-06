from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from app.depends import AsyncSessionDep
from app.utils.cache_tools import get_redis_data, redis_exists_key, set_redis_data

from . import fields_schema as schema
from .fields_deps import get_or_create_fields, set_fields_depends

router = APIRouter()


@router.get("/get", summary="获取字段配置", response_model=schema.FieldsResponse)
async def assets_fields_get(session: AsyncSessionDep) -> Any:
    """
    获取系统配置
    """
    response = schema.FieldsResponse
    cache_state = await redis_exists_key("assets:fields")
    if not cache_state:
        data = await get_or_create_fields(session=session)
        await set_redis_data("assets:fields", value=data.model_dump())
    else:
        data = await get_redis_data("assets:fields")
    return response(message="查询成功", data=data).success()


@router.patch("/set", summary="更新字段配置", response_model=schema.FieldsResponse)
async def assets_fields_set(
    session: AsyncSessionDep,
    update_content: Annotated[dict, Depends(set_fields_depends)],
) -> Any:
    """
    更新字段配置
    """
    response = schema.FieldsResponse
    # 查询结果
    db_fields = await get_or_create_fields(session=session)

    # 更新并缓存
    fields = db_fields.sqlmodel_update(update_content)
    session.add(fields)
    await session.commit()
    await session.refresh(fields)
    await set_redis_data(
        "assets:fields",
        value=fields.model_dump(),
    )
    return response(message="更新成功", data=fields).success()
