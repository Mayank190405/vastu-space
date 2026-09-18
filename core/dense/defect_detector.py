"""
VĀSTU Dense Reconstruction: Defect Detector
Audits the dense 3D evidence point cloud for:
1. Holes (unpopulated expected surface regions)
2. Isolated regions (disconnected spatial clusters)
3. Floating geometry (statistical outlier points)
4. Excessive noise (high local planar roughness)
5. Inconsistent depth (geometric multi-view conflict)
"""

import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional
from core.dense.evidence_fusion import DenseEvidencePoint

logger = logging.getLogger("vastu.dense.defects")


class ReconstructionDefectDetector:
    """
    Quality and defect inspection engine for dense 3D evidence point clouds.
    """
    def __init__(
        self,
        min_cluster_size: int = 40,
        outlier_std_ratio: float = 2.5,
        max_noise_roughness: float = 0.08,
        inconsistency_warning_ratio: float = 0.20
    ):
        self.min_cluster_size = min_cluster_size
        self.outlier_std_ratio = outlier_std_ratio
        self.max_noise_roughness = max_noise_roughness
        self.inconsistency_warning_ratio = inconsistency_warning_ratio

    def audit_reconstruction(
        self,
        points: List[DenseEvidencePoint],
        consistency_stats: Dict[str, Any],
        camera_centers: Optional[List[np.ndarray]] = None
    ) -> Dict[str, Any]:
        """
        Executes comprehensive defect detection across the dense reconstruction dataset.
        """
        if not points:
            return {
                "total_points": 0,
                "defects_detected": {
                    "holes": {"count": 0, "regions": []},
                    "isolated_regions": {"count": 0, "clusters": []},
                    "floating_geometry": {"count": 0, "outlier_indices": []},
                    "excessive_noise": {"detected": False, "mean_roughness": 0.0},
                    "inconsistent_depth": {"detected": True, "ratio": 1.0}
                },
                "is_acceptable": False
            }

        coords = np.array([p.position for p in points])
        n_points = len(coords)

        # 1. Floating Geometry Detection (Statistical Outlier Filter)
        # Fast voxel-based neighbor count: points in voxels with very few neighbors
        voxel_size = 0.10  # 10cm voxel for neighbor support
        inv_v = 1.0 / voxel_size
        voxel_buckets: Dict[Tuple[int, int, int], List[int]] = {}
        for idx, pt in enumerate(coords):
            key = (
                int(np.floor(pt[0] * inv_v)),
                int(np.floor(pt[1] * inv_v)),
                int(np.floor(pt[2] * inv_v))
            )
            if key not in voxel_buckets:
                voxel_buckets[key] = []
            voxel_buckets[key].append(idx)

        neighbor_counts = np.zeros(n_points, dtype=int)
        for key, indices in voxel_buckets.items():
            # Sum neighbors in 27 adjacent cells
            count = 0
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        adj_key = (key[0] + dx, key[1] + dy, key[2] + dz)
                        count += len(voxel_buckets.get(adj_key, []))
            for idx in indices:
                neighbor_counts[idx] = count

        mean_neighbors = float(np.mean(neighbor_counts))
        std_neighbors = float(np.std(neighbor_counts))
        outlier_cutoff = max(2, mean_neighbors - self.outlier_std_ratio * std_neighbors)
        floating_indices = [int(i) for i in np.where(neighbor_counts < outlier_cutoff)[0]]

        # 2. Isolated Regions Detection (Connected Component Clustering on Voxels)
        visited_voxels = set()
        clusters: List[List[Tuple[int, int, int]]] = []

        for v_key in voxel_buckets.keys():
            if v_key in visited_voxels:
                continue
            # BFS for connected component
            cluster = []
            queue = [v_key]
            visited_voxels.add(v_key)

            while queue:
                curr = queue.pop(0)
                cluster.append(curr)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for dz in (-1, 0, 1):
                            neighbor_v = (curr[0] + dx, curr[1] + dy, curr[2] + dz)
                            if neighbor_v in voxel_buckets and neighbor_v not in visited_voxels:
                                visited_voxels.add(neighbor_v)
                                queue.append(neighbor_v)
            clusters.append(cluster)

        isolated_clusters = []
        for c in clusters:
            total_pts_in_cluster = sum(len(voxel_buckets[v]) for v in c)
            if total_pts_in_cluster < self.min_cluster_size:
                isolated_clusters.append({
                    "voxel_count": len(c),
                    "point_count": total_pts_in_cluster,
                    "center": (np.mean([np.array(v) * voxel_size for v in c], axis=0)).tolist()
                })

        # 3. Excessive Noise / Roughness
        # Sample small batches to estimate PCA normal deviation / plane variance
        sample_indices = np.random.choice(n_points, min(100, n_points), replace=False)
        roughness_scores = []
        for s_idx in sample_indices:
            pt = coords[s_idx]
            v_key = (
                int(np.floor(pt[0] * inv_v)),
                int(np.floor(pt[1] * inv_v)),
                int(np.floor(pt[2] * inv_v))
            )
            pts_local = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        pts_local.extend(voxel_buckets.get((v_key[0] + dx, v_key[1] + dy, v_key[2] + dz), []))
            if len(pts_local) >= 8:
                local_xyz = coords[pts_local]
                cov = np.cov(local_xyz.T)
                eigvals = np.sort(np.linalg.eigvalsh(cov))
                roughness = eigvals[0] / max(1e-7, np.sum(eigvals))
                roughness_scores.append(roughness)

        mean_roughness = float(np.mean(roughness_scores)) if roughness_scores else 0.0
        excessive_noise = mean_roughness > self.max_noise_roughness

        # 4. Inconsistent Depth Check
        inc_ratio = float(consistency_stats.get("inconsistent_pixels", 0)) / max(
            1, float(consistency_stats.get("total_tested_pixels", 1))
        )
        has_inconsistent_depth = inc_ratio > self.inconsistency_warning_ratio

        # 5. Hole Detection (Unpopulated cells between bounding surface bounds)
        # Detect large voids in interior occupied bounding volume
        min_b = np.min(coords, axis=0)
        max_b = np.max(coords, axis=0)
        extent = max_b - min_b
        grid_dim = np.maximum(1, np.int32(np.ceil(extent / 0.50)))
        total_possible_cells = int(grid_dim[0] * grid_dim[1] * grid_dim[2])
        occupied_05m_cells = len(set(
            (int(p[0] // 0.50), int(p[1] // 0.50), int(p[2] // 0.50))
            for p in coords
        ))
        void_fraction = max(0.0, 1.0 - (occupied_05m_cells / max(1, total_possible_cells)))

        holes_info = {
            "detected": void_fraction > 0.65,
            "void_volume_fraction": round(void_fraction, 3),
            "estimated_hole_regions": max(0, int(total_possible_cells * 0.10) if void_fraction > 0.65 else 0)
        }

        is_acceptable = (
            len(floating_indices) < 0.15 * n_points and
            not excessive_noise and
            len(isolated_clusters) < 15
        )

        return {
            "total_points": n_points,
            "defects_detected": {
                "floating_geometry": {
                    "count": len(floating_indices),
                    "ratio": round(len(floating_indices) / max(1, n_points), 4),
                    "sample_indices": floating_indices[:20]
                },
                "isolated_regions": {
                    "count": len(isolated_clusters),
                    "clusters": isolated_clusters[:10]
                },
                "excessive_noise": {
                    "detected": excessive_noise,
                    "mean_roughness": round(mean_roughness, 4)
                },
                "inconsistent_depth": {
                    "detected": has_inconsistent_depth,
                    "disagreement_ratio": round(inc_ratio, 4)
                },
                "holes": holes_info
            },
            "is_acceptable": is_acceptable
        }
