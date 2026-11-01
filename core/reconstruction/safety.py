"""Reusable reconstruction policy. Thresholds are acceptance criteria, not accuracy claims."""
from dataclasses import dataclass
import math


class ReconstructionSafetyError(RuntimeError):
    """Input evidence does not support safe reconstruction."""


@dataclass(frozen=True)
class ReconstructionPolicy:
    max_scene_depth_m: float = 20.0
    min_tracking_inliers: int = 30
    min_tracking_inlier_ratio: float = 0.4
    max_pair_translation_m: float = 1.0
    min_view_support: int = 2
    max_depth_disagreement_m: float = 0.05
    min_pair_overlap: float = 0.5
    min_parallax_residual_px: float = 1.5

    def __post_init__(self):
        for key, value in self.__dict__.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{key} must be a finite positive number')
        for key in ('min_tracking_inliers', 'min_view_support'):
            if not isinstance(getattr(self, key), int):
                raise ValueError(f'{key} must be an integer')
        if self.min_tracking_inliers < 6 or self.min_view_support < 2:
            raise ValueError('At least 6 tracking inliers and 2 supporting views are required')
        if self.min_tracking_inlier_ratio > 1 or self.min_pair_overlap > 1:
            raise ValueError('Ratios must be at most 1')

    def check_tracking(self, valid, inliers, ratio, translation):
        if (not valid or inliers < self.min_tracking_inliers or
                not math.isfinite(ratio) or ratio < self.min_tracking_inlier_ratio or
                not math.isfinite(translation) or translation > self.max_pair_translation_m):
            raise ReconstructionSafetyError(
                f'Camera tracking rejected: inliers={inliers}, ratio={ratio}, translation={translation}. '
                'Improve overlap or calibration; no repeated-pose fallback is permitted.')

