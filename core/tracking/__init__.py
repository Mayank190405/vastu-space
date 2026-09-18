"""
VĀSTU Camera Tracking & Pose Estimation Package
Hierarchical fusion of device AR/VIO, visual odometry, and SfM epipolar geometry,
with detection of tracking loss, insufficient parallax, disconnected trajectories, and loop closure drift.
"""

from core.tracking.tracker import VisualPoseTracker, VisualTrackingResult
from core.tracking.fusion import HierarchicalPoseEstimator

__all__ = [
    "VisualPoseTracker",
    "VisualTrackingResult",
    "HierarchicalPoseEstimator"
]
