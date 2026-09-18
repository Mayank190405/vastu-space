"""
VĀSTU Model Versioning & Comparison Subsystem
"""

from core.versioning.registry import ImmutableModelRegistry, ImmutableVersionError
from core.versioning.rescan_pipeline import RescanVersioningPipeline
from core.versioning.comparator import ModelComparator
from core.schemas.model_version import ModelVersion, ModelArtifactKeys
from core.schemas.model_comparison import (
    GeometryComparison,
    POIComparison,
    RelocatedPOI,
    NavigationComparison,
    ConfidenceComparison,
    ModelComparisonResult,
)

__all__ = [
    "ImmutableModelRegistry",
    "ImmutableVersionError",
    "RescanVersioningPipeline",
    "ModelComparator",
    "ModelVersion",
    "ModelArtifactKeys",
    "GeometryComparison",
    "POIComparison",
    "RelocatedPOI",
    "NavigationComparison",
    "ConfidenceComparison",
    "ModelComparisonResult",
]
