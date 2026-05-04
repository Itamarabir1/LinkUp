from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class BaseNotificationProvider(ABC):
    @abstractmethod
    async def send(
        self,
        user: Any,
        template_name: str,
        context: dict[str, Any],
        db: AsyncSession | None = None,
    ) -> None:
        pass

    def can_send(self, user: Any) -> bool:
        return True
