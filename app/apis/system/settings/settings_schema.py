from typing import Optional, Union

from sqlmodel import Field, SQLModel
from app.base import ResponseBase, ModelBase
from app.models.system_model import (
    generalSettings,
    securitySettings,
    ldapSettings,
    channelsSeetings,
)


class SettingsBase(SQLModel):
    """
    配置基础可更新字段
    """
    general: Optional[generalSettings] = Field(
        default=None,
        description="常规配置",
        nullable=True,
    )
    security: Optional[securitySettings] = Field(
        default=None,
        description="安全设置",
        nullable=True,
    )
    ldap: Optional[ldapSettings] = Field(
        default=None,
        description="ldap设置",
        nullable=True,
    )
    channels: Optional[channelsSeetings] = Field(
        default=None,
        description="通知渠道",
        nullable=True,
    )


class Settings(ModelBase, SettingsBase):
    """
    配置查询结果
    """


class SettingsResponse(ResponseBase):
    """
    获取系统配置响应
    """

    data: Optional[Union[Settings, dict]] = Field(default=None, description="完整配置")
