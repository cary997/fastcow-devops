from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.base import ModelBase, ResponseBase
from app.models.auth_model import Roles, UsersBase


class UserCreate(UsersBase):
    """
    创建用户
    """

    username: str = Field(default=..., max_length=32, description="用户名")
    password: str = Field(default=..., max_length=128, description="密码")
    roles: Optional[list[int]] = Field(default=None, description="角色ID列表")


class UserCreateResult(UsersBase, ModelBase):
    """
    用户创建结果
    """

    username: Optional[str] = Field(default=None, max_length=32, description="用户名")
    roles: Optional[list[int]] = Field(default=None, description="角色ID列表")


class UserCreateResponse(ResponseBase):
    """
    用户创建响应
    """

    data: Optional[UserCreateResult] = None


class UserDeleteResponse(ResponseBase):
    """
    单用户删除响应
    """

    data: dict[str, int] = {"id": 0}


class UserBulkDelete(SQLModel):
    """
    批量用户删除请求
    """

    user_list: list[int] = Field(description="用户ID列表")


class UserBulkDeleteResponse(ResponseBase):
    """
    批量用户删除响应
    """

    data: Optional[list[int]] = []


class UserUpdate(UsersBase):
    """
    更新用户
    """

    nickname: Optional[str] = Field(default=None, max_length=32, description="显示名称")
    roles: Optional[list[int]] = Field(default=None, description="角色列表")
    update_roles: bool = Field(
        default=False,
        description="是否要更新角色，更新则必须设置为true，此字段为了角色清空等场景",
    )


class UserUpdateResult(UserCreateResult):
    """
    更新用户结果
    """


class UserUpdateResponse(UserCreateResponse):
    """
    更新用户响应
    """


class UserBulkUpdate(SQLModel):
    """
    批量用户更新请求
    """

    user_list: list[int] = Field(description="用户ID列表")
    user_type: Optional[int] = Field(default=None, description="用户类型")
    user_status: Optional[bool] = Field(default=None, description="用户状态")
    roles: Optional[list[int]] = Field(default=None, description="角色列表")
    update_roles: bool = Field(
        default=False,
        description="是否要更新角色，更新则必须设置为true，此字段为了角色清空等场景",
    )


class UserBulkUpdateResponse(ResponseBase):
    """
    批量用户更新响应
    """

    data: Optional[list[int]] = None


class UserReadWithRoles(UsersBase, ModelBase):
    """
    用户读取包含关联角色
    """
    username: str = Field(default=..., max_length=32, description="用户名")
    roles: list[Roles] = []


class UserReadWithRolesResponse(ResponseBase):
    """
    用户读取包含关联角色 响应
    """

    data: Optional[UserReadWithRoles] = None


class UserQueryResult(SQLModel):
    """
    用户过滤结果
    """

    result: Optional[list[UserCreateResult]] = None
    total: Optional[int] = None
    page_total: Optional[int] = None
    page: Optional[int] = None
    limit: Optional[int] = None


class UserQueryResponse(ResponseBase):
    """
    用户过滤响应
    """

    data: Optional[UserQueryResult] = None


class UserUpdatePassword(SQLModel):
    """
    更新用户密码
    """

    user_id: int
    is_reset: Optional[bool] = Field(default=False, description="是否重置密码")
    password: str = Field(default=None, description="新密码")
    repassword: str = Field(default=None, description="确认密码")
