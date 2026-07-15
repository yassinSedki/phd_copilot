"""Outbound email via a single shared SMTP relay account (SMTP__* env vars)
— replaces the removed per-user Gmail OAuth send path. Every message is
relayed through the same configured account, but Reply-To is set to the
sending user's own contact email, so a reply lands in their inbox even
though the message itself came from the relay address.

Error messages here are shown to the end user as-is (see the /send routes),
so they stay short and non-technical — never leak SMTP codes or stack
traces into the API response.
"""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from shared.config import get_settings


class MailerNotConfigured(Exception):
    pass


class MailerError(Exception):
    pass


def is_configured() -> bool:
    settings = get_settings().smtp
    return bool(settings.host and settings.from_email)


def send(*, to: str, subject: str, body: str, sender_name: str | None = None, reply_to: str | None = None) -> None:
    settings = get_settings().smtp
    if not is_configured():
        raise MailerNotConfigured("Email sending isn't set up yet — use Copy instead.")

    msg = MIMEText(body)
    msg["To"] = to
    msg["From"] = formataddr((sender_name or "PhD Copilot", settings.from_email))
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    try:
        with smtplib.SMTP(settings.host, settings.port, timeout=20) as server:
            if settings.use_tls:
                server.starttls()
            if settings.username:
                server.login(settings.username, settings.password)
            server.send_message(msg)
    except Exception as exc:
        # Never surface raw SMTP exceptions (auth codes, server banners) to
        # the user — log it server-side if needed, show a plain retry hint.
        raise MailerError("Couldn't send the email right now. Try again in a moment, or use Copy instead.") from exc
