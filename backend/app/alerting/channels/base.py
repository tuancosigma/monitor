"""Base notification channel abstract class.

All concrete channel integrations must inherit from BaseNotificationChannel
and implement the async send method.
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from typing import Any


class BaseNotificationChannel(ABC):
    """Abstract base class for all notification channels."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = self._expand_config(config)

    def _expand_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Expand environment variable references like ${VAR_NAME} in configuration values."""
        expanded: dict[str, Any] = {}
        for k, v in config.items():
            if isinstance(v, str):
                # Match ${VAR} patterns and replace with os.environ values
                pattern = r"\$\{([^}]+)\}"
                matches = re.findall(pattern, v)
                expanded_val = v
                for var in matches:
                    val = os.environ.get(var, "")
                    expanded_val = expanded_val.replace(f"${{{var}}}", val)
                expanded[k] = expanded_val
            elif isinstance(v, dict):
                expanded[k] = self._expand_config(v)
            else:
                expanded[k] = v
        return expanded

    @abstractmethod
    async def send(self, message: str, subject: str | None = None) -> None:
        """Send a notification message.

        Must raise an exception on failure to trigger retry/backoff logic.
        """
        pass
