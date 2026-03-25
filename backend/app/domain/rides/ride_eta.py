from datetime import datetime, timedelta
from typing import Union


def calculate_estimated_arrival(
    departure_time: Union[str, datetime], duration_min: int
) -> datetime:
    """
    Business Logic: Calculates ETA based on departure and duration.
    Handles both string (ISO) and datetime objects.
    """
    if isinstance(departure_time, str):
        departure_time = datetime.fromisoformat(departure_time)

    return departure_time + timedelta(minutes=duration_min)
