from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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
    result = []
    for g in groups:
        count = await crud.get_member_count(db, g.group_id)
        result.append(group_to_out(g, count))
    return result


async def join_by_invite(db: AsyncSession, invite_code: str, user_id: UUID) -> GroupOut:
    group = await crud.get_group_by_invite_code(db, invite_code)
    if not group or not group.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="קבוצה לא נמצאה")

    existing = await crud.get_membership(db, group.group_id, user_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="כבר חבר בקבוצה")

    if group.max_members:
        count = await crud.get_member_count(db, group.group_id)
        if count >= group.max_members:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="הקבוצה מלאה")

    await crud.join_group(db, group.group_id, user_id)
    count = await crud.get_member_count(db, group.group_id)
    return group_to_out(group, count)
