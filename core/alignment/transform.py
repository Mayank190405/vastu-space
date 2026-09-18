"""
Metric Sim(3) Transformation Representation:
Explicitly handles scale, rotation, translation, and matrix representations for 3D coordinate alignment.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from core.schemas.metric_transform import MetricTransformSchema, MetricScaleSource

class MetricTransform:
    def __init__(
        self,
        scale: float = 1.0,
        rotation_matrix: Optional[np.ndarray] = None,
        translation: Optional[np.ndarray] = None,
        scale_source: MetricScaleSource = MetricScaleSource.UNSCALED,
        scale_confidence: float = 0.0,
        canonical_frame: str = "RIGHT_HANDED_Z_UP",
        floor_elevation_m: float = 0.0,
        evidence_details: Optional[Dict[str, Any]] = None
    ):
        if scale <= 0.0:
            raise ValueError(f"Scale must be strictly positive, got {scale}")
        self.scale = float(scale)
        self.rotation_matrix = rotation_matrix if rotation_matrix is not None else np.eye(3, dtype=np.float64)
        self.translation = translation if translation is not None else np.zeros(3, dtype=np.float64)
        self.scale_source = scale_source
        self.scale_confidence = float(scale_confidence)
        self.canonical_frame = canonical_frame
        self.floor_elevation_m = float(floor_elevation_m)
        self.evidence_details = evidence_details or {}

    @property
    def rotation_quaternion(self) -> List[float]:
        """Converts rotation matrix to unit quaternion [qx, qy, qz, qw]."""
        R = self.rotation_matrix
        tr = R[0, 0] + R[1, 1] + R[2, 2]
        if tr > 0:
            S = np.sqrt(tr + 1.0) * 2
            qw = 0.25 * S
            qx = (R[2, 1] - R[1, 2]) / S
            qy = (R[0, 2] - R[2, 0]) / S
            qz = (R[1, 0] - R[0, 1]) / S
        elif (R[0, 0] > R[1, 1]) and (R[0, 0] > R[2, 2]):
            S = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
            qw = (R[2, 1] - R[1, 2]) / S
            qx = 0.25 * S
            qy = (R[0, 1] + R[1, 0]) / S
            qz = (R[0, 2] + R[2, 0]) / S
        elif R[1, 1] > R[2, 2]:
            S = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
            qw = (R[0, 2] - R[2, 0]) / S
            qx = (R[0, 1] + R[1, 0]) / S
            qy = 0.25 * S
            qz = (R[1, 2] + R[2, 1]) / S
        else:
            S = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
            qw = (R[1, 0] - R[0, 1]) / S
            qx = (R[0, 2] + R[2, 0]) / S
            qy = (R[1, 2] + R[2, 1]) / S
            qz = 0.25 * S

        q = np.array([qx, qy, qz, qw])
        q = q / (np.linalg.norm(q) + 1e-9)
        return [float(round(v, 6)) for v in q]

    @property
    def matrix_4x4(self) -> List[List[float]]:
        """Returns the 4x4 homogeneous Sim(3) transformation matrix."""
        T = np.eye(4, dtype=np.float64)
        T[:3, :3] = self.scale * self.rotation_matrix
        T[:3, 3] = self.translation
        return [[float(round(val, 6)) for val in row] for row in T]

    def apply(self, points: np.ndarray) -> np.ndarray:
        """
        Transforms points from local reconstruction frame to canonical world frame:
        P_world = s * (R @ P_local) + t
        """
        pts = np.asarray(points, dtype=np.float64)
        if len(pts) == 0:
            return pts
        # (N, 3) @ (3, 3).T = (N, 3)
        rotated = np.dot(pts, self.rotation_matrix.T)
        scaled = self.scale * rotated
        translated = scaled + self.translation
        return translated

    def apply_inverse(self, points: np.ndarray) -> np.ndarray:
        """
        Transforms points from canonical world frame back to local reconstruction frame:
        P_local = (1/s) * (R^T @ (P_world - t))
        """
        pts = np.asarray(points, dtype=np.float64)
        if len(pts) == 0:
            return pts
        untranslated = pts - self.translation
        unscaled = untranslated / self.scale
        unrotated = np.dot(unscaled, self.rotation_matrix)
        return unrotated

    def to_schema(self) -> MetricTransformSchema:
        """Converts to validated MetricTransformSchema."""
        return MetricTransformSchema(
            scale=float(round(self.scale, 6)),
            translation=[float(round(v, 4)) for v in self.translation],
            rotation_matrix=[[float(round(v, 6)) for v in row] for row in self.rotation_matrix],
            rotation_quaternion=self.rotation_quaternion,
            matrix_4x4=self.matrix_4x4,
            scale_source=self.scale_source,
            scale_confidence=float(round(self.scale_confidence, 4)),
            canonical_frame=self.canonical_frame,
            floor_elevation_m=float(round(self.floor_elevation_m, 4)),
            evidence_details=self.evidence_details
        )
