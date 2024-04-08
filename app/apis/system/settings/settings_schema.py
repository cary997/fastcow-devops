from typing import Optional, Union

from pydantic import BaseModel, computed_field
from sqlmodel import Field, SQLModel

from app.core.base import ModelBase, ResponseBase
from app.core.config import settings
from app.models.system_model import (
    channelsSeetings,
    generalSettings,
    ldapSettings,
    securitySettings,
)


class PathSettings(BaseModel):
    """
    系统路径设置
    """

    base_path: Optional[str] = Field(
        default=settings.DATA_PATH,
        description="基础路径",
    )
    tasks_templates_path: Optional[str] = Field(
        default=settings.tasks_templates_path,
        description="任务模版存放路径",
    )
    upload_temp_path: Optional[str] = Field(
        default=settings.upload_temp_path,
        description="上传文件临时路径",
    )
    download_temp_path: Optional[str] = Field(
        default=settings.download_tmp_path,
        description="下载文件临时路径",
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

    @computed_field
    def system_path(self) -> dict:
        return PathSettings().model_dump()


class Settings(ModelBase, SettingsBase):
    """
    配置查询结果
    """


class SettingsResponse(ResponseBase):
    """
    获取系统配置响应
    """

    data: Optional[Union[Settings, dict]] = Field(default=None, description="完整配置")


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
