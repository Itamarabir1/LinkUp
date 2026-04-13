"""
Schemas for AI analysis of chat conversations.
"""

from pydantic import BaseModel


class RideSummary(BaseModel):
    """AI analysis summary for a rideshare chat."""

    driver_name: str
    passenger_name: str
    pickup_location: str
    meeting_time: str
    summary_hebrew: str
