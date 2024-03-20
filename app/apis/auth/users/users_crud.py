from sqlmodel import Session, col, or_, select

from app.models.auth_model import Roles, Users
from app.utils.password_tools import generate_password, get_password_hash

from . import users_schema as schema


def get_user_name_or_phone(
    *, session: Session, username: str, phone: str
) -> Users | None:
    """
    username查找用户
    """
    stmt = select(Users).where(or_(Users.username == username, Users.phone == phone))
    user = session.exec(stmt).first()
    return user


def update_roles_by_id(
    session: Session, user: Users, roles_id_list: list[int]
) -> Users:
    """
    根据Roles ID更新User Roles字段
    """
    roles_list = session.exec(
        select(Roles).where(col(Roles.id).in_(roles_id_list))
    ).all()
    user.roles = roles_list
    return user


def create_user(
    session: Session, user_create: schema.UserCreate
) -> schema.UserCreateResult:
    """
    添加用户
    """
    roles_id_list = user_create.roles
    db_user = Users.model_validate(
        user_create.model_dump(exclude={"roles"}),
        update={"password": get_password_hash(user_create.password)},
    )
    if roles_id_list:
        db_user = update_roles_by_id(session, db_user, roles_id_list)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    res = schema.UserCreateResult(**db_user.model_dump(), roles=roles_id_list)
    return res


def update_user(
    session: Session, db_user: Users, user_update: schema.UserUpdate
) -> schema.UserUpdateResult:
    """
    更新单用户
    """
    roles_id_list = user_update.roles
    user_data = user_update.model_dump(
        exclude_unset=True, exclude={"roles", "update_roles"}
    )
    db_user.sqlmodel_update(user_data)
    if user_update.update_roles:
        db_user.roles.clear()
    if roles_id_list:
        db_user = update_roles_by_id(session, db_user, roles_id_list)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    res = schema.UserUpdateResult(**db_user.model_dump(), roles=roles_id_list)
    return res


def reset_password(session: Session, user: Users, password: str | None = None) -> str:
    """
    重置或更新密码
    """
    if password is None:
        password = generate_password(12)
    user.sqlmodel_update({"password": get_password_hash(password)})
    session.add(user)
    session.commit()
    return password
