"""Constrained script execution for the SOAR ``script`` action.

Strong isolation (RCE-proof) requires containerization; in MVP this is a defense-in-depth
subprocess runner: disabled by default, time-limited, output-capped, and run with a
restricted environment (no inherited secrets). Enable via ``SENTINEL_SOAR_SCRIPT_ENABLED``.
"""

from __future__ import annotations

import asyncio

from app.core.config import settings

_MAX_OUTPUT = 64 * 1024
_TIMEOUT_S = 10.0


class ScriptDisabledError(Exception):
    """Script action is disabled by configuration."""


async def run_script(command: list[str]) -> dict[str, object]:
    """Run an allowlisted command with a timeout and restricted env.

    Returns {exit_code, stdout, stderr}. Raises ScriptDisabledError if disabled.
    """
    if not settings.soar_script_enabled:
        raise ScriptDisabledError("script action disabled (set SENTINEL_SOAR_SCRIPT_ENABLED=1)")
    if not command:
        raise ValueError("empty command")

    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={},  # restricted: no inherited environment / secrets
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_TIMEOUT_S)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        raise

    return {
        "exit_code": proc.returncode,
        "stdout": stdout[:_MAX_OUTPUT].decode("utf-8", errors="replace"),
        "stderr": stderr[:_MAX_OUTPUT].decode("utf-8", errors="replace"),
    }
