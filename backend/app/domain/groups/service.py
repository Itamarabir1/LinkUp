from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import LinkUpError
from app.domain.groups import crud
from app.domain.groups.schema import GroupCreate, GroupOut, group_to_out


async def create_group(db: AsyncSession, data: GroupCreate, user_id: UUID) -> GroupOut:
    group = await crud.create_group(
        db,
        name=data.name,
        admin_id=user_id,
        max_members=data.max_members,
        description=data.description,
    )
    count = await crud.get_member_count(db, group.group_id)
    return group_to_out(group, count)


async def get_my_groups(db: AsyncSession, user_id: UUID) -> list[GroupOut]:
    groups = await crud.get_user_groups(db, user_id)
    if not groups:
        return []
    counts = await crud.get_member_counts_batch(db, [g.group_id for g in groups])
    return [group_to_out(g, counts.get(g.group_id, 0)) for g in groups]


async def join_by_invite(db: AsyncSession, invite_code: str, user_id: UUID) -> GroupOut:
    group = await crud.get_group_by_invite_code(db, invite_code)
    if not group or not group.is_active:
        raise LinkUpError(
            message="קבוצה לא נמצאה",
            status_code=404,
            error_code="GROUP_NOT_FOUND",
        )

    existing = await crud.get_membership(db, group.group_id, user_id)
    if existing:
        raise LinkUpError(
            message="כבר חבר בקבוצה",
            status_code=409,
            error_code="GROUP_ALREADY_MEMBER",
        )

    if group.max_members:
        count = await crud.get_member_count(db, group.group_id)
        if count >= group.max_members:
            raise LinkUpError(
                message="הקבוצה מלאה",
                status_code=400,
                error_code="GROUP_FULL",
            )

    await crud.join_group(db, group.group_id, user_id)
    count = await crud.get_member_count(db, group.group_id)
    return group_to_out(group, count)
