from typing import Any

from fastapi import APIRouter, Query
from sqlmodel import col, select

from app.depends import AsyncSessionDep
from app.models.auth_model import Menus
from app.utils.format_tools import ToTree

from . import menus_schema as schema

router = APIRouter()


@router.post("/add", summary="创建菜单", response_model=schema.MenuCreateResponse)
async def auth_menus_add(
    session: AsyncSessionDep, create_menu: schema.MenuCreate
) -> Any:
    """
    创建菜单
    """
    response = schema.MenuCreateResponse
    # 判断菜单是否存在
    stmt = select(Menus).where((col(Menus.name) == create_menu.name))
    menu = (await session.exec(stmt)).first()
    if menu:
        return response(message=f"对象 {create_menu.name} 已存在").fail()
    db_menu = Menus.model_validate(create_menu)
    session.add(db_menu)
    await session.commit()
    await session.refresh(db_menu)
    return response(message="创建成功", data=db_menu).success()


@router.delete(
    "/del/{menu_id}", summary="删除菜单", response_model=schema.MenuDeleteResponse
)
async def auth_menus_del(session: AsyncSessionDep, menu_id: int) -> Any:
    """
    删除菜单
    """
    response = schema.MenuDeleteResponse
    menu = await session.get(Menus, menu_id)
    if not menu:
        return response(message="对象不存在", data={"id": menu_id}).fail()
    session.delete(menu)
    await session.commit()
    return response(message="删除成功", data={"id": menu_id}).success()


@router.patch(
    "/set/{menu_id}", summary="更新菜单", response_model=schema.MenuUpdateResponse
)
async def auth_menus_set(
    session: AsyncSessionDep, menu_id: int, update_menu: schema.MenuUpdate
) -> Any:
    """
    更新菜单
    """
    response = schema.MenuUpdateResponse
    menu = await session.get(Menus, menu_id)
    if not menu:
        return response(message="对象不存在").fail()
    menu_data = update_menu.model_dump(exclude_unset=True)
    menu.sqlmodel_update(menu_data)
    session.add(menu)
    await session.commit()
    await session.refresh(menu)
    return response(message="更新成功", data=menu).success()


@router.get("/list", summary="菜单列表", response_model=schema.MenuQueryResponse)
async def auth_menus_list(session: AsyncSessionDep, to_tree: bool = Query(True)) -> Any:
    """
    过滤菜单
    """
    response = schema.MenuQueryResponse
    # 查询结果
    query_data = (await session.exec(select(Menus))).all()
    # 格式化为树
    if to_tree:
        query_data = ToTree(query_data, True, "meta.rank").list_to_tree()
    data = {"result": query_data}
    return response(message="查询成功", data=data).success()
