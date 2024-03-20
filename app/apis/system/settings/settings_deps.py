from fastapi import HTTPException
from loguru import logger
from sqlmodel import Session

from app.utils.ipaddress_tools import check_ip_list
from app.utils.password_tools import aes_hash_password, is_decrypt
from .settings_schema import SettingsBase
from app.models.system_model import SystemSettings


def get_or_create_settings(session: Session) -> SystemSettings:
    """
    获取或创建系统配置
    """
    settings = session.get(SystemSettings, 1)
    if not settings:
        try:
            settings = SystemSettings.model_validate(SystemSettings(id=1))
            session.add(settings)
            session.commit()
            session.refresh(settings)
            return settings
        except Exception as e:  # pylint: disable=broad-exception-caught
            session.rollback()
            logger.error(f"{e}")
    return settings


async def set_settings_depends(update_content: SettingsBase) -> dict:
    """
    更新系统配置
    """
    # 检查安全配置中的IP黑白名单中的IP是否符合规范
    ip_list = []
    update_dict = update_content.model_dump(exclude_unset=True, exclude_none=True)
    if "security" in update_dict:
        ip_white_list = update_dict.get("security").get("ip_white_list")
        ip_black_list = update_dict.get("security").get("ip_black_list")
        if bool(ip_white_list) or bool(ip_black_list):
            ip_list = [*ip_white_list, *ip_black_list]
    if bool(ip_list):
        check_state, failed_ip = await check_ip_list(ip_list)
        if not check_state:
            raise HTTPException(
                detail=f"请检查IP或IP范围格式 {failed_ip}", status_code=400
            )
    # general配置中的密码加密
    if "general" in update_dict:
        general = update_dict.get("general")
        user_default_password = general.get("user_default_password")
        if user_default_password is not None and not is_decrypt(user_default_password):
            update_dict["general"]["user_default_password"] = aes_hash_password(
                user_default_password
            )
    # ldap配置中的密码加密
    if "ldap" in update_dict:
        ldap = update_dict.get("ldap")
        ldap_password = ldap.get("password")
        if ldap_password is not None and not is_decrypt(ldap_password):
            update_dict["ldap"]["password"] = aes_hash_password(ldap_password)

    # channels配置中的密码加密
    if "channels" in update_dict:
        channels = update_dict.get("channels")
        mail_password = channels.get("email").get("MAIL_PASSWORD")
        if mail_password is not None and not is_decrypt(mail_password):
            update_dict["channels"]["email"]["MAIL_PASSWORD"] = aes_hash_password(
                mail_password
            )
    return update_dict
