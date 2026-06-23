"""Central audit middleware: append an audit_log row for every mutating request.

Logging happens for POST/PUT/PATCH/DELETE after the response is produced (actor from
the X-Sentinel-Role header, method, path, status). Best-effort: an audit failure never
breaks the request. This avoids decorating every endpoint individually.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger
from app.core.metadata_db import AsyncSessionLocal
from app.models.audit_log import AuditLog

log = get_logger("sentinel.audit")

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if request.method in _MUTATING:
            actor = request.headers.get("x-sentinel-role", "anonymous")
            try:
                async with AsyncSessionLocal() as session:
                    session.add(
                        AuditLog(
                            actor=actor,
                            method=request.method,
                            path=request.url.path,
                            status_code=response.status_code,
                        )
                    )
                    await session.commit()
            except Exception as exc:  # auditing must never break the request
                log.error("audit_write_failed", error=str(exc))
        return response
