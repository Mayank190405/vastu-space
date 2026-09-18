"""
Semantic Taxonomy & Architectural Dimension Priors:
Defines canonical classes for indoor spatial understanding and plausibility bounds.
"""

from typing import Dict, Any, Tuple
from enum import Enum

class SemanticClass(str, Enum):
    ROOM = "room"
    DOOR = "door"
    WINDOW = "window"
    FURNITURE = "furniture"
    TABLE = "table"
    CHAIR = "chair"
    SOFA = "sofa"
    DESK = "desk"
    SIGNAGE = "signage"
    ARCHITECTURAL_OBJECT = "architectural_object"
    OTHER = "other"

# Category groupings
CLASS_TO_CATEGORY: Dict[str, str] = {
    SemanticClass.ROOM.value: "SPATIAL_ZONE",
    SemanticClass.DOOR.value: "CIRCULATION",
    SemanticClass.WINDOW.value: "APERTURE",
    SemanticClass.FURNITURE.value: "FURNISHING",
    SemanticClass.TABLE.value: "FURNISHING",
    SemanticClass.CHAIR.value: "FURNISHING",
    SemanticClass.SOFA.value: "FURNISHING",
    SemanticClass.DESK.value: "FURNISHING",
    SemanticClass.SIGNAGE.value: "WAYFINDING",
    SemanticClass.ARCHITECTURAL_OBJECT.value: "STRUCTURAL",
    SemanticClass.OTHER.value: "GENERAL"
}

# Dimension priors (min_extent, max_extent) in meters [dx, dy, dz]
DIMENSION_PRIORS: Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = {
    SemanticClass.DOOR.value: ((0.6, 0.05, 1.8), (1.5, 0.4, 2.5)),
    SemanticClass.WINDOW.value: ((0.4, 0.05, 0.4), (3.0, 0.4, 2.5)),
    SemanticClass.CHAIR.value: ((0.3, 0.3, 0.4), (0.9, 0.9, 1.2)),
    SemanticClass.TABLE.value: ((0.5, 0.5, 0.5), (3.5, 2.0, 1.1)),
    SemanticClass.DESK.value: ((0.8, 0.4, 0.6), (2.4, 1.2, 0.9)),
    SemanticClass.SOFA.value: ((0.8, 0.6, 0.5), (3.5, 1.5, 1.1)),
    SemanticClass.SIGNAGE.value: ((0.1, 0.01, 0.1), (1.5, 0.2, 1.0)),
    SemanticClass.ARCHITECTURAL_OBJECT.value: ((0.1, 0.1, 0.1), (10.0, 10.0, 5.0)),
}

def validate_dimensions(class_name: str, extent: Tuple[float, float, float]) -> bool:
    """Returns True if the object extent is physically plausible for its class."""
    if class_name not in DIMENSION_PRIORS:
        return True
    min_ext, max_ext = DIMENSION_PRIORS[class_name]
    # Allow some orientation variance by sorting extents
    s_ext = sorted(extent)
    s_min = sorted(min_ext)
    s_max = sorted(max_ext)
    for val, mi, ma in zip(s_ext, s_min, s_max):
        if val < mi * 0.5 or val > ma * 1.8:
            return False
    return True
