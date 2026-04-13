import logging
from datetime import datetime, timedelta

from geoalchemy2.shape import to_shape

logger = logging.getLogger(__name__)


def convert_db_route_to_list(route_geom) -> list[list[float]]:
    """Converts a DB Geometry object to a list of [lat, lon] for the frontend."""
    if not route_geom:
        return []
    try:
        shape = to_shape(route_geom)
        # shape.coords is (lon, lat) as tuple or Point; convert to [lat, lon]
        out: list[list[float]] = []
        for pt in shape.coords:
            if hasattr(pt, "x") and hasattr(pt, "y"):
                out.append([pt.y, pt.x])
            elif isinstance(pt, (tuple, list)) and len(pt) >= 2:
                out.append([float(pt[1]), float(pt[0])])  # (lon, lat) -> [lat, lon]
            else:
                continue
        return out
    except Exception as e:
        logger.error(f"❌ Failed to convert DB route geometry: {e}")
        return []


def calculate_eta(start_time: datetime, duration_seconds: float, buffer_percent: float = 0.15) -> str:
    """Computes estimated arrival time with a buffer."""
    total_seconds = duration_seconds * (1 + buffer_percent)
    eta_datetime = start_time + timedelta(seconds=total_seconds)
    return eta_datetime.strftime("%H:%M")


def format_duration(seconds: float) -> str:
    """Formats seconds as human-readable Hebrew duration text for the UI."""
    minutes = round(seconds / 60)
    if minutes < 60:
        return f"{minutes} דקות"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours} שעות ו-{mins} דקות"
