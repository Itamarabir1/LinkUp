from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.geo import geocode_cache
from app.infrastructure.geo.client import GeoClient


@pytest.mark.asyncio
async def test_geocode_cache_set_and_get_roundtrip():
    """כתובת נשמרת ונשלפת מה-cache עם ערכי lat/lon תקינים."""
    store: dict[str, dict] = {}

    async def fake_save(key, value, expire=None):
        assert expire == geocode_cache.GEOCODE_CACHE_TTL
        store[key] = value

    async def fake_get(key):
        return store.get(key)

    with patch.object(geocode_cache.redis_client, "save", new=AsyncMock(side_effect=fake_save)):
        with patch.object(geocode_cache.redis_client, "get", new=AsyncMock(side_effect=fake_get)):
            await geocode_cache.set_cached_coords("  Tel Aviv  ", 32.0853, 34.7818)
            coords = await geocode_cache.get_cached_coords("Tel Aviv")

    assert coords == (32.0853, 34.7818)


@pytest.mark.asyncio
async def test_geocode_cache_fail_open_on_redis_error():
    """אם Redis נופל, הקריאה לא נופלת — מחזירה None (fail-open)."""
    with patch.object(
        geocode_cache.redis_client,
        "get",
        new=AsyncMock(side_effect=RuntimeError("redis down")),
    ):
        coords = await geocode_cache.get_cached_coords("Jerusalem")
    assert coords is None


@pytest.mark.asyncio
async def test_fetch_coordinates_uses_cache_without_external_lookup():
    """כאשר יש cache hit, לא קוראים ל-Nominatim בכלל."""
    client = GeoClient()
    with patch(
        "app.infrastructure.geo.geocode_cache.get_cached_coords",
        new=AsyncMock(return_value=(31.7683, 35.2137)),
    ):
        with patch.object(client.geolocator, "geocode", side_effect=AssertionError("should not call geocode")):
            lat, lon = await client.fetch_coordinates("Jerusalem")

    assert (lat, lon) == (31.7683, 35.2137)


@pytest.mark.asyncio
async def test_fetch_coordinates_writes_cache_after_lookup():
    """כאשר אין cache hit ויש תוצאת geocode, נשמר cache חדש."""
    client = GeoClient()

    class Location:
        latitude = 32.0853
        longitude = 34.7818

    with patch(
        "app.infrastructure.geo.geocode_cache.get_cached_coords",
        new=AsyncMock(return_value=None),
    ):
        with patch(
            "app.infrastructure.geo.geocode_cache.set_cached_coords",
            new=AsyncMock(),
        ) as mock_set:
            with patch.object(client.geolocator, "geocode", return_value=Location()):
                lat, lon = await client.fetch_coordinates("Tel Aviv")

    assert (lat, lon) == (32.0853, 34.7818)
    mock_set.assert_awaited_once_with("Tel Aviv", 32.0853, 34.7818)
