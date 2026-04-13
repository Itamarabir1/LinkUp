from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.events.enum import DispatchTarget


class Event(BaseModel):
    """
    Domain event DTO — shared contract for cross-service messaging.
    """

    name: str = Field(..., example="user.verification_code_created")
    payload: dict[str, Any] = Field(default_factory=dict)
    targets: list[DispatchTarget] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # --- Validation ---
    @field_validator("name")
    @classmethod
    def validate_event_name(cls, v: str) -> str:
        if "." not in v:
            raise ValueError("Event name must follow the 'domain.action' format (e.g., user.created)")
        return v.lower()

    # --- Smart properties ---

    @property
    def user_id(self) -> UUID | None:
        """Safely parse user_id from payload."""
        val = self.payload.get("user_id")
        if val is None:
            return None
        if isinstance(val, UUID):
            return val
        try:
            return UUID(str(val))
        except (ValueError, TypeError):
            return None

    @property
    def ride_id(self) -> UUID | None:
        """Safely parse ride_id from payload."""
        val = self.payload.get("ride_id")
        if val is None:
            return None
        if isinstance(val, UUID):
            return val
        try:
            return UUID(str(val))
        except (ValueError, TypeError):
            return None

    @property
    def routing_key(self) -> str:
        """Derived RabbitMQ routing key (metadata override or event name)."""
        return self.metadata.get("routing_key", self.name)

    @property
    def exchange(self) -> str:
        """Exchange name from metadata or default."""
        return self.metadata.get("exchange", "system_events")

    class Config:
        # Build DTO from SQLAlchemy row (e.g. outbox)
        from_attributes = True
        # Immutable after creation (recommended for events)
        frozen = True
