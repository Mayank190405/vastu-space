"""
VĀSTU Post-Reconstruction AI Supervisor (P2 Post-Reconstruction AI)
Evaluates reconstructed 3D mesh geometry, surface plane residuals, floor/ceiling flatness,
mesh topology, and dimensional fidelity.
Directs targeted remediation actions and retries across engines when quality falls below threshold.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger("vastu.supervisor")


class PostReconstructionSupervisor:
    """
    Intelligent post-reconstruction evaluator measuring physical wall-plane residuals,
    floor/ceiling flatness, mesh topology, and generating targeted engine corrections.
    """
    def __init__(
        self,
        max_wall_plane_residual_m: float = 0.08,     # 8cm max acceptable wall residual for architectural pass
        max_floor_residual_m: float = 0.05,          # 5cm max floor residual
        max_self_intersecting_faces: int = 25
    ):
        self.max_wall_plane_residual_m = max_wall_plane_residual_m
        self.max_floor_residual_m = max_floor_residual_m
        self.max_self_intersecting_faces = max_self_intersecting_faces

    def audit_reconstruction(
        self,
        mesh: Any,
        pcd_pts: np.ndarray,
        planes_data: Dict[str, Any],
        backend_manifest: Dict[str, Any],
        parallax_report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes comprehensive post-reconstruction audit on the complete untextured mesh.
        Computes plane-fitting residuals and recommends targeted engine corrections.
        """
        verts = np.asarray(mesh.vertices)
        tris = np.asarray(mesh.triangles)

        # 1. Topology Metrics (Calculated on complete mesh)
        # Note: Open3D allow_boundary_edges=True returns only edges with > 2 incident faces (strict non-manifold pinch edges).
        # Open3D allow_boundary_edges=False returns all edges with != 2 incident faces (including 1-incident open boundary edges).
        strict_non_manifold_e = len(mesh.get_non_manifold_edges(allow_boundary_edges=True))
        all_non_manifold_including_boundary = len(mesh.get_non_manifold_edges(allow_boundary_edges=False))
        boundary_e = max(0, all_non_manifold_including_boundary - strict_non_manifold_e)
        self_intersect = len(mesh.get_self_intersecting_triangles())

        # 2. Floor Plane Residual
        y_vals = verts[:, 1]
        y_p10 = np.percentile(y_vals, 10)
        floor_pts = verts[y_vals <= (y_p10 + 0.15)]
        y_floor = float(np.median(floor_pts[:, 1])) if len(floor_pts) > 0 else 0.0
        floor_residuals = np.abs(floor_pts[:, 1] - y_floor) if len(floor_pts) > 0 else np.array([0.0])
        floor_rms = float(np.sqrt(np.mean(floor_residuals ** 2)))

        # 3. Ceiling Plane Residual
        y_p90 = np.percentile(y_vals, 90)
        ceil_pts = verts[y_vals >= (y_p90 - 0.20)]
        y_ceil = float(np.median(ceil_pts[:, 1])) if len(ceil_pts) > 0 else 2.40
        ceil_residuals = np.abs(ceil_pts[:, 1] - y_ceil) if len(ceil_pts) > 0 else np.array([0.0])
        ceil_rms = float(np.sqrt(np.mean(ceil_residuals ** 2)))

        # 4. Vertical Wall Plane Residuals
        mesh.compute_triangle_normals()
        tri_norms = np.asarray(mesh.triangle_normals)
        vert_tris = np.abs(tri_norms[:, 1]) < 0.25
        wall_residuals_list = []

        if np.sum(vert_tris) > 50:
            v_normals = tri_norms[vert_tris]
            angles = np.arctan2(v_normals[:, 2], v_normals[:, 0])
            hist, bin_edges = np.histogram(angles, bins=18, range=(-np.pi, np.pi))
            peak_indices = np.where(hist >= max(10, int(0.08 * len(angles))))[0]

            for p_idx in peak_indices:
                angle = 0.5 * (bin_edges[p_idx] + bin_edges[p_idx + 1])
                n = np.array([np.cos(angle), 0.0, np.sin(angle)])
                in_bin = np.abs(angles - angle) < (bin_edges[1] - bin_edges[0])
                v_idx = np.unique(tris[np.where(vert_tris)[0][in_bin]])
                projs = np.dot(verts[v_idx], n)
                d_wall = np.median(projs)
                res = np.abs(projs - d_wall)
                wall_residuals_list.append({
                    "wall_angle_deg": round(float(np.degrees(angle)), 1),
                    "support_vertices": len(v_idx),
                    "mean_residual_m": round(float(np.mean(res)), 4),
                    "rms_residual_m": round(float(np.sqrt(np.mean(res ** 2))), 4)
                })

        overall_wall_rms = float(np.mean([w["rms_residual_m"] for w in wall_residuals_list])) if wall_residuals_list else 0.25

        # 5. Targeted Diagnostics & Engine Correction Recommendations
        defects = []
        corrections = []

        if overall_wall_rms > self.max_wall_plane_residual_m:
            defects.append(f"HIGH_WALL_PLANE_RESIDUALS ({overall_wall_rms*100:.1f}cm > {self.max_wall_plane_residual_m*100:.1f}cm)")
            if parallax_report.get("parallax_gate_passed", False):
                corrections.append({
                    "target_engine": "ml.depth.estimator",
                    "action": "UPGRADE_DEPTH_BACKEND_TO_DEPTH_ANYTHING_V2_METRIC",
                    "reason": "MiDaS relative depth field causes radial barrel wall curvature; upgrade to true metric depth network."
                })
            else:
                corrections.append({
                    "target_engine": "mobile_capture",
                    "action": "TARGETED_RECAPTURE_WITH_LATERAL_TRANSLATION",
                    "reason": f"Baseline displacement {parallax_report.get('total_baseline_displacement_m', 0):.3f}m < 0.10m. Epipolar triangulation is degenerate."
                })

        if floor_rms > self.max_floor_residual_m:
            defects.append(f"UNEVEN_FLOOR_SURFACE ({floor_rms*100:.1f}cm > {self.max_floor_residual_m*100:.1f}cm)")
            corrections.append({
                "target_engine": "core.dense.tsdf_fusion",
                "action": "APPLY_CONTINUOUS_GROUNDING_REGULARIZATION",
                "reason": "Floor surface exceeds 5cm RMS deviation from horizontal ground datum."
            })

        if self_intersect > self.max_self_intersecting_faces:
            defects.append(f"FOLDED_TRIANGLES_DETECTED ({self_intersect} faces > {self.max_self_intersecting_faces})")
            corrections.append({
                "target_engine": "core.dense.tsdf_fusion",
                "action": "TRIGGER_TOPOLOGICAL_MANIFOLD_ROLLBACK",
                "reason": "Aggressive vertex shifts caused self-intersecting faces."
            })

        # Calculate architectural quality score
        topology_score = max(0.0, 1.0 - (self_intersect / 100.0) - (strict_non_manifold_e / 200.0))
        geometry_flatness_score = max(0.0, 1.0 - (overall_wall_rms / 0.40))
        floor_score = max(0.0, 1.0 - (floor_rms / 0.20))
        
        architectural_score = round(float(np.mean([topology_score, geometry_flatness_score, floor_score])), 3)
        architectural_pass = (
            len(defects) == 0 and
            self_intersect <= self.max_self_intersecting_faces and
            overall_wall_rms <= self.max_wall_plane_residual_m
        )

        audit_report = {
            "architectural_quality_score": architectural_score,
            "architectural_status": "PASS" if architectural_pass else "FAIL",
            "diagnosed_defects": defects,
            "targeted_engine_corrections": corrections,
            "metrics": {
                "floor_rms_residual_m": round(floor_rms, 4),
                "ceiling_rms_residual_m": round(ceil_rms, 4),
                "overall_wall_rms_residual_m": round(overall_wall_rms, 4),
                "individual_walls": wall_residuals_list,
                "topology": {
                    "vertex_count": len(verts),
                    "triangle_count": len(tris),
                    "self_intersecting_triangles": self_intersect,
                    "strict_non_manifold_edges": strict_non_manifold_e,
                    "boundary_edges": boundary_e
                }
            }
        }
        return audit_report
