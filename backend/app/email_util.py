"""
Email notifications (STRETCH GOAL, out of scope for the core deliverable).

Sends mail via SMTP using ``fastapi-mail``. For the demo we point it at
**Mailpit** - a mock SMTP server that catches mail and shows it in a web UI -
so nothing actually leaves the machine:

    docker run --rm -d -p 1025:1025 -p 8025:8025 axllent/mailpit
    # then set EMAIL_ENABLED=true and open http://localhost:8025

Off by default (``EMAIL_ENABLED``) and fully best-effort: a failure here never
affects the dashboard. Config is built lazily so importing this module can never
fail at startup.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("p13.email")

EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
EMAIL_TO = os.getenv("EMAIL_TO", "gardener@example.com")


def _config():
    from fastapi_mail import ConnectionConfig

    return ConnectionConfig(
        MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
        MAIL_FROM=os.getenv("MAIL_FROM", "plant-cps@example.com"),
        MAIL_PORT=int(os.getenv("MAIL_PORT", "1025")),
        MAIL_SERVER=os.getenv("MAIL_SERVER", "localhost"),
        MAIL_STARTTLS=False,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=False,
        VALIDATE_CERTS=False,
    )


async def send_email(subject: str, body: str, to: str | None = None) -> bool:
    """Best-effort send. Returns True on success, False if disabled or failed."""
    if not EMAIL_ENABLED:
        log.info("email disabled (EMAIL_ENABLED=false); skipping '%s'", subject)
        return False
    try:
        from fastapi_mail import FastMail, MessageSchema, MessageType

        message = MessageSchema(
            subject=subject,
            recipients=[to or EMAIL_TO],
            body=body,
            subtype=MessageType.plain,
        )
        await FastMail(_config()).send_message(message)
        log.info("email sent: %s", subject)
        return True
    except Exception as exc:  # noqa: BLE001 - never break the app on email failure
        log.warning("email send failed: %s", exc)
        return False
