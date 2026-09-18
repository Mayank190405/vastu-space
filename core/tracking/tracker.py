"""
VĀSTU Visual Pose Tracker
Extracts visual features (SIFT/ORB), computes robust epipolar geometry,
evaluates inliers, reprojection errors, and calculates angular parallax.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple


class VisualTrackingResult:
    def __init__(
        self,
        success: bool,
        R_rel: np.ndarray,
        t_rel: np.ndarray,
        inliers_count: int,
        inlier_ratio: float,
        reprojection_error_px: float,
        parallax_angle_deg: float,
        pts1: np.ndarray,
        pts2: np.ndarray
    ):
        self.success = success
        self.R_rel = R_rel
        self.t_rel = t_rel
        self.inliers_count = inliers_count
        self.inlier_ratio = inlier_ratio
        self.reprojection_error_px = reprojection_error_px
        self.parallax_angle_deg = parallax_angle_deg
        self.pts1 = pts1
        self.pts2 = pts2


class VisualPoseTracker:
    """
    Epipolar visual odometry and feature tracking engine.
    """
    def __init__(self, n_features: int = 1500, min_inliers: int = 25):
        self.n_features = n_features
        self.min_inliers = min_inliers
        if hasattr(cv2, "SIFT_create"):
            self.detector = cv2.SIFT_create(nfeatures=n_features)
            self.matcher = cv2.BFMatcher(cv2.NORM_L2)
        else:
            self.detector = cv2.ORB_create(nfeatures=n_features)
            self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)

    def extract_features(self, img_bgr: np.ndarray) -> Tuple[List[cv2.KeyPoint], Optional[np.ndarray]]:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        kps, descs = self.detector.detectAndCompute(gray, None)
        return kps, descs

    def track_pair(
        self,
        kps1: List[cv2.KeyPoint],
        descs1: np.ndarray,
        kps2: List[cv2.KeyPoint],
        descs2: np.ndarray,
        K: np.ndarray
    ) -> VisualTrackingResult:
        """
        Estimates relative pose (R, t) between two keyframes and computes parallax.
        """
        if descs1 is None or descs2 is None or len(descs1) < 8 or len(descs2) < 8:
            return VisualTrackingResult(
                success=False,
                R_rel=np.eye(3),
                t_rel=np.zeros((3, 1)),
                inliers_count=0,
                inlier_ratio=0.0,
                reprojection_error_px=999.0,
                parallax_angle_deg=0.0,
                pts1=np.empty((0, 2)),
                pts2=np.empty((0, 2))
            )

        matches = self.matcher.knnMatch(descs1, descs2, k=2)
        good = [m for m, n in matches if m.distance < 0.75 * n.distance]

        if len(good) < self.min_inliers:
            return VisualTrackingResult(
                success=False,
                R_rel=np.eye(3),
                t_rel=np.zeros((3, 1)),
                inliers_count=len(good),
                inlier_ratio=len(good) / max(1, len(matches)),
                reprojection_error_px=999.0,
                parallax_angle_deg=0.0,
                pts1=np.empty((0, 2)),
                pts2=np.empty((0, 2))
            )

        pts1 = np.float32([kps1[m.queryIdx].pt for m in good])
        pts2 = np.float32([kps2[m.trainIdx].pt for m in good])

        # Essential matrix with RANSAC
        E, mask = cv2.findEssentialMat(
            pts1, pts2, K,
            method=cv2.RANSAC,
            prob=0.999,
            threshold=1.5
        )

        if E is None or E.shape != (3, 3) or mask is None:
            return VisualTrackingResult(
                success=False,
                R_rel=np.eye(3),
                t_rel=np.zeros((3, 1)),
                inliers_count=0,
                inlier_ratio=0.0,
                reprojection_error_px=999.0,
                parallax_angle_deg=0.0,
                pts1=pts1,
                pts2=pts2
            )

        inliers_mask = mask.ravel() == 1
        inliers_count = int(np.sum(inliers_mask))

        if inliers_count < self.min_inliers:
            return VisualTrackingResult(
                success=False,
                R_rel=np.eye(3),
                t_rel=np.zeros((3, 1)),
                inliers_count=inliers_count,
                inlier_ratio=inliers_count / len(good),
                reprojection_error_px=999.0,
                parallax_angle_deg=0.0,
                pts1=pts1,
                pts2=pts2
            )

        _, R_rel, t_rel, pose_mask = cv2.recoverPose(E, pts1, pts2, K, mask=mask)

        inliers_pts1 = pts1[inliers_mask]
        inliers_pts2 = pts2[inliers_mask]

        # Compute angular parallax between matched inliers
        # Normalized camera ray vectors: ray = inv(K) * [u, v, 1].T
        K_inv = np.linalg.inv(K)
        rays1 = (K_inv @ np.column_stack([inliers_pts1, np.ones(len(inliers_pts1))]).T).T
        rays2 = (K_inv @ np.column_stack([inliers_pts2, np.ones(len(inliers_pts2))]).T).T
        norms1 = np.linalg.norm(rays1, axis=1, keepdims=True)
        norms2 = np.linalg.norm(rays2, axis=1, keepdims=True)
        rays1_unit = rays1 / np.maximum(1e-7, norms1)
        rays2_unit = rays2 / np.maximum(1e-7, norms2)

        # Apply rotation to align rays: ray2_in_frame1 = R_rel.T @ ray2
        rays2_aligned = (R_rel.T @ rays2_unit.T).T
        cos_angles = np.sum(rays1_unit * rays2_aligned, axis=1)
        cos_angles = np.clip(cos_angles, -1.0, 1.0)
        parallax_angles = np.degrees(np.arccos(cos_angles))
        mean_parallax = float(np.median(parallax_angles)) if len(parallax_angles) > 0 else 0.0

        # Compute epipolar reprojection residual
        # Sampson error approximation or point-to-epipolar line distance
        F = np.linalg.inv(K).T @ E @ np.linalg.inv(K)
        lines1 = cv2.computeCorrespondEpilines(inliers_pts2.reshape(-1, 1, 2), 2, F).reshape(-1, 3)
        num = np.abs(lines1[:, 0] * inliers_pts1[:, 0] + lines1[:, 1] * inliers_pts1[:, 1] + lines1[:, 2])
        den = np.sqrt(lines1[:, 0]**2 + lines1[:, 1]**2)
        errors = num / np.maximum(1e-7, den)
        mean_reproj_error = float(np.mean(errors)) if len(errors) > 0 else 0.5

        return VisualTrackingResult(
            success=True,
            R_rel=R_rel,
            t_rel=t_rel,
            inliers_count=inliers_count,
            inlier_ratio=float(inliers_count / len(good)),
            reprojection_error_px=mean_reproj_error,
            parallax_angle_deg=mean_parallax,
            pts1=inliers_pts1,
            pts2=inliers_pts2
        )
