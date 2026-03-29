"""
CRUD צ'אט 1:1 – שיחות והודעות.
תמיד שומרים user_id_1 < user_id_2 ב־Conversation.
"""

from uuid import UUID
from sqlalchemy import select, desc, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone

from app.domain.chat.model import Conversation, Message, ConversationParticipant, ChatAnalysis

# --- Conversations ---


async def get_or_create_conversation(db: AsyncSession, user_id_a: UUID, user_id_b: UUID) -> Conversation:
    """
    מחזיר שיחה קיימת בין שני המשתמשים, או יוצר חדשה.
    user_id_1 < user_id_2 תמיד.
    """
    u1_raw, u2_raw = (user_id_a, user_id_b) if user_id_a < user_id_b else (user_id_b, user_id_a)
    u1 = UUID(str(u1_raw)) if isinstance(u1_raw, str) else u1_raw
    u2 = UUID(str(u2_raw)) if isinstance(u2_raw, str) else u2_raw
    if u1 == u2:
        raise ValueError("Cannot create conversation with self")

    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id_1 == u1,
            Conversation.user_id_2 == u2,
        )
    )
    conv = result.scalars().first()
    if conv:
        return conv

    conv = Conversation(user_id_1=u1, user_id_2=u2)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def get_conversation_by_id(db: AsyncSession, conversation_id: UUID, participant_user_id: UUID) -> Conversation | None:
    """
    מחזיר שיחה לפי ID רק אם המשתמש הוא participant (user_id_1 או user_id_2).
    """
    cid = UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
    pid = UUID(str(participant_user_id)) if isinstance(participant_user_id, str) else participant_user_id
    result = await db.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.user_1),
            selectinload(Conversation.user_2),
        )
        .where(
            Conversation.conversation_id == cid,
            or_(
                Conversation.user_id_1 == pid,
                Conversation.user_id_2 == pid,
            ),
        )
    )
    return result.scalars().first()


async def list_conversations_for_user(db: AsyncSession, user_id: UUID) -> list[Conversation]:
    """
    רשימת כל השיחות של המשתמש (כשותף).
    """
    uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
    result = await db.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.user_1),
            selectinload(Conversation.user_2),
        )
        .where(
            or_(
                Conversation.user_id_1 == uid,
                Conversation.user_id_2 == uid,
            )
        )
        .order_by(desc(Conversation.created_at))
    )
    return list(result.scalars().unique().all())


async def get_conversations_with_timeout(
    db: AsyncSession,
    timeout_hours: int = 24,
) -> list[Conversation]:
    """
    מחזיר שיחות שלא נשלח להן סיכום ושההודעה האחרונה בהן היא לפני timeout_hours שעות.

    Args:
        db: AsyncSession
        timeout_hours: מספר שעות ללא הודעות חדשות (ברירת מחדל: 24)

    Returns:
        רשימת שיחות שצריכות ניתוח
    """
    # זמן גבול: עכשיו פחות timeout_hours
    timeout_threshold = datetime.utcnow() - timedelta(hours=timeout_hours)

    # שאילתה: שיחות שיש להן הודעה אחרונה לפני timeout_threshold
    # ואין להן ניתוח AI (chat_analysis)
    subquery = (
        select(
            Message.conversation_id,
            func.max(Message.created_at).label("last_message_at"),
        )
        .group_by(Message.conversation_id)
        .having(func.max(Message.created_at) < timeout_threshold)
        .subquery()
    )

    # שיחות שיש להן הודעה אחרונה לפני timeout, ואין להן ניתוח
    result = await db.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.user_1),
            selectinload(Conversation.user_2),
        )
        .join(subquery, Conversation.conversation_id == subquery.c.conversation_id)
        .outerjoin(ChatAnalysis, Conversation.conversation_id == ChatAnalysis.conversation_id)
        .where(ChatAnalysis.conversation_id.is_(None))  # אין ניתוח קיים
    )
    return list(result.scalars().unique().all())


# --- Messages ---


async def create_message(
    db: AsyncSession,
    conversation_id: UUID,
    sender_id: UUID,
    body: str,
) -> Message:
    """שומר הודעה חדשה בשיחה."""
    cid = UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
    sid = UUID(str(sender_id)) if isinstance(sender_id, str) else sender_id
    msg = Message(
        conversation_id=cid,
        sender_id=sid,
        body=body,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_messages(
    db: AsyncSession,
    conversation_id: UUID,
    limit: int = 50,
    before_message_id: int | None = None,
) -> tuple[list[Message], bool]:
    """
    היסטוריית הודעות בשיחה (pagination).
    מחזיר (רשימה בסדר כרונולוגי ישן→חדש, has_more).
    """
    cid = UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
    q = select(Message).where(Message.conversation_id == cid).order_by(desc(Message.created_at)).limit(limit + 1)
    if before_message_id is not None:
        sub = select(Message.created_at).where(Message.message_id == before_message_id)
        q = q.where(Message.created_at < sub.scalar_subquery())
    result = await db.execute(q)
    rows = list(result.scalars().unique().all())
    has_more = len(rows) > limit
    items = rows[:limit][::-1]  # ישן → חדש
    return (items, has_more)


async def get_all_messages_for_conversation(
    db: AsyncSession,
    conversation_id: UUID,
    limit: int | None = 5000,
) -> list[Message]:
    """שליפת כל ההודעות בשיחה (לשימוש פנימי: calendar export, AI analysis). בסדר כרונולוגי."""
    cid = UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
    q = select(Message).where(Message.conversation_id == cid).order_by(Message.created_at.asc())
    if limit is not None:
        q = q.limit(limit)
    result = await db.execute(q)
    return list(result.scalars().unique().all())


async def get_last_message(db: AsyncSession, conversation_id: UUID) -> Message | None:
    """הודעה אחרונה בשיחה (להרשימה)."""
    cid = UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
    result = await db.execute(select(Message).where(Message.conversation_id == cid).order_by(desc(Message.created_at)).limit(1))
    return result.scalars().first()


# --- Read / Unread ---


async def mark_conversation_read(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> None:
    """עדכון last_read_at למשתמש בשיחה."""
    cid = UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
    uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == cid,
            ConversationParticipant.user_id == uid,
        )
    )
    participant = result.scalars().first()
    if not participant:
        return
    participant.last_read_at = now
    await db.commit()


async def get_unread_conversations_count(db: AsyncSession, user_id: UUID) -> int:
    """
    מספר שיחות שבהן יש הודעות חדשות שנשלחו ע"י הצד השני אחרי last_read_at.
    נספר unread ברמת שיחה (conversation), לא הודעות.
    """
    uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id

    subq = (
        select(
            Message.conversation_id.label("conversation_id"),
            func.max(Message.created_at).label("last_message_at"),
        )
        .where(Message.sender_id != uid)
        .group_by(Message.conversation_id)
        .subquery()
    )

    q = (
        select(func.count())
        .select_from(ConversationParticipant)
        .join(subq, ConversationParticipant.conversation_id == subq.c.conversation_id)
        .where(
            ConversationParticipant.user_id == uid,
            or_(
                ConversationParticipant.last_read_at.is_(None),
                ConversationParticipant.last_read_at < subq.c.last_message_at,
            ),
        )
    )
    result = await db.execute(q)
    return int(result.scalar() or 0)


async def has_unread_messages(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> bool:
    """
    האם יש הודעות חדשות בשיחה (מאת הצד השני) אחרי last_read_at של המשתמש.
    """
    cid = UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
    uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id

    part_res = await db.execute(
        select(ConversationParticipant.last_read_at).where(
            ConversationParticipant.conversation_id == cid,
            ConversationParticipant.user_id == uid,
        )
    )
    last_read_at = part_res.scalar_one_or_none()

    msg_q = select(func.max(Message.created_at)).where(
        Message.conversation_id == cid,
        Message.sender_id != uid,
    )
    msg_res = await db.execute(msg_q)
    last_other_msg_at = msg_res.scalar_one_or_none()
    if not last_other_msg_at:
        return False
    if last_read_at is None:
        return True
    return last_other_msg_at > last_read_at
