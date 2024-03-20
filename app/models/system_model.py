from enum import IntEnum
from typing import Optional
from sqlmodel import SQLModel, Field, JSON, BIGINT

from app.base import ModelBase
from app.utils.password_tools import aes_hash_password


class generalSettings(SQLModel):
    """
    常规设置
    """

    class watermarkContentEnum(IntEnum):
        """
        水印内容
        """

        username = 1
        nickname = 2
        username_nickname = 3

    class watermarkSizeEnum(IntEnum):
        """
        水印大小
        """

        compact = 1
        default = 2
        loose = 3

    user_default_password: Optional[str] = Field(
        default=aes_hash_password("FastApi@2024"), description="用户创建时静态密码"
    )
    user_default_roles: Optional[list[int]] = Field(
        default=[], description="用户默认角色"
    )
    watermark: Optional[bool] = Field(default=False, description="是否开启水印")
    watermarkContent: Optional[watermarkContentEnum] = Field(
        default=1, description="水印内容"
    )
    watermarkSize: Optional[watermarkSizeEnum] = Field(
        default=2, description="水印大小"
    )


class LdapAttributesMap(SQLModel):
    """
    ldap与平台用户字段映射
    """

    username: str = Field(default="sAMAccountName", description="username映射字段")
    nickname: str = Field(default="cn", description="nickname映射字段")
    email: str = Field(default="mail", description="email映射字段")
    phone: str = Field(default="telephoneNumber", description="phone映射字段")


class ldapConfig(SQLModel):
    """
    ldap连接设置
    """

    enable: Optional[bool] = Field(default=False, description="开启LDAP登录")
    hosts: Optional[list[str]] = Field(default=None, description="ldap server列表")
    user: Optional[str] = Field(default=None, description="用于连接ldap 的user dn")
    password: Optional[str] = Field(
        default=None, description="用于连接ldap 的user password"
    )
    base_ou: Optional[str] = Field(default=None, description="搜索起始的OU")
    attributes: LdapAttributesMap = Field(
        default=LdapAttributesMap(), description="ldap与平台用户字段映射"
    )
    paged_size: Optional[int] = Field(default=500, lt=1000, description="查询分页数")


class ldapSync(SQLModel):
    """
    ldap同步设置
    """

    class ldapSyncEnum(IntEnum):
        """
        ldap同步策略
        """

        system = 1
        ldap = 2

    enable: Optional[bool] = Field(default=False, description="启用同步")
    interval: Optional[int] = Field(default=120, gt=1, description="同步间隔（分钟）")
    default_status: Optional[bool] = Field(default=False, description="是否默认启用")
    sync_rule: Optional[ldapSyncEnum] = Field(
        default=1, description="冲突时策略 1以平台为主 2以ldap为主"
    )


class ldapSettings(SQLModel):
    """
    ldap配置
    """

    config: Optional[ldapConfig] = Field(
        default=ldapConfig(), description="LDAP连接配置"
    )
    sync: Optional[ldapSync] = Field(default=ldapSync(), description="LDAP同步配置")


class mailServerSettings(SQLModel):
    """
    邮件服务器设置
    """

    MAIL_SERVER: Optional[str] = Field(default=None, description="邮件服务器地址")
    MAIL_PORT: Optional[int] = Field(default=None, description="邮件服务器端口")
    MAIL_USERNAME: Optional[str] = Field(default=None, description="邮件服务器用户")
    MAIL_PASSWORD: Optional[str] = Field(default=None, description="邮件服务器密码")
    MAIL_FROM: Optional[str] = Field(default=None, description=" 发件人地址")
    MAIL_FROM_NAME: Optional[str] = Field(default=None, description="邮件标题")
    MAIL_STARTTLS: Optional[bool] = Field(
        default=True, description="用于 STARTTLS 连接"
    )
    MAIL_SSL_TLS: Optional[bool] = Field(default=False, description="用于 SSL 连接")
    USE_CREDENTIALS: Optional[bool] = Field(default=True, description="否登录到服务器")
    VALIDATE_CERTS: Optional[bool] = Field(
        default=True, description="是否验证邮件服务器证书"
    )


class channelsSeetings(SQLModel):
    """
    通知渠道设置
    """

    email: Optional[mailServerSettings] = mailServerSettings()


class securitySettings(SQLModel):
    """
    安全设置
    """

    class CheckModeTypeEnum(IntEnum):
        """
        IP地址校验模式
        """

        black_list = 1
        white_list = 2

    totp: Optional[bool] = Field(default=False, description="开启TOTP")
    ip_check: Optional[bool] = Field(default=False, description="IP地址校验")
    ip_check_mode: CheckModeTypeEnum = Field(default=1, description="IP地址校验模式")
    ip_black_list: Optional[list[str]] = Field(default=[], description="IP黑名单")
    ip_white_list: Optional[list[str]] = Field(default=[], description="IP白名单")


class SettingsBase(SQLModel):
    """
    系统设置基础模型
    """

    general: Optional[dict] = Field(
        sa_type=JSON,
        default=generalSettings().model_dump(),
        description="常规配置",
        nullable=True,
    )
    security: Optional[dict] = Field(
        sa_type=JSON,
        default=securitySettings().model_dump(),
        description="安全设置",
        nullable=True,
    )
    ldap: Optional[dict] = Field(
        sa_type=JSON,
        default=ldapSettings().model_dump(),
        description="ldap设置",
        nullable=True,
    )
    channels: Optional[dict] = Field(
        sa_type=JSON,
        default=channelsSeetings().model_dump(),
        description="通知渠道",
        nullable=True,
    )


class SystemSettings(SettingsBase, ModelBase, table=True):
    """

    系统设置表
    """

    __tablename__ = "sys_settings"
    id: Optional[int] = Field(
        sa_type=BIGINT,
        default=None,
        primary_key=True,
        sa_column_kwargs={"autoincrement": False},
    )
