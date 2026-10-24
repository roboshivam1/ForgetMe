import smtplib
import ssl
from email.message import EmailMessage

from shared.config import env, env_bool


class MailError(Exception):
    pass


def send_email(to, subject, body, reply_to=None):
    if env_bool("EMAIL_DRY_RUN", True):
        return "dry_run"

    host = env("SMTP_HOST", "smtp.gmail.com")
    port = int(env("SMTP_PORT", "587"))
    user = env("SMTP_USER")
    password = env("SMTP_PASS")
    if not user or not password:
        raise MailError("Email sending isn't set up (SMTP_USER and SMTP_PASS are empty).")

    redirect = env("EMAIL_REDIRECT_TO")
    message = EmailMessage()
    message["From"] = f"{env('USER_DISPLAY_NAME') or user} <{user}>"
    message["To"] = redirect or to
    message["Subject"] = f"[would go to {to}] {subject}" if redirect else subject
    if reply_to and reply_to.lower() != user.lower():
        message["Reply-To"] = reply_to
    message.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(user, password)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as err:
        raise MailError(f"Email could not be sent: {err}") from err
    return "redirected" if redirect else "sent"
