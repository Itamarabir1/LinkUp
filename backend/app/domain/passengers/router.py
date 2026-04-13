import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, get_current_user_optional
from app.api.dependencies.group_membership import require_group_member
from app.core.exceptions.booking import (
    BookingAlreadyExistsError,
    ForbiddenRideActionError,
    PassengerRequestNotFoundError,
    RideNotAvailableError,
)
from app.core.exceptions.infrastructure import GeocodingError
from app.db.session import get_db
from app.domain.bookings.schema import BookingResponse
from app.domain.bookings.service import BookingService
from app.domain.passengers.schema import (
    PassengerRequestCreate,
    PassengerRequestResponse,
    PassengerRequestWithMatches,
    RequestRideFromSearch,
    RideSearchRequest,
    RideSearchResponse,
)
from app.domain.passengers.service import PassengerService
from app.domain.rides.schema import DriverInfoResponse, RideResponse
from app.domain.users.model import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passengers", tags=["Passenger"])
passenger_rides_router = APIRouter(prefix="/rides", tags=["Passenger"])


# 0. My requests (passenger)
@router.get("/me", response_model=list[PassengerRequestResponse])
async def get_my_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request_status: str | None = Query(
        None,
        description="סנן לפי סטטוס: pending, approved, cancelled, matched, expired, completed, rejected",
    ),
):
    """List the current user's passenger requests."""
    return await PassengerService.get_my_requests(db, current_user.user_id, status=request_status)


# 1. Create official request (smart flow)
@router.post(
    "/",
    response_model=PassengerRequestWithMatches,
    status_code=status.HTTP_201_CREATED,
    summary="רישום נוסע לטרמפ (יצירת בקשה קבועה)",
)
async def create_new_request(
    request: PassengerRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await PassengerService.create_passenger_request(db=db, request_in=request, passenger_id=current_user.user_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in create_new_request: {e!s}", exc_info=True)
        raise HTTPException(status_code=500, detail="שגיאת שרת פנימית ביצירת הבקשה")


# --- Passenger rides sub-router: GET /passenger/rides/{ride_id}/driver-info ---
@passenger_rides_router.get(
    "/{ride_id}/driver-info",
    response_model=DriverInfoResponse,
    summary="פרטי נהג לנסיעה (רק כשלחיצה על 'הצג פרטי הנהג')",
)
async def get_ride_driver_info(
    ride_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return driver name and phone for open rides; requires authentication."""
    try:
        return await PassengerService.get_ride_driver_info(db, ride_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- Join request from search ---
@router.post(
    "/request-ride-from-search",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="שלח בקשה להצטרפות לנסיעה מתוך תוצאות חיפוש",
)
async def request_ride_from_search(
    body: RequestRideFromSearch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Use request_id from search if present, else create one. Creates booking and outbox event; worker emails driver."""
    logger.info(
        "[NOTIF] API: request_ride_from_search called ride_id=%s, request_id=%s",
        body.ride_id,
        body.request_id,
    )
    try:
        request_id = body.request_id
        if not request_id:
            new_request = await PassengerService.create_passenger_request_for_ride_search(
                db,
                passenger_id=current_user.user_id,
                pickup_name=body.pickup_name,
                destination_name=body.destination_name,
                num_seats=body.num_seats,
            )
            request_id = new_request.request_id

        return await BookingService.request_to_join(
            db,
            ride_id=body.ride_id,
            request_id=request_id,
            num_seats=body.num_seats,
            current_user_id=current_user.user_id,
        )
    except GeocodingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RideNotAvailableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BookingAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PassengerRequestNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenRideActionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error("request_ride_from_search failed: %s", e, exc_info=True)
        try:
            from app.core.config import settings

            detail = str(e) if getattr(settings, "DEBUG", False) else "שגיאה בשליחת הבקשה – נסה שוב או פנה לתמיכה"
        except Exception:
            detail = "שגיאה בשליחת הבקשה – נסה שוב או פנה לתמיכה"
        raise HTTPException(status_code=500, detail=detail)


# 3. Free search (does not persist; use POST / to save alerts)
@router.get(
    "/search-rides",
    response_model=RideSearchResponse,
    summary="חיפוש טרמפים (ללא שמירת בקשה; שמירת התראה ב-POST /)",
)
async def search_available_rides(
    pickup_name: str,
    destination_name: str,
    search_radius: float = Query(1.0, ge=0.1, le=50, description="רדיוס חיפוש בקילומטרים (אחיד עם יצירת בקשה)"),
    departure_time: datetime | None = Query(None, description="אם ריק – יחפש מעכשיו"),
    limit: int = Query(20, ge=1, le=50, description="כמות תוצאות"),
    after: UUID | None = Query(None, description="cursor: ride_id להמשך"),
    group_id: UUID | None = Depends(require_group_member),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    try:
        search_data = RideSearchRequest(
            passenger_id=current_user.user_id if current_user else None,
            pickup_name=pickup_name,
            destination_name=destination_name,
            search_radius=search_radius,
            departure_time=departure_time,
            limit=limit,
            after=after,
            group_id=group_id,
        )
        result = await PassengerService.search_rides_for_passenger(db, search_data)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search_available_rides: {e!s}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"שגיאה בחיפוש נסיעות: {e!s}")


# 4. Cancel request
@router.delete("/{request_id}/cancel", summary="ביטול בקשת נסיעה ושחרור שריונים")
async def cancel_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel the request and release all seat holds against drivers (request owner only)."""
    try:
        return await PassengerService.cancel_request(db, request_id, current_user.user_id)
    except PassengerRequestNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenRideActionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# 5. Refresh matches for existing request
@router.get(
    "/{request_id}/matches",
    response_model=list[RideResponse],
    summary="שליפת התאמות עדכניות לבקשה קיימת",
)
async def get_latest_matches(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PassengerService.get_matches_by_request_id(db, request_id, current_user.user_id)


@router.get("/all", response_model=list[RideResponse], summary="תצוגת כל הנסיעות (ניהול ובקרה)")
async def get_all_rides_admin(
    filter_status: str = Query(None, description="סנן לפי סטטוס: open, cancelled, completed"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all rides in the system; optional status filter."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="גישה מנהלים בלבד")
    return await PassengerService.get_all_rides_for_admin(db, status=filter_status)
