"""
ראוטר צ'אט 1:1 – שיחות והודעות.
כל ה-endpoints דורשים אימות (get_current_user).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.exceptions.base import LinkupError
from app.core.exceptions.chat import ChatRoomNotFound
from app.db.session import get_db
from app.domain.chat import crud as chat_crud
from app.domain.chat.schema import (
    ConversationCreate,
    ConversationDetail,
    ConversationListItem,
    MessageCreate,
    MessageResponse,
    PaginatedMessagesResponse,
)
from app.domain.chat.service import (
    get_conversation_detail,
    get_messages,
    get_or_create_conversation,
    get_or_create_conversation_by_booking,
    list_my_conversations,
    send_message,
)
from app.domain.users.crud import crud_user
from app.domain.users.model import User

router = APIRouter(tags=["Chat"])


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
    מזהה או יוצר שיחת 1:1 עם other_user_id.
    מחזיר conversation_id + פרטי הצד השני.
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
    מזהה או יוצר שיחת 1:1 בין נהג לנוסע על בסיס booking_id.
    רק נהג או נוסע של ה-booking יכולים לפתוח שיחה,
    ורק אם הסטטוס הוא pending_approval או confirmed.
    """
    return await get_or_create_conversation_by_booking(
        db,
        booking_id=booking_id,
        current_user_id=current_user.user_id,
    )


@router.get(
    "/conversations",
    response_model=list[ConversationListItem],
    summary="רשימת השיחות שלי",
)
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """כל השיחות של המשתמש המחובר, עם פרטי הצד השני והודעה אחרונה."""
    return await list_my_conversations(db, current_user_id=current_user.user_id)


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
    """פרטי שיחה אחת – רק אם המשתמש participant."""
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
):
    """שולח הודעה בשיחה. רק participant יכול לשלוח."""
    msg = await send_message(
        db,
        conversation_id=conversation_id,
        sender_id=current_user.user_id,
        body=data.body,
    )
    await crud_user.update_last_active(db, user_id=current_user.user_id)
    return msg


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=PaginatedMessagesResponse,
    summary="היסטוריית הודעות",
)
async def list_conversation_messages(
    conversation_id: UUID,
    limit: int = Query(30, ge=1, le=100),
    before: int | None = Query(None, description="לפני message_id (טעינת הודעות ישנות יותר)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """הודעות בשיחה (cursor-based pagination). רק participant יכול לצפות."""
    return await get_messages(
        db,
        conversation_id=conversation_id,
        current_user_id=current_user.user_id,
        limit=limit,
        before_message_id=before,
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
    מייצא את השיחה לקובץ iCal (.ics) ללוח שנה.
    דורש ניתוח AI קיים או מנתח על המקום.
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

    raise LinkupError(
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
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/unread-count", response_model=dict)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await chat_crud.get_unread_conversations_count(db, current_user.user_id)
    return {"count": count}
