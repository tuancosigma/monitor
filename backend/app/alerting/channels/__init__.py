"""Notification channels module.

Provides the factory method for instantiating the correct notification
channel implementation based on channel type.
"""

from __future__ import annotations

from typing import Any

from app.alerting.channels.base import BaseNotificationChannel
from app.alerting.channels.discord import DiscordChannel
from app.alerting.channels.slack import SlackChannel
from app.alerting.channels.smtp import SMTPChannel
from app.alerting.channels.telegram import TelegramChannel
from app.alerting.channels.webhook import WebhookChannel

__all__ = [
    "BaseNotificationChannel",
    "DiscordChannel",
    "SMTPChannel",
    "SlackChannel",
    "TelegramChannel",
    "WebhookChannel",
    "get_channel_instance",
]


def get_channel_instance(channel_type: str, config: dict[str, Any]) -> BaseNotificationChannel:
    """Factory method to get a channel instance by type and configuration."""
    t = channel_type.lower()
    if t == "slack":
        return SlackChannel(config)
    elif t == "discord":
        return DiscordChannel(config)
    elif t == "telegram":
        return TelegramChannel(config)
    elif t == "smtp":
        return SMTPChannel(config)
    elif t == "webhook":
        return WebhookChannel(config)
    else:
        raise ValueError(f"Unknown notification channel type: {channel_type}")
