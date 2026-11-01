"""
VĀSTU SPZ Optimization Pipeline (Phase 9)
Generates optimized multi-tier SPZ Gaussian Splat packages:
- Desktop Tier: Full fidelity radiance field (60 FPS reference target)
- Mobile Browser Tier: Level-of-Detail (LOD) subsampled and pruned (30 FPS reference target, < 15MB payload)
"""

import os
import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np

from core.reconstruction.spz_exporter import SPZExporter

logger = logging.getLogger("vastu.reconstruction.spz_optimization_pipeline")


class SPZOptimizationPipeline:
    """
    Produces desktop and mobile-optimized compressed SPZ containers for progressive web streaming.
    """

    def __init__(self, spz_exporter: Optional[SPZExporter] = None):
        self.exporter = spz_exporter or SPZExporter()

    def build_multi_tier_spz(
        self,
        gaussians: Dict[str, Any],
        output_dir: str,
        asset_prefix: str = "splats"
    ) -> Dict[str, Any]:
        """
        Creates both desktop (full) and mobile (LOD) SPZ assets.
        
        Args:
            gaussians: Dict containing 'positions', 'scales', 'rotations', 'opacities', 'sh_dc'.
            output_dir: Destination folder.
            asset_prefix: Prefix filename.
            
        Returns:
            Dict containing desktop and mobile asset metadata, compression stats, and filepaths.
        """
        os.makedirs(output_dir, exist_ok=True)
        desktop_path = os.path.join(output_dir, f"{asset_prefix}_desktop.spz")
        mobile_path = os.path.join(output_dir, f"{asset_prefix}_mobile.spz")

        # 1. Desktop Tier: Full resolution export
        desktop_res = self.exporter.export_spz(gaussians, desktop_path)

        # 2. Mobile Tier: Decimate points by 50% based on opacity importance
        n_points = len(gaussians["positions"])
        if n_points > 1000:
            # Keep top 50% highest opacity splats
            opacities = gaussians["opacities"].flatten()
            importance_idx = np.argsort(opacities)[::-1][:n_points // 2]

            mobile_gaussians = {
                "positions": gaussians["positions"][importance_idx],
                "scales": gaussians["scales"][importance_idx],
                "rotations": gaussians["rotations"][importance_idx],
                "opacities": gaussians["opacities"][importance_idx],
                "sh_dc": gaussians["sh_dc"][importance_idx]
            }
        else:
            mobile_gaussians = gaussians

        mobile_res = self.exporter.export_spz(mobile_gaussians, mobile_path)

        logger.info(
            f"Multi-tier SPZ generated: Desktop ({desktop_res['compressed_bytes']}B), Mobile ({mobile_res['compressed_bytes']}B)"
        )

        return {
            "desktop_tier": {
                "path": desktop_path,
                "splat_count": desktop_res["splat_count"],
                "file_size_bytes": desktop_res["compressed_bytes"],
                "target_fps": 60
            },
            "mobile_tier": {
                "path": mobile_path,
                "splat_count": mobile_res["splat_count"],
                "file_size_bytes": mobile_res["compressed_bytes"],
                "target_fps": 30
            },
            "size_reduction_ratio": round(
                (desktop_res["compressed_bytes"] - mobile_res["compressed_bytes"]) / max(desktop_res["compressed_bytes"], 1),
                3
            )
        }
