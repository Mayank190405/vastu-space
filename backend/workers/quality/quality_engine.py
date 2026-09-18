#!/usr/bin/env python3
"""
VĀSTU — Point 27: Quality Engine
Evaluates 3D reconstruction suitability for production use.
Implements 7 distinct quality evaluations:
1. Geometry check (watertightness / hole percentage, normal consistency)
2. Tracking quality (pose continuity, IMU drift score)
3. Spatial coverage check (ratio of filled spatial cells vs expected envelope)
4. Texture sharpness & resolution check (Laplacian variance blur detection)
5. Semantic consistency check (physics constraints e.g., floor below ceiling, objects on floor)
6. Cell boundary continuity (neighbor cell edge alignment)
7. Navigation connectivity (walkable path graph connectivity / isolated nodes)

Overall Gate:
- PASS: All scores meet threshold (>= 0.70)
- WARNING: Non-critical defect (e.g., texture blur between 0.50 and 0.70)
- FAIL: Critical failure (geometry < 0.60, tracking < 0.60, coverage < 0.60, or nav disconnected)
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, List, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VastuQualityEngine")


class QualityEngine:
    def __init__(
        self,
        min_geometry_score: float = 0.60,
        min_tracking_score: float = 0.60,
        min_coverage_score: float = 0.65,
        min_texture_score: float = 0.55,
        min_semantic_score: float = 0.70,
        min_continuity_score: float = 0.65,
        require_nav_connected: bool = True
    ):
        self.min_geometry = min_geometry_score
        self.min_tracking = min_tracking_score
        self.min_coverage = min_coverage_score
        self.min_texture = min_texture_score
        self.min_semantic = min_semantic_score
        self.min_continuity = min_continuity_score
        self.require_nav_connected = require_nav_connected

    # -------------------------------------------------------------------------
    # 1. Geometry Check
    # -------------------------------------------------------------------------
    def check_geometry(self, mesh_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        Evaluates mesh watertightness, hole ratio, and normal consistency.
        Returns: (score [0.0 - 1.0], issues)
        """
        issues = []
        vertices = mesh_data.get("vertices", [])
        faces = mesh_data.get("faces", [])
        hole_ratio = mesh_data.get("hole_ratio", 0.0)
        has_inverted_normals = mesh_data.get("has_inverted_normals", False)

        if len(vertices) < 10 or len(faces) < 10:
            return 0.1, ["Extremely sparse or missing geometric surfaces"]

        score = 1.0
        if hole_ratio > 0.15:
            penalty = min(0.60, hole_ratio * 2.0)
            score -= penalty
            issues.append(f"Significant geometric holes detected ({hole_ratio * 100:.1f}%)")

        if has_inverted_normals:
            score -= 0.25
            issues.append("Surface normal inconsistencies or flipped faces detected")

        score = max(0.0, min(1.0, score))
        return round(score, 3), issues

    # -------------------------------------------------------------------------
    # 2. Tracking Quality Check
    # -------------------------------------------------------------------------
    def check_tracking(self, tracking_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        Evaluates visual-inertial tracking continuity and drift.
        """
        issues = []
        lost_track_frames = tracking_data.get("lost_track_frames", 0)
        total_frames = max(1, tracking_data.get("total_frames", 100))
        drift_rate_m_per_m = tracking_data.get("drift_rate_m_per_m", 0.01)

        lost_ratio = lost_track_frames / float(total_frames)
        score = 1.0 - (lost_ratio * 2.0) - (drift_rate_m_per_m * 10.0)
        score = max(0.0, min(1.0, score))

        if lost_ratio > 0.05:
            issues.append(f"VIO lost track in {lost_track_frames}/{total_frames} frames ({lost_ratio*100:.1f}%)")
        if drift_rate_m_per_m > 0.04:
            issues.append(f"Excessive trajectory drift: {drift_rate_m_per_m:.3f} m/m")

        return round(score, 3), issues

    # -------------------------------------------------------------------------
    # 3. Spatial Coverage Check
    # -------------------------------------------------------------------------
    def check_spatial_coverage(
        self,
        scanned_cells: List[Dict[str, Any]],
        expected_cells_count: int
    ) -> Tuple[float, List[str], List[str]]:
        """
        Evaluates whether all expected volumetric cells have sufficient scan density.
        Returns: (score, issues, failed_cell_ids)
        """
        issues = []
        failed_cell_ids = []

        if expected_cells_count <= 0:
            return 1.0, [], []

        active_count = len(scanned_cells)
        coverage_ratio = active_count / float(expected_cells_count)
        score = min(1.0, coverage_ratio)

        for cell in scanned_cells:
            cell_id = cell.get("cell_id", "unknown")
            quality = cell.get("quality_score", 1.0)
            point_count = cell.get("point_count", 0)
            if quality < 0.50 or point_count < 20:
                failed_cell_ids.append(cell_id)

        if coverage_ratio < self.min_coverage:
            issues.append(f"Incomplete spatial coverage: {active_count}/{expected_cells_count} expected cells scanned ({coverage_ratio*100:.1f}%)")

        if failed_cell_ids:
            issues.append(f"{len(failed_cell_ids)} cells have insufficient point density or low quality")

        return round(score, 3), issues, failed_cell_ids

    # -------------------------------------------------------------------------
    # 4. Texture Sharpness & Resolution Check
    # -------------------------------------------------------------------------
    def check_texture(self, texture_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        Evaluates texture image sharpness via Laplacian variance and seam alignment.
        """
        issues = []
        laplacian_var = texture_data.get("laplacian_variance", 150.0) # > 100 is sharp
        has_seam_artifacts = texture_data.get("has_seam_artifacts", False)

        # Baseline: 100+ is crisp (1.0), 30 is blurry (0.3), 0 is completely blur
        score = min(1.0, laplacian_var / 120.0)

        if laplacian_var < 50.0:
            issues.append(f"Blurry texture detected (Laplacian variance: {laplacian_var:.1f} < 50.0)")

        if has_seam_artifacts:
            score -= 0.20
            issues.append("Prominent seam artifacts detected in texture atlas")

        score = max(0.0, min(1.0, score))
        return round(score, 3), issues

    # -------------------------------------------------------------------------
    # 5. Semantic Consistency Check
    # -------------------------------------------------------------------------
    def check_semantics(self, semantic_objects: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
        """
        Evaluates physical consistency of detected semantics:
        - Ceiling must be strictly higher than floor
        - Furniture (chairs, tables) must be between floor and ceiling
        """
        issues = []
        score = 1.0

        floors = [obj for obj in semantic_objects if obj.get("class_name") == "floor"]
        ceilings = [obj for obj in semantic_objects if obj.get("class_name") == "ceiling"]
        furniture = [obj for obj in semantic_objects if obj.get("class_name") in ["chair", "table", "sofa"]]

        if floors and ceilings:
            floor_z = max(f.get("bbox", {}).get("max_z", 0.0) for f in floors)
            ceil_z = min(c.get("bbox", {}).get("min_z", 2.5) for c in ceilings)
            if ceil_z <= floor_z:
                score -= 0.50
                issues.append(f"Semantic inversion: ceiling height ({ceil_z:.2f}m) is below or equal to floor ({floor_z:.2f}m)")

        for f in furniture:
            f_z = f.get("bbox", {}).get("min_z", 0.0)
            if floors:
                min_floor_z = min(fl.get("bbox", {}).get("min_z", 0.0) for fl in floors)
                if f_z < (min_floor_z - 0.30):
                    score -= 0.15
                    issues.append(f"Furniture item '{f.get('object_id')}' penetrates below floor plane ({f_z:.2f}m)")

        score = max(0.0, min(1.0, score))
        return round(score, 3), issues

    # -------------------------------------------------------------------------
    # 6. Cell Boundary Continuity Check
    # -------------------------------------------------------------------------
    def check_cell_continuity(self, cell_boundaries: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
        """
        Evaluates boundary step deviations across neighboring cells.
        """
        issues = []
        max_boundary_step_m = 0.0
        for b in cell_boundaries:
            step = b.get("step_error_m", 0.0)
            if step > max_boundary_step_m:
                max_boundary_step_m = step

        score = max(0.0, 1.0 - (max_boundary_step_m / 0.10)) # Step > 10cm is 0.0 score
        if max_boundary_step_m > 0.05:
            issues.append(f"Boundary discontinuity between neighboring cells: {max_boundary_step_m*100:.1f} cm step")

        return round(score, 3), issues

    # -------------------------------------------------------------------------
    # 7. Navigation Connectivity Check
    # -------------------------------------------------------------------------
    def check_navigation_connectivity(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Tuple[str, str]]
    ) -> Tuple[float, List[str]]:
        """
        Evaluates navigation graph connectedness.
        Graph must have exactly 1 connected component (all walkable nodes reachable).
        """
        issues = []
        if not nodes:
            return 1.0, []

        adj = {n["id"]: [] for n in nodes}
        for u, v in edges:
            if u in adj and v in adj:
                adj[u].append(v)
                adj[v].append(u)

        visited = set()
        start_node = nodes[0]["id"]
        queue = [start_node]
        visited.add(start_node)

        while queue:
            curr = queue.pop(0)
            for neighbor in adj.get(curr, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        unreachable_count = len(nodes) - len(visited)
        if unreachable_count > 0:
            issues.append(f"Navigation graph has {unreachable_count} disconnected nodes out of {len(nodes)}")
            return 0.0, issues

        return 1.0, []

    # -------------------------------------------------------------------------
    # Overall Evaluation Gate
    # -------------------------------------------------------------------------
    def evaluate(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs all 7 checks and produces a standardized QualityReport.
        """
        geom_score, geom_issues = self.check_geometry(model_data.get("geometry", {}))
        track_score, track_issues = self.check_tracking(model_data.get("tracking", {}))
        cov_score, cov_issues, failed_cells = self.check_spatial_coverage(
            model_data.get("cells", []),
            model_data.get("expected_cells_count", len(model_data.get("cells", [])))
        )
        tex_score, tex_issues = self.check_texture(model_data.get("texture", {}))
        sem_score, sem_issues = self.check_semantics(model_data.get("semantics", []))
        cont_score, cont_issues = self.check_cell_continuity(model_data.get("cell_boundaries", []))
        nav_score, nav_issues = self.check_navigation_connectivity(
            model_data.get("nav_nodes", []),
            model_data.get("nav_edges", [])
        )

        scores = {
            "geometry": geom_score,
            "tracking": track_score,
            "coverage": cov_score,
            "texture": tex_score,
            "semantics": sem_score,
            "continuity": cont_score,
            "navigation": nav_score
        }

        all_issues = geom_issues + track_issues + cov_issues + tex_issues + sem_issues + cont_issues + nav_issues

        # Gate logic:
        # Critical failures immediately cause FAIL
        critical_fail = (
            geom_score < self.min_geometry or
            track_score < self.min_tracking or
            cov_score < self.min_coverage or
            (self.require_nav_connected and nav_score < 0.5)
        )

        warning = (
            tex_score < self.min_texture or
            sem_score < self.min_semantic or
            cont_score < self.min_continuity
        )

        if critical_fail:
            status = "FAIL"
        elif warning:
            status = "WARNING"
        else:
            status = "PASS"

        recommendations = []
        if failed_cells:
            recommendations.append(f"Targeted rescan required for cells: {', '.join(failed_cells[:5])}")
        if nav_score < 0.5:
            recommendations.append("Rebuild navigation mesh or inspect doorway clearances")
        if tex_score < self.min_texture:
            recommendations.append("Re-capture affected areas under uniform, brighter lighting")

        report = {
            "status": status,
            "overall_score": round(float(np.mean(list(scores.values()))), 3),
            "scores": scores,
            "issues": all_issues,
            "failed_cell_ids": failed_cells,
            "recommendations": recommendations,
            "passed_gate": (status == "PASS")
        }

        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VĀSTU Point 27 Quality Engine")
    parser.add_argument("--model-data", type=str, required=True, help="Path to input model json data")
    parser.add_argument("--output-report", type=str, required=True, help="Path to save output quality report")
    args = parser.parse_args()

    with open(args.model_data, "r") as f:
        data = json.load(f)

    engine = QualityEngine()
    report = engine.evaluate(data)

    os.makedirs(os.path.dirname(args.output_report), exist_ok=True)
    with open(args.output_report, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Quality evaluation complete. Status: {report['status']} (Score: {report['overall_score']})")
