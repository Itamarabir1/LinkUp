# app/api/v1/api_router.py
import app.db.models  # רישום כל המודלים לפני טעינת הרואטרים — מונע circular import

from fastapi import APIRouter

from app.domain.admin.router import router as admin_router
from app.domain.auth.router import router as auth_router
from app.domain.billing.router import router as billing_router
from app.domain.bookings.router import router as bookings_router
from app.domain.chat.router import router as chat_router
from app.domain.geo.router import router as geo_router
from app.domain.groups.router import router as groups_router
from app.domain.passengers.router import (
    passenger_rides_router,
)
from app.domain.passengers.router import (
    router as passenger_router,
)
from app.domain.rides.router import router as rides_router
from app.domain.users.router import router as user_router

api_router = APIRouter()

api_router.include_router(rides_router, prefix="/rides", tags=["Rides"])
api_router.include_router(passenger_router, prefix="/passenger", tags=["Passenger"])
api_router.include_router(passenger_rides_router, prefix="/passenger", tags=["Passenger"])
api_router.include_router(bookings_router, prefix="/bookings", tags=["Bookings"])
api_router.include_router(user_router, prefix="/users", tags=["Users"])
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(billing_router, prefix="/billing", tags=["Billing"])
api_router.include_router(geo_router, prefix="/geo", tags=["Geo"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_router.include_router(groups_router, prefix="/groups", tags=["Groups"])
