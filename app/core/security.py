import binascii
import time
from datetime import datetime, timedelta

import pyotp
from fastapi import Request
from IPy import IP
from jose import jwt
from loguru import logger

from app.apis.login.login_schema import AccessToken
from app.core.config import settings
from app.models.auth_model import Users
from app.utils.cache_tools import get_redis_data, redis_exists_key
from app.utils.ipaddress_tools import is_ip, is_ip_in_range
from app.utils.password_tools import get_password_hash, random_str

# openssl rand -hex 32
SECRET_KEY = settings.SECRET_JWT_KEY
ALGORITHM = settings.SECRET_JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.SECRET_JWT_EXP
REFRESH_TOKEN_EXPIRE_MINUTES = settings.SECRET_REJWT_EXP


def create_access_token(subject: dict, exp: int) -> str:
    """
    生成token
    :param exp:
    :param subject:需要存储到token的数据
    :return:
    """
    expires = int(time.mktime((datetime.now() + timedelta(minutes=exp)).timetuple()))
    subject.update(exp=expires)
    encoded_jwt: str = jwt.encode(subject, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def format_token(user: Users) -> AccessToken:
    """
    签发jwt
    :param user:
    :return:
    """
    jid = get_password_hash(random_str())
    username = user.username
    nickname = user.nickname
    user_id = user.id

    jwt_data = {"username": username, "user_id": user_id, "jid": jid}
    access_token = create_access_token(
        subject=jwt_data, exp=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    refresh_token = create_access_token(
        subject={"refresh_key": get_password_hash(f"{user_id}{jid}{username}")},
        exp=REFRESH_TOKEN_EXPIRE_MINUTES,
    )

    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": int(
            time.mktime(
                (
                    datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                ).timetuple()
            )
        ),
        "token_type": "Bearer",
        "user_id": user_id,
        "username": username,
        "nickname": nickname,
    }
    return AccessToken.model_validate(data)


def generate_totp(name: str, issuer_name: str = settings.SYS_TITLE) -> dict:
    """
    生成TOTP Key
    """
    key = pyotp.random_base32()
    data = pyotp.totp.TOTP(key).provisioning_uri(name=name, issuer_name=issuer_name)
    return {"key": key, "data": data}


def verify_totp(key: str, token: str) -> bool:
    """
    验证TOTP token
    """
    try:
        totp = pyotp.TOTP(key)
        return totp.verify(token)
    except binascii.Error as e:
        logger.error(f"binascii.Error - {e}")
        return False


async def get_client_ip(request: Request) -> str:
    """
    按照优先级获取request请求头中的客户端IP
    """
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if isinstance(x_forwarded_for, list) and x_forwarded_for:
        return x_forwarded_for[0]
    elif request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
    elif request.headers.get("X-Forwarded-Host"):
        return request.headers.get("X-Forwarded-Host")
    else:
        return request.client.host


async def verify_client_ip(client_ip: str) -> bool | None:
    """
    校验客户端IP是否允许访问
    """
    # 读取redis系统配置
    state = await redis_exists_key("sys:settings")
    if not state:
        return True
    # 读取redis系统配置中的安全设置
    security_settings = await get_redis_data("sys:settings", "security")
    # 判断是否开启了IP地址检查
    if not security_settings.get("ip_check"):
        return True
    # 根据IP地址检查模式获取不同模式的IP列表
    mode = security_settings.get("ip_check_mode")
    if mode == 1:
        ip_list = security_settings.get("ip_black_list")
    else:
        ip_list = security_settings.get("ip_white_list")
    if len(ip_list) == 0:
        return True
    # 判断client_ip 是否符合要求
    _ip_state = None
    for ip in ip_list:
        if is_ip(ip):
            if client_ip in IP(ip):
                _ip_state = not mode == 1
                break
            _ip_state = mode == 1
        else:
            if "-" in ip and is_ip_in_range(client_ip, ip):
                _ip_state = not mode == 1
                break
            _ip_state = False
    return _ip_state
