from fastapi import HTTPException
from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ext.ldap_tsk.utils import get_ldap_sync_conf
from app.ext.sqlmodel_celery_beat.models import (
    IntervalPeriod,
    IntervalSchedule,
    PeriodicTask,
)
from app.models.system_model import SettingsBase, SystemSettings
from app.utils.ipaddress_tools import check_ip_list
from app.utils.password_tools import aes_hash_password, is_decrypt


async def get_or_create_settings(session: AsyncSession) -> SystemSettings:
    """
    获取或创建系统配置
    """
    settings = await session.get(SystemSettings, 1)
    if not settings:
        try:
            settings = SystemSettings.model_validate(SystemSettings(id=1))
            session.add(settings)
            await session.commit()
            await session.refresh(settings)
            return settings
        except Exception as e:  # pylint: disable=broad-exception-caught
            await session.rollback()
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
        user_default_password = (
            general.get("user_default_password") if general else None
        )
        if user_default_password is not None and not is_decrypt(user_default_password):
            update_dict["general"]["user_default_password"] = aes_hash_password(
                user_default_password
            )
    # ldap配置中的密码加密
    if "ldap" in update_dict:
        ldap = update_dict.get("ldap")
        ldap_config = ldap.get("config") if ldap else None
        ldap_password = ldap_config.get("password") if ldap_config else None
        if ldap_password is not None and not is_decrypt(ldap_password):
            update_dict["ldap"]["config"]["password"] = aes_hash_password(ldap_password)
    # channels配置中的密码加密
    if "channels" in update_dict:
        channels = update_dict.get("channels")
        mail_config = channels.get("email") if channels else None
        mail_password = mail_config.get("mail_password") if mail_config else None
        if mail_password is not None and not is_decrypt(mail_password):
            update_dict["channels"]["email"]["MAIL_PASSWORD"] = aes_hash_password(
                mail_password
            )
    return update_dict


async def add_ldap_sync_interval_task(session: AsyncSession, username: str = "admin"):
    """
    添加ldap定时同步任务
    """
    sync_config = get_ldap_sync_conf()
    task = (
        await session.exec(
            select(PeriodicTask).where(PeriodicTask.task == "tasks.ldap_sync")
        )
    ).one_or_none()
    schedule = IntervalSchedule(
        every=sync_config.interval, period=IntervalPeriod.MINUTES
    )
    if task:
        scheduler = task.scheduled
        scheduler.sqlmodel_update(schedule.model_dump(exclude_unset=True))
        task.interval = schedule
        task.enabled = sync_config.enable
        task.user_by = username
    else:
        task = PeriodicTask(
            name="ldap_sync",
            task="tasks.ldap_sync",
            types="system",
            task_type="SysApi",
            user_by=username,
            interval=schedule,
            enabled=sync_config.enable,
        )
    session.add(schedule)
    session.add(task)
    await session.commit()
