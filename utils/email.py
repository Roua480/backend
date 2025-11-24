import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from core.config import settings
from models import User
from .tokens import make_token



def _send_mail(to: str, subject: str, body: str) -> None:
    if not (
        settings.SMTP_HOST
        and settings.SMTP_USER
        and settings.SMTP_PASSWORD
        and settings.MAIL_FROM
    ):
        print(f"[DEV] Would send email to {to}: {subject}\n{body}\n")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = str(settings.MAIL_FROM)
    msg["To"] = to
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        print(f"[MAIL] Sent email to {to}: {subject}")
    except Exception as exc:  # pragma: no cover - best effort
        print(f"[ERROR] SMTP send failed: {exc}")


def send_verification_email(db: Session, user: User) -> str:
    token = make_token(db, user, "verify", minutes=60)
    link = f"{settings.BACKEND_BASE_URL}/auth/verify-email?token={token}"
    body = (
        "Hi,\n\n"
        "Please verify your PolyLab account by clicking this link:\n"
        f"{link}\n\n"
        "If you did not create this account, you can ignore this email."
    )
    _send_mail(user.email, "Verify your PolyLab account", body)
    print(f"[DEV] Verify link for {user.email}: {link}")
    return token


def send_reset_email(db: Session, user: User) -> str:
    token = make_token(db, user, "reset", minutes=30)
    link = f"{settings.BACKEND_BASE_URL}/auth/reset/confirm?token={token}"
    body = (
        "Hi,\n\n"
        "To reset your PolyLab password, click this link:\n"
        f"{link}\n\n"
        "If you did not request a reset, you can ignore this email."
    )
    _send_mail(user.email, "Reset your PolyLab password", body)
    print(f"[DEV] Reset link for {user.email}: {link}")
    return token

