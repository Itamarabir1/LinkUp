from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.infrastructure.geo import geocode_cache
from app.infrastructure.geo.client import GeoClient


@pytest.mark.asyncio
async def test_geocode_cache_set_and_get_roundtrip():
    """Address round-trips through cache with valid lat/lon."""
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
    """Redis errors fail open (returns None, no crash)."""
    with patch.object(
        geocode_cache.redis_client,
        "get",
        new=AsyncMock(side_effect=RuntimeError("redis down")),
    ):
        coords = await geocode_cache.get_cached_coords("Jerusalem")
    assert coords is None


@pytest.mark.asyncio
async def test_fetch_coordinates_uses_cache_without_external_lookup():
    """Cache hit skips external geocoder."""
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
    """Miss then successful geocode writes a new cache entry."""
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


@pytest.mark.asyncio
async def test_get_coordinates_concurrent_cold_key_calls_geocoder_once():
    """Concurrent cold-key requests are coalesced by Redis mutex."""
    store: dict[str, dict] = {}
    locks: dict[str, str] = {}
    lock_guard = asyncio.Lock()

    class FakeRedis:
        async def set(self, key, value, ex=None, nx=False):
            async with lock_guard:
                if nx:
                    if key in locks:
                        return False
                    locks[key] = value
                    return True
                store[key] = value
                return True

        async def eval(self, _script, _numkeys, lock_key, token):
            async with lock_guard:
                if locks.get(lock_key) == token:
                    del locks[lock_key]
                    return 1
                return 0

    async def fake_get(key):
        return store.get(key)

    async def fake_save(key, value, expire=None):
        store[key] = value

    call_counter = {"count": 0}

    async def fake_google(_address):
        call_counter["count"] += 1
        await asyncio.sleep(0.05)
        return 32.0853, 34.7818

    fake_client = FakeRedis()
    with patch.object(geocode_cache.redis_client, "client", fake_client):
        with patch.object(geocode_cache.redis_client, "connect", new=AsyncMock()):
            with patch.object(geocode_cache.redis_client, "get", new=AsyncMock(side_effect=fake_get)):
                with patch.object(geocode_cache.redis_client, "save", new=AsyncMock(side_effect=fake_save)):
                    with patch.object(
                        geocode_cache.GeocodingService,
                        "get_coordinates_from_address",
                        new=AsyncMock(side_effect=fake_google),
                    ):
                        results = await asyncio.gather(
                            *[geocode_cache.get_coordinates("Tel Aviv") for _ in range(20)],
                        )

    assert all(r == (32.0853, 34.7818) for r in results)
    assert call_counter["count"] == 1


@pytest.mark.asyncio
async def test_get_coordinates_fail_open_when_redis_unavailable():
    """Redis failure does not block geocoding flow (fail-open)."""
    with patch.object(
        geocode_cache.redis_client,
        "get",
        new=AsyncMock(side_effect=RuntimeError("redis down")),
    ):
        with patch.object(
            geocode_cache.GeocodingService,
            "get_coordinates_from_address",
            new=AsyncMock(return_value=(31.7683, 35.2137)),
        ) as mock_google:
            coords = await geocode_cache.get_coordinates("Jerusalem")

    assert coords == (31.7683, 35.2137)
    mock_google.assert_awaited_once()
