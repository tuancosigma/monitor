"""Generic Webhook notification channel implementation with SSRF protection."""

from __future__ import annotations

import httpx

from app.alerting.channels.base import BaseNotificationChannel
from app.core.logging import get_logger
from app.core.ssrf_guard import get_safe_client

log = get_logger("sentinel.channels.webhook")


class WebhookChannel(BaseNotificationChannel):
    """Generic webhook notification channel with built-in SSRF and DNS-rebinding protection."""

    async def send(self, message: str, subject: str | None = None) -> None:
        webhook_url = self.config.get("webhook_url")
        if not webhook_url:
            raise ValueError("Webhook channel configuration missing 'webhook_url'")

        method = self.config.get("method", "POST").upper()
        headers = self.config.get("headers", {})
        
        # Default payload matches Slack format
        payload = {"text": message}
        if subject:
            payload["subject"] = subject

        # Use the SSRF-protected HTTPX client
        async with get_safe_client() as client:
            if method == "POST":
                response = await client.post(
                    webhook_url, json=payload, headers=headers, timeout=10.0
                )
            elif method == "PUT":
                response = await client.put(
                    webhook_url, json=payload, headers=headers, timeout=10.0
                )
            else:
                raise ValueError(f"Unsupported Webhook HTTP method: {method}")

        if response.status_code >= 400:
            log.error(
                "webhook_notification_failed",
                status_code=response.status_code,
                body=response.text,
            )
            raise httpx.HTTPStatusError(
                f"Generic Webhook returned status {response.status_code}",
                request=response.request,
                response=response,
            )

        log.info("webhook_notification_sent_successfully")
