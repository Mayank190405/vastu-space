"""
Semantic Reconstruction Engine:
Performs 3D semantic object reconstruction independent from geometry representation.
Fits 3D oriented bounding boxes, resolves room containment, tracks source observations,
and enforces strict confidence thresholds to prevent low-confidence detections from becoming ground truth.
"""

from typing import List, Dict, Any, Optional, Tuple
import uuid
import numpy as np

from core.schemas.semantic_object import SemanticObject, OrientedBoundingBox
from core.semantics.taxonomy import (
    SemanticClass,
    CLASS_TO_CATEGORY,
    validate_dimensions
)
from core.semantics.room_partitioner import RoomSemanticDetector

class SemanticReconstructionEngine:
    def __init__(
        self,
        ground_truth_confidence_threshold: float = 0.70,
        room_detector: Optional[RoomSemanticDetector] = None
    ):
        self.ground_truth_confidence_threshold = ground_truth_confidence_threshold
        self.room_detector = room_detector or RoomSemanticDetector()

    def fit_oriented_bounding_box(
        self,
        points_3d: np.ndarray
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Fits an oriented 3D bounding box (OBB) using PCA on the 3D points.
        Returns:
            center: [x, y, z]
            extent: [dx, dy, dz]
            quaternion: [qx, qy, qz, qw]
        """
        pts = np.asarray(points_3d, dtype=np.float64)
        if len(pts) == 0:
            return [0.0, 0.0, 0.0], [0.5, 0.5, 0.5], [0.0, 0.0, 0.0, 1.0]

        center = np.mean(pts, axis=0)

        if len(pts) < 4:
            min_xyz = np.min(pts, axis=0)
            max_xyz = np.max(pts, axis=0)
            extent = np.maximum(max_xyz - min_xyz, [0.1, 0.1, 0.1])
            return center.tolist(), extent.tolist(), [0.0, 0.0, 0.0, 1.0]

        # Use PCA for principal orientations
        cov = np.cov((pts - center).T)
        eigvals, eigvecs = np.linalg.eigh(cov)

        # Ensure right-handed coordinate frame
        if np.linalg.det(eigvecs) < 0:
            eigvecs[:, 0] = -eigvecs[:, 0]

        # Project points onto eigenvectors
        proj = np.dot(pts - center, eigvecs)
        min_proj = np.min(proj, axis=0)
        max_proj = np.max(proj, axis=0)

        center_offset = (min_proj + max_proj) / 2.0
        center_corrected = center + np.dot(eigvecs, center_offset)
        extent = np.maximum(max_proj - min_proj, [0.05, 0.05, 0.05])

        # Rotation matrix to quaternion conversion
        R = eigvecs
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

        return (
            [float(round(v, 4)) for v in center_corrected],
            [float(round(v, 4)) for v in extent],
            [float(round(v, 4)) for v in q]
        )

    def reconstruct_object(
        self,
        class_name: str,
        points_3d: np.ndarray,
        source_observations: List[str],
        base_detection_confidence: float = 0.85,
        object_id: Optional[str] = None,
        label: Optional[str] = None,
        room_id: Optional[str] = None,
        associated_cell_ids: Optional[List[str]] = None,
        parent_surface_id: Optional[str] = None
    ) -> SemanticObject:
        """
        Reconstructs a single 3D semantic object with full provenance, position, bounding geometry,
        room association, and strict ground truth policy gating.
        """
        obj_id = object_id or f"sem_{class_name}_{uuid.uuid4().hex[:8]}"
        human_label = label or f"{class_name.replace('_', ' ').title()}"

        center, extent, quat = self.fit_oriented_bounding_box(points_3d)

        # Multi-view observation consensus bonus
        obs_count = len(source_observations)
        multi_view_bonus = min(0.10, max(0.0, (obs_count - 1) * 0.03))

        # Dimensional plausibility verification
        is_plausible = validate_dimensions(class_name, tuple(extent))
        plausibility_penalty = 0.0 if is_plausible else 0.25

        # Final calculated confidence
        final_conf = float(np.clip(
            base_detection_confidence + multi_view_bonus - plausibility_penalty,
            0.0,
            1.0
        ))

        # Room association
        resolved_room_id = room_id or self.room_detector.find_enclosing_room(center)

        # Ground Truth Policy:
        # Never treat low-confidence detections (< threshold) as ground truth
        is_ground_truth = (final_conf >= self.ground_truth_confidence_threshold)
        status = "CONFIRMED" if is_ground_truth else "PROVISIONAL"

        category = CLASS_TO_CATEGORY.get(class_name, "GENERAL")

        obb = OrientedBoundingBox(
            center=center,
            extent_dx_dy_dz=extent,
            rotation_quaternion=quat
        )

        return SemanticObject(
            object_id=obj_id,
            class_name=class_name,
            label=human_label,
            category=category,
            position=center,
            oriented_bounding_box=obb,
            room_id=resolved_room_id,
            confidence=float(round(final_conf, 3)),
            source_observations=source_observations,
            is_ground_truth_candidate=is_ground_truth,
            status=status,
            associated_cell_ids=associated_cell_ids or [],
            parent_surface_id=parent_surface_id
        )
