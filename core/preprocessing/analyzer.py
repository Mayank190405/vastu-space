"""
VĀSTU Preprocessing: Frame Quality Analyzer
Extracts quantitative sharpness, exposure, feature distribution, and inter-frame delta metrics.
"""

import cv2
import numpy as np
from typing import Optional, Tuple
from core.schemas.preprocessing import FrameQualityMetrics


class FrameQualityAnalyzer:
    """
    Computes deterministic visual quality metrics on extracted video frames.
    """
    def __init__(
        self,
        blur_threshold: float = 60.0,
        dark_cutoff: int = 15,
        highlight_cutoff: int = 245,
        grid_rows: int = 4,
        grid_cols: int = 4
    ):
        self.blur_threshold = blur_threshold
        self.dark_cutoff = dark_cutoff
        self.highlight_cutoff = highlight_cutoff
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols

        # FAST detector for real-time corner/feature density estimation
        self.fast = cv2.FastFeatureDetector_create(threshold=20, nonmaxSuppression=True)

    def analyze(self, frame_bgr: np.ndarray, prev_gray: Optional[np.ndarray] = None) -> Tuple[FrameQualityMetrics, np.ndarray]:
        """
        Analyzes a single BGR frame. Returns computed metrics and the grayscale frame.
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # 1. Sharpness: Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = float(laplacian.var())

        # Tenengrad gradient energy (Sobel x & y squared)
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        tenengrad = float(np.mean(gx**2 + gy**2))

        # 2. Exposure analysis
        mean_lum = float(np.mean(gray))
        total_pixels = h * w
        dark_pixels = np.count_nonzero(gray < self.dark_cutoff)
        sat_pixels = np.count_nonzero(gray > self.highlight_cutoff)
        dark_ratio = float(dark_pixels / max(1, total_pixels))
        sat_ratio = float(sat_pixels / max(1, total_pixels))

        # 3. Feature density analysis using Shi-Tomasi corners
        corners = cv2.goodFeaturesToTrack(gray, maxCorners=600, qualityLevel=0.01, minDistance=6)
        keypoints_pts = [pt[0] for pt in corners] if corners is not None else []
        feat_count = len(keypoints_pts)

        # 4x4 spatial grid coverage
        cell_h = max(1, h // self.grid_rows)
        cell_w = max(1, w // self.grid_cols)
        occupied_cells = set()
        for pt in keypoints_pts:
            r = min(self.grid_rows - 1, int(pt[1] // cell_h))
            c = min(self.grid_cols - 1, int(pt[0] // cell_w))
            occupied_cells.add((r, c))

        grid_coverage = float(len(occupied_cells) / (self.grid_rows * self.grid_cols))

        # 4. Duplicate / visual delta from previous candidate
        if prev_gray is not None and prev_gray.shape == gray.shape:
            abs_diff = cv2.absdiff(gray, prev_gray)
            visual_delta = float(np.mean(abs_diff) / 255.0)
        else:
            visual_delta = 1.0  # Initial or unmatched frame

        metrics = FrameQualityMetrics(
            sharpness_score=sharpness,
            tenengrad_gradient_energy=tenengrad,
            mean_luminance=mean_lum,
            dark_ratio=dark_ratio,
            highlight_ratio=sat_ratio,
            feature_count=feat_count,
            spatial_grid_coverage=grid_coverage,
            visual_delta_prev=visual_delta
        )
        return metrics, gray
