import smtplib
from email.header import Header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from enum import Enum
from pathlib import Path
import socket
from typing import Optional

from jinja2 import Template
from pydantic import DirectoryPath

from app.core.config import settings


class MessageType(Enum):
    """
    A message type
    """

    plain = "plain"
    html = "html"


class MailInstance(object):
    """
    生成Mail实例
    """

    def __init__(
        self,
        subject: str,
        body: str | dict,
        recipients: str | list[str],
        config: dict = None,
        subtype: MessageType = "html",
        template_folder: Optional[DirectoryPath] = None,
        template_name: Optional[str] = None,
        **kwargs,
    ):
        """
        subject: 主题
        config: 邮件服务器配置
        body: 正文，为str直接解析为dict则需配合template_folder使用jinja2
        recipients: 接收人或接收人列表
        subtype: 邮件的子类型默认为html
        template_folder: 模板文件夹路径为None不使用
        template_name: 模板名称
        supperss_send: 测试发送值为1则模拟发送
        """
        self.subject = subject
        self.body = body
        self.recipients = recipients
        self.subtype = subtype
        self.config = config
        self.template_folder = template_folder
        self.template_name = template_name
        self.kwargs = kwargs

    def render_email_template(self) -> str:
        template_str = (Path(self.template_folder / self.template_name)).read_text(
            encoding="utf8"
        )
        html_content = Template(template_str).render(self.body)
        return html_content

    def build_message(self) -> MIMEMultipart:
        message = MIMEMultipart()
        if isinstance(self.recipients, str):
            self.recipients = [self.recipients]
        if isinstance(self.body, dict):
            self.body["sys_title"] = settings.SYS_TITLE
            self.body["sys_link"] = settings.SYS_LINK

        if self.subtype == "html":
            content = self.render_email_template()
            content_logo = MIMEImage(
                (Path(f"{settings.BASE_TEMPLATES_DIR}/logo.png")).read_bytes()
            )
            # 定义图片 ID，在 HTML 文本中引用
            content_logo.add_header("Content-ID", "logo")
            message.attach(content_logo)
        else:
            content = self.body
        message["From"] = formataddr(
            [self.config.get("mail_from_name"), self.config.get("mail_from")]
        )
        message["To"] = ",".join(self.recipients)
        message["Subject"] = Header(self.subject, "utf-8")
        message.attach(MIMEText(content, self.subtype, "utf-8"))
        return message

    def send(self) -> dict:
        try:
            message = self.build_message()
            if self.config.get("MAIL_SSL"):
                server = smtplib.SMTP_SSL(
                    self.config.get("mail_server"), self.config.get("mail_port")
                )
            else:
                server = smtplib.SMTP(
                    self.config.get("mail_server"), self.config.get("mail_port")
                )
                if self.config.get("mail_start_tls"):
                    server.starttls()
            server.login(
                self.config.get("mail_username"), self.config.get("mail_password")
            )
            server.sendmail(
                self.config.get("mail_from"), self.recipients, message.as_string()
            )
            return {"code": 1, "message": "发送成功"}
        except smtplib.SMTPException as e:
            return {"code": 0, "message": f"smtplib.SMTPException -- {e}"}
        except socket.gaierror as e:
            return {"code": 0, "message": f"socket.gaierror -- {e}"}