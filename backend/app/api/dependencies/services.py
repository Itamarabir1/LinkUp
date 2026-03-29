"""
Service dependencies — מקור אמת יחיד לכל service factories.
כל router מייבא מכאן דרך Depends.
"""

from app.domain.auth.service import AuthService
from app.domain.rides.repository import ride_cache_repo
from app.domain.rides.service import RideService


def get_ride_service() -> RideService:
    """Factory ל-RideService — מזריק את cache_repo."""
    return RideService(cache_repo=ride_cache_repo)


def get_auth_service() -> AuthService:
    """Factory ל-AuthService."""
    return AuthService()
