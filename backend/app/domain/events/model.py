from typing import Any

from pydantic import BaseModel, Field

# Event enums live in domain.events.enum
from app.domain.events.enum import DispatchTarget


class Event(BaseModel):
    """
    Domain event schema — contract for persisted/outbound events.
    """

    name: str = Field(..., min_length=1)
    payload: dict[str, Any]
    targets: list[DispatchTarget] = Field(..., min_items=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        # Immutable snapshot
        frozen = True
        # Works with SQLAlchemy instances and plain dicts
        from_attributes = True
