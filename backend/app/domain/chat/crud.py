"""
1:1 chat CRUD — conversations and messages.
Always persist user_id_1 < user_id_2 on Conversation.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.chat.model import ChatAnalysis, Conversation, ConversationParticipant, Message

# --- Conversations ---


async def get_or_create_conversation(db: AsyncSession, user_id_a: UUID, user_id_b: UUID) -> Conversation:
    """
    Returns an existing conversation between the two users, or creates one.
    Always stores user_id_1 < user_id_2.
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
        ),
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
    Returns a conversation by id only if the user is a participant (user_id_1 or user_id_2).
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
        ),
    )
    return result.scalars().first()


async def list_conversations_for_user(db: AsyncSession, user_id: UUID) -> list[Conversation]:
    """
    All conversations where the user is a participant.
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
            ),
        )
        .order_by(desc(Conversation.created_at)),
    )
    return list(result.scalars().unique().all())


async def get_conversations_with_timeout(
    db: AsyncSession,
    timeout_hours: int = 24,
) -> list[Conversation]:
    """
    Conversations with no AI analysis yet whose last message is older than timeout_hours.

    Args:
        db: AsyncSession
        timeout_hours: hours without a new message (default 24)

    Returns:
        Conversations that should be analyzed
    """
    # Cutoff: now minus timeout_hours
    timeout_threshold = datetime.utcnow() - timedelta(hours=timeout_hours)

    # Last message before threshold and no chat_analysis row
    subquery = (
        select(
            Message.conversation_id,
            func.max(Message.created_at).label("last_message_at"),
        )
        .group_by(Message.conversation_id)
        .having(func.max(Message.created_at) < timeout_threshold)
        .subquery()
    )

    # Join conversations to that subquery; outer join analysis and require none
    result = await db.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.user_1),
            selectinload(Conversation.user_2),
        )
        .join(subquery, Conversation.conversation_id == subquery.c.conversation_id)
        .outerjoin(ChatAnalysis, Conversation.conversation_id == ChatAnalysis.conversation_id)
        .where(ChatAnalysis.conversation_id.is_(None)),  # no analysis row
    )
    return list(result.scalars().unique().all())


# --- Messages ---


async def create_message(
    db: AsyncSession,
    conversation_id: UUID,
    sender_id: UUID,
    body: str,
) -> Message:
    """Persists a new message in a conversation."""
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
    Message history for a conversation (pagination).
    Returns (list in chronological order oldest→newest, has_more).
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
    """Loads all messages in a conversation (internal: calendar export, AI analysis). Chronological order."""
    cid = UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
    q = select(Message).where(Message.conversation_id == cid).order_by(Message.created_at.asc())
    if limit is not None:
        q = q.limit(limit)
    result = await db.execute(q)
    return list(result.scalars().unique().all())


async def get_last_message(db: AsyncSession, conversation_id: UUID) -> Message | None:
    """Latest message in a conversation (for conversation list)."""
    cid = UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
    result = await db.execute(select(Message).where(Message.conversation_id == cid).order_by(desc(Message.created_at)).limit(1))
    return result.scalars().first()


# --- Read / Unread ---


async def mark_conversation_read(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> None:
    """Updates last_read_at for a user in a conversation."""
    cid = UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
    uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id

    now = datetime.now(UTC)
    result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == cid,
            ConversationParticipant.user_id == uid,
        ),
    )
    participant = result.scalars().first()
    if not participant:
        return
    participant.last_read_at = now
    await db.commit()


async def get_unread_conversations_count(db: AsyncSession, user_id: UUID) -> int:
    """
    Count of conversations with new messages from the other party after last_read_at.
    Unread is per conversation, not per message.
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
    Whether the conversation has new messages from the other party after the user’s last_read_at.
    """
    cid = UUID(str(conversation_id)) if isinstance(conversation_id, str) else conversation_id
    uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id

    part_res = await db.execute(
        select(ConversationParticipant.last_read_at).where(
            ConversationParticipant.conversation_id == cid,
            ConversationParticipant.user_id == uid,
        ),
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
