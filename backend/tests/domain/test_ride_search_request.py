"""RideSearchRequest validation and Jerusalem day-window helper."""

from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.domain.passengers.schema import RideSearchRequest
from app.domain.passengers.service import jerusalem_calendar_day_utc_window


def test_departure_date_mutex_with_department_time():
    with pytest.raises(ValidationError, match="mutually exclusive"):
        RideSearchRequest(
            pickup_name="Tel Aviv",
            destination_name="Haifa",
            departure_date=date(2030, 6, 1),
            departure_time=datetime(2030, 6, 1, 12, 0, tzinfo=timezone.utc),
        )


def test_departure_time_to_requires_start():
    with pytest.raises(ValidationError, match="departure_time_to requires"):
        RideSearchRequest(
            pickup_name="Tel Aviv",
            destination_name="Haifa",
            departure_time_to=datetime(2030, 6, 1, 14, 0, tzinfo=timezone.utc),
        )


def test_departure_range_order():
    with pytest.raises(ValidationError, match="departure_time_to must not"):
        RideSearchRequest(
            pickup_name="Tel Aviv",
            destination_name="Haifa",
            departure_time=datetime(2030, 6, 1, 14, 0, tzinfo=timezone.utc),
            departure_time_to=datetime(2030, 6, 1, 12, 0, tzinfo=timezone.utc),
        )


def test_valid_date_only():
    req = RideSearchRequest(
        pickup_name="Tel Aviv",
        destination_name="Haifa",
        departure_date=date(2030, 12, 5),
    )
    assert req.departure_time is None
    assert req.departure_date == date(2030, 12, 5)


def test_valid_explicit_range():
    t0 = datetime(2030, 6, 1, 8, 0, tzinfo=timezone.utc)
    t1 = datetime(2030, 6, 1, 18, 0, tzinfo=timezone.utc)
    req = RideSearchRequest(
        pickup_name="Tel Aviv",
        destination_name="Haifa",
        departure_time=t0,
        departure_time_to=t1,
    )
    assert req.departure_time == t0
    assert req.departure_time_to == t1


def test_jerusalem_winter_midnight_window_is_24h_in_utc():
    start_utc, end_excl = jerusalem_calendar_day_utc_window(date(2026, 1, 15))
    assert end_excl > start_utc
    assert (end_excl - start_utc) == timedelta(hours=24)
    assert start_utc.tzinfo is UTC


def test_jerusalem_day_orders_correctly_vs_next_calendar_day():
    a0, _ = jerusalem_calendar_day_utc_window(date(2026, 1, 15))
    b0, _ = jerusalem_calendar_day_utc_window(date(2026, 1, 16))
    assert b0 > a0
