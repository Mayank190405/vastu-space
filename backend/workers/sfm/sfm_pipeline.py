#!/usr/bin/env python3
"""
VĀSTU Spatial Reconstruction Engine - Point 19: Structure-from-Motion (SfM)
Performs multi-view image matching, 3D point triangulation, robust Bundle Adjustment (BA),
outlier filtering, and sparse 3D point cloud generation in PLY and JSON formats.
"""

import os
import sys
import json
import math
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix

class Landmark3D:
    def __init__(
        self,
        point_id: int,
        xyz: np.ndarray,
        color_rgb: Tuple[int, int, int],
        observations: List[Tuple[int, int, float, float]], # (camera_id, feature_idx, px_x, px_y)
        error: float = 0.0
    ):
        self.point_id = point_id
        self.xyz = xyz # [X, Y, Z]
        self.color_rgb = color_rgb # [R, G, B] (0-255)
        self.observations = observations # [(cam_idx, feat_idx, u, v), ...]
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "point_id": self.point_id,
            "position": [round(float(v), 5) for v in self.xyz],
            "color": list(self.color_rgb),
            "track_length": len(self.observations),
            "reprojection_error_px": round(float(self.error), 3)
        }

class SfMPipeline:
    def __init__(
        self,
        max_reprojection_error: float = 2.0,
        min_track_length: int = 2,
        min_triangulation_angle_deg: float = 1.2,
        ratio_threshold: float = 0.75,
        ransac_threshold_px: float = 1.5,
        ba_max_nfev: int = 40
    ):
        self.max_reprojection_error = max_reprojection_error
        self.min_track_length = min_track_length
        self.min_triangulation_angle_deg = min_triangulation_angle_deg
        self.ratio_threshold = ratio_threshold
        self.ransac_threshold_px = ransac_threshold_px
        self.ba_max_nfev = ba_max_nfev

        try:
            self.detector = cv2.SIFT_create(nfeatures=2500)
            self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        except Exception:
            self.detector = cv2.ORB_create(nfeatures=2500)
            self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    @staticmethod
    def project_point(
        K: np.ndarray,
        R: np.ndarray,
        t: np.ndarray,
        point_3d: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Projects 3D world point into 2D camera image coordinates: x = K * (R * X + t)
        """
        P_cam = R @ point_3d.reshape((3, 1)) + t.reshape((3, 1))
        z = P_cam[2, 0]
        if z <= 1e-4:
            return None
        x_proj = (K @ P_cam).flatten()
        return np.array([x_proj[0] / z, x_proj[1] / z], dtype=np.float64)

    @staticmethod
    def rodrigues_to_rotation(rvec: np.ndarray) -> np.ndarray:
        R, _ = cv2.Rodrigues(rvec)
        return R

    @staticmethod
    def rotation_to_rodrigues(R: np.ndarray) -> np.ndarray:
        rvec, _ = cv2.Rodrigues(R)
        return rvec.flatten()

    def triangulate_two_views(
        self,
        K: np.ndarray,
        R1: np.ndarray,
        t1: np.ndarray,
        R2: np.ndarray,
        t2: np.ndarray,
        pts1: np.ndarray,
        pts2: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Triangulates 3D points from 2 calibrated camera views using DLT.
        Returns triangulated 3D points (Nx3) and boolean validity mask.
        """
        P1 = K @ np.hstack((R1, t1.reshape((3, 1))))
        P2 = K @ np.hstack((R2, t2.reshape((3, 1))))

        pts1_homo = pts1.T.astype(np.float64) # 2xN
        pts2_homo = pts2.T.astype(np.float64) # 2xN

        pts_4d_homo = cv2.triangulatePoints(P1.astype(np.float64), P2.astype(np.float64), pts1_homo, pts2_homo) # 4xN
        w = pts_4d_homo[3:4, :].copy()
        w[np.abs(w) < 1e-9] = 1e-9
        pts_3d = (pts_4d_homo[:3, :] / w).T # Nx3

        # Validation: Positive depth in both cameras and adequate parallax angle
        c1 = -R1.T @ t1.reshape((3, 1))
        c2 = -R2.T @ t2.reshape((3, 1))

        valid_mask = np.zeros(len(pts_3d), dtype=bool)
        for i in range(len(pts_3d)):
            p = pts_3d[i].reshape((3, 1))
            # Camera 1 depth
            z1 = (R1 @ p + t1.reshape((3, 1)))[2, 0]
            # Camera 2 depth
            z2 = (R2 @ p + t2.reshape((3, 1)))[2, 0]

            if z1 > 0.05 and z2 > 0.05:
                # Parallax angle check
                v1 = (p - c1).flatten()
                v2 = (p - c2).flatten()
                norm1 = np.linalg.norm(v1)
                norm2 = np.linalg.norm(v2)
                if norm1 > 1e-4 and norm2 > 1e-4:
                    cos_theta = np.clip(np.dot(v1, v2) / (norm1 * norm2), -1.0, 1.0)
                    angle_deg = math.degrees(math.acos(cos_theta))
                    if angle_deg >= self.min_triangulation_angle_deg:
                        valid_mask[i] = True

        return pts_3d, valid_mask

    def run_bundle_adjustment(
        self,
        K: np.ndarray,
        camera_poses: List[Dict[str, np.ndarray]], # [{'R': 3x3, 't': 3x1}, ...]
        landmarks: List[Landmark3D]
    ) -> Tuple[List[Dict[str, np.ndarray]], List[Landmark3D]]:
        """
        Executes Levenberg-Marquardt Non-linear Least Squares Bundle Adjustment:
        jointly refines camera rotations (Rodrigues vector), translations, and 3D point positions.
        """
        if len(landmarks) == 0 or len(camera_poses) < 2:
            return camera_poses, landmarks

        n_cameras = len(camera_poses)
        n_points = len(landmarks)

        # Anchor camera 0 (reference frame) to eliminate gauge ambiguity:
        # Camera 0 is fixed; cameras 1..N-1 and all 3D points are optimized.
        rvec0 = self.rotation_to_rodrigues(camera_poses[0]['R'])
        tvec0 = camera_poses[0]['t'].flatten()

        camera_params = []
        for i in range(1, n_cameras):
            rvec = self.rotation_to_rodrigues(camera_poses[i]['R'])
            tvec = camera_poses[i]['t'].flatten()
            camera_params.extend(rvec)
            camera_params.extend(tvec)
        camera_params = np.array(camera_params, dtype=np.float64)

        points_params = np.array([lm.xyz for lm in landmarks], dtype=np.float64).ravel()
        x0 = np.concatenate((camera_params, points_params)) if len(camera_params) > 0 else points_params

        # Build observations lookup
        camera_indices = []
        point_indices = []
        points_2d = []

        for p_idx, lm in enumerate(landmarks):
            for obs in lm.observations:
                cam_idx, _, u, v = obs
                camera_indices.append(cam_idx)
                point_indices.append(p_idx)
                points_2d.append([u, v])

        camera_indices = np.array(camera_indices, dtype=np.int32)
        point_indices = np.array(point_indices, dtype=np.int32)
        points_2d = np.array(points_2d, dtype=np.float64)

        n_opt_cams = n_cameras - 1

        def residuals(params: np.ndarray) -> np.ndarray:
            if n_opt_cams > 0:
                c_params = params[:n_opt_cams * 6].reshape((n_opt_cams, 6))
                p_params = params[n_opt_cams * 6:].reshape((n_points, 3))
            else:
                c_params = None
                p_params = params.reshape((n_points, 3))

            res = []
            for obs_i in range(len(camera_indices)):
                c_idx = camera_indices[obs_i]
                p_idx = point_indices[obs_i]

                if c_idx == 0 or c_params is None:
                    rvec = rvec0
                    tvec = tvec0.reshape((3, 1))
                else:
                    rvec = c_params[c_idx - 1, :3]
                    tvec = c_params[c_idx - 1, 3:].reshape((3, 1))

                R = SfMPipeline.rodrigues_to_rotation(rvec)
                P3 = p_params[p_idx]

                proj = SfMPipeline.project_point(K, R, tvec, P3)
                if proj is None:
                    res.append([50.0, 50.0])
                else:
                    observed = points_2d[obs_i]
                    res.append([proj[0] - observed[0], proj[1] - observed[1]])

            return np.array(res, dtype=np.float64).ravel()

        try:
            res = least_squares(
                residuals,
                x0,
                method='trf',
                loss='huber',
                f_scale=1.5,
                max_nfev=self.ba_max_nfev
            )
            opt_x = res.x
        except Exception as e:
            opt_x = x0

        if n_opt_cams > 0:
            opt_c_params = opt_x[:n_opt_cams * 6].reshape((n_opt_cams, 6))
            opt_p_params = opt_x[n_opt_cams * 6:].reshape((n_points, 3))
        else:
            opt_c_params = None
            opt_p_params = opt_x.reshape((n_points, 3))

        refined_poses = [{'R': camera_poses[0]['R'].copy(), 't': camera_poses[0]['t'].copy()}]
        for i in range(1, n_cameras):
            if opt_c_params is not None:
                R_ref = self.rodrigues_to_rotation(opt_c_params[i - 1, :3])
                t_ref = opt_c_params[i - 1, 3:].reshape((3, 1))
                refined_poses.append({'R': R_ref, 't': t_ref})
            else:
                refined_poses.append({'R': camera_poses[i]['R'].copy(), 't': camera_poses[i]['t'].copy()})

        refined_landmarks: List[Landmark3D] = []
        for p_idx, lm in enumerate(landmarks):
            P3_ref = opt_p_params[p_idx]
            errors = []
            for obs in lm.observations:
                cam_idx, feat_idx, u, v = obs
                proj = self.project_point(K, refined_poses[cam_idx]['R'], refined_poses[cam_idx]['t'], P3_ref)
                if proj is not None:
                    err = np.linalg.norm(proj - np.array([u, v]))
                    errors.append(err)

            mean_err = float(np.mean(errors)) if errors else 999.0
            if mean_err <= self.max_reprojection_error:
                lm.xyz = P3_ref
                lm.error = mean_err
                refined_landmarks.append(lm)

        return refined_poses, refined_landmarks

    def export_ply(self, landmarks: List[Landmark3D], output_path: str):
        """
        Exports reconstructed 3D point cloud into standard ASCII Stanford PLY format.
        """
        num_vertices = len(landmarks)
        header = f"""ply
format ascii 1.0
comment VASTU Spatial Computing SfM Point Cloud
element vertex {num_vertices}
property float x
property float y
property float z
property uchar red
property uchar green
property uchar blue
property float error
end_header
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            for lm in landmarks:
                x, y, z = lm.xyz
                r, g, b = lm.color_rgb
                err = lm.error
                f.write(f"{x:.6f} {y:.6f} {z:.6f} {int(r)} {int(g)} {int(b)} {err:.3f}\n")

    def run_reconstruction(
        self,
        preprocessing_dir: str,
        tracking_dir: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Runs complete SfM pipeline:
        Feature extraction -> Multi-view matching -> Triangulation -> Bundle Adjustment -> PLY export.
        """
        os.makedirs(output_dir, exist_ok=True)

        # 1. Load Calibration & Poses
        calib_path = os.path.join(preprocessing_dir, "calibration.json")
        manifest_path = os.path.join(preprocessing_dir, "preprocessing_manifest.json")
        poses_path = os.path.join(tracking_dir, "camera_poses.json")

        if not os.path.exists(calib_path) or not os.path.exists(poses_path):
            raise FileNotFoundError("Missing calibration.json or camera_poses.json")

        with open(calib_path, "r", encoding="utf-8") as f:
            calib = json.load(f)
        with open(poses_path, "r", encoding="utf-8") as f:
            poses_data = json.load(f)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        intr = calib["intrinsics"]
        K = np.array([
            [intr["fx"], 0.0, intr["cx"]],
            [0.0, intr["fy"], intr["cy"]],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        keyframes_dir = os.path.join(preprocessing_dir, "keyframes")
        kf_list = manifest.get("keyframes", [])
        poses_list = poses_data.get("poses", [])

        # Load images and initial camera poses
        images_rgb = []
        camera_poses = []
        keypoints_list = []
        descriptors_list = []

        for p_info in poses_list:
            fname = p_info["file_name"]
            img_path = os.path.join(keyframes_dir, fname)
            if not os.path.exists(img_path):
                continue
            bgr = cv2.imread(img_path)
            if bgr is None:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            images_rgb.append(rgb)

            R = np.array(p_info["rotation_matrix"], dtype=np.float64)
            pos = np.array(p_info["position"], dtype=np.float64).reshape((3, 1))
            t = -R @ pos # Camera translation vector t = -R * C
            camera_poses.append({'R': R, 't': t})

            kp, desc = self.detector.detectAndCompute(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), None)
            keypoints_list.append(kp)
            descriptors_list.append(desc)

        num_cameras = len(camera_poses)
        if num_cameras < 2:
            raise ValueError("Structure-from-Motion requires at least 2 calibrated keyframes")

        # 2. Sequential & Spatial Triangulation
        landmarks_raw: List[Landmark3D] = []
        point_id_counter = 0

        for i in range(num_cameras - 1):
            j = i + 1 # Consecutive view pair
            desc1, desc2 = descriptors_list[i], descriptors_list[j]
            kp1, kp2 = keypoints_list[i], keypoints_list[j]

            if desc1 is None or desc2 is None or len(desc1) < 8 or len(desc2) < 8:
                continue

            matches = self.matcher.knnMatch(desc1, desc2, k=2)
            good_matches = []
            for m_tuple in matches:
                if len(m_tuple) == 2:
                    m, n = m_tuple
                    if m.distance < self.ratio_threshold * n.distance:
                        good_matches.append(m)

            if len(good_matches) < 8:
                continue

            pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches])
            pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches])

            pts_3d, valid_mask = self.triangulate_two_views(
                K,
                camera_poses[i]['R'], camera_poses[i]['t'],
                camera_poses[j]['R'], camera_poses[j]['t'],
                pts1, pts2
            )

            for m_idx in range(len(good_matches)):
                if not valid_mask[m_idx]:
                    continue
                match = good_matches[m_idx]
                p3 = pts_3d[m_idx]

                # Sample color from camera 1
                u1, v1 = int(round(pts1[m_idx, 0])), int(round(pts1[m_idx, 1]))
                h, w, _ = images_rgb[i].shape
                u1 = max(0, min(w - 1, u1))
                v1 = max(0, min(h - 1, v1))
                color = tuple(images_rgb[i][v1, u1].tolist())

                obs = [
                    (i, match.queryIdx, float(pts1[m_idx, 0]), float(pts1[m_idx, 1])),
                    (j, match.trainIdx, float(pts2[m_idx, 0]), float(pts2[m_idx, 1]))
                ]

                # Initial reprojection error
                proj1 = self.project_point(K, camera_poses[i]['R'], camera_poses[i]['t'], p3)
                proj2 = self.project_point(K, camera_poses[j]['R'], camera_poses[j]['t'], p3)
                err1 = np.linalg.norm(proj1 - pts1[m_idx]) if proj1 is not None else 99.0
                err2 = np.linalg.norm(proj2 - pts2[m_idx]) if proj2 is not None else 99.0
                mean_err = float((err1 + err2) / 2.0)

                if mean_err <= self.max_reprojection_error:
                    lm = Landmark3D(
                        point_id=point_id_counter,
                        xyz=p3,
                        color_rgb=color,
                        observations=obs,
                        error=mean_err
                    )
                    landmarks_raw.append(lm)
                    point_id_counter += 1

        # 3. Non-linear Bundle Adjustment on top salient landmarks
        if len(landmarks_raw) > 120:
            # Sort by lowest initial error and select top 120 landmarks for fast BA
            ba_subset = sorted(landmarks_raw, key=lambda l: l.error)[:120]
        else:
            ba_subset = landmarks_raw

        refined_poses, _ = self.run_bundle_adjustment(K, camera_poses, ba_subset)

        # Refine and filter all landmarks using refined camera poses
        refined_landmarks: List[Landmark3D] = []
        for lm in landmarks_raw:
            errors = []
            for obs in lm.observations:
                cam_idx, feat_idx, u, v = obs
                proj = self.project_point(K, refined_poses[cam_idx]['R'], refined_poses[cam_idx]['t'], lm.xyz)
                if proj is not None:
                    err = np.linalg.norm(proj - np.array([u, v]))
                    errors.append(err)
            mean_err = float(np.mean(errors)) if errors else 999.0
            if mean_err <= self.max_reprojection_error:
                lm.error = mean_err
                refined_landmarks.append(lm)

        # 4. Export Artifacts
        ply_path = os.path.join(output_dir, "sparse_points3D.ply")
        self.export_ply(refined_landmarks, ply_path)

        json_points_path = os.path.join(output_dir, "sparse_points3D.json")
        with open(json_points_path, "w", encoding="utf-8") as f:
            json.dump([lm.to_dict() for lm in refined_landmarks], f, indent=2)

        # Calculate bounding box and statistics
        if refined_landmarks:
            all_xyz = np.array([lm.xyz for lm in refined_landmarks])
            min_bound = [round(float(v), 3) for v in np.min(all_xyz, axis=0)]
            max_bound = [round(float(v), 3) for v in np.max(all_xyz, axis=0)]
            mean_error = round(float(np.mean([lm.error for lm in refined_landmarks])), 3)
            mean_track = round(float(np.mean([len(lm.observations) for lm in refined_landmarks])), 2)
        else:
            min_bound, max_bound = [0, 0, 0], [0, 0, 0]
            mean_error = 0.0
            mean_track = 0.0

        stats = {
            "reconstruction_engine": "VASTU_SfM_BA_v1.0",
            "registered_keyframes": num_cameras,
            "total_sparse_points": len(refined_landmarks),
            "mean_reprojection_error_px": mean_error,
            "mean_track_length": mean_track,
            "bounding_box_min": min_bound,
            "bounding_box_max": max_bound,
            "artifacts": {
                "ply": "sparse_points3D.ply",
                "json": "sparse_points3D.json"
            }
        }

        stats_path = os.path.join(output_dir, "reconstruction_stats.json")
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        return stats

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python sfm_pipeline.py <preprocessing_dir> <tracking_dir> <output_dir>")
        sys.exit(1)

    prep_dir = sys.argv[1]
    track_dir = sys.argv[2]
    out_dir = sys.argv[3]

    sfm = SfMPipeline()
    try:
        results = sfm.run_reconstruction(prep_dir, track_dir, out_dir)
        print(f"SUCCESS: Reconstructed {results['total_sparse_points']} sparse 3D points. Mean error: {results['mean_reprojection_error_px']}px.")
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)
