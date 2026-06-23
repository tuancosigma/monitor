"""SMTP notification channel implementation using aiosmtplib."""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from app.alerting.channels.base import BaseNotificationChannel
from app.core.logging import get_logger

log = get_logger("sentinel.channels.smtp")


class SMTPChannel(BaseNotificationChannel):
    """SMTP email notification channel using aiosmtplib."""

    async def send(self, message: str, subject: str | None = None) -> None:
        smtp_host = self.config.get("host")
        smtp_port = int(self.config.get("port", 587))
        username = self.config.get("username")
        password = self.config.get("password")
        use_tls = bool(self.config.get("use_tls", False))
        use_starttls = bool(self.config.get("use_starttls", True))
        
        from_email = self.config.get("from_email")
        to_email = self.config.get("to_email")

        if not smtp_host or not from_email or not to_email:
            raise ValueError(
                "SMTP channel configuration missing 'host', 'from_email', or 'to_email'"
            )

        # Construct Email Message
        msg = EmailMessage()
        msg["Subject"] = subject or "Sentinel Alert Notification"
        msg["From"] = from_email
        msg["To"] = to_email
        msg.set_content(message)

        # Connect and send
        try:
            # We connect to SMTP
            # note: aiosmtplib.send signature maps host, port, username, password,
            # use_tls, start_tls, etc.
            await aiosmtplib.send(
                msg,
                hostname=smtp_host,
                port=smtp_port,
                username=username,
                password=password,
                use_tls=use_tls,
                start_tls=use_starttls,
                timeout=10.0,
            )
            log.info("smtp_notification_sent_successfully", recipient=to_email)
        except Exception as exc:
            log.error("smtp_notification_failed", error=str(exc))
            raise
