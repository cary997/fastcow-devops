from typing import Optional

from app.core.base import ResponseBase
from app.models.assets.assets_model import AssetsGroups, AssetsGroupsBase


class CreateAssetsGroups(AssetsGroupsBase):
    """
    创建主机分组
    """


class CreateAssetsGroupsResponse(ResponseBase):
    """
    创建主机分组响应
    """

    data: Optional[AssetsGroups] = None
