"""
Idempotency helpers for POST /request-ride-from-search.
Extracted from router to keep HTTP layer thin.
"""

import hashlib
import json as json_module

from app.domain.passengers.schema import RequestRideFromSearch


def idempotency_redis_key(user_id: str, client_key: str) -> str:
    return f"idempotency:request_ride:{user_id}:{client_key}"


def request_fingerprint(body: RequestRideFromSearch) -> str:
    """SHA-256 of canonical body fields for mismatch detection."""
    canonical = json_module.dumps(
        {
            "ride_id": str(body.ride_id),
            "pickup_name": body.pickup_name,
            "destination_name": body.destination_name,
            "num_seats": body.num_seats,
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
