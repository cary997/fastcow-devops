from enum import IntEnum
from typing import List, Optional

from sqlmodel import BIGINT, JSON, Field, Relationship, SQLModel

from app.core.base import ModelBase


class UserTypeEnum(IntEnum):
    """
    用户类型枚举
    """

    local = 1
    ldap = 2


class UsersBase(SQLModel):
    """
    用户基础模型
    """

    nickname: str = Field(default=..., max_length=32, description="显示名称")
    phone: Optional[str] = Field(
        default=None, max_length=20, nullable=True, unique=True, description="手机号"
    )
    email: Optional[str] = Field(
        default=None, max_length=128, nullable=True, description="邮箱"
    )
    user_type: UserTypeEnum = Field(
        default=UserTypeEnum.local, description="用户类型(1=local,2=ldap)"
    )
    user_status: Optional[bool] = Field(
        default=True, description="True:启用 False:禁用"
    )
    totp: Optional[str] = Field(
        default=None, max_length=64, nullable=True, description="otp Key"
    )


class RolesBase(SQLModel):
    """
    角色基础模型
    """

    name: str = Field(default=..., max_length=32, description="角色标识")
    nickname: str = Field(default=..., max_length=32, description="角色显示名称")
    desc: Optional[str] = Field(
        default=None, max_length=64, nullable=True, description="描述"
    )
    role_status: Optional[bool] = Field(
        default=True, description="True:启用 False:禁用"
    )


class MenuMeta(SQLModel):
    """
    菜单元数据
    """

    class MenusTypeEnum(IntEnum):
        """
        菜单类型枚举
        """

        directory = 1
        pages = 2
        button = 3
        extlink = 4

    title: str = Field(description="中文标题")
    en_title: str = Field(description="英文标题")
    menu_type: Optional[MenusTypeEnum] = Field(
        description="菜单类型(directory=1,pages=2,button=3,extlink=4"
    )
    icon: Optional[str] = Field(default=None, description="图标")
    showLink: Optional[bool] = Field(default=True, description="是否在菜单中显示")
    showParent: Optional[bool] = Field(default=True, description="是否显示父级菜单")
    keepAlive: Optional[bool] = Field(default=False, description="是否缓存页面")
    frameSrc: Optional[str] = Field(default=None, description="内嵌的iframe链接")
    frameLoading: Optional[bool] = Field(
        default=True, description="是否开启首次加载动画"
    )
    hiddenTag: Optional[bool] = Field(default=False, description="是否在标签页隐藏")
    enterTransition: Optional[str] = Field(default=None, description="页面进入动画")
    leaveTransition: Optional[str] = Field(default=None, description="页面离开动画")
    rank: Optional[int] = Field(
        default=None, description="菜单排序针对directory类型生效"
    )


class MenusBase(SQLModel):
    """
    菜单基础模型
    """

    path: str = Field(default=..., max_length=512, description="url")
    name: str = Field(default=..., max_length=512, description="唯一标识或外链链接")
    redirect: Optional[str] = Field(
        default=None, max_length=512, nullable=True, description="重定向url"
    )
    component: Optional[str] = Field(
        default=None, max_length=512, nullable=True, description="组件路径"
    )
    meta: Optional[MenuMeta] = Field(
        default=None, sa_type=JSON, nullable=True, description="菜单元数据"
    )
    parent: Optional[int] = Field(default=None, nullable=True, description="上级菜单")


# -----------------------------------------------数据库表------------------------------------------------------------------


class UsersRolesLink(SQLModel, table=True):
    """
    用户角色关联表
    """

    __tablename__ = "auth_users_roles"

    auth_users_id: Optional[int] = Field(
        sa_type=BIGINT, default=None, foreign_key="auth_users.id", primary_key=True
    )
    auth_roles_id: Optional[int] = Field(
        sa_type=BIGINT, default=None, foreign_key="auth_roles.id", primary_key=True
    )


class RolesMenusLink(SQLModel, table=True):
    """
    角色菜单关联表
    """

    __tablename__ = "auth_roles_menus"

    auth_roles_id: Optional[int] = Field(
        sa_type=BIGINT, default=None, foreign_key="auth_roles.id", primary_key=True
    )
    auth_menus_id: Optional[int] = Field(
        sa_type=BIGINT, default=None, foreign_key="auth_menus.id", primary_key=True
    )


class Users(UsersBase, ModelBase, table=True):
    """
    用户表
    """

    __tablename__ = "auth_users"
    username: str = Field(default=..., max_length=32, description="用户名")
    password: str = Field(default=..., max_length=128, description="密码")
    roles: List["Roles"] = Relationship(
        back_populates="users",
        link_model=UsersRolesLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class Roles(RolesBase, ModelBase, table=True):
    """
    角色表
    """

    __tablename__ = "auth_roles"

    users: List["Users"] = Relationship(
        back_populates="roles",
        link_model=UsersRolesLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    menus: List["Menus"] = Relationship(
        back_populates="roles",
        link_model=RolesMenusLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class Menus(MenusBase, ModelBase, table=True):
    """
    菜单
    """

    __tablename__ = "auth_menus"

    roles: List["Roles"] = Relationship(
        back_populates="menus", link_model=RolesMenusLink
    )
