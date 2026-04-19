import asyncio
import logging
from datetime import datetime
from functools import partial
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
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
from app.domain.passengers.ai_search_schema import AISearchQuery, AISearchResult
from app.domain.passengers.ai_search_service import parse_ride_search_query
from app.domain.passengers.ride_join_idempotency import (
    idempotency_redis_key,
    request_fingerprint,
)
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
from app.infrastructure.redis.client import redis_client

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
    idempotency_key: str | None = Header(
        None,
        alias="Idempotency-Key",
        description="UUID ייחודי לכל כוונת הצטרפות — מניע כפילות בלחיצה כפולה",
    ),
):
    """
    Join request from search results.
    Optional Idempotency-Key header prevents duplicate bookings on retry/double-click.
    Same key + different body → 422. Same key + same body → returns original result.
    """
    logger.info(
        "[NOTIF] request_ride_from_search ride_id=%s request_id=%s idempotency_key=%s",
        body.ride_id,
        body.request_id,
        bool(idempotency_key),
    )

    redis_key: str | None = None
    claimed = False

    if idempotency_key:
        fingerprint = request_fingerprint(body)
        redis_key = idempotency_redis_key(str(current_user.user_id), idempotency_key)
        state = await redis_client.idempotency_try_begin(redis_key, fingerprint)

        if state == "mismatch":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "idempotency_key_mismatch",
                    "message": "Idempotency-Key שימש בעבר עם גוף בקשה שונה",
                },
            )
        if state == "in_progress":
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": "בקשה זו כבר בעיבוד — נסה שוב בעוד רגע"},
                headers={"Retry-After": "1"},
            )
        if state.startswith("completed:"):
            cached_json = state[len("completed:") :]
            try:
                return Response(
                    content=cached_json,
                    status_code=status.HTTP_201_CREATED,
                    media_type="application/json",
                )
            except Exception:
                pass

        claimed = True

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

        booking = await BookingService.request_to_join(
            db,
            ride_id=body.ride_id,
            request_id=request_id,
            num_seats=body.num_seats,
            current_user_id=current_user.user_id,
        )

        if claimed and redis_key:
            result_json = BookingResponse.model_validate(booking).model_dump_json()
            await redis_client.idempotency_set_result(redis_key, result_json)

        return booking

    except (
        GeocodingError,
        RideNotAvailableError,
        BookingAlreadyExistsError,
        PassengerRequestNotFoundError,
        ForbiddenRideActionError,
    ) as e:
        if claimed and redis_key:
            await redis_client.idempotency_delete(redis_key)
        if isinstance(e, GeocodingError):
            raise HTTPException(status_code=400, detail=str(e)) from e
        if isinstance(e, RideNotAvailableError):
            raise HTTPException(status_code=400, detail=str(e)) from e
        if isinstance(e, BookingAlreadyExistsError):
            raise HTTPException(status_code=409, detail=str(e)) from e
        if isinstance(e, PassengerRequestNotFoundError):
            raise HTTPException(status_code=404, detail=str(e)) from e
        raise HTTPException(status_code=403, detail=str(e)) from e
    except Exception as e:
        if claimed and redis_key:
            await redis_client.idempotency_delete(redis_key)
        logger.error("request_ride_from_search failed: %s", e, exc_info=True)
        try:
            from app.core.config import settings

            detail = str(e) if getattr(settings, "DEBUG", False) else "שגיאה בשליחת הבקשה — נסה שוב"
        except Exception:
            detail = "שגיאה בשליחת הבקשה — נסה שוב"
        raise HTTPException(status_code=500, detail=detail) from e


# 2b. AI parse free-text into search fields (sync Groq in thread pool; no auto search)
@router.post(
    "/ai-parse-search",
    response_model=AISearchResult,
    summary="ניתוח חיפוש נסיעה בטקסט חופשי (AI)",
)
async def ai_parse_search(
    body: AISearchQuery,
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Parse Hebrew/English free text into structured pickup/destination/time/radius.
    Does not run search — client fills the form and calls GET /search-rides.
    """
    _ = current_user
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None,
            partial(parse_ride_search_query, body.query, body.conversation_history),
        )
        logger.info(
            "ai_parse_search ok query_len=%s needs_clarification=%s",
            len(body.query),
            getattr(result, "needs_clarification", None),
        )
        return result
    except Exception as e:
        logger.warning("ai_parse_search failed: %s", e)
        return AISearchResult(
            pickup_name=None,
            destination_name=None,
            departure_time=None,
            search_radius=None,
            confidence=0.0,
            raw_interpretation="",
            needs_clarification=True,
            missing_fields=["pickup_name", "destination_name"],
            ambiguity_reasons=[],
            follow_up_question="אירעה שגיאה. נסה שוב או מלא את הטופס ידנית.",
        )


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
