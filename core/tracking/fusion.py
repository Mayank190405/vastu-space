"""
VĀSTU Hierarchical Camera Pose Estimator
Fuses device AR/VIO, visual odometry, feature matching, and epipolar geometry.
Explicitly detects tracking loss, insufficient parallax, disconnected trajectories,
high reprojection error, and loop-closure drift failures.
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple

from core.schemas.camera_poses import (
    CameraPoses,
    CameraTrajectoryFrame,
    TrackingSource,
    PoseAnomalyType,
    UnreliablePoseSegment
)
from core.tracking.tracker import VisualPoseTracker, VisualTrackingResult

logger = logging.getLogger("vastu.tracking.fusion")


def rotation_matrix_to_quaternion(R: np.ndarray) -> List[float]:
    """Converts a 3x3 rotation matrix into a unit quaternion [x, y, z, w]."""
    tr = np.trace(R)
    if tr > 0:
        S = 0.5 / np.sqrt(tr + 1.0)
        w = 0.25 / S
        x = (R[2, 1] - R[1, 2]) * S
        y = (R[0, 2] - R[2, 0]) * S
        z = (R[1, 0] - R[0, 1]) * S
    elif (R[0, 0] > R[1, 1]) and (R[0, 0] > R[2, 2]):
        S = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
        w = (R[2, 1] - R[1, 2]) / S
        x = 0.25 * S
        y = (R[0, 1] + R[1, 0]) / S
        z = (R[0, 2] + R[2, 0]) / S
    elif R[1, 1] > R[2, 2]:
        S = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
        w = (R[0, 2] - R[2, 0]) / S
        x = (R[0, 1] + R[1, 0]) / S
        y = 0.25 * S
        z = (R[1, 2] + R[2, 1]) / S
    else:
        S = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
        w = (R[1, 0] - R[0, 1]) / S
        x = (R[0, 2] + R[2, 0]) / S
        y = (R[1, 2] + R[2, 1]) / S
        z = 0.25 * S
    q = np.array([x, y, z, w], dtype=float)
    norm = np.linalg.norm(q)
    return (q / max(1e-7, norm)).tolist()


class HierarchicalPoseEstimator:
    """
    Hierarchical pose estimator that fuses Device VIO, Visual tracking,
    and SfM epipolar constraints without blindly trusting any single source.
    """
    def __init__(
        self,
        min_parallax_deg: float = 1.5,
        max_reprojection_error_px: float = 3.0,
        max_interframe_displacement_m: float = 2.0,
        loop_closure_threshold_m: float = 0.50
    ):
        self.tracker = VisualPoseTracker()
        self.min_parallax_deg = min_parallax_deg
        self.max_reprojection_error_px = max_reprojection_error_px
        self.max_interframe_displacement_m = max_interframe_displacement_m
        self.loop_closure_threshold_m = loop_closure_threshold_m

    def estimate_trajectory(
        self,
        keyframe_images: List[np.ndarray],
        keyframe_metadata: List[Dict[str, Any]],
        intrinsics_k: np.ndarray,
        device_vio_poses: Optional[List[Dict[str, Any]]] = None
    ) -> CameraPoses:
        """
        Processes keyframe image sequence and produces an auditable CameraPoses object.
        """
        n_frames = len(keyframe_images)
        if n_frames == 0:
            raise ValueError("No keyframe images provided for trajectory estimation")

        fx, fy = intrinsics_k[0, 0], intrinsics_k[1, 1]
        cx, cy = intrinsics_k[0, 2], intrinsics_k[1, 2]
        intrinsics_list = [float(fx), float(fy), float(cx), float(cy)]

        # Map device poses by frame_index if available
        vio_map = {}
        if device_vio_poses:
            for p in device_vio_poses:
                vio_map[p["frame_index"]] = p

        # Extract features for all keyframes
        features = [self.tracker.extract_features(img) for img in keyframe_images]

        trajectory: List[CameraTrajectoryFrame] = []
        anomalies_detected: List[Dict[str, Any]] = []

        # Anchor Frame 0
        R_curr = np.eye(3, dtype=np.float64)
        t_curr = np.zeros((3, 1), dtype=np.float64)
        if 0 in vio_map:
            R_curr = np.array(vio_map[0].get("rotation_matrix", np.eye(3)), dtype=np.float64)
            t_curr = np.array(vio_map[0].get("translation_vector_m", [0, 0, 0]), dtype=np.float64).reshape(3, 1)

        f0_meta = keyframe_metadata[0]
        q0 = rotation_matrix_to_quaternion(R_curr)
        c0 = (-R_curr.T @ t_curr).flatten().tolist()

        trajectory.append(CameraTrajectoryFrame(
            frame_index=f0_meta.get("frame_index", 0),
            timestamp_ns=f0_meta.get("timestamp_ns", 0),
            rotation_matrix=R_curr.tolist(),
            translation_vector_m=t_curr.flatten().tolist(),
            quaternion_xyzw=q0,
            camera_center_m=c0,
            reprojection_error_px=0.0,
            inlier_points_count=len(features[0][0]),
            tracking_source=TrackingSource.DEVICE_VIO if 0 in vio_map else TrackingSource.SFM_BA,
            confidence=1.0,
            is_reliable=True,
            anomaly_flags=[]
        ))

        # Track sequentially from i to i+1
        for i in range(n_frames - 1):
            next_idx = i + 1
            meta_curr = keyframe_metadata[next_idx]
            frame_idx = meta_curr.get("frame_index", next_idx)
            ts_ns = meta_curr.get("timestamp_ns", int(next_idx * 1e8))

            kps1, descs1 = features[i]
            kps2, descs2 = features[next_idx]

            vis_result: VisualTrackingResult = self.tracker.track_pair(
                kps1, descs1, kps2, descs2, intrinsics_k
            )

            has_vio = frame_idx in vio_map
            vio_data = vio_map.get(frame_idx, {})

            flags = []
            is_reliable = True
            tracking_source = TrackingSource.ESTIMATED_INTERPOLATION
            confidence = 1.0
            reproj_err = vis_result.reprojection_error_px

            # Parallax check
            if vis_result.success and vis_result.parallax_angle_deg < self.min_parallax_deg:
                flags.append(PoseAnomalyType.INSUFFICIENT_PARALLAX.value)
                confidence *= 0.85

            # High reprojection error check
            if vis_result.reprojection_error_px > self.max_reprojection_error_px:
                flags.append(PoseAnomalyType.HIGH_REPROJECTION_ERROR.value)
                confidence *= 0.70

            # Hierarchical Fusion Decisions
            if vis_result.success and vis_result.inliers_count >= 30 and vis_result.reprojection_error_px <= self.max_reprojection_error_px:
                if vis_result.is_repetitive:
                    flags.append("REPETITIVE_PATTERN_AMBIGUITY")
                    logger.warning(f"Frame {frame_idx}: Repetitive pattern detected (e.g. grid tiles). Downweighting pure visual matching.")

                if has_vio:
                    # Fused Hybrid: Combine VIO translation scale with visual rotation
                    vio_t = np.array(vio_data.get("translation_vector_m", [0, 0, 0])).reshape(3, 1)
                    vio_R = np.array(vio_data.get("rotation_matrix", np.eye(3)))
                    delta_t = vio_t - t_curr
                    step_len = np.linalg.norm(delta_t)
                    t_curr = t_curr + (R_curr @ (vis_result.t_rel * max(0.1, step_len)))
                    R_curr = vis_result.R_rel @ R_curr
                    tracking_source = TrackingSource.FUSED_HYBRID
                    confidence = min(1.0, vis_result.inliers_count / 80.0)
                    if vis_result.is_repetitive:
                        confidence *= 0.8
                else:
                    # Pure Visual / SfM Odometry
                    t_curr = t_curr + (R_curr @ (vis_result.t_rel * 0.3))
                    R_curr = vis_result.R_rel @ R_curr
                    tracking_source = TrackingSource.SFM_BA
                    confidence = min(1.0, vis_result.inliers_count / 100.0)
                    if vis_result.is_repetitive:
                        confidence *= 0.7
            elif has_vio:
                # Visual failed, fallback to device VIO prior
                logger.warning(f"Visual tracking degraded on frame {frame_idx}; falling back to DEVICE_VIO")
                R_curr = np.array(vio_data.get("rotation_matrix", R_curr))
                t_curr = np.array(vio_data.get("translation_vector_m", t_curr)).reshape(3, 1)
                tracking_source = TrackingSource.DEVICE_VIO
                confidence = float(vio_data.get("confidence", 0.60)) * 0.8
                flags.append("VISUAL_TRACKING_FALLBACK")
            else:
                # Complete tracking loss!
                logger.error(f"Complete tracking loss on frame {frame_idx}: visual tracking failed and no VIO available")
                flags.append(PoseAnomalyType.TRACKING_LOSS.value)
                is_reliable = False
                tracking_source = TrackingSource.ESTIMATED_INTERPOLATION
                confidence = 0.05
                # Extrapolate slightly to avoid exact collapse
                t_curr = t_curr + np.array([[0.05], [0.0], [0.0]])

            # Disconnected trajectory check
            prev_t = np.array(trajectory[-1].translation_vector_m).reshape(3, 1)
            displacement = float(np.linalg.norm(t_curr - prev_t))
            if displacement > self.max_interframe_displacement_m:
                flags.append(PoseAnomalyType.DISCONNECTED_TRAJECTORY.value)
                is_reliable = False
                confidence *= 0.5

            if not is_reliable or flags:
                anomalies_detected.append({
                    "frame_index": frame_idx,
                    "flags": flags,
                    "is_reliable": is_reliable
                })

            q_curr = rotation_matrix_to_quaternion(R_curr)
            c_curr = (-R_curr.T @ t_curr).flatten().tolist()

            trajectory.append(CameraTrajectoryFrame(
                frame_index=frame_idx,
                timestamp_ns=ts_ns,
                rotation_matrix=R_curr.tolist(),
                translation_vector_m=t_curr.flatten().tolist(),
                quaternion_xyzw=q_curr,
                camera_center_m=c_curr,
                reprojection_error_px=float(reproj_err),
                inlier_points_count=int(vis_result.inliers_count),
                tracking_source=tracking_source,
                confidence=round(float(confidence), 4),
                is_reliable=is_reliable,
                anomaly_flags=flags
            ))

        # Step 3: Loop Closure Verification
        loop_closure_detected = False
        loop_residual_m = None
        if n_frames >= 6:
            # Check visual loop closure between origin keyframe (0) and last keyframe (N-1)
            kps_start, descs_start = features[0]
            kps_end, descs_end = features[-1]
            loop_match: VisualTrackingResult = self.tracker.track_pair(
                kps_start, descs_start, kps_end, descs_end, intrinsics_k
            )
            if loop_match.success and loop_match.inliers_count >= 20:
                loop_closure_detected = True
                t_start = np.array(trajectory[0].translation_vector_m)
                t_end = np.array(trajectory[-1].translation_vector_m)
                loop_residual_m = float(np.linalg.norm(t_end - t_start))
                if loop_residual_m > self.loop_closure_threshold_m:
                    logger.warning(f"Loop closure drift detected: residual {loop_residual_m:.3f}m > threshold {self.loop_closure_threshold_m}m")
                    trajectory[-1].anomaly_flags.append(PoseAnomalyType.LOOP_CLOSURE_MISMATCH.value)
                    trajectory[-1].is_reliable = False
                    anomalies_detected.append({
                        "frame_index": trajectory[-1].frame_index,
                        "flags": [PoseAnomalyType.LOOP_CLOSURE_MISMATCH.value],
                        "is_reliable": False
                    })

        # Step 4: Aggregate Unreliable Segments
        unreliable_segments = []
        if anomalies_detected:
            start_f = None
            curr_flags = set()
            for item in anomalies_detected:
                f_idx = item["frame_index"]
                if start_f is None:
                    start_f = f_idx
                    curr_flags = set(item["flags"])
                else:
                    curr_flags.update(item["flags"])
            if start_f is not None:
                primary_anomaly = PoseAnomalyType.TRACKING_LOSS
                for a_type in PoseAnomalyType:
                    if a_type.value in curr_flags:
                        primary_anomaly = a_type
                        break
                unreliable_segments.append(UnreliablePoseSegment(
                    start_frame=start_f,
                    end_frame=anomalies_detected[-1]["frame_index"],
                    reason=f"Degraded tracking: {', '.join(curr_flags)}",
                    anomaly_type=primary_anomaly
                ))

        overall_conf = float(np.mean([f.confidence for f in trajectory])) if trajectory else 0.0

        return CameraPoses(
            camera_model="PINHOLE",
            intrinsics=intrinsics_list,
            trajectory=trajectory,
            unreliable_segments=unreliable_segments,
            loop_closure_detected=loop_closure_detected,
            loop_closure_residual_m=round(loop_residual_m, 4) if loop_residual_m is not None else None,
            overall_confidence=round(overall_conf, 4)
        )
