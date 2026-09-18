"""
VĀSTU Tri-Representation Subsystem: Visual, Structural, and Collision Separation
"""

from core.schemas.representation_bundle import (
    VisualRepresentationMeta,
    StructuralRepresentationMeta,
    CollisionRepresentationMeta,
    CollisionObstacle,
    TriRepresentationBundle
)
from core.representations.builder import TriRepresentationBuilder
from core.representations.runtime import RepresentationRuntimeCoordinator

__all__ = [
    "VisualRepresentationMeta",
    "StructuralRepresentationMeta",
    "CollisionRepresentationMeta",
    "CollisionObstacle",
    "TriRepresentationBundle",
    "TriRepresentationBuilder",
    "RepresentationRuntimeCoordinator",
]
