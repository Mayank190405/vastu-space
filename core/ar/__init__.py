"""
VĀSTU AR Independent Layer Subsystem (Stage 29)
Provides marker-based AR relocalization, spatial anchors,
device-to-model coordinate alignment, and route projection.
"""

from core.ar.marker_detector import ARMarkerDetector
from core.ar.localization_engine import ARLocalizationEngine
from core.ar.validator import ARLocalizationValidator

__all__ = [
    "ARMarkerDetector",
    "ARLocalizationEngine",
    "ARLocalizationValidator",
]
