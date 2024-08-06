from fastapi import APIRouter
from sqlmodel import func, select

from app.depends import AsyncSessionDep
from app.models.assets.assets_model import AssetsGroups

from . import groups_schema as schema

router = APIRouter()


@router.post(
    "/add", summary="添加group信息", response_model=schema.CreateAssetsGroupsResponse
)
async def assets_group_add(
    session: AsyncSessionDep, create_group: schema.CreateAssetsGroups
):
    response = schema.CreateAssetsGroupsResponse
    group = (
        await session.exec(
            select(AssetsGroups).where(AssetsGroups.name == create_group.name)
        )
    ).one_or_none()
    if group:
        return response(message="分组已存在").fail()
    group = AssetsGroups.model_validate(create_group.model_dump())
    session.add(group)
    await session.commit()
    return response(message="添加成功", data=group).success()


@router.delete(
    "/del/{gid}", summary="删除group", response_model=schema.CreateAssetsGroupsResponse
)
async def assets_group_del(session: AsyncSessionDep, gid: int):
    group = await session.get(AssetsGroups, gid)
    if not group:
        return schema.CreateAssetsGroupsResponse(message="组不存在").fail()
    children =(await session.exec(select(AssetsGroups).where(AssetsGroups.parent == gid)))
    await session.delete(group)
    await session.commit()
    return schema.CreateAssetsGroupsResponse(message="删除成功",data=group).success()
