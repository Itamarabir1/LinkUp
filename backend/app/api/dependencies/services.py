"""
Service dependencies — single source of truth for service factories.
Routers import from here via Depends.
"""

from app.domain.auth.service import AuthService
from app.domain.rides.repository import ride_cache_repo
from app.domain.rides.service import RideService


def get_ride_service() -> RideService:
    """Factory for RideService — injects cache_repo."""
    return RideService(cache_repo=ride_cache_repo)


def get_auth_service() -> AuthService:
    """Factory for AuthService."""
    return AuthService()
