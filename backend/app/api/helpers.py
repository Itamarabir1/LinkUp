"""Shared API-layer utilities used by dependencies and routers."""

from __future__ import annotations

from fastapi import Request


def client_ip(request: Request) -> str:
    """Extract client IP from X-Forwarded-For (first entry) or fallback to client.host."""
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
