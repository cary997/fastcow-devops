from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.base import ResponseBase, ModelBase
from app.models.auth_model import Menus, MenusBase


class MenuCreate(MenusBase):
    """
    创建菜单
    """


class MenuCreateResponse(ResponseBase):
    """
    创建菜单响应
    """

    data: Optional[Menus]


class MenuDeleteResponse(ResponseBase):
    """
    菜单删除响应
    """

    data: Optional[dict] = {"menu_id": 0}


class MenuUpdate(MenusBase, ModelBase):
    """
    更新菜单
    """

    path: Optional[str] = Field(default=None, max_length=512, description="url")
    name: Optional[str] = Field(
        default=None, max_length=512, description="唯一标识或外链链接"
    )


class MenuUpdateResult(MenusBase):
    """
    菜单更新结果
    """


class MenuUpdateResponse(ResponseBase):
    """
    菜单更新响应
    """

    data: Optional[MenuUpdateResult] = None


class MenuTreeResult(MenusBase, ModelBase):
    """
    菜单树结果
    """

    parent_key: Optional[str] = Field(default=None, description="上级节点name")
    children: Optional[list] = Field(default=[], description="子节点")


class MenuQueryResult(SQLModel):
    """
    菜单查询结果
    """

    result: Optional[list[MenuTreeResult]] = None


class MenuQueryResponse(ResponseBase):
    """
    菜单过滤响应
    """

    data: Optional[MenuQueryResult | list[Menus]] = None
