from typing import Any
from fastapi import APIRouter
from sqlmodel import select

from app.apis.deps import SessionDep
from app.models.auth_model import Roles, RolesMenusLink, UsersRolesLink
from . import roles_schema as schema
from . import roles_crud as crud

router = APIRouter()


@router.post("/add", summary="创建角色", response_model=schema.RoleCreateResponse)
async def auth_roles_add(session: SessionDep, create_roles: schema.RoleCreate) -> Any:
    response = schema.RoleCreateResponse
    stmt = select(Roles).where(Roles.name == create_roles.name)
    roles = session.exec(stmt).first()
    if roles:
        return response(message=f"对象 {create_roles.name} 已经存在!").fail()
    add_role = crud.create_role(session=session, role_create=create_roles)
    if not add_role:
        return response(message="创建失败").fail()
    return response(message="创建成功", data=add_role).success()


@router.delete(
    "/del/{role_id}", summary="删除角色", response_model=schema.RoleDeleteResponse
)
async def auth_roles_del(session: SessionDep, role_id: int) -> Any:
    """
    删除角色
    """
    response = schema.RoleDeleteResponse
    if role_id == 1:
        return response(message="不能删除平台内置角色！").fail()
    role = session.get(Roles, role_id)
    if not role:
        return response(message="角色不存在").fail()
    session.delete(role)
    session.commit()
    return response(message="删除成功", data={"id": role_id}).success()


@router.patch(
    "/set/{role_id}", summary="更新角色", response_model=schema.RoleUpdateResponse
)
async def auth_roles_set(
    session: SessionDep, role_id: int, update_role: schema.RoleUpdate
) -> Any:
    """
    更新角色
    """
    response = schema.RoleUpdateResponse
    db_role = session.get(Roles, role_id)
    if not db_role:
        return response(message="角色不存在").fail()
    result = crud.update_role(session, db_role, update_role)
    return response(message="更新成功", data=result).success()


@router.get("/list", summary="角色列表", response_model=schema.RoleQueryResponse)
async def auth_roles_list(session: SessionDep) -> Any:
    """
    角色列表
    """
    response = schema.RoleQueryResponse
    # 查询结果
    stmt = select(Roles).order_by("id")
    query_data = session.exec(stmt).all()

    # 过滤菜单使role[menus]中只包含关联菜单的id
    result = []
    for role in query_data:
        menus_id_list = session.exec(
            select(RolesMenusLink.auth_menus_id).where(
                RolesMenusLink.auth_roles_id == role.id
            )
        ).all()
        users_id_list = session.exec(
            select(UsersRolesLink.auth_users_id).where(
                UsersRolesLink.auth_roles_id == role.id
            )
        ).all()
        format_role = role.model_dump()
        format_role["menus"] = menus_id_list
        format_role["user_count"] = len(users_id_list)
        result.append(format_role)
    data = {"result": result}
    return response(message="查询成功", data=data).success()
