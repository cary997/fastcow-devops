from typing import Optional, Union

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from app.core.base import ResponseBase
from app.models.system_model import SystemSettings


class SettingsResponse(ResponseBase):
    """
    获取系统配置响应
    """

    data: Optional[Union[SystemSettings, dict]] = Field(
        default=None, description="完整配置"
    )


class LdapSyncResult(BaseModel):
    """
    ldap同步结果
    """

    code: int = Field(default=0, description="状态")
    message: Optional[str] = Field(default=None, description="提示信息")
    date_done: Optional[str] = Field(default=None, description="完成时间")
    user_num: Optional[int] = Field(default=0, description="同步总数")
    skip_num: Optional[int] = Field(default=0, description="已存在并跳过数量")
    update_num: Optional[int] = Field(default=0, description="更新数量")
    create_num: Optional[int] = Field(default=0, description="新建数量")


class LdapSyncResultResponse(ResponseBase):
    """
    ldap同步任务结果
    """

    data: Optional[list[LdapSyncResult]] = None
