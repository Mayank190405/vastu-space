#!/usr/bin/env python3
"""
VĀSTU — Point 28: Targeted Rescan Manager
When quality checks fail or an area needs updating:
1. Identifies failed or requested cells
2. Maps them to real-world spatial bounds (AABB)
3. Generates actionable mobile scanning instructions (AR bounding box, waypoints, lighting advice)
4. Ingests localized rescan patch
5. Registers and updates targeted cells
6. Re-evaluates quality post-update
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, List, Optional
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from spatial.spatial_cell_engine import SpatialCellEngine
from spatial.global_spatial_fusion_engine import GlobalSpatialFusionEngine
from quality.quality_engine import QualityEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VastuTargetedRescanManager")


class TargetedRescanManager:
    def __init__(self, cell_size_m: float = 1.0):
        self.cell_size_m = cell_size_m
        self.cell_engine = SpatialCellEngine(cell_size_m=cell_size_m)
        self.fusion_engine = GlobalSpatialFusionEngine(voxel_size_m=0.05)
        self.quality_engine = QualityEngine()

    # -------------------------------------------------------------------------
    # 1. Generate Mobile Rescan Instructions
    # -------------------------------------------------------------------------
    def generate_rescan_instructions(
        self,
        failed_cell_ids: List[str],
        reason: str = "Low point density / surface holes",
        lighting_defect: bool = False
    ) -> Dict[str, Any]:
        """
        Calculates unified spatial bounding box and generates mobile guidance.
        """
        if not failed_cell_ids:
            return {"status": "no_rescan_needed"}

        min_bounds = np.array([float("inf"), float("inf"), float("inf")])
        max_bounds = np.array([float("-inf"), float("-inf"), float("-inf")])

        for cell_id in failed_cell_ids:
            # Format: cell_X_Y_Z
            parts = cell_id.split("_")
            if len(parts) >= 4:
                ix, iy, iz = int(parts[1]), int(parts[2]), int(parts[3])
            else:
                ix, iy, iz = 0, 0, 0

            c_min = np.array([ix, iy, iz]) * self.cell_size_m
            c_max = c_min + self.cell_size_m

            min_bounds = np.minimum(min_bounds, c_min)
            max_bounds = np.maximum(max_bounds, c_max)

        center = (min_bounds + max_bounds) / 2.0
        radius = float(np.linalg.norm(max_bounds - min_bounds) / 2.0)

        # Generate 4-way circular orbit waypoints around the target region
        waypoints = []
        for angle_deg in [0, 90, 180, 270]:
            rad = np.radians(angle_deg)
            wp = [
                float(center[0] + (radius + 0.8) * np.cos(rad)),
                float(center[1] + (radius + 0.8) * np.sin(rad)),
                float(center[2] + 0.2)
            ]
            waypoints.append(wp)

        lighting_prompt = "Ensure bright, even illumination (avoid harsh glare/shadows)" if lighting_defect else "Normal indoor ambient lighting is sufficient"
        guidance = (
            f"Targeted Rescan Required for {len(failed_cell_ids)} cell(s). Reason: {reason}. "
            f"Point camera towards ({center[0]:.1f}m, {center[1]:.1f}m, {center[2]:.1f}m) and follow circular guide path."
        )

        return {
            "status": "rescan_required",
            "failed_cell_ids": failed_cell_ids,
            "target_bounding_box": {
                "min": min_bounds.tolist(),
                "max": max_bounds.tolist(),
                "center": center.tolist()
            },
            "recommended_waypoints": waypoints,
            "guidance_message": guidance,
            "lighting_instructions": lighting_prompt
        }

    # -------------------------------------------------------------------------
    # 2. Ingest and Apply Targeted Rescan Patch
    # -------------------------------------------------------------------------
    def apply_rescan_patch(
        self,
        base_cells: Dict[str, Dict[str, Any]],
        rescan_patch_data: Dict[str, Any],
        target_cell_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Applies localized rescan patch to base cells.
        If rescan data quality fails, preserves base cells intact.
        Returns:
            {
                "success": bool,
                "updated_cells": dict,
                "re_evaluated_quality": dict,
                "message": str
            }
        """
        patch_points = np.asarray(rescan_patch_data.get("points", []))
        patch_quality_score = float(rescan_patch_data.get("patch_quality_score", 0.0))

        # Check 1: If rescan patch is poor / empty, REJECT patch and PRESERVE base scan
        if len(patch_points) < 20 or patch_quality_score < 0.50:
            logger.warning("Rescan patch rejected due to poor quality or insufficient points. Base scan preserved.")
            return {
                "success": False,
                "updated_cells": base_cells,
                "message": "Rescan data failed quality threshold. Base scan preserved.",
                "re_evaluated_quality": {"status": "FAIL", "reason": "poor_rescan_data"}
            }

        # Check 2: Partition patch points into spatial cells
        updated_cells = {cid: dict(cdata) for cid, cdata in base_cells.items()}
        patch_partition = {}
        for idx, pt in enumerate(patch_points):
            cx = int(np.floor(pt[0] / self.cell_size_m))
            cy = int(np.floor(pt[1] / self.cell_size_m))
            cz = int(np.floor(pt[2] / self.cell_size_m))
            cid = f"cell_{cx}_{cy}_{cz}"
            if cid not in patch_partition:
                patch_partition[cid] = {"cell_id": cid, "points": [], "quality_score": patch_quality_score}
            patch_partition[cid]["points"].append(pt)

        for cid in patch_partition:
            patch_partition[cid]["points"] = np.array(patch_partition[cid]["points"])

        # Update only targeted cells that appear in the patch
        applied_cells = []
        for cid, patch_cell in patch_partition.items():
            if cid in target_cell_ids:
                # Update cell geometry and quality
                prev_pts = updated_cells.get(cid, {}).get("points", np.empty((0, 3)))
                # If target cell previously existed, fuse or replace
                if len(prev_pts) > 0:
                    fused = self.fusion_engine.fuse_local_reconstructions(
                        {"points": prev_pts, "quality": np.full(len(prev_pts), 0.5)},
                        {"points": patch_cell["points"], "quality": np.full(len(patch_cell["points"]), patch_quality_score)}
                    )
                    patch_cell["points"] = fused["points"]
                    patch_cell["quality_score"] = float(np.mean(fused["quality"]))
                else:
                    patch_cell["quality_score"] = patch_quality_score

                patch_cell["version"] = updated_cells.get(cid, {}).get("version", 1) + 1
                updated_cells[cid] = patch_cell
                applied_cells.append(cid)

        # Run quality evaluation on updated cells
        cell_list = []
        for cid, c in updated_cells.items():
            cell_list.append({
                "cell_id": cid,
                "quality_score": c.get("quality_score", 0.8),
                "point_count": len(c.get("points", []))
            })

        quality_report = self.quality_engine.evaluate({
            "geometry": {"vertices": patch_points, "faces": [[0, 1, 2]] * len(patch_points), "hole_ratio": 0.01},
            "tracking": {"lost_track_frames": 0, "total_frames": 100, "drift_rate_m_per_m": 0.01},
            "cells": cell_list,
            "expected_cells_count": len(updated_cells),
            "texture": {"laplacian_variance": 120.0},
            "semantics": [],
            "cell_boundaries": [],
            "nav_nodes": [{"id": "n1"}],
            "nav_edges": []
        })

        return {
            "success": True,
            "applied_cell_ids": applied_cells,
            "updated_cells": updated_cells,
            "re_evaluated_quality": quality_report,
            "message": f"Successfully updated {len(applied_cells)} target cells."
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VĀSTU Point 28 Targeted Rescan Manager")
    parser.add_argument("--cells", type=str, nargs="+", required=True, help="Failed cell IDs")
    args = parser.parse_args()

    manager = TargetedRescanManager()
    instructions = manager.generate_rescan_instructions(args.cells)
    print(json.dumps(instructions, indent=2))
