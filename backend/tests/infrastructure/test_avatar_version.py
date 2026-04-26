"""Versioned avatar key contract (immutable prefix) without hitting S3."""

from app.infrastructure.s3.image_processor import new_avatar_version_id
from app.workers.tasks.avatar_tasks import _is_versioned_avatar_prefix


def test_new_avatar_version_id_unique_and_shape():
    a = new_avatar_version_id()
    b = new_avatar_version_id()
    assert a != b
    parts = a.split("_", 1)
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert len(parts[1]) == 8


def test_versioned_prefix_concatenates_filename():
    prefix = "avatars/550e8400-e29b-41d4-a716-446655440000/v1700000000000000000_deadbeef/"
    assert f"{prefix}400x400.webp" == ("avatars/550e8400-e29b-41d4-a716-446655440000/v1700000000000000000_deadbeef/400x400.webp")


def test_is_versioned_avatar_prefix_true():
    assert _is_versioned_avatar_prefix("avatars/550e8400-e29b-41d4-a716-446655440000/v1700000000000000000_deadbeef/")
    assert _is_versioned_avatar_prefix("avatars/550e8400-e29b-41d4-a716-446655440000/v1700000000000000000_deadbeef")


def test_is_versioned_avatar_prefix_false_legacy_user_folder():
    assert not _is_versioned_avatar_prefix("avatars/550e8400-e29b-41d4-a716-446655440000/")
    assert not _is_versioned_avatar_prefix("avatars/550e8400-e29b-41d4-a716-446655440000")


def test_is_versioned_avatar_prefix_false_staging():
    assert not _is_versioned_avatar_prefix("avatars/staging/uuid_abc123.webp")
