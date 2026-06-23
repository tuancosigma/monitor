"""Slack webhook notification channel implementation."""

from __future__ import annotations

import httpx

from app.alerting.channels.base import BaseNotificationChannel
from app.core.logging import get_logger
from app.core.ssrf_guard import get_safe_client

log = get_logger("sentinel.channels.slack")


class SlackChannel(BaseNotificationChannel):
    """Slack Incoming Webhooks notification channel."""

    async def send(self, message: str, subject: str | None = None) -> None:
        webhook_url = self.config.get("webhook_url")
        if not webhook_url:
            raise ValueError("Slack channel configuration missing 'webhook_url'")

        payload = {"text": message}

        # SSRF-guarded: webhook_url is user-configured, so block internal targets.
        async with get_safe_client() as client:
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            
        if response.status_code >= 400:
            log.error(
                "slack_notification_failed",
                status_code=response.status_code,
                body=response.text,
            )
            raise httpx.HTTPStatusError(
                f"Slack API returned status {response.status_code}",
                request=response.request,
                response=response,
            )
            
        log.info("slack_notification_sent_successfully")
