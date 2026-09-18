"""
VĀSTU AR Localization Engine (Stage 29)
Core independent layer for marker-based AR relocalization and route projection.
Implements:
1. Spatial anchor registration.
2. Single and multi-marker closed-form rigid transform estimation (T_model_AR).
3. Temporal filtering (EMA / Slerp) for walking stability.
4. VIO dead-reckoning continuation when markers leave FOV.
5. Perspective route projection into AR camera viewport.
"""

import time
import math
import logging
from typing import List, Dict, Tuple, Optional, Any
import numpy as np

from core.schemas.ar_localization import (
    SpatialMarkerAnchor,
    DetectedMarker,
    ARCameraFrame,
    ARLocalizationRequest,
    ARLocalizationResult,
    ARRouteProjectionRequest,
    ARRouteProjectionResult,
    ARProjectedWaypoint,
)
from core.ar.marker_detector import ARMarkerDetector

logger = logging.getLogger("vastu.ar.localization")


class ARLocalizationEngine:
    """
    Independent AR Localization Engine.
    Aligns device ARKit/ARCore tracking coordinates with digital twin world frame (+Z up).
    """

    def __init__(self, filter_alpha: float = 0.35):
        # In-memory spatial anchor store: model_id -> Dict[marker_id, SpatialMarkerAnchor]
        self._anchors: Dict[str, Dict[int, SpatialMarkerAnchor]] = {}
        # Active alignment state per model: model_id -> current smoothed T_model_AR
        self._active_model_t_ar: Dict[str, np.ndarray] = {}
        self._filter_alpha = filter_alpha
        self.detector = ARMarkerDetector()

    # -------------------------------------------------------------------------
    # SPATIAL ANCHOR MANAGEMENT
    # -------------------------------------------------------------------------

    def register_marker_anchor(self, anchor: SpatialMarkerAnchor) -> None:
        """Registers a known physical marker anchor in the model frame."""
        if anchor.model_id not in self._anchors:
            self._anchors[anchor.model_id] = {}
        self._anchors[anchor.model_id][anchor.marker_id] = anchor
        logger.info(
            f"Registered AR spatial anchor marker_{anchor.marker_id} for model '{anchor.model_id}' "
            f"at pos {anchor.position_model}"
        )

    def get_marker_anchors(self, model_id: str) -> List[SpatialMarkerAnchor]:
        """Returns all registered anchors for a model."""
        return list(self._anchors.get(model_id, {}).values())

    def clear_anchors(self, model_id: Optional[str] = None) -> None:
        """Clears spatial anchors."""
        if model_id:
            self._anchors.pop(model_id, None)
            self._active_model_t_ar.pop(model_id, None)
        else:
            self._anchors.clear()
            self._active_model_t_ar.clear()

    # -------------------------------------------------------------------------
    # LOCALIZATION PIPELINE
    # -------------------------------------------------------------------------

    def localize(self, request: ARLocalizationRequest) -> ARLocalizationResult:
        """
        Executes the marker-based AR relocalization pipeline:
        AR camera frame -> marker detection & PnP -> known anchor matching
        -> rigid transform (T_model_AR) -> device-to-model transform (T_model_device).
        """
        start_t = time.perf_counter()
        model_id = request.model_id
        frame = request.frame
        anchors_map = self._anchors.get(model_id, {})

        t_ar_cam = np.array(frame.device_pose_ar, dtype=np.float64)

        # 1. Match observed markers against known model anchors
        matched_obs: List[Tuple[DetectedMarker, SpatialMarkerAnchor]] = []
        for det in frame.detected_markers:
            if det.marker_id in anchors_map:
                matched_obs.append((det, anchors_map[det.marker_id]))

        # 2. If no markers detected, check if we can continue via dead-reckoning
        if len(matched_obs) == 0:
            if model_id in self._active_model_t_ar:
                # Dead reckoning using stored T_model_AR and current T_AR_device
                t_model_ar = self._active_model_t_ar[model_id]
                t_model_device = t_model_ar @ t_ar_cam
                latency_ms = (time.perf_counter() - start_t) * 1000.0
                return ARLocalizationResult(
                    success=True,
                    model_id=model_id,
                    model_t_ar=t_model_ar.tolist(),
                    device_pose_model=t_model_device.tolist(),
                    device_position_model=t_model_device[:3, 3].tolist(),
                    matched_marker_ids=[],
                    confidence=0.85,  # Slightly lower confidence under dead reckoning
                    relocalization_time_ms=round(latency_ms, 3),
                    is_tracked_via_dead_reckoning=True,
                    rejection_reason=None
                )
            else:
                latency_ms = (time.perf_counter() - start_t) * 1000.0
                return ARLocalizationResult(
                    success=False,
                    model_id=model_id,
                    matched_marker_ids=[],
                    confidence=0.0,
                    relocalization_time_ms=round(latency_ms, 3),
                    rejection_reason="REJECTED_NO_MARKERS_DETECTED: No registered spatial anchors in view."
                )

        # 3. Calculate rigid transform T_model_AR from observation(s)
        candidate_t_model_ar = self._solve_rigid_transform(matched_obs, t_ar_cam)

        if candidate_t_model_ar is None:
            latency_ms = (time.perf_counter() - start_t) * 1000.0
            return ARLocalizationResult(
                success=False,
                model_id=model_id,
                matched_marker_ids=[m.marker_id for m, _ in matched_obs],
                confidence=0.0,
                relocalization_time_ms=round(latency_ms, 3),
                rejection_reason="REJECTED_TRANSFORM_SOLVER_FAILED: Degenerate or unstable marker geometry."
            )

        # 4. Apply temporal smoothing for walking stability
        smoothed_t_model_ar = self._filter_transform(model_id, candidate_t_model_ar)
        self._active_model_t_ar[model_id] = smoothed_t_model_ar

        # 5. Derive device pose in digital twin coordinates: T_model_device = T_model_AR * T_AR_device
        t_model_device = smoothed_t_model_ar @ t_ar_cam
        device_pos = t_model_device[:3, 3].tolist()

        latency_ms = (time.perf_counter() - start_t) * 1000.0

        return ARLocalizationResult(
            success=True,
            model_id=model_id,
            model_t_ar=smoothed_t_model_ar.tolist(),
            device_pose_model=t_model_device.tolist(),
            device_position_model=device_pos,
            matched_marker_ids=[m.marker_id for m, _ in matched_obs],
            confidence=0.99,
            relocalization_time_ms=round(latency_ms, 3),
            is_tracked_via_dead_reckoning=False,
            rejection_reason=None
        )

    # -------------------------------------------------------------------------
    # RIGID TRANSFORM ESTIMATION
    # -------------------------------------------------------------------------

    def _solve_rigid_transform(
        self,
        matches: List[Tuple[DetectedMarker, SpatialMarkerAnchor]],
        t_ar_cam: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Solves T_model_AR from single or multiple marker observations.
        For single marker: T_model_AR = T_model_M * (T_AR_M)^-1
        For multiple markers: Kabsch / SVD Procrustes alignment on marker centers and corners.
        """
        if len(matches) == 1:
            det, anchor = matches[0]
            if det.camera_t_marker is None:
                return None
            t_cam_m = np.array(det.camera_t_marker, dtype=np.float64)
            # Marker in AR tracking frame: T_AR_M = T_AR_cam * T_cam_M
            t_ar_m = t_ar_cam @ t_cam_m
            # Marker in Model frame
            t_model_m = self._anchor_to_matrix(anchor)
            # Alignment: T_model_AR = T_model_M * inv(T_AR_M)
            t_model_ar = t_model_m @ np.linalg.inv(t_ar_m)
            return t_model_ar

        # Multiple markers: SVD Procrustes Alignment across 3D marker centers & corners
        pts_ar: List[np.ndarray] = []
        pts_model: List[np.ndarray] = []

        for det, anchor in matches:
            if det.camera_t_marker is None:
                continue
            t_cam_m = np.array(det.camera_t_marker, dtype=np.float64)
            t_ar_m = t_ar_cam @ t_cam_m
            t_model_m = self._anchor_to_matrix(anchor)

            # Center point
            pts_ar.append(t_ar_m[:3, 3])
            pts_model.append(t_model_m[:3, 3])

            # 4 corner offsets in marker plane
            s = anchor.physical_size_m / 2.0
            corner_offsets = [
                np.array([-s,  s, 0.0, 1.0]),
                np.array([ s,  s, 0.0, 1.0]),
                np.array([ s, -s, 0.0, 1.0]),
                np.array([-s, -s, 0.0, 1.0]),
            ]
            for c_off in corner_offsets:
                pts_ar.append((t_ar_m @ c_off)[:3])
                pts_model.append((t_model_m @ c_off)[:3])

        if len(pts_ar) < 3:
            return None

        # Solve Kabsch: find R, t minimizing || pts_model - (R * pts_ar + t) ||
        A = np.array(pts_ar, dtype=np.float64)      # source (AR)
        B = np.array(pts_model, dtype=np.float64)   # target (Model)

        centroid_A = np.mean(A, axis=0)
        centroid_B = np.mean(B, axis=0)

        AA = A - centroid_A
        BB = B - centroid_B

        H = AA.T @ BB
        U, S, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T

        # Reflection correction
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T

        t = centroid_B - R @ centroid_A

        t_model_ar = np.eye(4, dtype=np.float64)
        t_model_ar[:3, :3] = R
        t_model_ar[:3, 3] = t
        return t_model_ar

    # -------------------------------------------------------------------------
    # TEMPORAL FILTERING (Stability While Walking)
    # -------------------------------------------------------------------------

    def _filter_transform(self, model_id: str, new_t_model_ar: np.ndarray) -> np.ndarray:
        """
        Applies Exponential Moving Average (EMA) to translation and Slerp to rotation
        to filter out sensor jitter while walking.
        """
        if model_id not in self._active_model_t_ar:
            return new_t_model_ar

        prev_t = self._active_model_t_ar[model_id]
        alpha = self._filter_alpha

        # 1. Translation EMA
        t_smooth = (1.0 - alpha) * prev_t[:3, 3] + alpha * new_t_model_ar[:3, 3]

        # 2. Rotation SLERP via Quaternions
        q_prev = self._rot_matrix_to_quaternion(prev_t[:3, :3])
        q_new = self._rot_matrix_to_quaternion(new_t_model_ar[:3, :3])
        q_smooth = self._quaternion_slerp(q_prev, q_new, alpha)
        R_smooth = self._quaternion_to_rot_matrix(q_smooth)

        filtered = np.eye(4, dtype=np.float64)
        filtered[:3, :3] = R_smooth
        filtered[:3, 3] = t_smooth
        return filtered

    # -------------------------------------------------------------------------
    # ROUTE PROJECTION
    # -------------------------------------------------------------------------

    def project_route(self, request: ARRouteProjectionRequest) -> ARRouteProjectionResult:
        """
        Projects 3D digital twin route waypoints into the AR camera viewport:
        p_cam = T_cam_AR * T_AR_model * p_model
        p_pixel = K * p_cam / z_cam
        """
        t_model_ar = np.array(request.model_t_ar, dtype=np.float64)
        t_ar_cam = np.array(request.device_pose_ar, dtype=np.float64)
        intrinsics = np.array(request.intrinsics, dtype=np.float64)
        w, h = request.resolution

        # Invert to get camera from model: T_cam_model = inv(T_AR_cam) * inv(T_model_AR)
        t_cam_ar = np.linalg.inv(t_ar_cam)
        t_ar_model = np.linalg.inv(t_model_ar)
        t_cam_model = t_cam_ar @ t_ar_model

        fx, fy = intrinsics[0, 0], intrinsics[1, 1]
        cx, cy = intrinsics[0, 2], intrinsics[1, 2]

        projected: List[ARProjectedWaypoint] = []
        visible_count = 0

        for i, pt_model in enumerate(request.route_waypoints_model):
            pt_m_h = np.array([pt_model[0], pt_model[1], pt_model[2], 1.0], dtype=np.float64)
            pt_c = (t_cam_model @ pt_m_h)[:3]
            dist = float(np.linalg.norm(pt_c))

            in_front = bool(pt_c[2] > 0.1)  # in front of near clip
            pixel_2d: Optional[List[float]] = None

            if in_front:
                u = (fx * pt_c[0] / pt_c[2]) + cx
                v = (fy * pt_c[1] / pt_c[2]) + cy
                pixel_2d = [round(float(u), 2), round(float(v), 2)]
                if 0 <= u <= w and 0 <= v <= h:
                    visible_count += 1

            projected.append(ARProjectedWaypoint(
                waypoint_index=i,
                position_model=pt_model,
                position_cam=[round(float(pt_c[0]), 3), round(float(pt_c[1]), 3), round(float(pt_c[2]), 3)],
                pixel_2d=pixel_2d,
                is_in_front_of_camera=in_front,
                distance_meters=round(dist, 3)
            ))

        return ARRouteProjectionResult(
            projected_waypoints=projected,
            visible_waypoint_count=visible_count,
            total_waypoint_count=len(request.route_waypoints_model),
            mean_reprojection_error_px=0.0
        )

    # -------------------------------------------------------------------------
    # MATH UTILITIES (Quaternions & Matrices)
    # -------------------------------------------------------------------------

    def _anchor_to_matrix(self, anchor: SpatialMarkerAnchor) -> np.ndarray:
        """Converts SpatialMarkerAnchor position & quaternion to 4x4 matrix."""
        q = anchor.orientation_quaternion_model  # [qx, qy, qz, qw]
        R = self._quaternion_to_rot_matrix(np.array(q, dtype=np.float64))
        T = np.eye(4, dtype=np.float64)
        T[:3, :3] = R
        T[:3, 3] = np.array(anchor.position_model, dtype=np.float64)
        return T

    @staticmethod
    def _quaternion_to_rot_matrix(q: np.ndarray) -> np.ndarray:
        """Converts unit quaternion [qx, qy, qz, qw] to 3x3 rotation matrix."""
        qx, qy, qz, qw = q
        n = np.linalg.norm(q)
        if n > 1e-6:
            qx, qy, qz, qw = q / n
        return np.array([
            [1.0 - 2.0*(qy*qy + qz*qz), 2.0*(qx*qy - qz*qw),       2.0*(qx*qz + qy*qw)],
            [2.0*(qx*qy + qz*qw),       1.0 - 2.0*(qx*qx + qz*qz), 2.0*(qy*qz - qx*qw)],
            [2.0*(qx*qz - qy*qw),       2.0*(qy*qz + qx*qw),       1.0 - 2.0*(qx*qx + qy*qy)]
        ], dtype=np.float64)

    @staticmethod
    def _rot_matrix_to_quaternion(R: np.ndarray) -> np.ndarray:
        """Converts 3x3 rotation matrix to unit quaternion [qx, qy, qz, qw]."""
        tr = R[0, 0] + R[1, 1] + R[2, 2]
        if tr > 0.0:
            S = math.sqrt(tr + 1.0) * 2.0
            qw = 0.25 * S
            qx = (R[2, 1] - R[1, 2]) / S
            qy = (R[0, 2] - R[2, 0]) / S
            qz = (R[1, 0] - R[0, 1]) / S
        elif (R[0, 0] > R[1, 1]) and (R[0, 0] > R[2, 2]):
            S = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
            qw = (R[2, 1] - R[1, 2]) / S
            qx = 0.25 * S
            qy = (R[0, 1] + R[1, 0]) / S
            qz = (R[0, 2] + R[2, 0]) / S
        elif R[1, 1] > R[2, 2]:
            S = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
            qw = (R[0, 2] - R[2, 0]) / S
            qx = (R[0, 1] + R[1, 0]) / S
            qy = 0.25 * S
            qz = (R[1, 2] + R[2, 1]) / S
        else:
            S = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
            qw = (R[1, 0] - R[0, 1]) / S
            qx = (R[0, 2] + R[2, 0]) / S
            qy = (R[1, 2] + R[2, 1]) / S
            qz = 0.25 * S
        q = np.array([qx, qy, qz, qw], dtype=np.float64)
        return q / np.linalg.norm(q)

    @staticmethod
    def _quaternion_slerp(q0: np.ndarray, q1: np.ndarray, t: float) -> np.ndarray:
        """Spherical linear interpolation between two quaternions."""
        dot = np.dot(q0, q1)
        if dot < 0.0:
            q1 = -q1
            dot = -dot
        if dot > 0.9995:
            res = q0 + t * (q1 - q0)
            return res / np.linalg.norm(res)
        theta_0 = math.acos(np.clip(dot, -1.0, 1.0))
        theta = theta_0 * t
        sin_theta = math.sin(theta)
        sin_theta_0 = math.sin(theta_0)
        s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
        s1 = sin_theta / sin_theta_0
        return (s0 * q0) + (s1 * q1)
