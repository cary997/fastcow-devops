from typing import Optional, Union

from sqlmodel import Field

from app.core.base import ResponseBase
from app.models.assets.assets_model import AssetsFields


class FieldsResponse(ResponseBase):
    """
    获取字段配置响应模型
    """

    data: Optional[Union[AssetsFields, dict]] = Field(
        default=None, description="字段配置"
    )
