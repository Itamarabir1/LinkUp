from sqlalchemy import Column, Float
from geoalchemy2 import Geometry
from sqlalchemy.orm import declarative_mixin


@declarative_mixin
class GeoLocationMixin:
    """מוסיף שדות מיקום בסיסיים ויכולות גיאומטריות לכל מודל"""

    origin_lat = Column(Float, nullable=False)
    origin_lon = Column(Float, nullable=False)
    dest_lat = Column(Float, nullable=False)
    dest_lon = Column(Float, nullable=False)

    # השדות האלו קריטיים לשאילתות מרחק (Spatial Queries)
    origin_geom = Column(Geometry(geometry_type="POINT", srid=4326), index=True, nullable=False)
    destination_geom = Column(Geometry(geometry_type="POINT", srid=4326), index=True, nullable=False)

    @staticmethod
    def create_point(lat: float, lon: float):
        """עוזר ליצירת נקודה בפורמט ש-PostGIS אוהב"""
        return f"POINT({lon} {lat})"
