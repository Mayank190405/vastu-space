"""
Metric Coordinate Aligner:
Estimates canonical world coordinate alignment (gravity + yaw alignment, floor leveling at Z=0),
and evaluates scale evidence strictly across the 5-tier priority hierarchy.
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from core.schemas.metric_transform import MetricScaleSource
from core.alignment.transform import MetricTransform
from core.alignment.priorities import (
    LiDAREvidence,
    PhysicalMeasurementEvidence,
    FloorplanDimensionEvidence,
    KnownObjectEvidence,
    ManualCorrectionEvidence
)

def rotation_matrix_from_vectors(v_from: np.ndarray, v_to: np.ndarray) -> np.ndarray:
    """Computes 3x3 rotation matrix that rotates v_from to v_to using Rodrigues formula."""
    u1 = v_from / (np.linalg.norm(v_from) + 1e-9)
    u2 = v_to / (np.linalg.norm(v_to) + 1e-9)

    dot = float(np.dot(u1, u2))
    if dot >= 0.999999:
        return np.eye(3, dtype=np.float64)
    if dot <= -0.999999:
        # 180 degree flip around any perpendicular vector
        ortho = np.array([1.0, 0.0, 0.0]) if abs(u1[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        axis = np.cross(u1, ortho)
        axis = axis / np.linalg.norm(axis)
        return 2.0 * np.outer(axis, axis) - np.eye(3)

    v = np.cross(u1, u2)
    s = np.linalg.norm(v)
    vx = np.array([
        [0.0, -v[2], v[1]],
        [v[2], 0.0, -v[0]],
        [-v[1], v[0], 0.0]
    ])
    R = np.eye(3) + vx + np.dot(vx, vx) * ((1.0 - dot) / (s ** 2))
    return R

class MetricCoordinateAligner:
    def __init__(self, canonical_frame: str = "RIGHT_HANDED_Z_UP"):
        self.canonical_frame = canonical_frame

    def resolve_scale(
        self,
        lidar_evidence: Optional[LiDAREvidence] = None,
        physical_evidence: Optional[PhysicalMeasurementEvidence] = None,
        floorplan_evidence: Optional[FloorplanDimensionEvidence] = None,
        object_evidence: Optional[KnownObjectEvidence] = None,
        manual_evidence: Optional[ManualCorrectionEvidence] = None
    ) -> Tuple[float, MetricScaleSource, float, Dict[str, Any]]:
        """
        Resolves metric scale factor using available evidence in strict descending priority order:
        1. Metric LiDAR/AR data
        2. Measured physical dimensions
        3. Known floor-plan dimensions
        4. Reliable known object dimensions
        5. Manual correction
        """
        # Priority 1: Metric LiDAR/AR data
        if lidar_evidence is not None:
            return (
                float(lidar_evidence.scale_factor),
                MetricScaleSource.METRIC_LIDAR_AR,
                float(lidar_evidence.confidence),
                {"sensor_model": lidar_evidence.sensor_model, "point_count": lidar_evidence.point_count}
            )

        # Priority 2: Measured physical dimensions
        if physical_evidence is not None:
            scale = physical_evidence.compute_scale()
            return (
                float(scale),
                MetricScaleSource.MEASURED_PHYSICAL_DIMENSIONS,
                float(physical_evidence.confidence),
                {"measured_distance_m": physical_evidence.measured_distance_m, "tool": physical_evidence.measurement_tool}
            )

        # Priority 3: Known floor-plan dimensions
        if floorplan_evidence is not None:
            scale = floorplan_evidence.compute_scale()
            return (
                float(scale),
                MetricScaleSource.KNOWN_FLOORPLAN_DIMENSIONS,
                float(floorplan_evidence.confidence),
                {"reference_distance_m": floorplan_evidence.reference_distance_m, "drawing_id": floorplan_evidence.drawing_reference_id}
            )

        # Priority 4: Reliable known object dimensions
        if object_evidence is not None:
            scale = object_evidence.compute_scale()
            return (
                float(scale),
                MetricScaleSource.RELIABLE_KNOWN_OBJECT_DIMENSIONS,
                float(object_evidence.confidence),
                {"object_class": object_evidence.object_class, "standard_dim_m": object_evidence.standard_dimension_m}
            )

        # Priority 5: Manual correction
        if manual_evidence is not None:
            return (
                float(manual_evidence.manual_scale_factor),
                MetricScaleSource.MANUAL_CORRECTION,
                float(manual_evidence.confidence),
                {"operator_id": manual_evidence.operator_id, "reason": manual_evidence.reason}
            )

        # Fallback: Unscaled
        return (1.0, MetricScaleSource.UNSCALED, 0.0, {"warning": "No metric scale evidence available"})

    def compute_alignment_transform(
        self,
        points: np.ndarray,
        floor_normal: Optional[np.ndarray] = None,
        floor_point: Optional[np.ndarray] = None,
        gravity_vector: Optional[np.ndarray] = None,
        primary_facade_normal: Optional[np.ndarray] = None,
        lidar_evidence: Optional[LiDAREvidence] = None,
        physical_evidence: Optional[PhysicalMeasurementEvidence] = None,
        floorplan_evidence: Optional[FloorplanDimensionEvidence] = None,
        object_evidence: Optional[KnownObjectEvidence] = None,
        manual_evidence: Optional[ManualCorrectionEvidence] = None
    ) -> MetricTransform:
        """
        Computes the complete explicit Sim(3) metric transformation.
        """
        # 1. Resolve Scale strictly following priority order
        scale, scale_source, scale_conf, details = self.resolve_scale(
            lidar_evidence=lidar_evidence,
            physical_evidence=physical_evidence,
            floorplan_evidence=floorplan_evidence,
            object_evidence=object_evidence,
            manual_evidence=manual_evidence
        )

        # 2. Gravity / Up Vector Alignment
        target_up = np.array([0.0, 0.0, 1.0])  # Canonical Z is UP
        if floor_normal is not None and np.linalg.norm(floor_normal) > 1e-6:
            current_up = floor_normal / np.linalg.norm(floor_normal)
        elif gravity_vector is not None and np.linalg.norm(gravity_vector) > 1e-6:
            # Gravity points DOWN, so up vector is -gravity
            current_up = -gravity_vector / np.linalg.norm(gravity_vector)
        else:
            current_up = np.array([0.0, 0.0, 1.0])

        R_gravity = rotation_matrix_from_vectors(current_up, target_up)

        # 3. Facade / Yaw Alignment (align primary wall to +X)
        if primary_facade_normal is not None and np.linalg.norm(primary_facade_normal) > 1e-6:
            # Rotate facade normal under gravity alignment
            facade_rot = np.dot(R_gravity, primary_facade_normal)
            # Yaw is angle in XY plane
            yaw = float(np.arctan2(facade_rot[1], facade_rot[0]))
            # Rotate back by -yaw around Z to align with X axis
            c_y, s_y = np.cos(-yaw), np.sin(-yaw)
            R_yaw = np.array([
                [c_y, -s_y, 0.0],
                [s_y, c_y, 0.0],
                [0.0, 0.0, 1.0]
            ])
            R = np.dot(R_yaw, R_gravity)
        else:
            R = R_gravity

        # 4. Translation & Floor Leveling (Floor at Z = 0)
        if floor_point is not None:
            # Floor point transformed under scale and rotation
            p_rot_scale = scale * np.dot(R, floor_point)
            t_z = -float(p_rot_scale[2])
        elif len(points) > 0:
            # Fallback: lowest point transformed to Z = 0
            pts_rot_scale = scale * np.dot(points, R.T)
            t_z = -float(np.min(pts_rot_scale[:, 2]))
        else:
            t_z = 0.0

        # Center in XY plane
        if len(points) > 0:
            pts_rot_scale = scale * np.dot(points, R.T)
            t_x = -float(np.mean(pts_rot_scale[:, 0]))
            t_y = -float(np.mean(pts_rot_scale[:, 1]))
        else:
            t_x, t_y = 0.0, 0.0

        translation = np.array([t_x, t_y, t_z], dtype=np.float64)

        return MetricTransform(
            scale=scale,
            rotation_matrix=R,
            translation=translation,
            scale_source=scale_source,
            scale_confidence=scale_conf,
            canonical_frame=self.canonical_frame,
            floor_elevation_m=0.0,
            evidence_details=details
        )
