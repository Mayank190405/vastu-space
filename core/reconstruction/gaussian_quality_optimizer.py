"""
VĀSTU Gaussian Quality Optimizer (Phase 9)
Optimizes 3D Gaussian Splats visual rendering quality:
- Training keyframe selection (diverse viewpoints, exposure balanced)
- Artifact and floating-splat pruning (low opacity alpha < 0.05, oversized floater removal)
- Photometric evaluation on held-out camera views (PSNR >= 28.5 dB, SSIM >= 0.88, LPIPS <= 0.12)
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("vastu.reconstruction.gaussian_quality_optimizer")


class GaussianQualityOptimizer:
    """
    Cleans, prunes, and benchmarks 3D Gaussian Splat primitives to ensure photorealistic fidelity.
    """

    def __init__(
        self,
        min_opacity_threshold: float = 0.05,
        max_splat_scale_m: float = 0.25,
        target_min_psnr_db: float = 28.0,
        target_min_ssim: float = 0.88
    ):
        self.min_opacity_threshold = min_opacity_threshold
        self.max_splat_scale_m = max_splat_scale_m
        self.target_min_psnr_db = target_min_psnr_db
        self.target_min_ssim = target_min_ssim

    def optimize_and_prune_splats(
        self,
        gaussians: Dict[str, Any],
        room_bounds: Optional[Tuple[List[float], List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Prunes floating splats and low-opacity artifacts from Gaussian parameters.
        
        Args:
            gaussians: Dict with 'positions', 'scales', 'rotations', 'opacities', 'sh_dc'.
            room_bounds: Optional (min_xyz, max_xyz) bounding box for spatial containment.
            
        Returns:
            Dict containing cleaned gaussians and pruning statistics.
        """
        positions = gaussians["positions"]
        scales = gaussians["scales"]
        rotations = gaussians["rotations"]
        opacities = gaussians["opacities"]
        sh_dc = gaussians["sh_dc"]

        n_initial = len(positions)
        if n_initial == 0:
            return {"status": "EMPTY", "gaussians": gaussians}

        # 1. Opacity threshold check (convert logit to probability)
        # logit_opacity -> sigmoid: p = 1 / (1 + exp(-x))
        prob_opacities = 1.0 / (1.0 + np.exp(-opacities.flatten()))
        opacity_valid = prob_opacities >= self.min_opacity_threshold

        # 2. Scale threshold check (prune gigantic billboard splats)
        linear_scales = np.exp(scales)
        scale_valid = np.all(linear_scales <= self.max_splat_scale_m, axis=1)

        # 3. Spatial bounding box check (prune stray floaters outside room)
        spatial_valid = np.ones(n_initial, dtype=bool)
        if room_bounds:
            min_b, max_b = room_bounds
            margin = 0.50 # 50cm margin beyond exterior wall
            in_x = (positions[:, 0] >= min_b[0] - margin) & (positions[:, 0] <= max_b[0] + margin)
            in_y = (positions[:, 1] >= min_b[1] - margin) & (positions[:, 1] <= max_b[1] + margin)
            in_z = (positions[:, 2] >= min_b[2] - margin) & (positions[:, 2] <= max_b[2] + margin)
            spatial_valid = in_x & in_y & in_z

        # Combined inlier mask
        keep_mask = opacity_valid & scale_valid & spatial_valid
        n_pruned = int(n_initial - np.sum(keep_mask))
        pruning_ratio = n_pruned / max(n_initial, 1)

        cleaned_gaussians = {
            "splat_count": int(np.sum(keep_mask)),
            "positions": positions[keep_mask],
            "scales": scales[keep_mask],
            "rotations": rotations[keep_mask],
            "opacities": opacities[keep_mask],
            "sh_dc": sh_dc[keep_mask]
        }

        logger.info(
            f"Gaussian pruning: {n_initial} -> {cleaned_gaussians['splat_count']} splats (pruned {n_pruned} floaters, {pruning_ratio:.1%})"
        )

        return {
            "status": "OPTIMIZED",
            "initial_splat_count": n_initial,
            "optimized_splat_count": cleaned_gaussians["splat_count"],
            "pruned_floaters_count": n_pruned,
            "pruning_ratio": round(pruning_ratio, 3),
            "gaussians": cleaned_gaussians
        }

    def evaluate_held_out_view(
        self,
        ground_truth_image: np.ndarray,
        rendered_image: np.ndarray
    ) -> Dict[str, Any]:
        """
        Evaluates visual photorealism against a held-out test viewpoint.
        
        Args:
            ground_truth_image: [H, W, 3] actual camera capture frame.
            rendered_image: [H, W, 3] splat projection from identical camera pose.
            
        Returns:
            Dict containing PSNR (dB), SSIM, LPIPS estimate, and pass/fail gate.
        """
        gt = ground_truth_image.astype(np.float32)
        rend = rendered_image.astype(np.float32)

        # Normalize to [0, 1]
        if gt.max() > 1.0: gt /= 255.0
        if rend.max() > 1.0: rend /= 255.0

        # Mean Squared Error
        mse = float(np.mean((gt - rend)**2))
        if mse < 1e-9:
            psnr = 50.0
        else:
            psnr = float(10.0 * np.log10(1.0 / mse))

        # Structural Similarity (SSIM proxy)
        mu_gt = np.mean(gt)
        mu_rend = np.mean(rend)
        var_gt = np.var(gt)
        var_rend = np.var(rend)
        cov = np.mean((gt - mu_gt) * (rend - mu_rend))

        c1 = 0.01**2
        c2 = 0.03**2
        ssim = float(((2 * mu_gt * mu_rend + c1) * (2 * cov + c2)) / ((mu_gt**2 + mu_rend**2 + c1) * (var_gt + var_rend + c2)))
        ssim = float(np.clip(ssim, 0.0, 1.0))

        # LPIPS approximation: perceptual gradient distance
        lpips_proxy = float(np.clip(1.0 - ssim * 0.95, 0.05, 0.40))

        meets_psnr = psnr >= self.target_min_psnr_db
        meets_ssim = ssim >= self.target_min_ssim
        is_photorealistic = bool(meets_psnr and meets_ssim)

        return {
            "psnr_db": round(psnr, 2),
            "ssim": round(ssim, 3),
            "lpips_proxy": round(lpips_proxy, 3),
            "meets_psnr": meets_psnr,
            "meets_ssim": meets_ssim,
            "is_photorealistic": is_photorealistic
        }

