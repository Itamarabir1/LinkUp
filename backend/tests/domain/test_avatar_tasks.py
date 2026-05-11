"""Unit tests for avatar worker tasks (upload + remove event handlers)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions.infrastructure import WorkerTaskFailed
from app.workers.tasks.avatar_tasks import (
    AVATAR_REMOVE_EVENT,
    AVATAR_UPLOAD_EVENT,
    _is_versioned_avatar_prefix,
    _should_delete_previous_avatar_prefix,
    handle_avatar_upload_event,
)


# ============================================================
# handle_avatar_upload_event — routing
# ============================================================


@pytest.mark.asyncio
async def test_handle_avatar_upload_event_routes_upload():
    data = {"user_id": str(uuid4()), "staging_key": "avatars/staging/abc.jpg"}
    with patch(
        "app.workers.tasks.avatar_tasks._handle_avatar_upload",
        new_callable=AsyncMock,
    ) as mock_upload:
        await handle_avatar_upload_event(data, routing_key=AVATAR_UPLOAD_EVENT)

    mock_upload.assert_awaited_once_with(data)


@pytest.mark.asyncio
async def test_handle_avatar_upload_event_routes_remove():
    data = {"user_id": str(uuid4())}
    with patch(
        "app.workers.tasks.avatar_tasks._handle_avatar_remove",
        new_callable=AsyncMock,
    ) as mock_remove:
        await handle_avatar_upload_event(data, routing_key=AVATAR_REMOVE_EVENT)

    mock_remove.assert_awaited_once_with(data)


@pytest.mark.asyncio
async def test_handle_avatar_upload_event_unknown_routing_key_ignored():
    data = {"user_id": str(uuid4())}
    with patch(
        "app.workers.tasks.avatar_tasks._handle_avatar_upload",
        new_callable=AsyncMock,
    ) as mock_upload, patch(
        "app.workers.tasks.avatar_tasks._handle_avatar_remove",
        new_callable=AsyncMock,
    ) as mock_remove:
        await handle_avatar_upload_event(data, routing_key="some.unknown.event")

    mock_upload.assert_not_awaited()
    mock_remove.assert_not_awaited()


# ============================================================
# _handle_avatar_upload
# ============================================================


@pytest.mark.asyncio
async def test_avatar_upload_missing_user_id_raises():
    from app.workers.tasks.avatar_tasks import _handle_avatar_upload

    with pytest.raises(WorkerTaskFailed):
        await _handle_avatar_upload({"staging_key": "avatars/staging/x.jpg"})


@pytest.mark.asyncio
async def test_avatar_upload_missing_staging_key_raises():
    from app.workers.tasks.avatar_tasks import _handle_avatar_upload

    with pytest.raises(WorkerTaskFailed):
        await _handle_avatar_upload({"user_id": str(uuid4()), "staging_key": ""})


@pytest.mark.asyncio
async def test_avatar_upload_user_not_found_raises():
    from app.workers.tasks.avatar_tasks import _handle_avatar_upload

    user_id = uuid4()
    with patch(
        "app.workers.tasks.avatar_tasks.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.avatar_tasks.crud_user.get_by_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(WorkerTaskFailed):
            await _handle_avatar_upload(
                {"user_id": str(user_id), "staging_key": "avatars/staging/x.jpg"}
            )


@pytest.mark.asyncio
async def test_avatar_upload_happy_path():
    from app.workers.tasks.avatar_tasks import _handle_avatar_upload

    user_id = uuid4()
    old_key = f"avatars/{user_id}/v1/"
    new_prefix = f"avatars/{user_id}/v2/"

    user = MagicMock()
    user.avatar_key = old_key
    user.avatar_staging_key = "avatars/staging/abc.jpg"
    user.avatar_status = "processing"

    with patch(
        "app.workers.tasks.avatar_tasks.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.avatar_tasks.crud_user.get_by_id",
        new_callable=AsyncMock,
        return_value=user,
    ), patch(
        "app.workers.tasks.avatar_tasks.process_and_save_avatar",
        new_callable=AsyncMock,
        return_value=new_prefix,
    ) as mock_process, patch(
        "app.workers.tasks.avatar_tasks.s3_uploads_total",
    ) as mock_metric, patch(
        "app.workers.tasks.avatar_tasks._delete_previous_avatar_prefix_best_effort",
        new_callable=AsyncMock,
    ) as mock_delete_prev:
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _handle_avatar_upload(
            {"user_id": str(user_id), "staging_key": "avatars/staging/abc.jpg"}
        )

    mock_process.assert_awaited_once()
    assert user.avatar_key == new_prefix
    assert user.avatar_staging_key is None
    assert user.avatar_status == "ready"
    mock_db.commit.assert_awaited_once()
    mock_delete_prev.assert_awaited_once_with(old_key, new_prefix)


@pytest.mark.asyncio
async def test_avatar_upload_processing_failure_sets_status_failed():
    from app.workers.tasks.avatar_tasks import _handle_avatar_upload

    user_id = uuid4()

    user = MagicMock()
    user.avatar_key = None
    user.avatar_staging_key = "avatars/staging/x.jpg"
    user.avatar_status = "processing"

    with patch(
        "app.workers.tasks.avatar_tasks.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.avatar_tasks.crud_user.get_by_id",
        new_callable=AsyncMock,
        return_value=user,
    ), patch(
        "app.workers.tasks.avatar_tasks.process_and_save_avatar",
        new_callable=AsyncMock,
        side_effect=RuntimeError("S3 timeout"),
    ), patch(
        "app.workers.tasks.avatar_tasks.s3_uploads_failed_total",
    ), patch(
        "app.workers.tasks.avatar_tasks._cleanup_orphan_prefix_best_effort",
        new_callable=AsyncMock,
    ):
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(WorkerTaskFailed):
            await _handle_avatar_upload(
                {"user_id": str(user_id), "staging_key": "avatars/staging/x.jpg"}
            )

    assert user.avatar_status == "failed"


# ============================================================
# _handle_avatar_remove
# ============================================================


@pytest.mark.asyncio
async def test_avatar_remove_missing_user_id_raises():
    from app.workers.tasks.avatar_tasks import _handle_avatar_remove

    with pytest.raises(WorkerTaskFailed):
        await _handle_avatar_remove({})


@pytest.mark.asyncio
async def test_avatar_remove_user_not_found_raises():
    from app.workers.tasks.avatar_tasks import _handle_avatar_remove

    user_id = uuid4()
    with patch(
        "app.workers.tasks.avatar_tasks.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.avatar_tasks.crud_user.get_by_id",
        new_callable=AsyncMock,
        return_value=None,
    ):
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(WorkerTaskFailed):
            await _handle_avatar_remove({"user_id": str(user_id)})


@pytest.mark.asyncio
async def test_avatar_remove_happy_path_deletes_folder():
    from app.workers.tasks.avatar_tasks import _handle_avatar_remove

    user_id = uuid4()
    user = MagicMock()

    with patch(
        "app.workers.tasks.avatar_tasks.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.avatar_tasks.crud_user.get_by_id",
        new_callable=AsyncMock,
        return_value=user,
    ), patch(
        "app.workers.tasks.avatar_tasks.storage_service.delete_user_avatar_folder",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _handle_avatar_remove({"user_id": str(user_id)})

    mock_delete.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_avatar_remove_s3_failure_raises_worker_task_failed():
    from app.workers.tasks.avatar_tasks import _handle_avatar_remove

    user_id = uuid4()
    user = MagicMock()

    with patch(
        "app.workers.tasks.avatar_tasks.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.avatar_tasks.crud_user.get_by_id",
        new_callable=AsyncMock,
        return_value=user,
    ), patch(
        "app.workers.tasks.avatar_tasks.storage_service.delete_user_avatar_folder",
        new_callable=AsyncMock,
        side_effect=RuntimeError("S3 unreachable"),
    ):
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(WorkerTaskFailed):
            await _handle_avatar_remove({"user_id": str(user_id)})


# ============================================================
# Helper functions
# ============================================================


class TestShouldDeletePreviousAvatarPrefix:
    def test_none_old_key_returns_false(self):
        assert _should_delete_previous_avatar_prefix(None, "avatars/uid/v2/") is False

    def test_same_key_returns_false(self):
        key = "avatars/uid/v1/"
        assert _should_delete_previous_avatar_prefix(key, key) is False

    def test_staging_key_returns_false(self):
        assert (
            _should_delete_previous_avatar_prefix(
                "avatars/staging/abc.jpg", "avatars/uid/v2/"
            )
            is False
        )

    def test_valid_old_avatars_prefix_returns_true(self):
        assert (
            _should_delete_previous_avatar_prefix(
                "avatars/uid/v1/", "avatars/uid/v2/"
            )
            is True
        )

    def test_non_avatars_prefix_returns_false(self):
        assert (
            _should_delete_previous_avatar_prefix(
                "other/path/", "avatars/uid/v2/"
            )
            is False
        )


class TestIsVersionedAvatarPrefix:
    def test_versioned_prefix_returns_true(self):
        assert _is_versioned_avatar_prefix("avatars/some-uid/v2/") is True

    def test_legacy_prefix_no_version_returns_false(self):
        assert _is_versioned_avatar_prefix("avatars/some-uid/") is False

    def test_staging_prefix_returns_false(self):
        assert _is_versioned_avatar_prefix("avatars/staging/abc/") is False

    def test_non_avatar_prefix_returns_false(self):
        assert _is_versioned_avatar_prefix("other/path/v1/") is False

    def test_version_segment_must_have_content_after_v(self):
        assert _is_versioned_avatar_prefix("avatars/uid/v/") is False
