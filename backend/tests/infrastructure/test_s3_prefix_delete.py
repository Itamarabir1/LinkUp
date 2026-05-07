"""S3 prefix cleanup: streamed listing + DeleteObjects batching."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions.infrastructure import S3DeleteFailed
from app.infrastructure.s3.client import S3_DELETE_OBJECTS_MAX_KEYS, S3Client
from app.infrastructure.s3.service import StorageService


@pytest.mark.asyncio
async def test_list_and_delete_prefix_batches_chunks() -> None:
    n = S3_DELETE_OBJECTS_MAX_KEYS + 400
    keys = [f"avatars/u/k{i}" for i in range(n)]

    svc = StorageService()

    async def fake_iter_prefix(_prefix: str):
        for k in keys:
            yield k

    batches: list[list[str]] = []

    async def fake_batch(chunk: list[str]) -> None:
        batches.append(list(chunk))

    svc.client.iter_prefix_keys = fake_iter_prefix
    svc.client.delete_object_keys_batch = fake_batch

    await svc.list_and_delete_prefix("avatars/u/")

    assert len(batches) == 2
    assert len(batches[0]) == S3_DELETE_OBJECTS_MAX_KEYS
    assert len(batches[1]) == 400


@pytest.mark.asyncio
async def test_list_and_delete_prefix_empty_prefix() -> None:
    svc = StorageService()

    async def fake_iter_prefix(_prefix: str):
        if False:
            yield ""  # pragma: no cover — async generator, zero items

    batches: list[list[str]] = []

    async def fake_batch(chunk: list[str]) -> None:
        batches.append(list(chunk))

    svc.client.iter_prefix_keys = fake_iter_prefix
    svc.client.delete_object_keys_batch = fake_batch

    await svc.list_and_delete_prefix("empty/")

    assert batches == []


@pytest.mark.asyncio
async def test_delete_object_keys_batch_splits_and_calls_delete_objects() -> None:
    client = S3Client()
    n = 2400
    calls: list[int] = []

    mock_s3 = AsyncMock()
    mock_s3.delete_objects = AsyncMock(
        side_effect=lambda **kwargs: (
            calls.append(len(kwargs["Delete"]["Objects"])),
            {"Deleted": [], "Errors": []},
        )[1]
    )

    cm = AsyncMock()
    cm.__aenter__.return_value = mock_s3
    cm.__aexit__.return_value = None

    session = MagicMock()
    session.client = MagicMock(return_value=cm)

    keys = [f"k{i}" for i in range(n)]

    with patch.object(client, "_session", session):
        await client.delete_object_keys_batch(keys)

    assert calls == [1000, 1000, 400]
    assert mock_s3.delete_objects.await_count == 3


@pytest.mark.asyncio
async def test_delete_object_keys_batch_raises_on_errors_response() -> None:
    client = S3Client()

    mock_s3 = AsyncMock()
    mock_s3.delete_objects = AsyncMock(
        return_value={"Errors": [{"Key": "x", "Code": "AccessDenied", "Message": "denied"}]}
    )

    cm = AsyncMock()
    cm.__aenter__.return_value = mock_s3
    cm.__aexit__.return_value = None

    session = MagicMock()
    session.client = MagicMock(return_value=cm)

    with patch.object(client, "_session", session):
        with pytest.raises(S3DeleteFailed):
            await client.delete_object_keys_batch(["x"])


@pytest.mark.asyncio
async def test_delete_object_keys_batch_noop_empty() -> None:
    client = S3Client()
    session = MagicMock()
    session.client = MagicMock()

    with patch.object(client, "_session", session):
        await client.delete_object_keys_batch([])

    session.client.assert_not_called()
