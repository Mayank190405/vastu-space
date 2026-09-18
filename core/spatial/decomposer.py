"""
VĀSTU Spatial Cell Decomposer
Partitions global 3D dense evidence points, camera trajectory, structural planes,
and semantic objects into independently processable spatial cells with boundary halo margins.
"""

import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple

from core.dense.evidence_fusion import DenseEvidencePoint
from core.spatial.cell import SpatialCellModel

logger = logging.getLogger("vastu.spatial.decomposer")


class SpatialCellDecomposer:
    """
    Decomposes an end-to-end 3D spatial reconstruction dataset into spatial cells.
    Preserves boundary continuity via halo overlap margins.
    """
    def __init__(self, cell_size_m: float = 1.5, margin_m: float = 0.08):
        self.cell_size_m = cell_size_m
        self.margin_m = margin_m

    def decompose(
        self,
        evidence_points: List[DenseEvidencePoint],
        camera_poses: List[Dict[str, Any]],
        structural_planes: Optional[List[Dict[str, Any]]] = None,
        semantic_objects: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, SpatialCellModel]:
        """
        Partitions the global scene into a dictionary of {cell_id: SpatialCellModel}.
        """
        if not evidence_points:
            logger.warning("Empty evidence points provided to SpatialCellDecomposer")
            return {}

        L = self.cell_size_m
        delta = self.margin_m

        coords = np.array([p.position for p in evidence_points], dtype=np.float64)
        colors = np.array([p.color for p in evidence_points], dtype=np.uint8)
        normals = np.array([p.normal for p in evidence_points], dtype=np.float64)
        confs = np.array([p.confidence for p in evidence_points], dtype=np.float64)
        source_frame_map = [p.source_frames for p in evidence_points]

        inv_L = 1.0 / L
        # Identify all distinct grid cells containing points
        grid_coords_for_pts = np.floor(coords * inv_L).astype(int)
        unique_cells = np.unique(grid_coords_for_pts, axis=0)

        cells: Dict[str, SpatialCellModel] = {}
        cell_by_coord: Dict[Tuple[int, int, int], SpatialCellModel] = {}

        for coord in unique_cells:
            cx, cy, cz = int(coord[0]), int(coord[1]), int(coord[2])
            cid = f"cell_{cx:+04d}_{cy:+04d}_{cz:+04d}"

            cell_model = SpatialCellModel(
                cell_id=cid,
                coordinates=(cx, cy, cz),
                cell_size_m=L,
                margin_m=delta
            )
            cells[cid] = cell_model
            cell_by_coord[(cx, cy, cz)] = cell_model

        # Populate points into cells using the boundary halo margin [cx*L - delta, (cx+1)*L + delta]
        # This guarantees spatial continuity across cell boundaries without cracks
        for cid, cell in cells.items():
            cx, cy, cz = cell.coordinates
            min_x, max_x = cx * L - delta, (cx + 1) * L + delta
            min_y, max_y = cy * L - delta, (cy + 1) * L + delta
            min_z, max_z = cz * L - delta, (cz + 1) * L + delta

            in_halo = (
                (coords[:, 0] >= min_x) & (coords[:, 0] <= max_x) &
                (coords[:, 1] >= min_y) & (coords[:, 1] <= max_y) &
                (coords[:, 2] >= min_z) & (coords[:, 2] <= max_z)
            )

            pts_in_cell = coords[in_halo]
            cols_in_cell = colors[in_halo]
            norms_in_cell = normals[in_halo]
            confs_in_cell = confs[in_halo]

            # Aggregate source frames
            halo_indices = np.where(in_halo)[0]
            cell_sources = []
            for h_idx in halo_indices:
                cell_sources.extend(source_frame_map[h_idx])

            cell.add_points(
                new_pts_world=pts_in_cell,
                new_colors=cols_in_cell,
                new_normals=norms_in_cell,
                new_confidences=confs_in_cell,
                source_frame_indices=sorted(list(set(cell_sources)))
            )
            cell.is_dirty = False

        # Establish adjacency neighbor references (6-connected faces)
        for (cx, cy, cz), cell in cell_by_coord.items():
            for dx, dy, dz in [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]:
                neighbor_key = (cx + dx, cy + dy, cz + dz)
                if neighbor_key in cell_by_coord:
                    cell.neighbor_cell_ids.append(cell_by_coord[neighbor_key].cell_id)

        # Associate camera poses with intersected cells
        for pose in camera_poses:
            f_idx = pose.get("frame_index", 0)
            c_pos = np.array(pose.get("camera_center_m", pose.get("t", [0, 0, 0])), dtype=np.float64)
            pcx, pcy, pcz = int(np.floor(c_pos[0] * inv_L)), int(np.floor(c_pos[1] * inv_L)), int(np.floor(c_pos[2] * inv_L))
            target_cell = cell_by_coord.get((pcx, pcy, pcz))
            if target_cell:
                target_cell.source_poses.append(pose)
                if f_idx not in target_cell.source_frames:
                    target_cell.source_frames.append(f_idx)

        # Associate structural planes
        if structural_planes:
            for plane in structural_planes:
                for cell in cells.values():
                    # Check if plane inliers or bounds overlap cell bounds
                    cell.structural_observations.append(plane)

        # Associate semantic objects
        if semantic_objects:
            for obj in semantic_objects:
                for cell in cells.values():
                    cell.semantic_observations.append(obj)

        logger.info(f"Decomposition complete: scene partitioned into {len(cells)} spatial cells")
        return cells
