"""SMTP delivery. Development uses Mailpit, never a fake 'sent' response."""
from email.message import EmailMessage
import smtplib
import ssl
from urllib.parse import urlencode

from fastapi import Depends

from api.settings import Settings, get_settings
from api.telemetry import emit


class MailDeliveryError(Exception):
    pass


class SMTPMailer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send_password_reset(self, email: str, token: str):
        settings = self.settings
        # A fragment keeps the secret out of HTTP request URLs and ordinary access logs.
        link = f"{settings.origin}/reset-password#{urlencode({'token': token})}"
        action = "Đặt lại mật khẩu"
        lifetime = settings.reset_seconds
        message = EmailMessage()
        message["Subject"] = f"{action} — Trợ lý hỏi đáp Đại học"
        message["From"] = settings.mail_from
        message["To"] = email
        message.set_content(
            f"{action} bằng liên kết sau (hiệu lực {lifetime // 60} phút, dùng một lần):\n\n"
            f"{link}\n\nNếu bạn không yêu cầu thao tác này, hãy bỏ qua email.\n"
        )
        try:
            emit("smtp_delivery", status="started")
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
            emit("smtp_delivery", status="accepted")
        except (OSError, smtplib.SMTPException) as exc:
            emit("smtp_delivery", status="failed", errorType=type(exc).__name__)
            raise MailDeliveryError("Email delivery is unavailable") from exc


def get_mailer(settings: Settings = Depends(get_settings)) -> SMTPMailer:
    return SMTPMailer(settings)
