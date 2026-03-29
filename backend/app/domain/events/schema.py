from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional
from uuid import UUID
from app.domain.events.enum import DispatchTarget


class Event(BaseModel):
    """
    Domain Event DTO.
    השפה המשותפת של כל המערכת להעברת אירועים.
    """

    name: str = Field(..., example="user.verification_code_created")
    payload: Dict[str, Any] = Field(default_factory=dict)
    targets: List[DispatchTarget] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # --- וולידציה ברמת סניור ---
    @field_validator("name")
    @classmethod
    def validate_event_name(cls, v: str) -> str:
        if "." not in v:
            raise ValueError("Event name must follow the 'domain.action' format (e.g., user.created)")
        return v.lower()

    # --- חילוץ נתונים חכם (Properties) ---

    @property
    def user_id(self) -> Optional[UUID]:
        """חילוץ בטוח של user_id מה-payload"""
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
    def ride_id(self) -> Optional[UUID]:
        """חילוץ בטוח של ride_id מה-payload"""
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
        """מחשב אוטומטית את ה-Routing Key ל-RabbitMQ"""
        return self.metadata.get("routing_key", self.name)

    @property
    def exchange(self) -> str:
        """מחלץ את ה-Exchange המבוקש או מחזיר ברירת מחדל"""
        return self.metadata.get("exchange", "system_events")

    class Config:
        # מאפשר ליצור את ה-DTO ישירות מאובייקט SQLAlchemy (מה-Outbox)
        from_attributes = True
        # מונע שינוי של האובייקט אחרי שהוא נוצר (Immutability - מומלץ לאירועים)
        frozen = True
