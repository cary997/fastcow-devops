from typing import Optional

from pydantic import DirectoryPath

from app.core.config import settings
from app.ext.channels_tsk.email import MailInstance, MessageType
from app.ext.channels_tsk.utils import get_mail_conf
from app.models.system_model import mailServerSettings
from app.tasks import celery
from app.utils.password_tools import aes_decrypt_password, is_decrypt


@celery.task(name="tasks.send_email",rate_limit="60/m")
def send_email(
    recipients: str | list[str],
    subject: str,
    subtype: MessageType = "html",
    body: str | dict = None,
    template_name: str = None,
    config: mailServerSettings | dict = None,
    template_folder: Optional[DirectoryPath] = settings.BASE_TEMPLATES_DIR,
):
    if config is None:
        _config = get_mail_conf()
    else:
        _config = mailServerSettings.model_validate(config)
    if _config is None or _config.mail_server is None:
        return {
            "code": 0,
            "message": f"mail server not find - MAIL_SERVER: {_config.mail_server}",
            "recipients": recipients,
            "subject": subject,
        }
    if is_decrypt(_config.mail_password):
        _config.mail_password = aes_decrypt_password(_config.mail_password)
    if body is None:
        body = {}
    _send = MailInstance(
        recipients=recipients,
        subject=subject,
        body=body,
        subtype=subtype,
        config=_config.model_dump(),
        template_folder=template_folder,
        template_name=template_name,
    )
    _res = _send.send()
    return {
        "code": _res.get("code"),
        "message": _res.get("message"),
        "recipients": recipients,
        "subject": subject,
    }
