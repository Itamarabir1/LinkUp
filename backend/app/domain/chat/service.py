"""
1:1 chat service — logic above CRUD, response shaping (partner, last message).
After saving a message — publishes to Redis Pub/Sub (Go WS server subscribes).
"""

import json
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import LinkUpError
from app.core.exceptions.booking import (
    BookingNotFoundError,
    ForbiddenRideActionError,
)
from app.core.exceptions.chat import (
    ChatRoomNotFound,
    UnauthorizedChatAccess,
)
from app.core.exceptions.ride import RideNotFoundError
from app.core.exceptions.user import UserNotFoundError
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.model import Booking
from app.domain.chat import crud as chat_crud
from app.domain.chat.model import ConversationParticipant
from app.domain.chat.schema import (
    ConversationDetail,
    ConversationListItem,
    ConversationPartner,
    MessageResponse,
    PaginatedMessagesResponse,
)
from app.domain.rides.model import Ride
from app.domain.users.crud import crud_user
from app.infrastructure.events.publishers.redis import publish_chat_message
from app.infrastructure.s3.service import storage_service
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub

logger = logging.getLogger(__name__)


async def _get_partner_last_read_at(db: AsyncSession, conversation_id: UUID, current_user_id: UUID) -> datetime | None:
    conv = await chat_crud.get_conversation_by_id(db, conversation_id, current_user_id)
    if not conv:
        return None
    partner_id = conv.user_id_2 if conv.user_id_1 == current_user_id else conv.user_id_1
    result = await db.execute(
        select(ConversationParticipant.last_read_at).where(
            ConversationParticipant.conversation_id == conv.conversation_id,
            ConversationParticipant.user_id == partner_id,
        ),
    )
    return result.scalar_one_or_none()


async def _get_partner_read_up_to_message_id(
    db: AsyncSession,
    conversation_id: UUID,
    current_user_id: UUID,
) -> int | None:
    return await chat_crud.get_partner_read_up_to_message_id(db, conversation_id, current_user_id)


async def _require_booking_and_ride_for_chat(db: AsyncSession, booking_id: UUID, current_user_id: UUID) -> tuple[Booking, Ride]:
    """Loads booking and ride; raises domain error if chat is not allowed."""
    bid = UUID(str(booking_id)) if isinstance(booking_id, str) else booking_id
    result = await db.execute(select(Booking).where(Booking.booking_id == bid))
    booking = result.scalars().first()
    if not booking:
        raise BookingNotFoundError(booking_id=str(bid))

    ride_result = await db.execute(select(Ride).where(Ride.ride_id == booking.ride_id))
    ride = ride_result.scalars().first()
    if not ride:
        raise RideNotFoundError(booking.ride_id)

    is_driver = ride.driver_id == current_user_id
    is_passenger = booking.passenger_id == current_user_id
    if not (is_driver or is_passenger):
        raise UnauthorizedChatAccess()

    allowed_statuses = {BookingStatus.PENDING, BookingStatus.CONFIRMED}
    if booking.status not in allowed_statuses:
        raise ForbiddenRideActionError("ניתן לשוחח רק כשסטטוס ההזמנה ממתין לאישור או מאושר")
    return booking, ride


async def get_or_create_conversation(db: AsyncSession, current_user_id: UUID, other_user_id: UUID) -> ConversationDetail:
    """
    Returns or creates a conversation between current_user and other_user.
    Returns ConversationDetail (for the router).
    """
    if other_user_id == current_user_id:
        raise LinkUpError(
            message="לא ניתן לפתוח שיחה עם עצמך",
            status_code=400,
            error_code="CHAT_INVALID_SELF_CONVERSATION",
        )
    other = await crud_user.get_by_id(db, id=other_user_id)
    if not other:
        raise UserNotFoundError(user_id=other_user_id)
    conv = await chat_crud.get_or_create_conversation(db, current_user_id, other_user_id)
    partner = ConversationPartner(
        user_id=other.user_id,
        full_name=other.full_name,
        avatar_url=storage_service.build_avatar_url(other.avatar_key, "150x150.webp"),
    )
    return ConversationDetail(
        conversation_id=conv.conversation_id,
        partner=partner,
        created_at=conv.created_at,
        partner_last_read_at=await _get_partner_last_read_at(db, conv.conversation_id, current_user_id),
        partner_read_up_to_message_id=await _get_partner_read_up_to_message_id(db, conv.conversation_id, current_user_id),
    )


async def get_or_create_conversation_by_booking(db: AsyncSession, booking_id: UUID, current_user_id: UUID) -> ConversationDetail:
    """
    Returns or creates a driver–passenger conversation for a booking_id.
    Permission: only the booking’s driver or passenger may open chat,
    and only when status is pending approval or confirmed.
    """
    booking, ride = await _require_booking_and_ride_for_chat(db, booking_id, current_user_id)

    driver_id = ride.driver_id
    passenger_id = booking.passenger_id
    other_user_id = driver_id if current_user_id == passenger_id else passenger_id

    if other_user_id == current_user_id:
        raise LinkUpError(
            message="לא ניתן לפתוח שיחה עם עצמך",
            status_code=400,
            error_code="CHAT_INVALID_SELF_CONVERSATION",
        )

    other = await crud_user.get_by_id(db, id=other_user_id)
    if not other:
        raise UserNotFoundError(user_id=other_user_id)

    conv = await chat_crud.get_or_create_conversation(db, current_user_id, other_user_id)
    partner = ConversationPartner(
        user_id=other.user_id,
        full_name=other.full_name,
        avatar_url=storage_service.build_avatar_url(other.avatar_key, "150x150.webp"),
    )
    return ConversationDetail(
        conversation_id=conv.conversation_id,
        partner=partner,
        created_at=conv.created_at,
        booking_id=booking.booking_id,
        partner_last_read_at=await _get_partner_last_read_at(db, conv.conversation_id, current_user_id),
        partner_read_up_to_message_id=await _get_partner_read_up_to_message_id(db, conv.conversation_id, current_user_id),
    )


def _partner_from_conversation(conv, current_user_id: UUID) -> ConversationPartner:
    """Returns the other party in the conversation (User → ConversationPartner)."""
    user = conv.user_2 if conv.user_id_1 == current_user_id else conv.user_1
    return ConversationPartner(
        user_id=user.user_id,
        full_name=user.full_name,
        avatar_url=storage_service.build_avatar_url(user.avatar_key, "150x150.webp"),
    )


async def list_my_conversations(db: AsyncSession, current_user_id: UUID) -> list[ConversationListItem]:
    """
    Lists the user’s conversations with partner details and last message.
    Uses a single aggregated DB batch — no N+1 per conversation.
    """
    convs = await chat_crud.list_conversations_for_user(db, current_user_id)
    if not convs:
        return []

    conversation_ids = [conv.conversation_id for conv in convs]
    aggregates = await chat_crud.get_inbox_aggregates(db, current_user_id, conversation_ids)

    out = []
    for conv in convs:
        partner_user = conv.user_2 if conv.user_id_1 == current_user_id else conv.user_1
        partner = ConversationPartner(
            user_id=partner_user.user_id,
            full_name=partner_user.full_name,
            avatar_url=storage_service.build_avatar_url(partner_user.avatar_key, "150x150.webp"),
        )
        agg = aggregates.get(conv.conversation_id, {})
        body = agg.get("last_message_body")
        out.append(
            ConversationListItem(
                conversation_id=conv.conversation_id,
                partner=partner,
                last_message_at=agg.get("last_message_at"),
                last_message_preview=(body[:80] + "…") if body and len(body) > 80 else body,
                has_unread=agg.get("has_unread", False),
            ),
        )
    return out


async def get_conversation_detail(db: AsyncSession, conversation_id: UUID, current_user_id: UUID) -> ConversationDetail:
    """
    One conversation’s details — only if the user is a participant.
    """
    conv = await chat_crud.get_conversation_by_id(db, conversation_id, current_user_id)
    if not conv:
        raise ChatRoomNotFound()
    partner = _partner_from_conversation(conv, current_user_id)
    return ConversationDetail(
        conversation_id=conv.conversation_id,
        partner=partner,
        created_at=conv.created_at,
        partner_last_read_at=await _get_partner_last_read_at(db, conv.conversation_id, current_user_id),
        partner_read_up_to_message_id=await _get_partner_read_up_to_message_id(db, conv.conversation_id, current_user_id),
    )


async def send_message(
    db: AsyncSession,
    conversation_id: UUID,
    sender_id: UUID,
    body: str,
) -> MessageResponse:
    """
    Sends a message: persist in DB + publish to Redis (Go WS server listens).
    """
    conv = await chat_crud.get_conversation_by_id(db, conversation_id, sender_id)
    if not conv:
        raise ChatRoomNotFound()
    msg = await chat_crud.create_message(db, conversation_id=conversation_id, sender_id=sender_id, body=body)
    recipient_id = conv.user_id_2 if conv.user_id_1 == sender_id else conv.user_id_1
    payload = {
        "message_id": msg.message_id,
        "conversation_id": str(msg.conversation_id),
        "sender_id": str(msg.sender_id),
        "recipient_id": str(recipient_id),
        "body": msg.body,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }
    await publish_chat_message(conversation_id, payload)

    # Publish unread-count notification to recipient (for instant badge updates via chat-ws).
    try:
        unread = await chat_crud.get_unread_conversations_count(db, recipient_id)
        await redis_chat_pubsub.publish(
            f"chat:notification:{recipient_id}",
            json.dumps({"type": "unread_count", "count": unread}),
        )
    except Exception as e:
        logger.warning("Publish unread_count failed: %s", e, exc_info=True)

    return MessageResponse(
        message_id=msg.message_id,
        conversation_id=msg.conversation_id,
        sender_id=msg.sender_id,
        body=msg.body,
        created_at=msg.created_at,
    )


async def get_messages(
    db: AsyncSession,
    conversation_id: UUID,
    current_user_id: UUID,
    limit: int = 50,
    before_message_id: int | None = None,
    after_message_id: int | None = None,
) -> PaginatedMessagesResponse:
    """
    Message history for a conversation (pagination).
    """
    conv = await chat_crud.get_conversation_by_id(db, conversation_id, current_user_id)
    if not conv:
        raise ChatRoomNotFound()
    messages, has_more = await chat_crud.get_messages(
        db,
        conversation_id=conversation_id,
        limit=limit,
        before_message_id=before_message_id,
        after_message_id=after_message_id,
    )
    items = [
        MessageResponse(
            message_id=m.message_id,
            conversation_id=m.conversation_id,
            sender_id=m.sender_id,
            body=m.body,
            created_at=m.created_at,
        )
        for m in messages
    ]
    next_cursor = str(items[0].message_id) if has_more and items else None
    return PaginatedMessagesResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    )


async def publish_read_receipt(db: AsyncSession, conversation_id: UUID, reader_id: UUID) -> None:
    """
    Broadcast read progress to Redis on chat:conversation:{id}.

    Contract (1:1, chat-ws PublishChatMessage): include ``recipient_id`` — the WS
    routing target (the other participant who should render ✓✓), same field as chat messages.
    """
    try:
        conv = await chat_crud.get_conversation_by_id(db, conversation_id, reader_id)
        if not conv:
            return
        partner_id = conv.user_id_2 if conv.user_id_1 == reader_id else conv.user_id_1
        reader_result = await db.execute(
            select(ConversationParticipant.last_read_message_id).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == reader_id,
            )
        )
        read_up_to = reader_result.scalar_one_or_none()
        payload: dict[str, str | int] = {
            "type": "message_read",
            "conversation_id": str(conversation_id),
            "reader_id": str(reader_id),
            "recipient_id": str(partner_id),
        }
        if read_up_to is not None:
            payload["read_up_to_message_id"] = read_up_to
        await redis_chat_pubsub.publish(
            f"chat:conversation:{conversation_id}",
            json.dumps(payload),
        )
    except Exception as e:
        logger.warning("publish_read_receipt failed: %s", e, exc_info=True)
