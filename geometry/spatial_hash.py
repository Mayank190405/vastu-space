"""
VĀSTU Pure Geometry Engine: Spatial Hash Grid
Voxel hashing, spatial deduplication, and uniform point cloud subsampling.
"""

from typing import Dict, List, Tuple
import numpy as np

class SpatialHashGrid:
    def __init__(self, voxel_size_m: float = 0.02):
        self.voxel_size_m = float(voxel_size_m)
        self.inv_voxel = 1.0 / self.voxel_size_m
        self.grid: Dict[Tuple[int, int, int], List[int]] = {}

    def get_voxel_key(self, point: np.ndarray) -> Tuple[int, int, int]:
        return (
            int(np.floor(point[0] * self.inv_voxel)),
            int(np.floor(point[1] * self.inv_voxel)),
            int(np.floor(point[2] * self.inv_voxel)),
        )

    def insert(self, point: np.ndarray, point_idx: int) -> bool:
        """
        Inserts a point. If voxel already occupied, returns False (duplicate).
        """
        key = self.get_voxel_key(point)
        if key in self.grid:
            self.grid[key].append(point_idx)
            return False
        self.grid[key] = [point_idx]
        return True

    def downsample(self, points: np.ndarray, colors: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Subsamples points to one representative point per voxel (centroid).
        """
        grid: Dict[Tuple[int, int, int], List[int]] = {}
        for idx, pt in enumerate(points):
            k = self.get_voxel_key(pt)
            if k not in grid:
                grid[k] = []
            grid[k].append(idx)

        sub_pts = []
        sub_cols = []
        for indices in grid.values():
            sub_pts.append(np.mean(points[indices], axis=0))
            if colors is not None:
                sub_cols.append(np.mean(colors[indices], axis=0))

        res_pts = np.asarray(sub_pts, dtype=np.float32)
        res_cols = np.asarray(sub_cols, dtype=np.uint8) if colors is not None else None
        return res_pts, res_cols
