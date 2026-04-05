import logging
from datetime import datetime
from typing import Any

from sqlalchemy import inspect as sa_inspect

from app.core.exceptions.ride import InvalidRouteError
from app.domain.rides.enum import RideStatus

# מודלים ו-Enums
from app.domain.rides.model import Ride

# לוגיקה ותשתיות
from app.domain.rides.ride_eta import calculate_estimated_arrival
from app.domain.rides.schema import RideResponse
from app.infrastructure.geo.utils import to_geo_line, to_geo_point

logger = logging.getLogger(__name__)


class RideMapper:
    """
    Ride Domain Mapper.
    אחראי על טרנספורמציה וולידציה של נתוני נסיעה בין שכבות (Cache -> DB).
    משתמש ב-Static Methods מכיוון שהוא Stateless.
    """

    @staticmethod
    def map_cache_to_model(cached_data: dict[str, Any], selected_index: int) -> Ride:
        """
        הפונקציה הראשית (Orchestrator).
        ממירה נתוני חיפוש זמניים מה-Cache לאובייקט Ride קבוע של SQLAlchemy.
        """
        # 1. ולידציה של שלמות הנתונים
        RideMapper._validate_input(cached_data, selected_index)

        try:
            # המסלול שהמשתמש בחר – ממנו לוקחים זמן נסיעה וק"מ לשמירה בטבלה
            route = cached_data["routes"][selected_index]
            departure_time = RideMapper._parse_time(cached_data["departure_time"])

            # זמן נסיעה וק"מ שייכים למסלול הנבחר בלבד (נשמרים בעמודות בטבלת rides)
            duration_min = route.get("duration_min")
            distance_km = route.get("distance_km")
            if duration_min is None:
                duration_min = 0
            if distance_km is None:
                distance_km = 0

            # 2. חישוב נתונים נגזרים (Derived Data)
            estimated_arrival = calculate_estimated_arrival(
                departure_time=departure_time,
                duration_min=int(duration_min) if duration_min is not None else 0,
            )

            # 3. בניית המודל (יצירת אובייקט Ride) – כולל זמן נסיעה וק"מ של המסלול הנבחר
            return Ride(
                driver_id=cached_data["driver_id"],
                group_id=cached_data.get("group_id"),
                departure_time=departure_time,
                estimated_arrival_time=estimated_arrival,
                # המרות גיאוגרפיות (PostGIS)
                origin_geom=to_geo_point(cached_data["origin_lat"], cached_data["origin_lon"]),
                destination_geom=to_geo_point(cached_data["dest_lat"], cached_data["dest_lon"]),
                route_coords=to_geo_line(route.get("coords", [])),
                route_summary=(route.get("summary") or "").strip() or None,
                # נתוני מסלול – מהמסלול שנבחר בלבד (נכנסים לטבלה)
                distance_km=float(distance_km),
                duration_min=float(duration_min),
                # סטטוס התחלתי
                status=RideStatus.OPEN,
                # נתונים נוספים
                price=cached_data.get("price"),
                available_seats=cached_data.get("available_seats"),
                origin_name=cached_data.get("origin_name"),
                destination_name=cached_data.get("destination_name"),
            )

        except Exception as e:
            logger.error(f"Mapping failed for ride: {e!s}")
            raise InvalidRouteError(detail=f"Failed to map ride data: {e!s}")

    @staticmethod
    def _validate_input(data: dict[str, Any], idx: int) -> None:
        """בדיקת תקינות המבנה מה-Cache – כולל זמן נסיעה וק\"מ של המסלול הנבחר"""
        routes = data.get("routes", [])
        if not (0 <= idx < len(routes)):
            raise InvalidRouteError(index=idx)

        required_fields = [
            "origin_lat",
            "origin_lon",
            "dest_lat",
            "dest_lon",
            "departure_time",
            "driver_id",
        ]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise InvalidRouteError(detail=f"Missing required cache fields: {missing}")

        # וידוא שהמסלול הנבחר כולל זמן נסיעה וק\"מ (יישמרו בטבלת rides)
        selected_route = routes[idx]
        for field in ("duration_min", "distance_km"):
            if field not in selected_route:
                raise InvalidRouteError(detail=f"Missing route field for selected route: {field}")

    @staticmethod
    def _parse_time(departure_time: Any) -> datetime:
        """מבטיח חזרה של אובייקט datetime תקין"""
        if isinstance(departure_time, str):
            try:
                return datetime.fromisoformat(departure_time)
            except ValueError:
                # ניסיון פורמט נוסף אם צריך או זריקת שגיאה
                raise InvalidRouteError(detail="Invalid departure_time format")
        return departure_time

    @staticmethod
    def _resolve_group_name(ride: Ride, explicit: str | None) -> str | None:
        """שם קבוצה מפורש או מ-relationship שכבר בזיכרון — בלי lazy load."""
        if explicit is not None:
            return explicit
        if ride.group_id is None:
            return None
        state = sa_inspect(ride)
        if "group" in state.unloaded:
            return None
        grp = ride.group
        if grp is None:
            return None
        return getattr(grp, "name", None)

    @staticmethod
    def to_response(
        ride: Ride,
        group_name: str | None = None,
        user_booking_status: str | None = None,
    ) -> RideResponse:
        """
        ממיר Ride ORM ל-RideResponse — שדות מפורשים, בלי model_validate על ה-ORM.
        group_name / user_booking_status אופציונליים מהשירות.
        """
        resolved_group_name = RideMapper._resolve_group_name(ride, group_name)
        return RideResponse(
            ride_id=ride.ride_id,
            driver_id=ride.driver_id,
            group_id=ride.group_id,
            group_name=resolved_group_name,
            origin_name=ride.origin_name or "",
            destination_name=ride.destination_name or "",
            departure_time=ride.departure_time,
            estimated_arrival_time=ride.estimated_arrival_time,
            available_seats=ride.available_seats,
            price=float(ride.price) if ride.price is not None else 0.0,
            status=ride.status,
            created_at=ride.created_at,
            user_booking_status=user_booking_status,
            total_distance_km=float(ride.distance_km) if ride.distance_km is not None else 0.0,
            total_duration_min=float(ride.duration_min) if ride.duration_min is not None else 0.0,
            route_coords=ride.route_coords_list or [],
            route_summary=ride.route_summary,
        )


to_response = RideMapper.to_response
