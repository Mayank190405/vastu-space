"""
VĀSTU Preprocessing: Frame Validator & Hallucination Prevention
Enforces:
1. Symmetrical optical flow validation to reject warped or ghost frames.
2. Unrecoverable non-linear motion blur detection (no fake edge hallucination).
3. Rolling-shutter distortion risk gating from rotational telemetry.
4. Exposure histogram entropy gating (no noise amplification in deep shadows).
"""

import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional


class FrameValidator:
    """
    Validates physical fidelity of video frames and synthesized transitions.
    Guarantees corrupted or hallucinated image data never enters SfM or dense depth.
    """
    def __init__(
        self,
        max_flow_symmetry_error_px: float = 1.2,
        max_angular_velocity_rad_s: float = 0.785,  # 45 deg/sec rolling shutter threshold
        min_histogram_entropy: float = 3.5,
        min_recoverable_sharpness: float = 25.0
    ):
        self.max_flow_symmetry_error_px = max_flow_symmetry_error_px
        self.max_angular_velocity_rad_s = max_angular_velocity_rad_s
        self.min_histogram_entropy = min_histogram_entropy
        self.min_recoverable_sharpness = min_recoverable_sharpness

    def validate_optical_flow_symmetry(
        self,
        prev_gray: np.ndarray,
        curr_gray: np.ndarray
    ) -> Tuple[bool, float, str]:
        """
        Computes forward-backward optical flow consistency.
        Rejects artificial warping or duplicate ghost geometry.
        """
        if prev_gray is None or curr_gray is None:
            return True, 0.0, "INITIAL_FRAME"

        # Downsample for fast robust dense flow
        h, w = prev_gray.shape
        scale = min(1.0, 320.0 / max(h, w))
        small_prev = cv2.resize(prev_gray, (0, 0), fx=scale, fy=scale)
        small_curr = cv2.resize(curr_gray, (0, 0), fx=scale, fy=scale)

        # Forward flow: prev -> curr
        flow_fwd = cv2.calcOpticalFlowFarneback(
            small_prev, small_curr, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )

        # Backward flow: curr -> prev
        flow_bwd = cv2.calcOpticalFlowFarneback(
            small_curr, small_prev, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )

        # Symmetry check: flow_fwd + flow_bwd(at fwd target) should sum to zero vector
        sh, sw = small_prev.shape
        grid_y, grid_x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        mapped_x = np.clip(grid_x + flow_fwd[..., 0], 0, sw - 1)
        mapped_y = np.clip(grid_y + flow_fwd[..., 1], 0, sh - 1)

        # Remap backward flow to target points
        bwd_at_fwd_x = cv2.remap(flow_bwd[..., 0], mapped_x, mapped_y, cv2.INTER_LINEAR)
        bwd_at_fwd_y = cv2.remap(flow_bwd[..., 1], mapped_x, mapped_y, cv2.INTER_LINEAR)

        # Consistency error: norm of residual displacement
        residual_x = flow_fwd[..., 0] + bwd_at_fwd_x
        residual_y = flow_fwd[..., 1] + bwd_at_fwd_y
        error_map = np.sqrt(residual_x**2 + residual_y**2)
        mean_symmetry_error = float(np.mean(error_map) / scale)

        if mean_symmetry_error > self.max_flow_symmetry_error_px:
            return False, mean_symmetry_error, f"OPTICAL_FLOW_SYMMETRY_VIOLATION ({mean_symmetry_error:.2f}px)"

        return True, mean_symmetry_error, "SYMMETRY_VERIFIED"

    def detect_unrecoverable_motion_blur(
        self,
        frame_gray: np.ndarray,
        sharpness_score: float
    ) -> Tuple[bool, str]:
        """
        Determines whether motion blur contains genuine recoverable gradient signal
        or if deblurring would purely hallucinate artificial high-frequency edges.
        """
        if sharpness_score < self.min_recoverable_sharpness:
            return False, f"UNRECOVERABLE_MOTION_BLUR (Sharpness {sharpness_score:.1f} < {self.min_recoverable_sharpness})"

        # Frequency domain energy analysis (FFT)
        h, w = frame_gray.shape
        dft = np.fft.fft2(frame_gray)
        dft_shift = np.fft.fftshift(dft)
        magnitude_spectrum = 20 * np.log(np.abs(dft_shift) + 1e-6)

        # Energy in middle-to-high frequency bands
        cy, cx = h // 2, w // 2
        r_inner = min(h, w) // 8
        r_outer = min(h, w) // 4
        y_grid, x_grid = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x_grid - cx)**2 + (y_grid - cy)**2)
        band_mask = (dist_from_center >= r_inner) & (dist_from_center <= r_outer)

        band_energy = float(np.mean(magnitude_spectrum[band_mask]))
        if band_energy < 120.0 and sharpness_score < 45.0:
            return False, "DEFICIENT_HIGH_FREQUENCY_SIGNAL (High risk of edge hallucination)"

        return True, "RECOVERABLE_GRADIENTS"

    def evaluate_rolling_shutter_risk(
        self,
        gyro_yaw_rad_s: float,
        gyro_pitch_rad_s: float = 0.0
    ) -> Tuple[bool, float, str]:
        """
        Audits rolling-shutter curvature risk based on rotational velocity telemetry.
        """
        total_angular_vel = float(np.sqrt(gyro_yaw_rad_s**2 + gyro_pitch_rad_s**2))
        if total_angular_vel > self.max_angular_velocity_rad_s:
            deg_s = np.degrees(total_angular_vel)
            return False, total_angular_vel, f"ROLLING_SHUTTER_DISTORTION_RISK ({deg_s:.1f}°/s)"

        return True, total_angular_vel, "ANGULAR_MOTION_SAFE"

    def evaluate_histogram_entropy(
        self,
        frame_gray: np.ndarray
    ) -> Tuple[bool, float, str]:
        """
        Computes Shannon entropy of pixel intensity distribution.
        Prevents noise amplification when trying to recover deep, uninformative shadows.
        """
        hist, _ = np.histogram(frame_gray, bins=256, range=(0, 256), density=True)
        hist_nonzero = hist[hist > 0]
        entropy = float(-np.sum(hist_nonzero * np.log2(hist_nonzero)))

        if entropy < self.min_histogram_entropy:
            return False, entropy, f"LOW_ENTROPY_UNDEREXPOSURE ({entropy:.2f} < {self.min_histogram_entropy})"

        return True, entropy, "ENTROPY_ADEQUATE"
