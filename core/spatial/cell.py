"""
VĀSTU Spatial Cell Model
Defines an independently processable 3D spatial cell containing local coordinate frame,
source frames/poses, evidence points, confidences, structural & semantic observations,
and boundary halo margins to preserve spatial continuity.
"""

import uuid
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

from core.schemas.spatial_cell import (
    SpatialCell,
    CellCoordinates,
    CellBounds,
    LocalCoordinateSystem,
    CellBoundaryInfo
)


class SpatialCellModel:
    """
    In-memory representation of an independently processable spatial cell.
    """
    def __init__(
        self,
        cell_id: str,
        coordinates: Tuple[int, int, int],
        cell_size_m: float = 1.5,
        margin_m: float = 0.08,
        origin_world: Optional[np.ndarray] = None,
        rotation_matrix: Optional[np.ndarray] = None
    ):
        self.cell_id = cell_id
        self.coordinates = coordinates
        self.cell_size_m = cell_size_m
        self.margin_m = margin_m

        # Local coordinate system definition
        if origin_world is not None:
            self.origin_world = np.array(origin_world, dtype=np.float64)
        else:
            # Default center of voxel grid
            cx, cy, cz = coordinates
            self.origin_world = np.array([
                (cx + 0.5) * cell_size_m,
                (cy + 0.5) * cell_size_m,
                (cz + 0.5) * cell_size_m
            ], dtype=np.float64)

        self.rotation_matrix = (
            np.array(rotation_matrix, dtype=np.float64)
            if rotation_matrix is not None
            else np.eye(3, dtype=np.float64)
        )

        # Core data containers
        self.points_world: np.ndarray = np.empty((0, 3), dtype=np.float64)
        self.colors: np.ndarray = np.empty((0, 3), dtype=np.uint8)
        self.normals: np.ndarray = np.empty((0, 3), dtype=np.float64)
        self.confidences: np.ndarray = np.empty((0,), dtype=np.float64)

        # Provenance & Observations
        self.source_frames: List[int] = []
        self.source_poses: List[Dict[str, Any]] = []
        self.semantic_observations: List[Dict[str, Any]] = []
        self.structural_observations: List[Dict[str, Any]] = []

        # Boundary information
        self.neighbor_cell_ids: List[str] = []

        # Reconstructed local surface mesh
        self.local_mesh_vertices: Optional[np.ndarray] = None
        self.local_mesh_faces: Optional[np.ndarray] = None

        # State & Versioning
        self.quality_score: float = 1.0
        self.version: int = 1
        self.is_dirty: bool = False

    @property
    def local_points(self) -> np.ndarray:
        """Returns points transformed into the cell's local coordinate system."""
        if len(self.points_world) == 0:
            return np.empty((0, 3), dtype=np.float64)
        return self.to_local(self.points_world)

    def to_local(self, pts_world: np.ndarray) -> np.ndarray:
        """Transforms points from world coordinates to cell local coordinates."""
        pts = np.atleast_2d(pts_world)
        diff = pts - self.origin_world
        return (self.rotation_matrix @ diff.T).T

    def to_world(self, pts_local: np.ndarray) -> np.ndarray:
        """Transforms points from cell local coordinates to world coordinates."""
        pts = np.atleast_2d(pts_local)
        rotated = (self.rotation_matrix.T @ pts.T).T
        return rotated + self.origin_world

    def get_core_bounds_world(self) -> Tuple[np.ndarray, np.ndarray]:
        """Returns (min_xyz, max_xyz) for the cell core in world coordinates."""
        half = self.cell_size_m / 2.0
        min_xyz = self.origin_world - half
        max_xyz = self.origin_world + half
        return min_xyz, max_xyz

    def get_halo_bounds_world(self) -> Tuple[np.ndarray, np.ndarray]:
        """Returns (min_xyz, max_xyz) including the boundary halo margin in world coordinates."""
        half = (self.cell_size_m / 2.0) + self.margin_m
        min_xyz = self.origin_world - half
        max_xyz = self.origin_world + half
        return min_xyz, max_xyz

    def get_core_mask(self) -> np.ndarray:
        """Returns boolean mask of points strictly inside the inner core bounds."""
        if len(self.points_world) == 0:
            return np.empty((0,), dtype=bool)
        half = self.cell_size_m / 2.0
        local_p = self.local_points
        return (
            (local_p[:, 0] >= -half) & (local_p[:, 0] <= half) &
            (local_p[:, 1] >= -half) & (local_p[:, 1] <= half) &
            (local_p[:, 2] >= -half) & (local_p[:, 2] <= half)
        )

    def get_halo_mask(self) -> np.ndarray:
        """Returns boolean mask of points in the boundary halo margin zone."""
        if len(self.points_world) == 0:
            return np.empty((0,), dtype=bool)
        core_mask = self.get_core_mask()
        return ~core_mask

    def add_points(
        self,
        new_pts_world: np.ndarray,
        new_colors: np.ndarray,
        new_normals: np.ndarray,
        new_confidences: np.ndarray,
        source_frame_indices: Optional[List[int]] = None
    ):
        """Adds points in world space to this cell."""
        if len(new_pts_world) == 0:
            return

        if len(self.points_world) == 0:
            self.points_world = np.array(new_pts_world, dtype=np.float64)
            self.colors = np.array(new_colors, dtype=np.uint8)
            self.normals = np.array(new_normals, dtype=np.float64)
            self.confidences = np.array(new_confidences, dtype=np.float64)
        else:
            self.points_world = np.vstack([self.points_world, new_pts_world])
            self.colors = np.vstack([self.colors, new_colors])
            self.normals = np.vstack([self.normals, new_normals])
            self.confidences = np.concatenate([self.confidences, new_confidences])

        if source_frame_indices:
            self.source_frames = sorted(list(set(self.source_frames + source_frame_indices)))

        self.is_dirty = True

    def to_contract(self, model_id: Optional[uuid.UUID] = None) -> SpatialCell:
        """Serializes cell metadata into the formal Contract 6 SpatialCell schema."""
        min_xyz, max_xyz = self.get_core_bounds_world()
        n_points = len(self.points_world)
        vol_m3 = self.cell_size_m ** 3
        density = int(round(n_points / vol_m3)) if vol_m3 > 0 else 0
        mean_conf = float(np.mean(self.confidences)) if n_points > 0 else 1.0

        n_triangles = len(self.local_mesh_faces) if self.local_mesh_faces is not None else 0
        boundary_pts = int(np.sum(self.get_halo_mask()))

        plane_ids = [str(p.get("structure_id", idx)) for idx, p in enumerate(self.structural_observations)]
        sem_ids = [str(s.get("object_id", idx)) for idx, s in enumerate(self.semantic_observations)]

        return SpatialCell(
            cell_id=self.cell_id,
            model_id=model_id or uuid.uuid4(),
            coordinates=CellCoordinates(
                cx=self.coordinates[0],
                cy=self.coordinates[1],
                cz=self.coordinates[2]
            ),
            cell_size_m=self.cell_size_m,
            bounds=CellBounds(
                min_xyz=min_xyz.tolist(),
                max_xyz=max_xyz.tolist(),
                center_xyz=self.origin_world.tolist()
            ),
            local_coordinate_system=LocalCoordinateSystem(
                origin_world_xyz=self.origin_world.tolist(),
                rotation_matrix=self.rotation_matrix.tolist()
            ),
            boundary_info=CellBoundaryInfo(
                neighbor_cell_ids=self.neighbor_cell_ids,
                margin_m=self.margin_m,
                boundary_points_count=boundary_pts,
                adjacent_plane_ids=plane_ids
            ),
            quality_score=round(self.quality_score, 4),
            is_low_confidence=self.quality_score < 0.60,
            density_points_per_m3=density,
            point_count=n_points,
            mean_point_confidence=round(mean_conf, 4),
            triangle_count=n_triangles,
            source_frames=self.source_frames,
            source_poses_count=len(self.source_poses),
            structural_plane_ids=plane_ids,
            semantic_object_ids=sem_ids,
            version=self.version,
            is_dirty=self.is_dirty
        )
