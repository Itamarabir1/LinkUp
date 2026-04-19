"""
Schemas for AI-powered free-text ride search parsing.
"""

import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

VALID_MISSING_FIELDS = frozenset(
    {
        "pickup_name",
        "destination_name",
        "departure_time",
        "departure_time_to",
        "departure_date",
        "destination_radius",
        "search_radius",
    }
)


class ConversationTurn(BaseModel):
    """Single turn in conversation history."""

    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=500)


class AISearchQuery(BaseModel):
    """Input: free text + optional conversation history."""

    query: str = Field(..., min_length=1, max_length=400)
    conversation_history: list[ConversationTurn] = Field(
        default_factory=list,
        max_length=6,
        description="Previous turns for context (max 6)",
    )


class AISearchResult(BaseModel):
    """
    Structured parameters extracted by AI from free text.
    Location/time fields may be null when uncertain.
    """

    pickup_name: str | None = Field(None)
    destination_name: str | None = Field(None)
    departure_time: datetime | None = Field(None)
    departure_time_to: datetime | None = Field(None)
    departure_date: date | None = Field(None)
    destination_radius: float | None = Field(None, ge=0.1, le=50)
    search_radius: float | None = Field(None, ge=0.1, le=50)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_interpretation: str = Field(default="")
    needs_clarification: bool = Field(default=True)
    missing_fields: list[str] = Field(default_factory=list)
    ambiguity_reasons: list[str] = Field(default_factory=list)
    follow_up_question: str | None = Field(
        None,
        max_length=120,
        description="Hebrew question when critical fields missing",
    )

    @field_validator("departure_date", mode="before")
    @classmethod
    def parse_departure_date(cls, v: object) -> date | None:
        if v is None or v == "":
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return None
            if "T" in s:
                return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
            return date.fromisoformat(s[:10])
        return None

    @field_validator("missing_fields")
    @classmethod
    def validate_missing_fields(cls, v: list[str]) -> list[str]:
        """Only allow known field names — prevents LLM hallucination."""
        return [f for f in v if f in VALID_MISSING_FIELDS]

    @field_validator("ambiguity_reasons")
    @classmethod
    def validate_ambiguity_reasons(cls, v: list[str]) -> list[str]:
        """Truncate each reason to 100 chars max."""
        return [r[:100].strip() for r in v if r.strip()]

    @staticmethod
    def _sanitize_follow_up(q: str | None) -> str | None:
        if not q:
            return None
        cleaned = re.sub(r"<[^>]+>", "", q)
        out = cleaned[:120].strip()
        return out or None

    @model_validator(mode="after")
    def harmonize_clarification_and_follow_up(self):
        """Locations + at least one time anchor (instant, range, or date-only) => ready to search."""
        missing_location = not self.pickup_name or not self.destination_name
        if missing_location:
            self.needs_clarification = True
            if not self.follow_up_question:
                if not self.pickup_name and not self.destination_name:
                    self.follow_up_question = "מאיפה ולאן אתה רוצה לנסוע?"
                elif not self.pickup_name:
                    self.follow_up_question = "מאיפה אתה יוצא?"
                else:
                    self.follow_up_question = "לאן אתה רוצה להגיע?"
            self.follow_up_question = self._sanitize_follow_up(self.follow_up_question)
            if not self.follow_up_question:
                self.follow_up_question = "מאיפה ולאן אתה רוצה לנסוע?"
            return self

        has_time_anchor = bool(self.departure_date or self.departure_time)
        if not has_time_anchor:
            self.needs_clarification = True
            if not self.follow_up_question:
                self.follow_up_question = "באיזה תאריך אתה מחפש נסיעה?"
            self.follow_up_question = self._sanitize_follow_up(self.follow_up_question)
            if not self.follow_up_question:
                self.follow_up_question = "באיזה תאריך אתה מחפש נסיעה?"
            return self

        self.needs_clarification = False
        self.follow_up_question = None
        return self
