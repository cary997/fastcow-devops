from typing import Optional
from sqlmodel import Field, SQLModel

from app.base import ResponseBase


class ldapSearchUserResults(SQLModel):
    """
    ldap测试接口搜索用户结果
    """
    username: str = Field(default=None, description="用户名")
    nickname: str = Field(default=None, description="显示名")
    email: str = Field(default=None, description="邮箱")
    phone: str = Field(default=None, description="手机")


class testLdapResponse(ResponseBase):
    """
    ldap测试接口响应
    """
    data: Optional[ldapSearchUserResults] = None
