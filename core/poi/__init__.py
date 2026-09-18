"""
VĀSTU POI (Point of Interest) Subsystem
"""

from core.poi.service import POIService
from core.schemas.poi import PointOfInterest, POICoordinates, POICameraViewpoint, POIAttachment

__all__ = [
    "POIService",
    "PointOfInterest",
    "POICoordinates",
    "POICameraViewpoint",
    "POIAttachment",
]
