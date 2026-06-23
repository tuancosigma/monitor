"""SSRF DNS-Rebinding Guard.

Provides host/IP validation and pins connections to verified safe IP addresses
to prevent SSRF and DNS rebinding attacks on outgoing webhooks.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Iterable
from typing import Any

import httpcore
import httpx

from app.core.logging import get_logger

log = get_logger("sentinel.ssrf_guard")


def is_safe_ip(ip_str: str) -> bool:
    """Validate if an IP is public and safe to connect to."""
    try:
        # Strip zones from IPv6 addresses if present
        if "%" in ip_str:
            ip_str = ip_str.split("%")[0]
            
        ip = ipaddress.ip_address(ip_str)
        # Block loopback, private, link-local, multicast, unspecified, and reserved ranges
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_unspecified
            or ip.is_reserved
        ):
            return False
            
        # Explicitly block cloud metadata service endpoints (AWS, GCP, etc.)
        if ip_str == "169.254.169.254":
            return False
            
        return True
    except ValueError:
        return False


class SSRFProtectedBackend(httpcore.AnyIOBackend):
    """Network backend for httpcore that intercepts DNS resolution and blocks unsafe targets."""

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,  # noqa: ASYNC109
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        # If host is already an IP, validate it directly
        if is_safe_ip(host):
            return await super().connect_tcp(
                host=host,
                port=port,
                timeout=timeout,
                local_address=local_address,
                socket_options=socket_options,
            )
        # Otherwise host is a name (or unsafe literal IP) — resolve below and validate
        # every returned address, which also catches unsafe literal IPs.

        try:
            # Resolve DNS records in a thread pool to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            addr_info = await loop.run_in_executor(
                None, lambda: socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
            )
        except Exception as exc:
            log.error("ssrf_dns_resolution_failed", host=host, error=str(exc))
            raise httpcore.ConnectError(f"DNS resolution failed for {host}") from exc

        # Validate all resolved addresses
        safe_ips: list[str] = []
        for _family, _socktype, _proto, _canonname, sockaddr in addr_info:
            ip_str = str(sockaddr[0])
            if is_safe_ip(ip_str):
                safe_ips.append(ip_str)
            else:
                log.warning("ssrf_blocked_unsafe_ip", host=host, ip=ip_str)
                raise httpcore.ConnectError(f"SSRF violation: target {ip_str} is blocked")

        if not safe_ips:
            raise httpcore.ConnectError(f"No safe IP addresses found for host '{host}'")

        # Pin connection to the first safe IP address to prevent DNS-rebinding
        target_ip = safe_ips[0]
        log.debug("ssrf_resolved_safe_ip", host=host, ip=target_ip)
        
        return await super().connect_tcp(
            host=target_ip,
            port=port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


class SSRFProtectedAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """HTTPX Async Transport utilizing the SSRF protected network backend."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Patch the underlying connection pool to use our protected backend
        if hasattr(self, "_pool"):
            self._pool._network_backend = SSRFProtectedBackend()


def get_safe_client() -> httpx.AsyncClient:
    """Return an httpx.AsyncClient configured with SSRF protection."""
    transport = SSRFProtectedAsyncHTTPTransport()
    return httpx.AsyncClient(transport=transport, follow_redirects=False)
