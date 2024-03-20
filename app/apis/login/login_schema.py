from typing import Optional

from fastapi import Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Field, SQLModel
from app.base import ModelBase, ResponseBase
from app.models.auth_model import MenusBase


class totpResult(SQLModel):
    """
    用户初次MFA登录响应
    """

    totp: Optional[bool] = Field(default=False, title="TOTP设置是否开启")
    new: Optional[bool] = Field(default=False, title="用户是否未绑定令牌")
    new_totp: Optional[str] = Field(default=None, title="新生成令牌绑定链接")


class AccessToken(SQLModel):
    """
    access token 内容
    """

    access_token: Optional[str] = Field(default=None, title="令牌")
    refresh_token: Optional[str] = Field(default=None, title="刷新令牌")
    expires_in: Optional[int] = Field(default=None, title="过期时间")
    token_type: Optional[str] = Field(default=None, title="令牌类型")
    user_id: Optional[int] = Field(default=None, title="用户ID")
    username: Optional[str] = Field(default=None, title="用户名")
    nickname: Optional[str] = Field(default=None, title="显示名")


class AccessResponse(ResponseBase):
    """
    登录后响应
    access_token & token_type是为了swagger验证使用
    """

    data: Optional[AccessToken | totpResult] = Field(default=None, title="令牌信息")
    access_token: Optional[str] = Field(default=None, title="令牌(用于swagger认证)")
    token_type: Optional[str] = Field(default=None, title="令牌类型(用于swagger认证)")


class RefreshToken(SQLModel):
    """
    access token 刷新请求
    """

    access_token: Optional[str] = Field(default=None, title="令牌")
    expires_in: Optional[int] = Field(default=None, title="过期时间")
    refresh_token: Optional[str] = Field(default=None, title="刷新令牌")


class RefreshResponse(ResponseBase):
    """
    刷新令牌响应
    """

    data: Optional[AccessToken] = Field(default=None, title="令牌信息")


class LoginRequestForm(OAuth2PasswordRequestForm):
    """
    登录请求表单
    """

    def __init__(
        self,
        grant_type: str = Form(default="password", description="验证方式"),
        username: str = Form(description="账户"),
        password: Optional[str] = Form(description="密码"),
        scope: str = Form(default="", description="作用域"),
        client_id: Optional[str] = Form(default=None),
        client_secret: Optional[str] = Form(default=None),
        totp_code: Optional[str] = Form(default=None, description="totp验证码"),
    ):
        super().__init__(
            grant_type=grant_type,
            username=username,
            password=password,
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
        )
        self.totp_code = totp_code


class MenusTree(MenusBase, ModelBase):
    """
    菜单树结果
    """

    parent_key: Optional[str] = Field(default=None, description="上级节点name")
    children: Optional[list] = Field(default=[], description="子节点")


class MenusTreeResponse(ResponseBase):
    """
    同步动态路由响应
    """

    data: list[MenusTree]
