from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.exceptions.user import UserNotFoundError
from app.db.session import get_db
from app.core.constants import NOTIFICATIONS_DEFAULT_LIMIT, NOTIFICATIONS_MAX_LIMIT
from app.domain.bookings.schema import MarkNotificationsReadRequest, PaginatedNotificationsResponse
from app.domain.bookings.booking_reads_service import BookingReadsService
from app.domain.users.crud import crud_user
from app.domain.users.model import User
from app.domain.users.schema import (
    AvatarUploadAcceptedResponse,
    AvatarUploadConfirmRequest,
    AvatarUploadUrlResponse,
    FCMTokenUpdate,
    MessageResponse,
    UserRead,
    UserUpdate,
)
from app.domain.users.service import user_service

router = APIRouter(tags=["Users"])  # prefix="/users" is mounted in api_router


# --- 1. My profile ---
@router.get("/me", response_model=UserRead)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile (including sensitive fields like verification state)."""
    return current_user


# --- Presence / Last seen ---
@router.patch("/me/last-seen", status_code=status.HTTP_204_NO_CONTENT)
async def update_last_seen(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await crud_user.update_last_active(db, user_id=current_user.user_id)
    if not ok:
        raise UserNotFoundError(identifier=str(current_user.user_id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{user_id}/last-seen")
async def get_user_last_seen(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Source for chat UI `last_seen`; called from chat-ws on GET /presence/{id}."""
    user = await crud_user.get_by_id(db, user_id)
    if not user:
        return {"last_seen": None}
    ts = user.last_active_at or user.last_login
    return {
        "last_seen": ts.isoformat() if ts else None,
    }


# --- Notifications (notifications screen) ---
@router.get("/me/notifications", response_model=PaginatedNotificationsResponse)
async def get_my_notifications(
    limit: int = Query(NOTIFICATIONS_DEFAULT_LIMIT, ge=1, le=NOTIFICATIONS_MAX_LIMIT),
    after: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cursor-paginated notifications: driver pending joins + passenger booking updates."""
    return await BookingReadsService.get_notifications_for_user(
        db,
        current_user.user_id,
        limit=limit,
        after=after,
    )


@router.patch("/me/notifications/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notifications_read(
    body: MarkNotificationsReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark specific notifications as read (idempotent upsert)."""
    await BookingReadsService.mark_notifications_read(
        db, current_user.user_id, body.items
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/me/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all current notifications as read in one pass."""
    await BookingReadsService.mark_all_notifications_read(db, current_user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- 2. FCM token update (push notifications) ---
@router.patch("/fcm-token", response_model=MessageResponse)
async def update_fcm_token(
    data: FCMTokenUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await user_service.update_fcm_token(db, user_id=current_user.user_id, fcm_token=data.fcm_token)

    # Prefer returning a response-model instance
    return MessageResponse(message="FCM Token updated successfully", status="success")


@router.post("/me/test-push")
async def test_push(
    current_user: User = Depends(get_current_user),
):
    from app.core.config import settings
    from app.core.exceptions.base import LinkUpError

    if not settings.DEBUG:
        raise LinkUpError(
            message="Endpoint available in debug mode only",
            status_code=404,
            error_code="NOT_FOUND",
        )
    from app.domain.notifications.channels.push.client import fcm_client

    if not current_user.fcm_token:
        return {"error": "no fcm_token"}
    result = await fcm_client.send(
        token=current_user.fcm_token,
        title="בדיקת FCM",
        body="אם אתה רואה את זה — FCM עובד!",
    )
    return {"result": str(result)}


# --- 5. Profile photo upload (two paths) ---


# Path 1: presigned URL (recommended — 202 faster)
@router.get(
    "/me/avatar/upload-url",
    response_model=AvatarUploadUrlResponse,
    status_code=status.HTTP_200_OK,
)
async def get_avatar_upload_url(
    filename: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """
    Return a presigned URL for direct upload to S3.
    Flow:
    1. Client calls this endpoint → receives presigned URL + staging_key
    2. Client uploads directly to S3 via the URL (5–8s)
    3. Client calls POST /me/avatar/confirm with staging_key
    4. Server enqueues work and returns 202 immediately (~1s)
    5. Worker processes in the background (finalize + DB update)
    """
    presigned_url, staging_key = await user_service.get_avatar_upload_url(user_id=current_user.user_id, filename=filename)
    return AvatarUploadUrlResponse(
        upload_url=presigned_url,
        staging_key=staging_key,
        expires_in=300,  # 5 minutes
    )


@router.post(
    "/me/avatar/confirm",
    response_model=AvatarUploadAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def confirm_avatar_upload(
    data: AvatarUploadConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm upload after the client uploaded directly to S3. Updates avatar_key in DB immediately and enqueues work.
    Processing (resize to 3 sizes) runs in the background. staging_key must start with avatars/staging/{user_id}_.
    """
    await user_service.confirm_avatar_upload(db, current_user, data.staging_key)
    return AvatarUploadAcceptedResponse()


@router.delete(
    "/me/avatar",
    response_model=AvatarUploadAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def remove_my_avatar(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove profile photo: deletes avatars/{user_id}/ from S3 and clears avatar_key in DB.
    """
    await user_service.remove_avatar(db, user_id=current_user.user_id)
    return AvatarUploadAcceptedResponse(message="Avatar removed", status="accepted")


# --- Update profile fields (name, email, etc.) ---
@router.put("/me", response_model=UserRead)
async def update_my_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the authenticated user's profile.
    Accepts a UserUpdate object and passes it through to the service unchanged.
    """
    return await user_service.update_user_info(
        db,
        user_id=current_user.user_id,
        update_data=data,  # pass the full schema through
    )


# --- 3. Location update (for nearby ride search) ---
# @router.patch("/me/location", response_model=MessageResponse)
# async def update_my_location(
#     data: UserLocationUpdate,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     # Logic and LinkUpError raises live in the service
#     await user_service.update_user_location(
#         db,
#         user_id=current_user.user_id,
#         lat=data.latitude,
#         lon=data.longitude
#     )

#     return MessageResponse(
#         message="Location updated successfully",
#         status="success"
#     )
# --- 4. Public profile view ---
# @router.get("/{user_id}", response_model=UserPublicRead)
# async def get_user_public_profile(
#     user_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """View another driver/passenger — returns only name, photo, rating, join date"""
#     user = await UserService.get_user_by_id(db, user_id=user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user
