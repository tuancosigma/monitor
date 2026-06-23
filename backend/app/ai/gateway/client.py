"""Single OpenAI-compatible client used for both Groq and Gemini.

Per-account base_url + api_key are swapped per call. Raises typed errors the router
understands: RateLimited (carries retry_after) and ProviderError (everything else).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openai import APIStatusError, AsyncOpenAI, RateLimitError

from app.ai.gateway.pool import Account


class RateLimited(Exception):
    def __init__(self, retry_after: float) -> None:
        super().__init__(f"rate limited, retry after {retry_after}s")
        self.retry_after = retry_after


class ProviderError(Exception):
    pass


@dataclass
class CallResult:
    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    headers: dict[str, str] = field(default_factory=dict)


def _retry_after_seconds(err: RateLimitError) -> float:
    headers = getattr(getattr(err, "response", None), "headers", {}) or {}
    raw = headers.get("retry-after")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return 30.0


async def call_account(
    account: Account,
    model: str,
    messages: list[dict[str, str]],
    *,
    json_object: bool = False,
    temperature: float = 0.1,
) -> CallResult:
    """Make one chat-completion call against a specific account+model."""
    client = AsyncOpenAI(api_key=account.api_key, base_url=account.base_url)
    # Build kwargs as Any: messages/response_format here are plain dicts, looser than the
    # SDK's TypedDict overloads but valid at runtime for any OpenAI-compatible endpoint.
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_object:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        resp = await client.chat.completions.with_raw_response.create(**kwargs)
    except RateLimitError as err:
        raise RateLimited(_retry_after_seconds(err)) from err
    except APIStatusError as err:
        raise ProviderError(str(err)) from err
    except Exception as err:  # network / unexpected
        raise ProviderError(str(err)) from err

    headers = {k.lower(): v for k, v in resp.headers.items()}
    parsed = resp.parse()
    content = parsed.choices[0].message.content or ""
    usage = parsed.usage
    return CallResult(
        content=content,
        tokens_in=usage.prompt_tokens if usage else 0,
        tokens_out=usage.completion_tokens if usage else 0,
        headers=headers,
    )
