import logging
import secrets
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions.base import LinkupError
from app.domain.groups.model import Group, GroupMember

logger = logging.getLogger(__name__)

_BASE62 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def _generate_invite_code(length: int = 8) -> str:
    return "".join(secrets.choice(_BASE62) for _ in range(length))


def _is_invite_code_unique_violation(exc: IntegrityError) -> bool:
    """התאמה ל-duplicate על invite_code (PostgreSQL / asyncpg)."""
    parts: list[str] = []
    if exc.orig is not None:
        parts.append(str(exc.orig))
    parts.append(str(exc))
    msg = " ".join(parts).lower()
    return "invite_code" in msg or getattr(exc.orig, "pgcode", None) == "23505"


async def create_group(
    db: AsyncSession,
    name: str,
    admin_id: UUID,
    max_members: int | None = None,
    description: str | None = None,
) -> Group:
    desc_trimmed = description[:500] if description else None

    for attempt in range(5):
        invite_code = _generate_invite_code()
        group = Group(
            name=name,
            invite_code=invite_code,
            admin_id=admin_id,
            max_members=max_members,
            description=desc_trimmed,
        )
        db.add(group)
        try:
            await db.flush()
            break
        except IntegrityError as e:
            await db.rollback()
            if not _is_invite_code_unique_violation(e):
                raise
            if attempt == 4:
                logger.warning("Failed to generate unique invite_code after 5 attempts")
                raise LinkupError(
                    message="שגיאה ביצירת קוד הזמנה",
                    status_code=500,
                    error_code="INVITE_CODE_GENERATION_FAILED",
                )

    member = GroupMember(group_id=group.group_id, user_id=admin_id, role="admin")
    db.add(member)
    await db.commit()
    await db.refresh(group)
    return group


async def get_group_by_id(db: AsyncSession, group_id: UUID) -> Group | None:
    result = await db.execute(select(Group).where(Group.group_id == group_id))
    return result.scalars().first()


async def get_group_by_invite_code(db: AsyncSession, invite_code: str) -> Group | None:
    result = await db.execute(select(Group).where(Group.invite_code == invite_code))
    return result.scalars().first()


async def get_user_groups(db: AsyncSession, user_id: UUID) -> list[Group]:
    result = await db.execute(
        select(Group).join(GroupMember, Group.group_id == GroupMember.group_id).where(GroupMember.user_id == user_id, Group.is_active.is_(True)),
    )
    return list(result.scalars().all())


async def get_group_members(db: AsyncSession, group_id: UUID) -> list[GroupMember]:
    result = await db.execute(select(GroupMember).where(GroupMember.group_id == group_id).options(selectinload(GroupMember.user)))
    return list(result.scalars().all())


async def get_membership(db: AsyncSession, group_id: UUID, user_id: UUID) -> GroupMember | None:
    result = await db.execute(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id))
    return result.scalars().first()


async def join_group(db: AsyncSession, group_id: UUID, user_id: UUID) -> GroupMember:
    member = GroupMember(group_id=group_id, user_id=user_id, role="member")
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def remove_member(db: AsyncSession, group_id: UUID, user_id: UUID) -> None:
    member = await get_membership(db, group_id, user_id)
    if not member:
        return
    group = await get_group_by_id(db, group_id)
    members = await get_group_members(db, group_id)
    others = [m for m in members if m.user_id != user_id]

    if group:
        if others:
            # מנהל יוצא — העבר מנהלות לחבר אחר (הוותיק ביותר)
            if group.admin_id == user_id:
                others.sort(key=lambda m: m.joined_at)
                new_admin = others[0]
                group.admin_id = new_admin.user_id
                new_admin.role = "admin"
        else:
            # אין חברים אחרי היציאה — כמו סגירת קבוצה (לא נשארת קבוצה "ריקה" פעילה)
            group.is_active = False

    db.delete(member)
    await db.commit()


async def update_member_role(db: AsyncSession, group_id: UUID, user_id: UUID, role: str) -> GroupMember | None:
    member = await get_membership(db, group_id, user_id)
    if member:
        member.role = role
        await db.commit()
        await db.refresh(member)
    return member


async def rename_group(db: AsyncSession, group: Group, name: str) -> Group:
    group.name = name
    await db.commit()
    await db.refresh(group)
    return group


async def update_group_description(db: AsyncSession, group: Group, description: str | None) -> Group:
    if description is not None and len(description) > 500:
        description = description[:500]
    group.description = description
    await db.commit()
    await db.refresh(group)
    return group


async def update_group_avatar_key(db: AsyncSession, group: Group, avatar_key: str | None) -> Group:
    group.avatar_key = avatar_key
    await db.commit()
    await db.refresh(group)
    return group


async def close_group(db: AsyncSession, group: Group) -> Group:
    group.is_active = False
    await db.commit()
    return group


async def get_member_count(db: AsyncSession, group_id: UUID) -> int:
    result = await db.execute(select(func.count()).select_from(GroupMember).where(GroupMember.group_id == group_id))
    return result.scalar_one()
