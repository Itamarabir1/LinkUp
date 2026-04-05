import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, get_db
from app.api.dependencies.services import get_ride_service
from app.domain.groups import crud, service
from app.domain.groups.schema import (
    GroupCreate,
    GroupImageConfirmRequest,
    GroupImageUploadResponse,
    GroupMemberOut,
    GroupOut,
    GroupUpdate,
    group_member_to_out,
    group_to_out,
)
from app.domain.rides.schema import RideResponse
from app.domain.rides.service import RideService
from app.domain.users.model import User
from app.infrastructure.s3.service import storage_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.create_group(db, data, current_user.user_id)


@router.get("/my", response_model=list[GroupOut])
async def get_my_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_my_groups(db, current_user.user_id)


@router.get("/join/{invite_code}", response_model=GroupOut)
async def get_group_by_invite(
    invite_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = await crud.get_group_by_invite_code(db, invite_code)
    if not group:
        raise HTTPException(status_code=404, detail="קבוצה לא נמצאה")
    count = await crud.get_member_count(db, group.group_id)
    return group_to_out(group, count)


@router.post("/join/{invite_code}", response_model=GroupOut)
async def join_group(
    invite_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.join_by_invite(db, invite_code, current_user.user_id)


@router.get("/{group_id}/members", response_model=list[GroupMemberOut])
async def get_members(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = await crud.get_membership(db, group_id, current_user.user_id)
    if not membership:
        raise HTTPException(status_code=403, detail="אינך חבר בקבוצה")
    members = await crud.get_group_members(db, group_id)
    return [group_member_to_out(m) for m in members]


@router.get("/{group_id}/rides", response_model=list[RideResponse])
async def get_group_rides(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ride_svc: RideService = Depends(get_ride_service),
):
    """פיד נסיעות של הקבוצה. רק חברי הקבוצה יכולים לראות."""
    membership = await crud.get_membership(db, group_id, current_user.user_id)
    if not membership:
        raise HTTPException(status_code=403, detail="אינך חבר בקבוצה")
    return await ride_svc.get_rides_by_group_id(db, group_id)


@router.post("/{group_id}/upload-image", response_model=GroupImageUploadResponse)
async def get_group_image_upload_url(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """מנהל בלבד. מחזיר presigned URL להעלאת תמונת קבוצה."""
    group = await crud.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="קבוצה לא נמצאה")
    if group.admin_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="רק אדמין יכול להעלות תמונת קבוצה")
    upload_url, key = await storage_service.generate_group_image_upload_url(group_id)
    return GroupImageUploadResponse(upload_url=upload_url, key=key)


@router.post("/{group_id}/confirm-image", response_model=GroupOut)
async def confirm_group_image(
    group_id: UUID,
    data: GroupImageConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """מנהל בלבד. מאשר העלאה ומעדכן את avatar_key של הקבוצה."""
    group = await crud.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="קבוצה לא נמצאה")
    if group.admin_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="רק אדמין יכול לעדכן תמונת קבוצה")
    expected_prefix = f"GROUPS/{group_id}/"
    if not data.key.startswith(expected_prefix):
        raise HTTPException(status_code=400, detail="מפתח תמונה לא תקין")
    group = await crud.update_group_avatar_key(db, group, data.key)
    count = await crud.get_member_count(db, group_id)
    return group_to_out(group, count)


@router.delete("/{group_id}/image", response_model=GroupOut)
async def delete_group_image(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """מנהל בלבד. מוחק תמונת קבוצה מ-S3 ומאפס avatar_key."""
    group = await crud.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="קבוצה לא נמצאה")
    if group.admin_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="רק אדמין יכול למחוק תמונת קבוצה")
    try:
        await storage_service.delete_group_image_folder(group_id)
    except Exception as e:
        logger.warning("S3 delete failed (non-critical): %s", e)
    group = await crud.update_group_avatar_key(db, group, None)
    count = await crud.get_member_count(db, group_id)
    return group_to_out(group, count)


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    group_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = await crud.get_membership(db, group_id, current_user.user_id)
    if not membership or membership.role != "admin":
        raise HTTPException(status_code=403, detail="רק אדמין יכול להסיר חברים")
    await crud.remove_member(db, group_id, user_id)


@router.patch("/{group_id}/members/{user_id}/promote", response_model=GroupMemberOut)
async def promote_member(
    group_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = await crud.get_membership(db, group_id, current_user.user_id)
    if not membership or membership.role != "admin":
        raise HTTPException(status_code=403, detail="רק אדמין יכול לקדם חברים")
    member = await crud.update_member_role(db, group_id, user_id, "admin")
    if not member:
        raise HTTPException(status_code=404, detail="חבר לא נמצא")
    return group_member_to_out(member)


@router.delete("/{group_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await crud.remove_member(db, group_id, current_user.user_id)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def close_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = await crud.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="קבוצה לא נמצאה")
    if group.admin_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="רק אדמין יכול לסגור קבוצה")
    await crud.close_group(db, group)


@router.patch("/{group_id}", response_model=GroupOut)
async def update_group(
    group_id: UUID,
    data: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = await crud.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="קבוצה לא נמצאה")
    if group.admin_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="רק אדמין יכול לעדכן קבוצה")
    if data.name is not None:
        group = await crud.rename_group(db, group, data.name)
    if data.description is not None:
        group = await crud.update_group_description(db, group, data.description)
    count = await crud.get_member_count(db, group_id)
    return group_to_out(group, count)
