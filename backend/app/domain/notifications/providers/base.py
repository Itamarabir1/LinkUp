from abc import ABC, abstractmethod
from typing import Any


class BaseNotificationProvider(ABC):
    """
    Interface defining what a notification provider looks like in LinkUp.
    Architectural contract, not a thin wrapper.
    """

    @abstractmethod
    async def send(self, user: Any, channel_config: dict[str, Any], context: dict[str, Any]) -> None:
        """Subclasses must implement async send logic."""
        pass

    def can_send(self, user: Any) -> bool:
        """Default: always allow send. Specific providers may override."""
        return True
