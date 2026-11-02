"""
VĀSTU v3.0 — Camera Tracking Diagnostics & Visualizers (Stage 03 / Phase 1)
===========================================================================
Generates authoritative Phase 1 tracking deliverables:
1. camera_trajectory.ply: 3D point cloud & camera frustum lines in ASCII PLY format
2. camera_intrinsics.json: Full pinhole calibration, uncertainty, and per-keyframe assignments
3. pose_validation.json: Rigorous trajectory validation and continuity auditing
4. pnp_diagnostics.csv: Per-keyframe tabular diagnostic log
5. reprojection_overlays/: Visual debug images showing 2D keypoints vs reprojected 3D points
"""

import os
import csv
import json
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np

from core.coordinates.conventions import (
    C_OPENCV_FROM_ARKIT,
    CameraPose,
    CameraConvention,
    CameraIntrinsics
)


def convert_arkit_pose_to_opencv(T_arkit_4x4: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Converts ARKit 4x4 camera-to-world transform (RUB: -Z forward, +Y up)
    to OpenCV RDF (+Z forward, +Y down).
    Returns (R_world_camera_cv, t_world_camera_cv, camera_center_world).
    """
    T = np.asarray(T_arkit_4x4, dtype=np.float64)
    R_arkit = T[:3, :3]
    t_arkit = T[:3, 3]

    # In ARKit: P_world = R_arkit @ P_arkit + t_arkit
    # Since P_arkit = C @ P_cv (where C = diag(1, -1, -1)):
    # P_world = R_arkit @ C @ P_cv + t_arkit
    R_cv = R_arkit @ C_OPENCV_FROM_ARKIT
    t_cv = t_arkit.copy()
    cam_center = t_cv.copy()

    return R_cv, t_cv, cam_center


def export_camera_trajectory_ply(
    output_path: str,
    poses: List[Optional[Dict[str, Any]]],
    K: np.ndarray,
    width: int,
    height: int
) -> None:
    """
    Exports camera trajectory and viewing frustums to standard ASCII PLY format.
    Vertices represent camera optical centers and frustum corners colored by confidence:
    - High confidence (>=0.70): Bright Green (0, 230, 80)
    - Moderate confidence (0.40 - 0.70): Amber / Yellow (240, 190, 20)
    - Untracked / low confidence: Red (235, 40, 40)
    Edges connect sequential camera positions and outline viewing frustums.
    """
    vertices = []  # (x, y, z, r, g, b)
    edges = []     # (v1, v2)

    frustum_scale = 0.15  # 15 cm frustum depth
    fx = float(K[0, 0])
    fy = float(K[1, 1])
    cx = float(K[0, 2])
    cy = float(K[1, 2])

    # 4 image corners in camera frame at z = frustum_scale
    corners_cam = np.array([
        [-cx * frustum_scale / fx, -cy * frustum_scale / fy, frustum_scale],
        [(width - cx) * frustum_scale / fx, -cy * frustum_scale / fy, frustum_scale],
        [(width - cx) * frustum_scale / fx, (height - cy) * frustum_scale / fy, frustum_scale],
        [-cx * frustum_scale / fx, (height - cy) * frustum_scale / fy, frustum_scale],
    ], dtype=np.float64)

    prev_center_idx = None

    for idx, p in enumerate(poses):
        if p is None or not p.get("is_tracked", True):
            is_tracked = False
            conf = 0.0
            cam_center = np.array([0.0, 0.0, 0.0], dtype=np.float64)
            color = (235, 40, 40)  # Red
        else:
            is_tracked = True
            conf = float(p.get("confidence", 0.8))
            R = np.asarray(p["R"], dtype=np.float64)
            t = np.asarray(p["t"], dtype=np.float64).reshape(3, 1)
            # Optical center in world coordinates: C = -R^T @ t
            cam_center = (-R.T @ t).flatten()

            if conf >= 0.70:
                color = (0, 230, 80)    # Green
            elif conf >= 0.40:
                color = (240, 190, 20)  # Amber
            else:
                color = (235, 40, 40)   # Red

        center_idx = len(vertices)
        vertices.append((cam_center[0], cam_center[1], cam_center[2], color[0], color[1], color[2]))

        if is_tracked and prev_center_idx is not None:
            edges.append((prev_center_idx, center_idx))
        if is_tracked:
            prev_center_idx = center_idx

            # Add 4 frustum base vertices in world coordinates
            # P_world = R^T @ (P_cam - t)
            base_indices = []
            for c_c in corners_cam:
                c_w = (R.T @ (c_c.reshape(3, 1) - t)).flatten()
                base_indices.append(len(vertices))
                vertices.append((c_w[0], c_w[1], c_w[2], color[0], color[1], color[2]))

            # Connect center to 4 frustum corners
            for bi in base_indices:
                edges.append((center_idx, bi))
            # Connect the 4 corners of the frustum base
            for k in range(4):
                edges.append((base_indices[k], base_indices[(k + 1) % 4]))

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(vertices)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write(f"element edge {len(edges)}\n")
        f.write("property int vertex1\n")
        f.write("property int vertex2\n")
        f.write("end_header\n")
        for v in vertices:
            f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f} {int(v[3])} {int(v[4])} {int(v[5])}\n")
        for e in edges:
            f.write(f"{e[0]} {e[1]}\n")


def export_pnp_diagnostics_csv(output_path: str, diagnostics: List[Dict[str, Any]]) -> None:
    """
    Exports per-keyframe PnP diagnostics table in standardized CSV format.
    """
    headers = [
        "frame_idx", "anchor_idx", "candidate_matches", "valid_3d_2d_correspondences",
        "inliers", "inlier_ratio", "reprojection_rmse_px", "reprojection_median_px",
        "translation_m", "rotation_deg", "camera_pos_x", "camera_pos_y", "camera_pos_z",
        "confidence", "is_tracked", "estimator", "rejection_reason"
    ]
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in diagnostics:
            writer.writerow({h: row.get(h, "") for h in headers})


def generate_reprojection_overlays(
    output_dir: str,
    frames: List[np.ndarray],
    kps: List[Any],
    descs: List[Any],
    depths: List[np.ndarray],
    K: np.ndarray,
    poses: List[Optional[Dict[str, Any]]],
    diagnostics: List[Dict[str, Any]]
) -> None:
    """
    Generates visual debug images showing:
    - 2D keypoints (green circles)
    - Reprojected 3D points (blue/amber crosses)
    - Residual error vectors
    - Top summary overlay with inlier count, RMSE, and translation step
    """
    os.makedirs(output_dir, exist_ok=True)
    bf = cv2.BFMatcher(cv2.NORM_L2)
    h, w = frames[0].shape[:2]

    for d in diagnostics:
        curr = int(d.get("frame_idx", 0))
        anchor = int(d.get("anchor_idx", -1))
        if curr == 0 or anchor < 0 or not d.get("is_tracked", False):
            continue
        if curr >= len(frames) or anchor >= len(frames):
            continue
        if poses[curr] is None or poses[anchor] is None:
            continue

        overlay = frames[curr].copy()
        des_a = descs[anchor]
        des_b = descs[curr]
        if des_a is None or des_b is None:
            continue

        m = bf.knnMatch(des_a, des_b, k=2)
        good = [x[0] for x in m if len(x) == 2 and x[0].distance < 0.75 * x[1].distance]
        if len(good) < 4:
            continue

        pts_a = np.float32([kps[anchor][x.queryIdx].pt for x in good])
        pts_b = np.float32([kps[curr][x.trainIdx].pt for x in good])

        u_a = np.clip(np.round(pts_a[:, 0]).astype(int), 0, w - 1)
        v_a = np.clip(np.round(pts_a[:, 1]).astype(int), 0, h - 1)
        z_a = depths[anchor][v_a, u_a]
        valid_z = np.isfinite(z_a) & (z_a > 0.35) & (z_a < 15.0)

        if np.count_nonzero(valid_z) < 4:
            continue

        pts_a = pts_a[valid_z]
        pts_b = pts_b[valid_z]
        z_a = z_a[valid_z]

        # 3D points in anchor camera frame
        X_a = (np.linalg.inv(K) @ np.column_stack([pts_a, np.ones(len(pts_a))]).T).T * z_a[:, None]

        # Relative transformation: from anchor camera to current camera
        pose_a = poses[anchor]
        pose_b = poses[curr]
        R_rel = pose_b["R"] @ pose_a["R"].T
        t_rel = pose_b["t"] - R_rel @ pose_a["t"]
        rvec_rel, _ = cv2.Rodrigues(R_rel)

        proj_b, _ = cv2.projectPoints(X_a.astype(np.float32), rvec_rel, t_rel, K, None)
        proj_b = proj_b.reshape(-1, 2)

        # Plot up to 80 representative correspondences
        for k in range(min(len(pts_b), 80)):
            u_true, v_true = int(round(pts_b[k, 0])), int(round(pts_b[k, 1]))
            u_proj, v_proj = int(round(proj_b[k, 0])), int(round(proj_b[k, 1]))

            err = np.hypot(u_true - u_proj, v_true - v_proj)
            line_color = (0, 220, 0) if err <= 2.5 else (0, 0, 240)

            # 2D detected point
            cv2.circle(overlay, (u_true, v_true), 4, (0, 255, 0), -1)
            # Reprojected 3D point
            cv2.drawMarker(overlay, (u_proj, v_proj), (255, 140, 0), cv2.MARKER_CROSS, 8, 2)
            # Residual error line
            cv2.line(overlay, (u_true, v_true), (u_proj, v_proj), line_color, 1)

        # Overlay banner
        rmse = float(d.get("reprojection_rmse_px", 0.0))
        inliers = int(d.get("inliers", 0))
        trans = float(d.get("translation_m", 0.0))
        rot = float(d.get("rotation_deg", 0.0))
        text = f"Frame {curr:02d} (Anchor {anchor:02d}) | Inliers: {inliers} | Reproj RMSE: {rmse:.2f}px | Step: {trans:.3f}m, {rot:.1f}deg"
        cv2.rectangle(overlay, (0, 0), (w, 36), (20, 20, 20), -1)
        cv2.putText(overlay, text, (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

        out_img_path = os.path.join(output_dir, f"reproj_overlay_frame_{curr:02d}.jpg")
        cv2.imwrite(out_img_path, overlay)
