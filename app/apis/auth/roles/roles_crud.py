from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.auth_model import Menus, Roles

from . import roles_schema as schema


async def update_menus_by_id(
    session: AsyncSession, role: Roles, menus_id_list: list[int]
) -> Roles:
    """
    根据Roles ID更新User Roles字段
    """
    menus_list = (
        await session.exec(select(Roles).where(col(Menus.id).in_(menus_id_list)))
    ).all()
    role.menus = menus_list
    return role


async def create_role(
    session: AsyncSession, role_create: schema.RoleCreate
) -> schema.RoleCreateResult:
    """
    新建角色
    """
    menu_id_list = role_create.menus
    db_role = Roles.model_validate(
        role_create.model_dump(exclude={"menus"}),
    )
    if menu_id_list:
        db_role = await update_menus_by_id(session, db_role, menu_id_list)
    session.add(db_role)
    await session.commit()
    await session.refresh(db_role)
    res = schema.RoleCreateResult(**db_role.model_dump(), menus=menu_id_list)
    return res


async def update_role(
    session: AsyncSession, db_role: Roles, role_update: schema.RoleUpdate
) -> schema.RoleUpdateResult:
    """
    更新角色
    """
    menus_id_list = role_update.menus
    role_data = role_update.model_dump(exclude_unset=True, exclude={"menus"})
    db_role.sqlmodel_update(role_data)
    db_role.menus.clear()
    if menus_id_list:
        db_role = await update_menus_by_id(session, db_role, menus_id_list)
    session.add(db_role)
    await session.commit()
    await session.refresh(db_role)
    res = schema.RoleUpdateResult(**db_role.model_dump(), menus=menus_id_list)
    return res
