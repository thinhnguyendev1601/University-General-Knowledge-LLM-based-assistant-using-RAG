"""Check SMTP connection/TLS/auth without sending a message or exposing credentials."""
import json
import smtplib
import ssl
import sys

from api.settings import get_settings


def check(settings):
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.ehlo()
            if settings.smtp_starttls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            code, _ = smtp.noop()
            if code != 250:
                return {"status": "unavailable", "errorType": "SMTPNoopRejected"}
        return {"status": "ready", "deliveryVerified": False}
    except (OSError, smtplib.SMTPException) as error:
        return {"status": "unavailable", "errorType": type(error).__name__, "deliveryVerified": False}


def main():
    result = check(get_settings())
    print(json.dumps(result))
    sys.exit(0 if result["status"] == "ready" else 1)


if __name__ == "__main__":
    main()
