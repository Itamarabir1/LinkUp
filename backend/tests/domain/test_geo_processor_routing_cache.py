"""get_full_routing_data uses geocode_cache (Redis path), not bare GeocodingService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.geo.processor import get_full_routing_data


@pytest.mark.asyncio
async def test_get_full_routing_data_uses_geocode_cache(monkeypatch):

    async def gc_side_effect(address: str):
        if address == "A":
            return (1.0, 2.0)
        if address == "B":
            return (3.0, 4.0)
        return None

    fake_gc = AsyncMock(side_effect=gc_side_effect)
    raw_routes = [
        {"summary": "r1", "duration": 120, "distance": 5000, "coords": [[1.0, 2.0]]},
    ]
    fake_fetch = AsyncMock(return_value=raw_routes)

    with (
        patch("app.domain.geo.processor.get_coordinates", fake_gc),
        patch("app.domain.geo.processor.geo_client.fetch_raw_routes", fake_fetch),
    ):
        out = await get_full_routing_data("A", "B", departure_time=datetime.now(UTC))

    assert out is not None
    assert out["origin"].lat == 1.0
    assert out["dest"].lat == 3.0
    assert len(out["routes"]) == 1
    assert fake_gc.await_count == 2
    fake_fetch.assert_awaited_once()
