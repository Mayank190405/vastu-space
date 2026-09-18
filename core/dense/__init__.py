"""
VĀSTU Dense Reconstruction Package
Multi-view depth consistency, evidence point cloud fusion with observation traceability,
density mapping, and comprehensive defect detection (holes, isolated clusters, floating geometry, noise).
"""

from core.dense.consistency import MultiViewDepthConsistency
from core.dense.evidence_fusion import DenseEvidenceFusion, DenseEvidencePoint
from core.dense.defect_detector import ReconstructionDefectDetector

__all__ = [
    "MultiViewDepthConsistency",
    "DenseEvidenceFusion",
    "DenseEvidencePoint",
    "ReconstructionDefectDetector"
]
