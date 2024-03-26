from typing import Optional

# from pydantic import computed_field
from sqlmodel import Field, SQLModel

from app.core.base import ModelBase, ResponseBase
from app.models.auth_model import RolesBase


class RoleCreate(RolesBase):
    """
    创建角色
    """

    menus: Optional[list[int]] = Field(default=None, description="菜单id列表")


class RoleCreateResult(RolesBase, ModelBase):
    """
    创建角色结果
    """

    menus: Optional[list[int]] = Field(default=None, description="菜单id列表")


class RoleCreateResponse(ResponseBase):
    """
    创建角色响应
    """

    data: Optional[RoleCreateResult] = None


class RoleDeleteResponse(ResponseBase):
    """
    角色删除响应
    """

    data: Optional[dict] = {"id": 0}


class RoleUpdate(RoleCreate):
    """
    角色更新
    """

    name: Optional[str] = Field(default=None, max_length=32, description="角色标识")
    nickname: Optional[str] = Field(
        default=None, max_length=32, description="角色显示名称"
    )


class RoleUpdateResult(RoleCreateResult):
    """
    角色更新结果
    """


class RoleUpdateResponse(ResponseBase):
    """
    角色更新更新响应
    """

    data: Optional[RoleUpdateResult] = None


class RoleQuery(RolesBase, ModelBase):
    """
    角色过滤
    """

    user_count: Optional[int] = Field(default=None, description="关联用户数")
    menus: Optional[list[int]] = Field(default=None, description="菜单id列表")

    # @computed_field
    # @property
    # def user_count(self)->int:
    #     """
    #     用户数量
    #     """
    #     return len(self.users)


class RoleQueryResult(SQLModel):
    """
    角色过滤结果
    """

    result: Optional[list[RoleQuery]] = None


class RoleQueryResponse(ResponseBase):
    """
    角色列表响应
    """

    data: Optional[RoleQueryResult] = None
