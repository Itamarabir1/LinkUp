"""Unit tests for booking summary pagination cursors (UTC)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.core.pagination.cursor import CursorDecodeError, decode_cursor, encode_cursor


def test_encode_decode_roundtrip_utc_naive_normalized():
    t = datetime(2024, 3, 15, 12, 30, 0)
    uid = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    s = encode_cursor(t, uid)
    out_t, out_id = decode_cursor(s)
    assert out_id == uid
    assert out_t.tzinfo == timezone.utc
    assert out_t.year == t.year and out_t.month == t.month and out_t.day == t.day


def test_encode_preserves_tz_as_utc():
    t = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    uid = UUID("11111111-2222-3333-4444-555555555555")
    s = encode_cursor(t, uid)
    out_t, out_id = decode_cursor(s)
    assert out_id == uid
    assert out_t == t


def test_decode_invalid_raises():
    with pytest.raises(CursorDecodeError):
        decode_cursor("not-a-real-cursor")
