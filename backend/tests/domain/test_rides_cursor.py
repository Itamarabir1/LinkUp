"""Unit tests for rides pagination cursors."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.core.pagination.cursor import CursorDecodeError, decode_cursor, encode_cursor


def test_encode_decode_roundtrip() -> None:
    ts = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    ride_id = UUID("11111111-2222-3333-4444-555555555555")

    cursor = encode_cursor(ts, ride_id)
    decoded_ts, decoded_ride_id = decode_cursor(cursor)

    assert decoded_ride_id == ride_id
    assert decoded_ts == ts
    assert decoded_ts.tzinfo == timezone.utc


def test_decode_rejects_invalid_cursor() -> None:
    with pytest.raises(CursorDecodeError):
        decode_cursor("not-a-valid-cursor")
