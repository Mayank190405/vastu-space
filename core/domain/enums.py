"""
VĀSTU Core Domain Enums
Authoritative domain enumerations matching the canonical architecture.
"""

from enum import Enum

class JobStage(str, Enum):
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    SFM_TRACKING = "sfm_tracking"
    DEPTH_ESTIMATION = "depth_estimation"
    POINT_CLOUD = "point_cloud"
    MESHING = "meshing"
    TEXTURING = "texturing"
    SEMANTIC_SEGMENTATION = "semantic_segmentation"
    NAVMESH_GENERATION = "navmesh_generation"
    QUALITY_ASSURANCE = "quality_assurance"
    CELL_FUSION = "cell_fusion"
    COMPLETED = "completed"
    FAILED = "failed"

class QualityVerdict(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"

class QualityLevel(str, Enum):
    OPTIMAL = "QUALITY: OPTIMAL"
    MOTION_BLUR = "WARNING: MOTION BLUR DETECTED"
    LOW_FEATURE_DENSITY = "GUIDANCE: FEATURE POOR AREA"
    INSUFFICIENT_OVERLAP = "WARNING: INSUFFICIENT OVERLAP"
    LOW_LIGHT = "WARNING: LOW LIGHT"
    RESCAN_REQUIRED = "RESCAN RECOMMENDED"

class POICategory(str, Enum):
    GENERAL = "GENERAL"
    UTILITY = "UTILITY"
    SAFETY = "SAFETY"
    NAVIGATION = "NAVIGATION"
    ASSET = "ASSET"
    STRUCTURAL = "STRUCTURAL"
    HAZARD = "HAZARD"

class PlaneType(str, Enum):
    WALL = "WALL"
    FLOOR = "FLOOR"
    CEILING = "CEILING"
    OPENING = "OPENING"
    FEATURE = "FEATURE"

class NavEdgeType(str, Enum):
    CORRIDOR = "CORRIDOR"
    DOORWAY = "DOORWAY"
    STAIRS = "STAIRS"
    ELEVATOR = "ELEVATOR"
    RAMP = "RAMP"
    OPEN_SPACE = "OPEN_SPACE"

class UploadStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    ABORTED = "aborted"
    EXPIRED = "expired"

class WorkerStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    FAILED = "FAILED"

class ModelFormat(str, Enum):
    GLTF = "glTF_2.0"
    GLB = "GLB"
    OBJ = "OBJ"
    PLY = "PLY"
    GAUSSIAN_SPLAT = "3DGS_PLY"

class CoordinateSystem(str, Enum):
    OPENCV_RDF = "RDF_RIGHT_DOWN_FORWARD"
    OPENGL_RUB = "RUB_RIGHT_UP_BACK"
    ROS_FLU = "FLU_FORWARD_LEFT_UP"

class ScaleSource(str, Enum):
    LIDAR_SPARSE = "lidar_sparse"
    IMU_VBA = "imu_vba"
    ARUCO_MARKER = "aruco_marker"
    MANUAL_METRIC = "manual_metric"
    UNSCALED = "unscaled"

class CaptureUploadStatus(str, Enum):
    PENDING = "PENDING"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"

class CameraDistortionModel(str, Enum):
    PINHOLE = "pinhole"
    RADTAN = "radtan"
    BROWN_CONRADY = "brown_conrady"
    FISHEYE = "fisheye"

class CalibrationType(str, Enum):
    FACTORY = "factory"
    RUNTIME_AR = "runtime_ar"
    MANUAL_CHESSBOARD = "manual_chessboard"
    UNVERIFIED = "unverified"

