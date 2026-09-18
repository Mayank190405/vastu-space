#!/usr/bin/env python3
"""
VĀSTU — Point 25: Spatial Cell System Engine
Modular 3D Spatial Cell partitioning and localized representation engine.

Development sequence:
1. Define coordinate system (metric cartesian indoor frame)
2. Define cell representation (voxel index cx, cy, cz and spatial bounds)
3. Assign geometry (vertices, faces, point clouds)
4. Assign semantics (associated 3D semantic objects)
5. Assign quality (per-cell quality score)
6. Assign navigation information (nav nodes and edges)
7. Add spatial index (fast voxel hash map / spatial index)
8. Define neighboring cells (26-connectivity / 6-connectivity)
9. Define cell version (versioning & dirty flag tracking)
10. Store cell metadata (export JSON manifest and cell partition files)
"""

import os
import sys
import json
import logging
import argparse
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VastuSpatialCellEngine")


class SpatialCell:
    def __init__(
        self,
        cell_coords: tuple,
        cell_size_m: float,
        version: int = 1
    ):
        self.coords = cell_coords # (cx, cy, cz)
        self.cell_size_m = float(cell_size_m)
        self.version = version
        self.is_dirty = False

        cx, cy, cz = cell_coords
        self.min_bounds = np.array([cx * cell_size_m, cy * cell_size_m, cz * cell_size_m], dtype=np.float64)
        self.max_bounds = self.min_bounds + self.cell_size_m
        self.center = self.min_bounds + 0.5 * self.cell_size_m

        # Cellular contents
        self.point_indices = []
        self.face_indices = []
        self.semantic_object_ids = []
        self.nav_node_ids = []
        self.nav_edge_ids = []
        self.quality_score = 1.0 # 0.0 to 1.0
        self.observation_views = 0
        self.texture_chart_ids = []
        self.is_low_confidence = False
        self.neighbor_coords = []

    def contains_point(self, pt: np.ndarray) -> bool:
        return bool(np.all(pt >= self.min_bounds) and np.all(pt < self.max_bounds))

    def to_dict(self) -> dict:
        return {
            "cell_id": f"cell_{self.coords[0]}_{self.coords[1]}_{self.coords[2]}",
            "coords": list(self.coords),
            "cell_size_m": self.cell_size_m,
            "bounds": {
                "min_xyz": [round(float(v), 3) for v in self.min_bounds],
                "max_xyz": [round(float(v), 3) for v in self.max_bounds],
                "center_xyz": [round(float(v), 3) for v in self.center],
            },
            "stats": {
                "point_count": len(self.point_indices),
                "face_count": len(self.face_indices),
                "semantic_objects_count": len(self.semantic_object_ids),
                "nav_nodes_count": len(self.nav_node_ids),
                "observation_views": self.observation_views,
            },
            "quality": {
                "score": round(float(self.quality_score), 2),
                "is_low_confidence": self.is_low_confidence,
            },
            "semantic_object_ids": self.semantic_object_ids,
            "nav_node_ids": self.nav_node_ids,
            "neighbor_coords": [list(nc) for nc in self.neighbor_coords],
            "version": self.version,
            "is_dirty": self.is_dirty,
        }


class SpatialCellEngine:
    def __init__(self, cell_size_m: float = 1.0, quality_threshold: float = 0.50):
        self.cell_size_m = float(cell_size_m)
        self.quality_threshold = quality_threshold
        self.cells = {} # (cx, cy, cz) -> SpatialCell

    # -------------------------------------------------------------------------
    # Step 1 & 2: Coordinate System & Cell Representation
    # -------------------------------------------------------------------------
    def get_or_create_cell(self, cx: int, cy: int, cz: int, version: int = 1) -> SpatialCell:
        coord = (int(cx), int(cy), int(cz))
        if coord not in self.cells:
            self.cells[coord] = SpatialCell(coord, self.cell_size_m, version=version)
        return self.cells[coord]

    def point_to_cell_coord(self, pt: np.ndarray) -> tuple:
        """Step 1 & 2: Maps continuous 3D coordinate to discrete voxel cell index."""
        cx = int(np.floor(pt[0] / self.cell_size_m))
        cy = int(np.floor(pt[1] / self.cell_size_m))
        cz = int(np.floor(pt[2] / self.cell_size_m))
        return (cx, cy, cz)

    # -------------------------------------------------------------------------
    # Step 3: Assign Geometry (Points & Triangle Faces)
    # -------------------------------------------------------------------------
    def assign_geometry(
        self,
        vertices: np.ndarray,
        faces: np.ndarray = None,
        normals: np.ndarray = None
    ):
        """Partitions 3D point cloud and triangle mesh faces into spatial cells."""
        # 1. Partition points
        for idx, pt in enumerate(vertices):
            coord = self.point_to_cell_coord(pt)
            cell = self.get_or_create_cell(*coord)
            cell.point_indices.append(idx)

        # 2. Partition mesh faces by centroid
        if faces is not None and len(faces) > 0:
            centroids = np.mean(vertices[faces], axis=1)
            for f_idx, cent in enumerate(centroids):
                coord = self.point_to_cell_coord(cent)
                cell = self.get_or_create_cell(*coord)
                cell.face_indices.append(f_idx)

        logger.info(f"[Step 3: Geometry] Partitioned {len(vertices)} points into {len(self.cells)} cells")

    # -------------------------------------------------------------------------
    # Step 4: Assign Semantics
    # -------------------------------------------------------------------------
    def assign_semantics(self, semantic_objects: list):
        """Assigns semantic objects to cells based on object centroids and bounds."""
        for obj in semantic_objects:
            obj_id = obj.get("object_id", "unknown")
            cent = np.array(obj.get("centroid", [0, 0, 0]), dtype=np.float64)
            coord = self.point_to_cell_coord(cent)
            cell = self.get_or_create_cell(*coord)
            if obj_id not in cell.semantic_object_ids:
                cell.semantic_object_ids.append(obj_id)

    # -------------------------------------------------------------------------
    # Step 5: Assign Quality
    # -------------------------------------------------------------------------
    def assign_quality(self, min_points_expected: int = 20):
        """Calculates per-cell quality score based on density and geometric completeness."""
        for cell in self.cells.values():
            n_pts = len(cell.point_indices)
            if n_pts == 0:
                cell.quality_score = 0.0
                cell.is_low_confidence = True
            else:
                density_ratio = min(1.0, float(n_pts) / float(min_points_expected))
                cell.quality_score = density_ratio
                cell.is_low_confidence = cell.quality_score < self.quality_threshold

    # -------------------------------------------------------------------------
    # Step 6: Assign Navigation Information
    # -------------------------------------------------------------------------
    def assign_navigation(self, nav_nodes: list, nav_edges: list = None):
        """Assigns indoor graph nodes and edges to containing spatial cells."""
        for node in nav_nodes:
            nid = node.get("id")
            pt = np.array([node.get("pos_x", 0), node.get("pos_y", 0), node.get("pos_z", 0)])
            coord = self.point_to_cell_coord(pt)
            cell = self.get_or_create_cell(*coord)
            if nid not in cell.nav_node_ids:
                cell.nav_node_ids.append(nid)

    # -------------------------------------------------------------------------
    # Step 7 & 8: Spatial Index & Neighbor Queries (26-connectivity)
    # -------------------------------------------------------------------------
    def build_spatial_index(self, connectivity: int = 26):
        """Step 7: Builds spatial adjacency index using Moore/von Neumann neighborhood."""
        return self.compute_neighbors(connectivity=connectivity)

    def compute_neighbors(self, connectivity: int = 26):
        """Computes neighboring cell coordinates for each active spatial cell."""
        offsets = []
        if connectivity == 6:
            offsets = [
                (1, 0, 0), (-1, 0, 0),
                (0, 1, 0), (0, -1, 0),
                (0, 0, 1), (0, 0, -1)
            ]
        else: # 26-connectivity (Moore neighborhood)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    for dz in [-1, 0, 1]:
                        if dx == 0 and dy == 0 and dz == 0:
                            continue
                        offsets.append((dx, dy, dz))

        for coord, cell in self.cells.items():
            cell.neighbor_coords = []
            for dx, dy, dz in offsets:
                nbr_coord = (coord[0] + dx, coord[1] + dy, coord[2] + dz)
                if nbr_coord in self.cells:
                    cell.neighbor_coords.append(nbr_coord)

    def query_neighbors(self, cx: int, cy: int, cz: int) -> list:
        """Returns list of existing neighboring SpatialCells."""
        cell = self.cells.get((cx, cy, cz))
        if not cell:
            return []
        return [self.cells[nc] for nc in cell.neighbor_coords if nc in self.cells]

    # -------------------------------------------------------------------------
    # Step 9: Cell Versioning & Dirty Flag
    # -------------------------------------------------------------------------
    def mark_cell_dirty(self, cx: int, cy: int, cz: int):
        """Flags a cell as modified; increments version."""
        cell = self.cells.get((cx, cy, cz))
        if cell:
            cell.is_dirty = True
            cell.version += 1

    # -------------------------------------------------------------------------
    # Step 10: Store Cell Metadata
    # -------------------------------------------------------------------------
    def store_cell_metadata(self, output_dir: str) -> dict:
        """Serializes all spatial cells into JSON manifest."""
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "spatial_cells.json")

        cells_dict = {
            f"{coord[0]}_{coord[1]}_{coord[2]}": cell.to_dict()
            for coord, cell in self.cells.items()
        }

        manifest = {
            "status": "success",
            "pipeline_point": 25,
            "engine": "VastuSpatialCellEngine",
            "cell_size_m": self.cell_size_m,
            "total_cells": len(self.cells),
            "cells": cells_dict,
        }

        with open(out_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Stored {len(self.cells)} spatial cells in {out_path}")
        return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VĀSTU Point 25 Spatial Cell Engine")
    parser.add_argument("--cell-size", type=float, default=1.0, help="Cell size in meters")
    parser.add_argument("--output-dir", type=str, required=True, help="Output directory")
    args = parser.parse_args()

    engine = SpatialCellEngine(cell_size_m=args.cell_size)
    print(f"Spatial Cell Engine initialized with {args.cell_size}m grid.")
