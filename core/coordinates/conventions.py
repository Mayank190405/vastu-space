"""
VĀSTU v3.0 — S5 Coordinate Conventions & Spatial Transforms
============================================================
Authoritative definitions for 3D coordinate frames, camera poses,
intrinsics, and explicit conversions across ARKit, OpenCV, and OpenGL.

Rules (per Master Architecture v3.0 S5):
1. World coordinate frame: Right-handed, Y-up, metric units (meters).
2. Internal camera pose contract: T_world_camera (camera-to-world 4x4 matrix)
   P_world = T_world_camera @ P_camera
3. ARKit camera frame: -Z forward, +X right, +Y up (Right-Up-Back / RUB).
4. OpenCV camera frame: +Z forward, +X right, +Y down (Right-Down-Forward / RDF).
5. Conversion between ARKit and OpenCV is explicit at import/export boundaries.
6. Reprojection roundtrip must satisfy synthetic error < 1.0 pixel.
"""

from enum import Enum
from typing import Dict, Any, List, Tuple, Optional, Union
import numpy as np
import cv2


class CameraConvention(str, Enum):
    """Camera local coordinate frame conventions."""
    ARKIT_RUB = "ARKIT_RUB"      # -Z forward, +X right, +Y up (ARKit / OpenGL standard)
    OPENCV_RDF = "OPENCV_RDF"    # +Z forward, +X right, +Y down; do not infer other SDK conventions
    OPENGL_RUB = "OPENGL_RUB"    # -Z forward, +X right, +Y up (Three.js camera local frame)


class WorldConvention(str, Enum):
    """World coordinate frame conventions."""
    RIGHT_HANDED_Y_UP = "RIGHT_HANDED_Y_UP"  # VĀSTU standard: +Y up, right-handed (meters)
    RIGHT_HANDED_Z_UP = "RIGHT_HANDED_Z_UP"  # Traditional GIS / ROS standard: +Z up


# Fixed transform flipping Y and Z axes: [1, 0, 0; 0, -1, 0; 0, 0, -1]
# Maps vector in ARKit (-Z forward, +Y up) to OpenCV (+Z forward, +Y down)
C_OPENCV_FROM_ARKIT = np.array([
    [1.0,  0.0,  0.0],
    [0.0, -1.0,  0.0],
    [0.0,  0.0, -1.0]
], dtype=np.float64)

# Matrix is self-inverse: C @ C = I
C_ARKIT_FROM_OPENCV = C_OPENCV_FROM_ARKIT.copy()


def image_rotation_homography(width: int, height: int, quarter_turns: int) -> np.ndarray:
    """Map integer pixel centers to a clockwise-rotated image; not a world-axis flip.

    For display-only orientation use p_display ~ H @ K @ p_camera. Capture packages
    retain sensor-native pixels and K; rotating stored images requires a new calibration.
    """
    if width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive")
    transforms = (
        np.eye(3),
        np.array([[0, -1, height - 1], [1, 0, 0], [0, 0, 1]]),
        np.array([[-1, 0, width - 1], [0, -1, height - 1], [0, 0, 1]]),
        np.array([[0, 1, 0], [-1, 0, width - 1], [0, 0, 1]]),
    )
    return transforms[quarter_turns % 4].astype(np.float64)


def rotation_matrix_to_quaternion(R: np.ndarray) -> np.ndarray:
    """
    Converts a 3x3 orthonormal rotation matrix to unit quaternion [qx, qy, qz, qw].
    Orthonormality check is enforced.
    """
    R = np.asarray(R, dtype=np.float64)
    if R.shape != (3, 3):
        raise ValueError(f"Expected 3x3 rotation matrix, got shape {R.shape}")

    # Verify orthonormality
    err = np.linalg.norm(R @ R.T - np.eye(3))
    if err > 1e-4:
        raise ValueError(f"Matrix is not orthonormal (deviation={err:.6e})")

    det = np.linalg.det(R)
    if not np.isclose(det, 1.0, atol=1e-3):
        raise ValueError(f"Matrix determinant must be +1 (got {det:.4f})")

    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0:
        S = np.sqrt(tr + 1.0) * 2.0
        qw = 0.25 * S
        qx = (R[2, 1] - R[1, 2]) / S
        qy = (R[0, 2] - R[2, 0]) / S
        qz = (R[1, 0] - R[0, 1]) / S
    elif (R[0, 0] > R[1, 1]) and (R[0, 0] > R[2, 2]):
        S = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
        qw = (R[2, 1] - R[1, 2]) / S
        qx = 0.25 * S
        qy = (R[0, 1] + R[1, 0]) / S
        qz = (R[0, 2] + R[2, 0]) / S
    elif R[1, 1] > R[2, 2]:
        S = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
        qw = (R[0, 2] - R[2, 0]) / S
        qx = (R[0, 1] + R[1, 0]) / S
        qy = 0.25 * S
        qz = (R[1, 2] + R[2, 1]) / S
    else:
        S = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
        qw = (R[1, 0] - R[0, 1]) / S
        qx = (R[0, 2] + R[2, 0]) / S
        qy = (R[1, 2] + R[2, 1]) / S
        qz = 0.25 * S

    q = np.array([qx, qy, qz, qw], dtype=np.float64)
    norm = np.linalg.norm(q)
    if norm > 1e-12:
        q /= norm
    return q


def quaternion_to_rotation_matrix(q: Union[List[float], np.ndarray]) -> np.ndarray:
    """
    Converts unit quaternion [qx, qy, qz, qw] to 3x3 orthonormal rotation matrix.
    """
    q = np.asarray(q, dtype=np.float64).flatten()
    if q.shape != (4,):
        raise ValueError(f"Expected 4-element quaternion, got shape {q.shape}")

    norm = np.linalg.norm(q)
    if not np.all(np.isfinite(q)) or norm < 1e-12:
        raise ValueError("Cannot normalize zero-length quaternion")
    qx, qy, qz, qw = q / norm

    R = np.array([
        [1.0 - 2.0 * (qy**2 + qz**2), 2.0 * (qx * qy - qz * qw),     2.0 * (qx * qz + qy * qw)],
        [2.0 * (qx * qy + qz * qw),     1.0 - 2.0 * (qx**2 + qz**2), 2.0 * (qy * qz - qx * qw)],
        [2.0 * (qx * qz - qy * qw),     2.0 * (qy * qz + qx * qw),     1.0 - 2.0 * (qx**2 + qy**2)]
    ], dtype=np.float64)
    return R


class CameraIntrinsics:
    """Pinhole camera intrinsic calibration with explicit distortion."""

    def __init__(
        self,
        fx: float,
        fy: float,
        cx: float,
        cy: float,
        width: int,
        height: int,
        distortion_coeffs: Optional[List[float]] = None
    ):
        if not np.all(np.isfinite([fx, fy, cx, cy])) or fx <= 0 or fy <= 0:
            raise ValueError(f"Focal length must be positive, got fx={fx}, fy={fy}")
        if width <= 0 or height <= 0:
            raise ValueError(f"Dimensions must be positive, got {width}x{height}")

        self.fx = float(fx)
        self.fy = float(fy)
        self.cx = float(cx)
        self.cy = float(cy)
        self.width = int(width)
        self.height = int(height)
        dist = distortion_coeffs if distortion_coeffs is not None else [0.0, 0.0, 0.0, 0.0, 0.0]
        self.distortion = np.asarray(dist, dtype=np.float64).flatten()
        if not np.all(np.isfinite(self.distortion)):
            raise ValueError("Distortion coefficients must be finite")
        if len(self.distortion) < 5:
            padded = np.zeros(5, dtype=np.float64)
            padded[:len(self.distortion)] = self.distortion
            self.distortion = padded

    @property
    def has_distortion(self) -> bool:
        """Returns True if any lens distortion coefficient is non-zero."""
        return bool(np.any(np.abs(self.distortion) > 1e-6))

    def undistort_points(self, points_uv: np.ndarray) -> np.ndarray:
        """
        Undistorts 2D pixel coordinates using OpenCV cv2.undistortPoints.
        Input points shape: (N, 2) or (2,)
        Output points shape: matching (N, 2)
        """
        pts = np.asarray(points_uv, dtype=np.float64).reshape(-1, 1, 2)
        if not self.has_distortion:
            return pts.reshape(-1, 2)
        # Undistort with P=K to keep coordinates in pixel space
        undistorted = cv2.undistortPoints(pts, self.K, self.distortion, P=self.K)
        return undistorted.reshape(-1, 2)

    def ray_direction(self, u: float, v: float) -> np.ndarray:
        """
        Returns normalized 3D unit ray vector in OpenCV camera coordinates (+Z forward)
        for a given 2D pixel (u, v), properly accounting for lens distortion.
        """
        if self.has_distortion:
            undist = self.undistort_points(np.array([[u, v]], dtype=np.float64))[0]
            p_hom = np.array([undist[0], undist[1], 1.0], dtype=np.float64)
        else:
            p_hom = np.array([u, v, 1.0], dtype=np.float64)
        ray = self.K_inv @ p_hom
        norm = np.linalg.norm(ray)
        return ray / max(norm, 1e-12)

    @property
    def K(self) -> np.ndarray:
        """3x3 Camera calibration matrix."""
        return np.array([
            [self.fx, 0.0,     self.cx],
            [0.0,     self.fy, self.cy],
            [0.0,     0.0,     1.0]
        ], dtype=np.float64)

    @property
    def K_inv(self) -> np.ndarray:
        """Inverse of 3x3 Camera calibration matrix."""
        return np.linalg.inv(self.K)

    def rescale(self, new_width: int, new_height: int) -> "CameraIntrinsics":
        """Returns new scaled intrinsics for resized imagery."""
        sx = float(new_width) / float(self.width)
        sy = float(new_height) / float(self.height)
        return CameraIntrinsics(
            fx=self.fx * sx,
            fy=self.fy * sy,
            cx=self.cx * sx,
            cy=self.cy * sy,
            width=new_width,
            height=new_height,
            distortion_coeffs=self.distortion.tolist()
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fx": self.fx,
            "fy": self.fy,
            "cx": self.cx,
            "cy": self.cy,
            "width": self.width,
            "height": self.height,
            "distortion": self.distortion.tolist()
        }

    def validate_bounds(self) -> Dict[str, Any]:
        """Validate focal length and optical center against physical smartphone geometry."""
        max_dim = max(self.width, self.height)
        fov_h = 2.0 * np.arctan(self.width / (2.0 * self.fx)) * 180.0 / np.pi
        fov_v = 2.0 * np.arctan(self.height / (2.0 * self.fy)) * 180.0 / np.pi

        is_focal_plausible = (0.35 * max_dim <= self.fx <= 2.0 * max_dim) and (0.35 * max_dim <= self.fy <= 2.0 * max_dim)
        is_center_plausible = (abs(self.cx - self.width / 2.0) <= 0.15 * self.width) and (abs(self.cy - self.height / 2.0) <= 0.15 * self.height)
        aspect_ratio_err = abs(self.fx - self.fy) / self.fx
        is_square_pixel = aspect_ratio_err < 0.05

        return {
            "is_valid": bool(is_focal_plausible and is_center_plausible and is_square_pixel),
            "is_focal_plausible": bool(is_focal_plausible),
            "is_center_plausible": bool(is_center_plausible),
            "is_square_pixel": bool(is_square_pixel),
            "fov_h_deg": round(float(fov_h), 2),
            "fov_v_deg": round(float(fov_v), 2),
            "pixel_aspect_ratio_err": round(float(aspect_ratio_err), 4)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CameraIntrinsics":
        return cls(
            fx=data["fx"],
            fy=data["fy"],
            cx=data["cx"],
            cy=data["cy"],
            width=data["width"],
            height=data["height"],
            distortion_coeffs=data.get("distortion")
        )


class CameraPose:
    """
    Authoritative Camera Pose Representation.
    Represents T_world_camera (Camera-to-World transform in meters).
    P_world = R_world_camera @ P_camera + t_world_camera
    """

    def __init__(
        self,
        R_world_camera: np.ndarray,
        t_world_camera: np.ndarray,
        convention: CameraConvention = CameraConvention.ARKIT_RUB
    ):
        R = np.asarray(R_world_camera, dtype=np.float64)
        t = np.asarray(t_world_camera, dtype=np.float64).flatten()

        if R.shape != (3, 3):
            raise ValueError(f"Expected 3x3 rotation matrix, got shape {R.shape}")
        if t.shape != (3,):
            raise ValueError(f"Expected 3-element translation, got shape {t.shape}")

        if not np.all(np.isfinite(R)) or not np.all(np.isfinite(t)):
            raise ValueError("Pose must contain finite rotation and translation")
        if not np.allclose(R.T @ R, np.eye(3), atol=1e-4, rtol=0):
            raise ValueError("Rotation must be orthonormal")
        # Check rotation matrix validity
        det = np.linalg.det(R)
        if not np.isclose(det, 1.0, atol=1e-3):
            raise ValueError(f"Invalid rotation matrix determinant: {det:.4f}")

        self.R = R
        self.t = t
        self.convention = CameraConvention(convention)

    @property
    def T_4x4(self) -> np.ndarray:
        """4x4 Homogeneous transformation matrix (Camera to World)."""
        T = np.eye(4, dtype=np.float64)
        T[:3, :3] = self.R
        T[:3, 3] = self.t
        return T

    @property
    def quaternion(self) -> np.ndarray:
        """Rotation unit quaternion [qx, qy, qz, qw]."""
        return rotation_matrix_to_quaternion(self.R)

    @classmethod
    def from_4x4(
        cls,
        T: np.ndarray,
        convention: CameraConvention = CameraConvention.ARKIT_RUB
    ) -> "CameraPose":
        T = np.asarray(T, dtype=np.float64)
        if T.shape != (4, 4):
            raise ValueError(f"Expected 4x4 matrix, got shape {T.shape}")
        if not np.all(np.isfinite(T)) or not np.allclose(T[3], [0, 0, 0, 1], atol=1e-6, rtol=0):
            raise ValueError("Expected finite homogeneous transform with bottom row [0,0,0,1]")
        return cls(
            R_world_camera=T[:3, :3],
            t_world_camera=T[:3, 3],
            convention=convention
        )

    @classmethod
    def from_quaternion_translation(
        cls,
        q: Union[List[float], np.ndarray],
        t: Union[List[float], np.ndarray],
        convention: CameraConvention = CameraConvention.ARKIT_RUB
    ) -> "CameraPose":
        R = quaternion_to_rotation_matrix(q)
        return cls(R_world_camera=R, t_world_camera=np.asarray(t, dtype=np.float64), convention=convention)

    def world_to_camera_transform(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes World-to-Camera extrinsics (R_cw, t_cw):
        P_camera = R_cw @ P_world + t_cw
        Where R_cw = R^T, t_cw = -R^T @ t
        """
        R_cw = self.R.T
        t_cw = -R_cw @ self.t
        return R_cw, t_cw

    @property
    def T_cw_4x4(self) -> np.ndarray:
        """4x4 Homogeneous transformation matrix (World to Camera)."""
        R_cw, t_cw = self.world_to_camera_transform()
        T = np.eye(4, dtype=np.float64)
        T[:3, :3] = R_cw
        T[:3, 3] = t_cw
        return T

    @property
    def camera_center_world(self) -> np.ndarray:
        """3D camera optical center in world coordinates [X, Y, Z] (meters)."""
        return self.t.copy()

    @property
    def optical_axis_world(self) -> np.ndarray:
        """Unit vector of camera viewing direction in world coordinates."""
        if self.convention == CameraConvention.OPENCV_RDF:
            # OpenCV forward is +Z
            return self.R @ np.array([0.0, 0.0, 1.0])
        else:
            # ARKit / OpenGL forward is -Z
            return self.R @ np.array([0.0, 0.0, -1.0])

    def to_opencv(self) -> "CameraPose":
        """
        Converts camera pose to OpenCV convention (+Z forward, +X right, +Y down).
        If already in OpenCV convention, returns a copy.
        T_world_camera_cv = T_world_camera_arkit @ diag(1, -1, -1, 1)
        """
        if self.convention == CameraConvention.OPENCV_RDF:
            return CameraPose(self.R.copy(), self.t.copy(), CameraConvention.OPENCV_RDF)

        R_cv = self.R @ C_OPENCV_FROM_ARKIT
        return CameraPose(R_world_camera=R_cv, t_world_camera=self.t.copy(), convention=CameraConvention.OPENCV_RDF)

    def to_arkit(self) -> "CameraPose":
        """
        Converts camera pose to ARKit/OpenGL convention (-Z forward, +X right, +Y up).
        If already in ARKit convention, returns a copy.
        """
        if self.convention in (CameraConvention.ARKIT_RUB, CameraConvention.OPENGL_RUB):
            return CameraPose(self.R.copy(), self.t.copy(), CameraConvention.ARKIT_RUB)

        R_arkit = self.R @ C_ARKIT_FROM_OPENCV
        return CameraPose(R_world_camera=R_arkit, t_world_camera=self.t.copy(), convention=CameraConvention.ARKIT_RUB)

    def project_point(
        self,
        P_world: np.ndarray,
        intrinsics: CameraIntrinsics
    ) -> Tuple[np.ndarray, float]:
        """
        Projects a 3D point in world coordinates [X, Y, Z] into pixel coordinates (u, v) and depth Z_cam.
        Returns:
            Tuple[pixel_uv (2,), depth_z_cam (float)]
        """
        P_w = np.asarray(P_world, dtype=np.float64).flatten()
        if P_w.shape != (3,) or not np.all(np.isfinite(P_w)):
            raise ValueError(f"Expected 3D point, got shape {P_w.shape}")

        # Ensure camera is in OpenCV RDF frame for standard pinhole projection
        pose_cv = self.to_opencv()
        R_cw, t_cw = pose_cv.world_to_camera_transform()

        # Transform to OpenCV camera coordinates (+Z forward)
        P_cam = R_cw @ P_w + t_cw
        z_cam = P_cam[2]

        if z_cam <= 1e-4:
            raise ValueError(f"Point is behind or on the camera optical center (Z_cam={z_cam:.4f})")

        # Pinhole projection (accounting for radial/tangential distortion if present)
        if intrinsics.has_distortion:
            rvec, _ = cv2.Rodrigues(R_cw)
            tvec = t_cw.reshape(3, 1)
            pts_2d, _ = cv2.projectPoints(P_w.reshape(1, 3), rvec, tvec, intrinsics.K, intrinsics.distortion)
            u, v = float(pts_2d[0, 0, 0]), float(pts_2d[0, 0, 1])
            return np.array([u, v], dtype=np.float64), float(z_cam)
        else:
            p_hom = intrinsics.K @ (P_cam / z_cam)
            u, v = p_hom[0], p_hom[1]
            return np.array([u, v], dtype=np.float64), float(z_cam)

    def backproject_pixel(
        self,
        u: float,
        v: float,
        depth_m: float,
        intrinsics: CameraIntrinsics
    ) -> np.ndarray:
        """
        Back-projects a 2D image pixel (u, v) with known metric depth Z into 3D world coordinates.
        P_cam = Z * K^-1 @ [u, v, 1]^T (accounting for lens distortion)
        P_world = R_wc @ P_cam + t_wc
        """
        if not np.all(np.isfinite([u, v, depth_m])) or depth_m <= 0:
            raise ValueError(f"Depth must be positive, got {depth_m}")

        if intrinsics.has_distortion:
            undist = intrinsics.undistort_points(np.array([[u, v]], dtype=np.float64))[0]
            u_clean, v_clean = float(undist[0]), float(undist[1])
        else:
            u_clean, v_clean = float(u), float(v)

        pose_cv = self.to_opencv()
        p_hom = np.array([u_clean, v_clean, 1.0], dtype=np.float64)
        ray_cam = intrinsics.K_inv @ p_hom
        P_cam = ray_cam * depth_m

        P_world = pose_cv.R @ P_cam + pose_cv.t
        return P_world
