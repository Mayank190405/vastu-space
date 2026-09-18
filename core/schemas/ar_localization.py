"""
VĀSTU AR Localization Schemas (Stage 29)
Formal contracts for marker-based AR localization, spatial anchors,
device-to-model rigid transforms, route projection, and quantitative validation.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field


class MarkerType(str, Enum):
    """Supported fiducial spatial marker types."""
    ARUCO_4X4_50 = "aruco_4x4_50"
    ARUCO_6X6_250 = "aruco_6x6_250"
    APRILTAG_36H11 = "apriltag_36h11"
    QR_CODE = "qr_code"


class SpatialMarkerAnchor(BaseModel):
    """
    Known physical marker anchor pre-registered in the digital twin model frame.
    Coordinates are in canonical metric world space (+Z up, floor Z=0).
    """
    marker_id: int
    marker_type: MarkerType = MarkerType.ARUCO_4X4_50
    model_id: str
    physical_size_m: float = Field(default=0.20, gt=0.0, description="Side length of square marker in meters")
    position_model: List[float] = Field(min_length=3, max_length=3, description="[x, y, z] in digital twin model coordinates")
    orientation_quaternion_model: List[float] = Field(
        default=[0.0, 0.0, 0.0, 1.0],
        min_length=4,
        max_length=4,
        description="[qx, qy, qz, qw] unit quaternion in model frame"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    label: Optional[str] = None


class DetectedMarker(BaseModel):
    """Observed marker detection from an AR camera frame."""
    marker_id: int
    corners_2d: List[List[float]] = Field(..., min_length=4, max_length=4, description="4 corners in pixel space [[u, v], ...]")
    camera_t_marker: Optional[List[List[float]]] = Field(None, description="4x4 transform T_cam_marker if solved via PnP")
    reprojection_error_px: float = 0.0
    detection_confidence: float = 1.0


class ARCameraFrame(BaseModel):
    """Single AR device camera observation with sensor-tracked pose."""
    frame_id: str
    timestamp_ns: int
    intrinsics: List[List[float]] = Field(..., min_length=3, max_length=3, description="3x3 camera intrinsic matrix K")
    resolution: List[int] = Field(..., min_length=2, max_length=2, description="[width, height] in pixels")
    device_pose_ar: List[List[float]] = Field(..., min_length=4, max_length=4, description="4x4 transform T_AR_cam in AR tracking frame")
    detected_markers: List[DetectedMarker] = Field(default_factory=list)


class ARLocalizationRequest(BaseModel):
    """Request payload to localize an AR camera frame within a digital twin model."""
    model_id: str
    frame: ARCameraFrame


class ARLocalizationResult(BaseModel):
    """Result of AR localization aligning AR tracking frame to digital twin coordinates."""
    success: bool
    model_id: str
    model_t_ar: Optional[List[List[float]]] = Field(None, description="4x4 rigid transformation T_model_AR")
    device_pose_model: Optional[List[List[float]]] = Field(None, description="4x4 device camera pose T_model_device")
    device_position_model: Optional[List[float]] = Field(None, min_length=3, max_length=3)
    matched_marker_ids: List[int] = Field(default_factory=list)
    confidence: float = 0.0
    relocalization_time_ms: float = 0.0
    is_tracked_via_dead_reckoning: bool = False
    rejection_reason: Optional[str] = None


class ARRouteProjectionRequest(BaseModel):
    """Request payload to project 3D route waypoints onto the AR camera viewport."""
    model_id: str
    route_waypoints_model: List[List[float]] = Field(..., min_length=2, description="3D route points in model coordinates")
    model_t_ar: List[List[float]] = Field(..., min_length=4, max_length=4)
    device_pose_ar: List[List[float]] = Field(..., min_length=4, max_length=4)
    intrinsics: List[List[float]] = Field(..., min_length=3, max_length=3)
    resolution: List[int] = Field(..., min_length=2, max_length=2)


class ARProjectedWaypoint(BaseModel):
    """Single projected route waypoint."""
    waypoint_index: int
    position_model: List[float]
    position_cam: List[float]  # 3D position in camera space [x_c, y_c, z_c]
    pixel_2d: Optional[List[float]] = None  # [u, v] if in front of camera
    is_in_front_of_camera: bool
    distance_meters: float


class ARRouteProjectionResult(BaseModel):
    """Projected AR route with 3D camera-frame waypoints and 2D on-screen coordinates."""
    route_id: Optional[str] = None
    projected_waypoints: List[ARProjectedWaypoint] = Field(default_factory=list)
    visible_waypoint_count: int
    total_waypoint_count: int
    mean_reprojection_error_px: float = 0.0


class ARValidationMetrics(BaseModel):
    """Quantitative validation metrics measuring alignment accuracy."""
    translation_error_m: float
    rotation_error_deg: float
    relocalization_time_ms: float
    walking_stability_jitter_m: float
    route_alignment_error_px: float
    translation_bound_met: bool  # <= 0.050m (5.0cm)
    rotation_bound_met: bool  # <= 2.00 deg
    time_bound_met: bool  # <= 15.0 ms
    stability_bound_met: bool  # <= 0.010m (1.0cm)
    route_bound_met: bool  # <= 2.50 px
    acceptance_criterion_met: bool


class ARValidationReport(BaseModel):
    """Complete quantitative AR localization validation report."""
    benchmark_id: str
    timestamp: str
    metrics: ARValidationMetrics
    frame_count_evaluated: int
    markers_evaluated_count: int
    acceptance_criterion: str = "The AR coordinate system aligns with the digital twin within a measured error bound."
    acceptance_criterion_met: bool
    narrative: str
