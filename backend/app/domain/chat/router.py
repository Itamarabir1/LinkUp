"""
1:1 chat router — conversations and messages.
All routes require authentication (get_current_user).
"""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.rate_limit import rate_limit_chat
from app.core.exceptions.base import LinkUpError
from app.core.exceptions.chat import ChatRoomNotFound
from app.db.session import get_db, SessionLocal
from app.domain.chat import crud as chat_crud
from app.domain.chat.message_idempotency import (
    chat_message_redis_key,
    message_send_fingerprint,
)
from app.domain.chat.schema import (
    ConversationCreate,
    ConversationDetail,
    MessageGapResponse,
    MessageCreate,
    MessageResponse,
    PaginatedConversationsResponse,
    PaginatedMessagesResponse,
)
from app.domain.chat.service import (
    get_conversation_detail,
    get_messages,
    get_messages_gap,
    get_or_create_conversation,
    get_or_create_conversation_by_booking,
    list_my_conversations,
    publish_read_receipt,
    send_message,
)
from app.domain.users.crud import crud_user
from app.domain.users.model import User
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub
from app.infrastructure.redis.client import redis_client

router = APIRouter(tags=["Chat"])
logger = logging.getLogger(__name__)


@router.post(
    "/conversations",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="פתיחת שיחה (או קבלת שיחה קיימת)",
)
async def create_or_get_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get or create a 1:1 thread with other_user_id.
    Returns conversation_id and partner details.
    """
    return await get_or_create_conversation(
        db,
        current_user_id=current_user.user_id,
        other_user_id=data.other_user_id,
    )


@router.post(
    "/conversations/by-booking/{booking_id}",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="פתיחת שיחה דרך booking",
)
async def create_or_get_conversation_by_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get or create a driver–passenger thread for a booking.
    Only booking parties may open; status must be pending_approval or confirmed.
    """
    return await get_or_create_conversation_by_booking(
        db,
        booking_id=booking_id,
        current_user_id=current_user.user_id,
    )


@router.get(
    "/conversations",
    response_model=PaginatedConversationsResponse,
    summary="רשימת השיחות שלי",
)
async def list_conversations(
    limit: int = Query(30, ge=1, le=100),
    after: str | None = Query(None, description="Cursor from previous page next_cursor"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Inbox for the current user with partner info and last message (cursor pagination)."""
    return await list_my_conversations(
        db,
        current_user_id=current_user.user_id,
        limit=limit,
        after=after,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="פרטי שיחה",
)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Single conversation header; participant only."""
    return await get_conversation_detail(db, conversation_id=conversation_id, current_user_id=current_user.user_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="שליחת הודעה",
)
async def post_message(
    conversation_id: UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit_chat),
    idempotency_key: str | None = Header(
        None,
        alias="Idempotency-Key",
        description=("Optional UUID per send intent — dedupe double-submit / client retries (same key + same body replays cached 201)."),
    ),
):
    """
    Post a message; participants only. Rate limited: 30 messages/minute per user.

    Optional Idempotency-Key: same semantics as POST request-ride-from-search (Redis TTL;
    mismatch → 422, in-flight → 409 + Retry-After).
    """
    redis_key: str | None = None
    claimed = False

    if idempotency_key:
        fingerprint = message_send_fingerprint(conversation_id, data.body)
        redis_key = chat_message_redis_key(str(current_user.user_id), idempotency_key)
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
                return MessageResponse.model_validate_json(cached_json)
            except Exception as e:
                logger.warning(
                    "chat message idempotency cache corrupt key=%s: %s",
                    redis_key,
                    e,
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Idempotency cache invalid",
                ) from e

        claimed = True

    try:
        msg, recipient_id = await send_message(
            db,
            conversation_id=conversation_id,
            sender_id=current_user.user_id,
            body=data.body,
        )
        await crud_user.update_last_active(db, user_id=current_user.user_id)
        await db.commit()

        try:
            async with SessionLocal() as fresh_db:
                unread = await chat_crud.get_unread_conversations_count(
                    fresh_db,
                    recipient_id,
                )
            await redis_chat_pubsub.publish(
                f"user:{recipient_id}:events",
                json.dumps(
                    {
                        "type": "invalidate",
                        "resource": "unread_messages",
                        "count": unread,
                    }
                ),
            )
        except Exception as e:
            logger.warning("Publish unread_count failed: %s", e, exc_info=True)

        if claimed and redis_key:
            await redis_client.idempotency_set_result(
                redis_key,
                MessageResponse.model_validate(msg).model_dump_json(),
            )
        return msg
    except ChatRoomNotFound:
        if claimed and redis_key:
            await redis_client.idempotency_delete(redis_key)
        raise
    except Exception:
        if claimed and redis_key:
            await redis_client.idempotency_delete(redis_key)
        raise


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=PaginatedMessagesResponse,
    summary="היסטוריית הודעות",
)
async def list_conversation_messages(
    conversation_id: UUID,
    limit: int = Query(30, ge=1, le=100),
    after: str | None = Query(None, description="Opaque cursor from previous page next_cursor"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Message history with cursor pagination; participants only."""
    return await get_messages(
        db,
        conversation_id=conversation_id,
        current_user_id=current_user.user_id,
        limit=limit,
        after_cursor=after,
    )


@router.get(
    "/conversations/{conversation_id}/messages/gap",
    response_model=MessageGapResponse,
    summary="פער הודעות מאז message_id אחרון",
)
async def list_conversation_messages_gap(
    conversation_id: UUID,
    since_message_id: int = Query(..., ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reconnect backfill for messages newer than since_message_id."""
    return await get_messages_gap(
        db,
        conversation_id=conversation_id,
        current_user_id=current_user.user_id,
        since_message_id=since_message_id,
    )


@router.get(
    "/conversations/{conversation_id}/calendar.ics",
    summary="ייצוא שיחה ללוח שנה (iCal)",
    response_class=Response,
)
async def export_conversation_calendar(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export conversation to iCal (.ics); requires AI analysis (not fully implemented).
    """
    from app.domain.chat.calendar_export import get_conversation_for_calendar_export

    # Load conversation context
    conv_data = await get_conversation_for_calendar_export(db, conversation_id, current_user.user_id)
    if not conv_data:
        raise ChatRoomNotFound()

    # TODO: analyze conversation or reuse cached analysis
    # Placeholder — wire to AI analyzer
    # For now: error if no analysis exists

    # Build RideSummary from messages (placeholder — needs real AI analysis)
    # ride = RideSummary(...)
    # ical_bytes = export_rides_to_ical_bytes([ride])

    raise LinkUpError(
        message="ייצוא ללוח שנה דורש ניתוח AI - עדיין לא מומש",
        status_code=501,
        error_code="CHAT_CALENDAR_NOT_IMPLEMENTED",
    )


@router.post("/conversations/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await chat_crud.mark_conversation_read(db, conversation_id, current_user.user_id)
    try:
        await publish_read_receipt(db, conversation_id, current_user.user_id)
    except Exception as e:
        logger.warning("publish_read_receipt failed: %s", e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/unread-count", response_model=dict)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await chat_crud.get_unread_conversations_count(db, current_user.user_id)
    return {"count": count}
