import hashlib
import uuid

from jose import jwt
from loguru import logger
from passlib import pwd
from passlib.context import CryptContext

from app.core.config import settings
from app.utils.encryption import AESCBC

# passlib密码加密不可解密为明文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# aes加密密码可解密为明文
aeshash = AESCBC(settings.SECRET_KEY, settings.SECRET_IV)


def random_str(text: str = None) -> str:
    """
    唯一随机字符串
    :return: str
    """
    if not text:
        text = str(uuid.uuid1())
    only = hashlib.md5(text.encode(encoding="UTF-8")).hexdigest()
    return str(only)


def generate_password(length: int) -> str:
    """
    生成随机密码
    """
    return pwd.genword(length=length, charset="ascii_72")


def verify_password(plain_password, hashed_password) -> bool:
    """
    passlib验证密码
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password) -> str:
    """
    passlib加密密码
    """
    return pwd_context.hash(password)


def aes_hash_password(password) -> str:
    """
    AES密码加密
    :param password:
    :return:
    """
    hash_res = aeshash.encrypt(password)
    if hash_res.get("code"):
        return hash_res.get("data")
    logger.error(f"AES加密失败 {hash_res.get('data')}")
    raise ValueError("AES加密失败")


def aes_decrypt_password(hash_password) -> str:
    """
    AES密码解密
    :param hash_password:
    :return:
    """

    hash_res = aeshash.decrypt(hash_password)
    if hash_res.get("code"):
        return hash_res.get("data")
    logger.error(f"AES解密失败 {hash_res.get('data')}")
    raise ValueError("AES解密失败")


def aes_verify_password(password, old_password) -> bool:
    """
    AES密码校验
    :param password: 输入的密码
    :param old_password: 数据库中的密码
    :return:
    """
    re_password = aes_hash_password(password)
    if re_password == old_password:
        return True
    return False


def is_decrypt(text) -> bool:
    """
    判读密码是否能正常解密 能解密说明已经加密过
    """
    try:
        aes_decrypt_password(text)
        return True
    except ValueError:
        return False


def jwt_decode(token, verify_exp=True) -> str:
    """
    jwt解密
    :param token:
    :param verify_exp:
    :return:
    """

    # token解密
    payload = jwt.decode(
        token,
        settings.SECRET_JWT_KEY,
        algorithms=[settings.SECRET_JWT_ALGORITHM],
        options={"verify_exp": verify_exp},
    )
    return payload


if __name__ == "__main__":
    test = aes_hash_password("bmaftjggvxbibeae12atg541")
    print(test)
    print(is_decrypt("zcqeqzyablobbfhc"))
    print(generate_password(12))
