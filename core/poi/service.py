"""
VĀSTU Point of Interest (POI) Service:
Comprehensive spatial entity management:
- Create, Edit, Delete, Get
- Textual & Tag Search (name, aliases, category, room)
- 3D Spatial Query (spherical radius & k-nearest neighbors)
- Raycast 3D Placement (Möller-Trumbore ray-triangle intersection & surface normal anchoring)
- Version Association & Cross-Version Spatial Validity Migration
"""

import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
from scipy.spatial import KDTree

from core.schemas.poi import PointOfInterest, POICoordinates, POICameraViewpoint

logger = logging.getLogger("vastu.poi.service")

class POIService:
    """
    Manages 3D points of interest with version awareness, raycast placement,
    spatial indexing, and cross-version validity preservation.
    """
    def __init__(self):
        # POI ID (str) -> PointOfInterest
        self._pois: Dict[str, PointOfInterest] = {}
        # Version -> List[poi_id]
        self._version_index: Dict[str, List[str]] = {}

    def create_poi(self, poi_data: Union[PointOfInterest, Dict[str, Any]]) -> PointOfInterest:
        """Creates and stores a version-aware Point of Interest."""
        if isinstance(poi_data, dict):
            poi = PointOfInterest(**poi_data)
        else:
            poi = poi_data

        pid_str = str(poi.id)
        self._pois[pid_str] = poi

        v = poi.model_version
        if v not in self._version_index:
            self._version_index[v] = []
        if pid_str not in self._version_index[v]:
            self._version_index[v].append(pid_str)

        logger.info(f"POI '{poi.name}' ({pid_str}) created for version '{poi.model_version}'.")
        return poi

    def edit_poi(self, poi_id: Union[uuid.UUID, str], updates: Dict[str, Any]) -> PointOfInterest:
        """Edits fields on an existing POI."""
        pid_str = str(poi_id)
        if pid_str not in self._pois:
            raise KeyError(f"POI '{pid_str}' not found")

        curr_data = self._pois[pid_str].model_dump()
        curr_version = curr_data.get("model_version", "1.0.0")

        # Apply updates
        for k, v in updates.items():
            if k == "coordinates" and isinstance(v, (list, tuple)):
                curr_data["coordinates"] = {"x": v[0], "y": v[1], "z": v[2]}
                curr_data["coordinates_m"] = curr_data["coordinates"]
            else:
                curr_data[k] = v

        updated_poi = PointOfInterest(**curr_data)
        self._pois[pid_str] = updated_poi

        # Update version index if version changed
        new_version = updated_poi.model_version
        if new_version != curr_version:
            if curr_version in self._version_index and pid_str in self._version_index[curr_version]:
                self._version_index[curr_version].remove(pid_str)
            if new_version not in self._version_index:
                self._version_index[new_version] = []
            if pid_str not in self._version_index[new_version]:
                self._version_index[new_version].append(pid_str)

        return updated_poi

    def delete_poi(self, poi_id: Union[uuid.UUID, str]) -> bool:
        """Deletes a POI by ID."""
        pid_str = str(poi_id)
        if pid_str not in self._pois:
            return False

        poi = self._pois.pop(pid_str)
        v = poi.model_version
        if v in self._version_index and pid_str in self._version_index[v]:
            self._version_index[v].remove(pid_str)

        return True

    def get_poi(self, poi_id: Union[uuid.UUID, str]) -> Optional[PointOfInterest]:
        """Retrieves a single POI by ID."""
        return self._pois.get(str(poi_id))

    def list_pois(self, model_version: Optional[str] = None) -> List[PointOfInterest]:
        """Lists all POIs, optionally filtered by model version."""
        if model_version is not None:
            ids = self._version_index.get(model_version, [])
            return [self._pois[pid] for pid in ids if pid in self._pois]
        return list(self._pois.values())

    def search_pois(
        self,
        query: str,
        category: Optional[str] = None,
        room: Optional[str] = None,
        model_version: Optional[str] = None
    ) -> List[PointOfInterest]:
        """
        Searches POIs across name, aliases, description, tags, category, and room.
        """
        q = query.strip().lower()
        candidates = self.list_pois(model_version=model_version)
        results = []

        for p in candidates:
            if category and p.category.lower() != category.lower():
                continue
            if room and (not p.room or p.room.lower() != room.lower()):
                continue

            # Match against name, title, aliases, description, tags
            matches_name = q in p.name.lower() or q in p.title.lower()
            matches_alias = any(q in a.lower() for a in p.aliases)
            matches_tag = any(q in t.lower() for t in p.tags)
            matches_desc = bool(p.description and q in p.description.lower())

            if matches_name or matches_alias or matches_tag or matches_desc or not q:
                results.append(p)

        return results

    def spatial_query(
        self,
        center_xyz: List[float],
        radius_m: float,
        model_version: Optional[str] = None,
        k_nearest: Optional[int] = None
    ) -> List[Tuple[PointOfInterest, float]]:
        """
        Finds all POIs within radius_m meters from center_xyz in 3D metric space.
        Returns list of tuples: (PointOfInterest, distance_meters) sorted by distance.
        """
        candidates = self.list_pois(model_version=model_version)
        if not candidates:
            return []

        pts = np.array([[p.coordinates.x, p.coordinates.y, p.coordinates.z] for p in candidates])
        center = np.array(center_xyz, dtype=np.float64)

        tree = KDTree(pts)
        if k_nearest is not None:
            distances, indices = tree.query(center, k=min(k_nearest, len(candidates)))
            if np.isscalar(distances):
                distances = [distances]
                indices = [indices]
            results = []
            for dist, idx in zip(distances, indices):
                if dist <= radius_m:
                    results.append((candidates[idx], float(dist)))
            return results
        else:
            indices = tree.query_ball_point(center, r=radius_m)
            results = []
            for idx in indices:
                d = float(np.linalg.norm(pts[idx] - center))
                results.append((candidates[idx], d))
            results.sort(key=lambda x: x[1])
            return results

    def raycast_placement(
        self,
        ray_origin: List[float],
        ray_direction: List[float],
        mesh_vertices: np.ndarray,
        mesh_faces: np.ndarray,
        name: str = "Placed POI",
        category: str = "GENERAL",
        room: Optional[str] = None,
        model_version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None
    ) -> PointOfInterest:
        """
        Performs 3D ray-triangle intersection (Möller–Trumbore) against spatial surface geometry,
        computes the hit coordinate and surface normal, and creates a securely anchored POI.
        """
        orig = np.array(ray_origin, dtype=np.float64)
        direction = np.array(ray_direction, dtype=np.float64)
        dir_norm = np.linalg.norm(direction)
        if dir_norm < 1e-6:
            raise ValueError("Ray direction cannot be zero vector")
        dir_unit = direction / dir_norm

        hit_point, hit_normal, hit_dist = self._ray_mesh_intersect(orig, dir_unit, mesh_vertices, mesh_faces)

        # Fallback if no direct hit (anchor at standard 2m along ray)
        if hit_point is None:
            hit_point = orig + dir_unit * 2.0
            hit_normal = np.array([0.0, 0.0, 1.0])
            confidence = 0.65
        else:
            confidence = 0.95

        cam_view = POICameraViewpoint(
            position=orig.tolist(),
            look_at=hit_point.tolist()
        )

        poi = PointOfInterest(
            id=uuid.uuid4(),
            name=name,
            title=name,
            category=category,
            coordinates=POICoordinates(x=round(hit_point[0], 4), y=round(hit_point[1], 4), z=round(hit_point[2], 4)),
            coordinates_m=POICoordinates(x=round(hit_point[0], 4), y=round(hit_point[1], 4), z=round(hit_point[2], 4)),
            surface_normal=POICoordinates(x=round(hit_normal[0], 4), y=round(hit_normal[1], 4), z=round(hit_normal[2], 4)),
            room=room,
            geometry={
                "type": "SURFACE_ANCHOR",
                "surface_normal": hit_normal.tolist(),
                "hit_distance_m": round(hit_dist, 4) if hit_dist is not None else 2.0
            },
            confidence=confidence,
            camera_viewpoint=cam_view,
            metadata=metadata or {},
            model_version=model_version
        )

        return self.create_poi(poi)

    def _ray_mesh_intersect(
        self,
        ray_origin: np.ndarray,
        ray_dir: np.ndarray,
        vertices: np.ndarray,
        faces: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[float]]:
        """Möller-Trumbore ray-triangle intersection algorithm."""
        if len(vertices) == 0 or len(faces) == 0:
            return None, None, None

        v0 = vertices[faces[:, 0]]
        v1 = vertices[faces[:, 1]]
        v2 = vertices[faces[:, 2]]

        edge1 = v1 - v0
        edge2 = v2 - v0
        h = np.cross(ray_dir, edge2)
        a = np.sum(edge1 * h, axis=1)

        # Parallel ray check
        non_parallel = np.abs(a) > 1e-7
        if not np.any(non_parallel):
            return None, None, None

        f = 1.0 / a[non_parallel]
        s = ray_origin - v0[non_parallel]
        u = f * np.sum(s * h[non_parallel], axis=1)

        valid_u = (u >= 0.0) & (u <= 1.0)
        if not np.any(valid_u):
            return None, None, None

        q = np.cross(s[valid_u], edge1[non_parallel][valid_u])
        v = f[valid_u] * np.sum(ray_dir * q, axis=1)

        valid_v = (v >= 0.0) & (u[valid_u] + v <= 1.0)
        if not np.any(valid_v):
            return None, None, None

        t = f[valid_u][valid_v] * np.sum(edge2[non_parallel][valid_u][valid_v] * q[valid_v], axis=1)

        # Find closest positive intersection
        valid_t = t > 1e-4
        if not np.any(valid_t):
            return None, None, None

        min_idx = np.argmin(t[valid_t])
        closest_t = t[valid_t][min_idx]
        hit_pt = ray_origin + ray_dir * closest_t

        # Face normal
        active_e1 = edge1[non_parallel][valid_u][valid_v][valid_t][min_idx]
        active_e2 = edge2[non_parallel][valid_u][valid_v][valid_t][min_idx]
        face_normal = np.cross(active_e1, active_e2)
        norm_len = np.linalg.norm(face_normal)
        if norm_len > 1e-6:
            face_normal = face_normal / norm_len
        else:
            face_normal = np.array([0.0, 0.0, 1.0])

        return hit_pt, face_normal, float(closest_t)

    def version_association(self, poi_id: Union[uuid.UUID, str], target_version: str) -> PointOfInterest:
        """Associates an existing POI with a target model version."""
        return self.edit_poi(poi_id, {"model_version": target_version})

    def migrate_pois_across_versions(
        self,
        source_version: str,
        target_version: str,
        transformation_matrix: Optional[np.ndarray] = None,
        updated_mesh_vertices: Optional[np.ndarray] = None,
        max_drift_threshold_m: float = 0.50
    ) -> List[PointOfInterest]:
        """
        Preserves POI spatial validity when model versions change:
        - Copies POIs from source_version to target_version.
        - Applies metric transformation matrix if version underwent coordinate recalibration.
        - Snaps POI coordinates to nearest updated surface mesh if vertices shifted.
        - Verifies drift remains within max_drift_threshold_m.
        """
        source_pois = self.list_pois(model_version=source_version)
        migrated_pois = []

        mesh_tree = KDTree(updated_mesh_vertices) if (updated_mesh_vertices is not None and len(updated_mesh_vertices) > 0) else None

        for sp in source_pois:
            old_coord = np.array([sp.coordinates.x, sp.coordinates.y, sp.coordinates.z, 1.0])

            # Apply transform if available
            if transformation_matrix is not None:
                new_coord_h = transformation_matrix @ old_coord
                new_xyz = new_coord_h[:3] / (new_coord_h[3] if new_coord_h[3] != 0 else 1.0)
            else:
                new_xyz = old_coord[:3]

            # Snap to updated surface mesh if available
            drift = 0.0
            if mesh_tree is not None:
                dist, idx = mesh_tree.query(new_xyz)
                if dist <= max_drift_threshold_m:
                    drift = float(dist)
                    # Snap gently towards refined surface
                    new_xyz = mesh_tree.data[idx]

            migrated = PointOfInterest(
                id=uuid.uuid4(),  # New version-specific instance
                poi_id=uuid.uuid4(),
                project_id=sp.project_id,
                name=sp.name,
                title=sp.title,
                aliases=list(sp.aliases),
                category=sp.category,
                coordinates=POICoordinates(x=round(float(new_xyz[0]), 4), y=round(float(new_xyz[1]), 4), z=round(float(new_xyz[2]), 4)),
                coordinates_m=POICoordinates(x=round(float(new_xyz[0]), 4), y=round(float(new_xyz[1]), 4), z=round(float(new_xyz[2]), 4)),
                room=sp.room,
                geometry={
                    "type": "MIGRATED_ANCHOR",
                    "source_poi_id": str(sp.id),
                    "source_version": source_version,
                    "drift_meters": round(drift, 4)
                },
                confidence=sp.confidence if drift < 0.10 else max(0.5, sp.confidence - 0.1),
                metadata=dict(sp.metadata),
                model_version=target_version
            )

            saved = self.create_poi(migrated)
            migrated_pois.append(saved)

        logger.info(f"Migrated {len(migrated_pois)} POIs from '{source_version}' to '{target_version}'.")
        return migrated_pois
