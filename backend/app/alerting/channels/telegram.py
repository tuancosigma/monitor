"""Telegram bot notification channel implementation."""

from __future__ import annotations

import httpx

from app.alerting.channels.base import BaseNotificationChannel
from app.core.logging import get_logger
from app.core.ssrf_guard import get_safe_client

log = get_logger("sentinel.channels.telegram")


class TelegramChannel(BaseNotificationChannel):
    """Telegram Bot sendMessage API notification channel."""

    async def send(self, message: str, subject: str | None = None) -> None:
        bot_token = self.config.get("bot_token")
        chat_id = self.config.get("chat_id")
        if not bot_token or not chat_id:
            raise ValueError("Telegram channel configuration missing 'bot_token' or 'chat_id'")

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
        }

        # SSRF-guarded for consistency with other outbound channels.
        async with get_safe_client() as client:
            response = await client.post(url, json=payload, timeout=10.0)

        if response.status_code >= 400:
            log.error(
                "telegram_notification_failed",
                status_code=response.status_code,
                body=response.text,
            )
            raise httpx.HTTPStatusError(
                f"Telegram API returned status {response.status_code}",
                request=response.request,
                response=response,
            )

        log.info("telegram_notification_sent_successfully")
