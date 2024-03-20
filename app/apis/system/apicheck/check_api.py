from typing import Any
from fastapi import APIRouter

from app.base import ResponseBase
from app.extend.channels.email import send_mail
from app.extend.ldap.ldap_auth import LdapAuthMixin
from app.models.system_model import ldapConfig, mailServerSettings

from .check_schema import testLdapResponse

router = APIRouter()


@router.post("/email", summary="邮件测试接口", response_model=ResponseBase)
async def test_email(config: mailServerSettings, receive: str) -> Any:
    response = ResponseBase
    _res = await send_mail(
        recipients=receive,
        config=config.model_dump(),
        subject="配置测试通知",
        template_name="email-test.html",
    )
    if _res.get("code"):
        return response(message="Test Success").success()
    else:
        return response(message=_res.get("message")).fail()


@router.post("/ldap", summary="ldap测试接口", response_model=testLdapResponse)
async def test_ldap(config: ldapConfig, username: str) -> Any:
    response = testLdapResponse
    _config = config.model_dump()
    conn = LdapAuthMixin(**_config)
    _res = conn.search_user(username)
    if not _res.get("code"):
        return response(message=f"{_res.get('message')}", data=_res.get("data")).fail()
    if len(_res.get("data")) == 0:
        return response(
            message=f"{_res.get('message')}", data=_res.get("data")
        ).success()
    attributes = _config.get("attributes")
    _data = _res.get("data")[0].get("attributes")
    _emial = _data.get(attributes.get("email"))
    _phone = _data.get(attributes.get("phone"))
    data = {
        "username": _data.get(attributes.get("username"))[0],
        "nickname": _data.get(attributes.get("nickname"))[0],
        "email": _emial[0] if _emial else None,
        "phone": _phone[0] if _phone else None,
    }

    return response(message="Test Success", data=data).success()
