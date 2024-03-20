from sqlmodel import Session, select, col

from app.models.auth_model import Roles, Menus
from . import roles_schema as schema


def update_menus_by_id(
    session: Session, role: Roles, menus_id_list: list[int]
) -> Roles:
    """
    根据Roles ID更新User Roles字段
    """
    menus_list = session.exec(
        select(Roles).where(col(Menus.id).in_(menus_id_list))
    ).all()
    role.menus = menus_list
    return role


def create_role(
    session: Session, role_create: schema.RoleCreate
) -> schema.RoleCreateResult:
    """
    新建角色
    """
    menu_id_list = role_create.menus
    db_role = Roles.model_validate(
        role_create.model_dump(exclude={"menus"}),
    )
    if menu_id_list:
        db_role = update_menus_by_id(session, db_role, menu_id_list)
    session.add(db_role)
    session.commit()
    session.refresh(db_role)
    res = schema.RoleCreateResult(**db_role.model_dump(), menus=menu_id_list)
    return res


def update_role(
    session: Session, db_role: Roles, role_update: schema.RoleUpdate
) -> schema.RoleUpdateResult:
    """
    更新角色
    """
    menus_id_list = role_update.menus
    role_data = role_update.model_dump(exclude_unset=True, exclude={"menus"})
    db_role.sqlmodel_update(role_data)
    db_role.menus.clear()
    if menus_id_list:
        db_role = update_menus_by_id(session, db_role, menus_id_list)
    session.add(db_role)
    session.commit()
    session.refresh(db_role)
    res = schema.RoleUpdateResult(**db_role.model_dump(), menus=menus_id_list)
    return res
