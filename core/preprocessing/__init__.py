"""
VĀSTU Preprocessing Package
Provides frame extraction, deterministic quality analysis, duplicate suppression,
adaptive keyframe selection, and auditable manifests with explicit discard reasons.
"""

from core.preprocessing.analyzer import FrameQualityAnalyzer
from core.preprocessing.selector import AdaptiveKeyframeSelector
from core.preprocessing.engine import PreprocessingEngine

__all__ = [
    "FrameQualityAnalyzer",
    "AdaptiveKeyframeSelector",
    "PreprocessingEngine"
]
