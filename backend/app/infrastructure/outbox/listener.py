import asyncio
from urllib.parse import urlparse, urlunparse

import asyncpg


class OutboxListener:
    def __init__(self) -> None:
        self._conn: asyncpg.Connection | None = None
        self._event = asyncio.Event()

    @staticmethod
    def _normalize_dsn(dsn: str) -> str:
        value = (dsn or "").strip()
        if value.startswith("postgresql+asyncpg://"):
            return "postgresql://" + value[len("postgresql+asyncpg://") :]
        if value.startswith("postgres://"):
            return "postgresql://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            return value
        parsed = urlparse(value)
        if parsed.scheme == "postgresql+asyncpg":
            return urlunparse(("postgresql", parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
        return value

    async def connect(self, dsn: str) -> None:
        normalized = self._normalize_dsn(dsn)
        self._conn = await asyncpg.connect(normalized)
        await self._conn.add_listener("outbox_new_event", self._on_notify)

    def _on_notify(self, _conn: asyncpg.Connection, _pid: int, _channel: str, _payload: str) -> None:
        self._event.set()

    async def wait_for_notify(self, timeout: float = 30.0) -> bool:
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
            self._event.clear()
            return True
        except TimeoutError:
            return False

    def wake(self) -> None:
        self._event.set()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
