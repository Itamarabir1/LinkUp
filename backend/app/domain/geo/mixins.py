from geoalchemy2 import Geometry
from sqlalchemy import Column, Float
from sqlalchemy.orm import declarative_mixin


@declarative_mixin
class GeoLocationMixin:
    """Adds baseline location fields and geometry columns to a model."""

    origin_lat = Column(Float, nullable=False)
    origin_lon = Column(Float, nullable=False)
    dest_lat = Column(Float, nullable=False)
    dest_lon = Column(Float, nullable=False)

    # Required for spatial distance queries
    origin_geom = Column(Geometry(geometry_type="POINT", srid=4326), index=True, nullable=False)
    destination_geom = Column(Geometry(geometry_type="POINT", srid=4326), index=True, nullable=False)

    @staticmethod
    def create_point(lat: float, lon: float):
        """Builds a WKT POINT string in the format PostGIS expects."""
        return f"POINT({lon} {lat})"
