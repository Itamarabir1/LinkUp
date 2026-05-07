"""Shared helpers for opaque cursor pagination."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from uuid import UUID


class CursorDecodeError(ValueError):
    """Invalid or corrupt cursor payload."""


def encode_cursor(t: datetime, identifier: UUID, *, id_field: str = "id") -> str:
    """Encode UTC timestamp + UUID into URL-safe Base64 JSON cursor."""
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    utc = t.astimezone(timezone.utc)
    t_iso = utc.isoformat().replace("+00:00", "Z")
    payload = {"t": t_iso, id_field: str(identifier)}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(
    s: str,
    *,
    id_field: str = "id",
    id_error_label: str = "id",
    error_cls: type[ValueError] = CursorDecodeError,
) -> tuple[datetime, UUID]:
    """Decode cursor into UTC datetime + UUID."""
    if not s or not isinstance(s, str):
        raise error_cls("empty cursor")
    pad = "=" * (-len(s) % 4)
    try:
        raw = base64.urlsafe_b64decode((s.strip() + pad).encode("ascii"))
        obj = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
        raise error_cls("invalid cursor encoding") from e
    if not isinstance(obj, dict):
        raise error_cls("invalid cursor shape")
    ts = obj.get("t")
    identifier = obj.get(id_field)
    if not isinstance(ts, str) or not isinstance(identifier, str):
        raise error_cls("invalid cursor fields")
    try:
        t_iso = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(t_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        row_id = UUID(identifier)
    except (ValueError, TypeError) as e:
        raise error_cls(f"invalid timestamp or {id_error_label}") from e
    return (dt, row_id)


def encode_cursor_int(t: datetime, id: int, *, id_field: str = "id") -> str:
    """Encode UTC timestamp + int id into URL-safe Base64 JSON cursor."""
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    utc = t.astimezone(timezone.utc)
    t_iso = utc.isoformat().replace("+00:00", "Z")
    payload = {"t": t_iso, id_field: id}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor_int(
    s: str,
    *,
    id_field: str = "id",
    error_cls: type[ValueError] = CursorDecodeError,
) -> tuple[datetime, int]:
    """Decode cursor into UTC datetime + int id."""
    if not s or not isinstance(s, str):
        raise error_cls("empty cursor")
    pad = "=" * (-len(s) % 4)
    try:
        raw = base64.urlsafe_b64decode((s.strip() + pad).encode("ascii"))
        obj = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
        raise error_cls("invalid cursor encoding") from e
    if not isinstance(obj, dict):
        raise error_cls("invalid cursor shape")
    ts = obj.get("t")
    identifier = obj.get(id_field)
    if not isinstance(ts, str) or not isinstance(identifier, int):
        raise error_cls("invalid cursor fields")
    try:
        t_iso = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(t_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
    except (ValueError, TypeError) as e:
        raise error_cls("invalid timestamp or id") from e
    return (dt, identifier)
