"""טסטים לשירות קבוצות — mock ל-CRUD, ללא DB."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions.base import LinkupError
from app.domain.groups.schema import GroupCreate
from app.domain.groups.service import create_group, join_by_invite


def _mock_group(**kwargs):
    """מימוש קל ללא ORM — נמנע מטעינת מיפוי Group↔User בזמן בניית אובייקט."""
    defaults = {
        "max_members": None,
        "invite_expires_at": None,
        "created_at": datetime.now(timezone.utc),
        "avatar_key": None,
        "description": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_create_group_returns_group_with_admin():
    """יצירת קבוצה — בדיקה שהקבוצה נוצרת עם admin_id נכון."""
    with patch("app.domain.groups.service.crud") as mock_crud:
        admin_id = uuid4()
        group_id = uuid4()

        mock_group = _mock_group(
            group_id=group_id,
            name="קבוצת טסט",
            invite_code="TEST123",
            admin_id=admin_id,
            is_active=True,
        )
        mock_crud.create_group = AsyncMock(return_value=mock_group)
        mock_crud.get_member_count = AsyncMock(return_value=1)

        data = GroupCreate(name="קבוצת טסט")
        result = await create_group(None, data, admin_id)

        assert result.admin_id == admin_id
        assert result.name == "קבוצת טסט"
        assert result.member_count == 1
        mock_crud.create_group.assert_called_once()


@pytest.mark.asyncio
async def test_join_by_invite_adds_member():
    """הצטרפות לקבוצה — בדיקה שמשתמש מצטרף בהצלחה."""
    with patch("app.domain.groups.service.crud") as mock_crud:
        user_id = uuid4()
        group_id = uuid4()
        admin_id = uuid4()

        mock_group = _mock_group(
            group_id=group_id,
            name="קבוצת טסט",
            invite_code="INVITE123",
            admin_id=admin_id,
            is_active=True,
            max_members=None,
        )
        mock_crud.get_group_by_invite_code = AsyncMock(return_value=mock_group)
        mock_crud.get_membership = AsyncMock(return_value=None)
        mock_crud.join_group = AsyncMock(return_value=None)
        mock_crud.get_member_count = AsyncMock(return_value=2)

        result = await join_by_invite(None, "INVITE123", user_id)

        assert result.group_id == group_id
        assert result.member_count == 2
        mock_crud.join_group.assert_called_once_with(None, group_id, user_id)


@pytest.mark.asyncio
async def test_join_full_group_raises_error():
    """קבוצה מלאה — בדיקה שלא ניתן להצטרף."""
    with patch("app.domain.groups.service.crud") as mock_crud:
        user_id = uuid4()
        group_id = uuid4()

        mock_group = _mock_group(
            group_id=group_id,
            name="קבוצה מלאה",
            invite_code="FULL123",
            admin_id=uuid4(),
            is_active=True,
            max_members=5,
        )
        mock_crud.get_group_by_invite_code = AsyncMock(return_value=mock_group)
        mock_crud.get_membership = AsyncMock(return_value=None)
        mock_crud.get_member_count = AsyncMock(return_value=5)

        with pytest.raises(LinkupError) as exc_info:
            await join_by_invite(None, "FULL123", user_id)

        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "GROUP_FULL"
