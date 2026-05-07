"""Inbox pagination cursor helpers."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.pagination.cursor import CursorDecodeError, decode_cursor, encode_cursor


def test_encode_decode_roundtrip():
    t = datetime(2026, 3, 15, 12, 30, 45, tzinfo=UTC)
    cid = UUID("12345678-1234-5678-1234-567812345678")
    s = encode_cursor(t, cid, id_field="c")
    t2, c2 = decode_cursor(s, id_field="c", id_error_label="conversation id")
    assert c2 == cid
    assert t2 == t


def test_decode_invalid_raises():
    with pytest.raises(CursorDecodeError):
        decode_cursor("", id_field="c", id_error_label="conversation id")
    with pytest.raises(CursorDecodeError):
        decode_cursor("not-base64!!!", id_field="c", id_error_label="conversation id")
