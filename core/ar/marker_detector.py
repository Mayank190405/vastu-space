"""
VĀSTU AR Marker Detection & PnP Pose Estimator (Stage 29)
Provides fiducial marker detection (ArUco / AprilTag) and Perspective-n-Point
rigid pose estimation (T_cam_marker).
Includes synthetic projection utilities for hardware-independent validation.
"""

import math
from typing import List, Tuple, Optional, Dict
import numpy as np
import cv2

from core.schemas.ar_localization import DetectedMarker, MarkerType


class ARMarkerDetector:
    """
    Fiducial marker detector and PnP pose solver.
    Extracts 2D image corners and estimates metric 6-DOF camera-to-marker pose.
    """

    def __init__(self, marker_type: MarkerType = MarkerType.ARUCO_4X4_50):
        self.marker_type = marker_type
        # OpenCV ArUco Dictionary Mapping
        self._aruco_dict_id = cv2.aruco.DICT_4X4_50 if marker_type == MarkerType.ARUCO_4X4_50 else cv2.aruco.DICT_6X6_250
        self._aruco_dict = cv2.aruco.getPredefinedDictionary(self._aruco_dict_id)
        self._aruco_params = cv2.aruco.DetectorParameters()
        self._detector = cv2.aruco.ArucoDetector(self._aruco_dict, self._aruco_params)

    def detect_markers(
        self,
        image_bgr: np.ndarray,
        intrinsics: np.ndarray,
        marker_size_m: float = 0.20
    ) -> List[DetectedMarker]:
        """
        Detects markers in an RGB/BGR camera frame and calculates 3D pose for each.
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if len(image_bgr.shape) == 3 else image_bgr
        corners, ids, rejected = self._detector.detectMarkers(gray)

        results: List[DetectedMarker] = []
        if ids is None or len(ids) == 0:
            return results

        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        for i, mid in enumerate(ids.flatten()):
            c_2d = corners[i][0]  # shape (4, 2)
            # Solve PnP for marker
            t_cam_marker, repr_err = self.solve_pnp_marker(c_2d, intrinsics, marker_size_m)
            results.append(DetectedMarker(
                marker_id=int(mid),
                corners_2d=c_2d.tolist(),
                camera_t_marker=t_cam_marker.tolist() if t_cam_marker is not None else None,
                reprojection_error_px=round(repr_err, 3),
                detection_confidence=1.0
            ))

        return results

    def solve_pnp_marker(
        self,
        corners_2d: np.ndarray,
        intrinsics: np.ndarray,
        marker_size_m: float
    ) -> Tuple[Optional[np.ndarray], float]:
        """
        Solves Perspective-n-Point to find 4x4 rigid transformation T_cam_marker.
        Marker frame definition:
        - Center: (0, 0, 0)
        - Corners: Top-Left, Top-Right, Bottom-Right, Bottom-Left on Z=0 plane.
        """
        s = marker_size_m / 2.0
        # Standard ArUco 3D object points in marker local frame
        obj_pts = np.array([
            [-s,  s, 0.0],
            [ s,  s, 0.0],
            [ s, -s, 0.0],
            [-s, -s, 0.0]
        ], dtype=np.float64)

        img_pts = np.ascontiguousarray(corners_2d, dtype=np.float64)
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        success, rvec, tvec = cv2.solvePnP(
            objectPoints=obj_pts,
            imagePoints=img_pts,
            cameraMatrix=intrinsics,
            distCoeffs=dist_coeffs,
            flags=cv2.SOLVEPNP_IPPE_SQUARE
        )

        if not success:
            return None, 999.0

        R, _ = cv2.Rodrigues(rvec)
        t = tvec.flatten()

        t_cam_marker = np.eye(4, dtype=np.float64)
        t_cam_marker[:3, :3] = R
        t_cam_marker[:3, 3] = t

        # Calculate reprojection error
        proj_pts, _ = cv2.projectPoints(obj_pts, rvec, tvec, intrinsics, dist_coeffs)
        proj_pts = proj_pts.reshape(-1, 2)
        error = float(np.mean(np.linalg.norm(img_pts - proj_pts, axis=1)))

        return t_cam_marker, error

    # -------------------------------------------------------------------------
    # SYNTHETIC SIMULATION HELPERS (Deterministic Benchmarking)
    # -------------------------------------------------------------------------

    @staticmethod
    def project_marker_corners_to_image(
        t_cam_marker: np.ndarray,
        intrinsics: np.ndarray,
        marker_size_m: float = 0.20,
        noise_std_px: float = 0.0
    ) -> Tuple[Optional[np.ndarray], bool]:
        """
        Projects 3D marker corners into 2D camera pixel coordinates.
        Returns corners shape (4, 2) and boolean indicating if marker is in front of camera.
        """
        s = marker_size_m / 2.0
        obj_pts_marker = np.array([
            [-s,  s, 0.0, 1.0],
            [ s,  s, 0.0, 1.0],
            [ s, -s, 0.0, 1.0],
            [-s, -s, 0.0, 1.0]
        ], dtype=np.float64)

        # Transform to camera frame
        pts_cam = (t_cam_marker @ obj_pts_marker.T).T[:, :3]

        # Check if all points are in front of camera
        if np.any(pts_cam[:, 2] <= 0.1):
            return None, False

        # Perspective projection
        fx, fy = intrinsics[0, 0], intrinsics[1, 1]
        cx, cy = intrinsics[0, 2], intrinsics[1, 2]

        corners_2d = np.zeros((4, 2), dtype=np.float64)
        for i in range(4):
            x, y, z = pts_cam[i]
            u = (fx * x / z) + cx
            v = (fy * y / z) + cy
            if noise_std_px > 0.0:
                u += np.random.normal(0, noise_std_px)
                v += np.random.normal(0, noise_std_px)
            corners_2d[i] = [u, v]

        return corners_2d, True
