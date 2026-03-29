"""
CRUD operations לניתוח AI של שיחות צ'אט.
"""

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat.model import ChatAnalysis


async def create_analysis(
    db: AsyncSession,
    conversation_id: UUID,
    driver_name: str,
    passenger_name: str,
    pickup_location: str,
    meeting_time: str,
    summary_hebrew: str,
    analysis_json: dict,
) -> ChatAnalysis:
    """
    יוצר ניתוח AI חדש לשיחה.
    """
    analysis = ChatAnalysis(
        conversation_id=conversation_id,
        driver_name=driver_name,
        passenger_name=passenger_name,
        pickup_location=pickup_location,
        meeting_time=meeting_time,
        summary_hebrew=summary_hebrew,
        analysis_json=analysis_json,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


async def get_analysis_by_conversation_id(
    db: AsyncSession,
    conversation_id: UUID,
) -> ChatAnalysis | None:
    """
    מחזיר ניתוח AI לפי conversation_id.
    """
    result = await db.execute(select(ChatAnalysis).where(ChatAnalysis.conversation_id == conversation_id))
    return result.scalars().first()


async def analysis_exists(db: AsyncSession, conversation_id: UUID) -> bool:
    """
    בודק אם קיים ניתוח AI לשיחה.
    """
    analysis = await get_analysis_by_conversation_id(db, conversation_id)
    return analysis is not None
