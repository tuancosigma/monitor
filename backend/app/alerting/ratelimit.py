"""Token Bucket rate-limiter implementation for notification channels."""

from __future__ import annotations

import time


class TokenBucket:
    """In-memory Token Bucket rate limiter."""

    def __init__(self, capacity: float, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_update = time.monotonic()

    def consume(self, tokens: float = 1.0) -> bool:
        """Consume tokens from the bucket. Returns True if successful."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now
        
        # Add new tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


# Global in-memory map of channel_id to its TokenBucket
_channel_buckets: dict[int, TokenBucket] = {}


def check_rate_limit(
    channel_id: int,
    capacity: float = 10.0,
    refill_rate: float = 0.1,  # 0.1 tokens/sec = 1 token per 10 seconds
) -> bool:
    """Check and consume a rate limit token for a channel.

    Returns:
        bool: True if connection is allowed (token consumed), False if rate-limited.
    """
    if channel_id not in _channel_buckets:
        _channel_buckets[channel_id] = TokenBucket(capacity, refill_rate)
    return _channel_buckets[channel_id].consume(1.0)
