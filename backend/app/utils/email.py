"""邮件发送封装：使用 QQ 邮箱 SMTP（SSL，端口 465）。"""

import smtplib
from email.header import Header
from email.mime.text import MIMEText

from ..config import settings


def send_email(to_email: str, subject: str, content: str) -> None:
    """发送纯文本邮件。失败时抛出异常，由调用方处理。"""
    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, [to_email], msg.as_string())
