"""
VĀSTU Pre-Reconstruction Preflight Validator (P1 Pre-Reconstruction AI)
Evaluates capture suitability, motion parallax reliability, depth scale confidence,
and scene structure before reconstruction.
Blocks architectural-quality certification when camera motion baseline is degenerate.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger("vastu.preflight")


class PreflightReconstructionValidator:
    """
    Intelligent preflight analyzer that inspects raw video characteristics,
    feature flow dynamics, and parallax baseline before reconstruction.
    """
    def __init__(
        self,
        min_translation_baseline_m: float = 0.10,
        max_homography_inlier_ratio: float = 0.70,
        min_usable_frame_pct: float = 85.0
    ):
        self.min_translation_baseline_m = min_translation_baseline_m
        self.max_homography_inlier_ratio = max_homography_inlier_ratio
        self.min_usable_frame_pct = min_usable_frame_pct

    def evaluate_preflight(
        self,
        capture_report: Dict[str, Any],
        parallax_report: Dict[str, Any],
        calib_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes preflight audit. Determines optimal depth backend and TSDF configuration,
        or blocks architectural certification when physical translation is insufficient.
        """
        usable_pct = float(capture_report.get("usable_frame_pct", 100.0))
        baseline_m = parallax_report.get("total_baseline_displacement_m")
        h_ratio = float(parallax_report.get("mean_homography_inlier_ratio", 0.0))
        flow_px = float(parallax_report.get("mean_optical_flow_px", 0.0))

        # Check capture signal integrity
        capture_ok = usable_pct >= self.min_usable_frame_pct

        # Check motion parallax (differentiate lateral translation from stationary pivot)
        motion_ok = (parallax_report.get("parallax_gate_passed") is True
                     and parallax_report.get("verified_multi_view_geometry") is True
                     and parallax_report.get("scale_status") == "METRIC_ESTABLISHED")
        is_stationary_pivot = not motion_ok  # legacy diagnostic name; does not prove physical pivot

        # Determine optimal depth backend
        try:
            import transformers
            recommended_depth_backend = "DEPTH_ANYTHING_V2_METRIC"
        except ImportError:
            recommended_depth_backend = "NEURAL_METRIC_CALIBRATED"

        # Determine TSDF voxel resolution based on estimated scene volume
        voxel_length_m = 0.03
        sdf_trunc_m = 0.09

        can_proceed_architectural = capture_ok and motion_ok
        
        status = "APPROVED_ARCHITECTURAL" if can_proceed_architectural else (
            "NEEDS_RESCAN" if not motion_ok else "CAPTURE_QUALITY_LOW"
        )

        guidance = (
            "Preflight passed: Lateral translation baseline confirmed. Proceeding with TSDF volumetric reconstruction."
            if can_proceed_architectural else
            "PREFLIGHT BLOCK: Camera geometry or metric scale is unverified. "
            "Use smooth sliding (truck/dolly) lateral motion with overlapping sharp views, "
            "and record a validated independent metric reference. Inspect parallax_analysis.json; "
            "unreliable tracking cannot establish the physical motion."

        )

        decision = {
            "preflight_status": status,
            "can_certify_architectural": can_proceed_architectural,
            "recommended_depth_backend": recommended_depth_backend,
            "tsdf_configuration": {
                "voxel_length_m": voxel_length_m,
                "sdf_trunc_m": sdf_trunc_m,
                "depth_range_m": [0.35, 5.50]
            },
            "diagnostics": {
                "usable_frame_pct": usable_pct,
                "baseline_displacement_m": baseline_m,
                "homography_inlier_ratio": h_ratio,
                "mean_optical_flow_px": flow_px,
                "stationary_pivot_detected": is_stationary_pivot
            },
            "user_guidance": guidance
        }

        if not can_proceed_architectural:
            logger.warning(f"  [PREFLIGHT GATE] {status}: {guidance}")
        else:
            logger.info(f"  [PREFLIGHT GATE] {status}: Approved for architectural reconstruction.")

        return decision
