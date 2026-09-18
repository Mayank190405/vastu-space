"""
VĀSTU Immutable Model Version Registry:
Guarantees strict immutability across all model releases.
Once a model version (e.g. V1) is registered, its state, artifacts, representation bundles,
spatial cells, and metadata can never be overwritten or mutated.
"""

import copy
import logging
from typing import Dict, Any, List, Optional
from core.schemas.model_version import ModelVersion
from core.schemas.representation_bundle import TriRepresentationBundle
from core.spatial.cell import SpatialCellModel
from core.schemas.poi import PointOfInterest
from core.schemas.navigation_graph import NavigationGraph

logger = logging.getLogger("vastu.versioning.registry")

class ImmutableVersionError(Exception):
    """Raised when an attempt is made to overwrite or modify an existing immutable model version."""
    pass

class ImmutableModelRegistry:
    """
    Central repository for immutable model versions and their decoupled artifacts.
    Enforces that published models are frozen permanently and historical versions (V1)
    remain independently viewable after subsequent versions (V2) are published.
    """
    def __init__(self):
        # Version ID -> ModelVersion
        self._versions: Dict[str, ModelVersion] = {}
        # Version ID -> TriRepresentationBundle
        self._bundles: Dict[str, TriRepresentationBundle] = {}
        # Version ID -> Dict[cell_id, SpatialCellModel]
        self._cells: Dict[str, Dict[str, SpatialCellModel]] = {}
        # Version ID -> List[PointOfInterest]
        self._pois: Dict[str, List[PointOfInterest]] = {}
        # Version ID -> Optional[NavigationGraph]
        self._nav_graphs: Dict[str, Optional[NavigationGraph]] = {}

    def register_version(
        self,
        version: ModelVersion,
        bundle: Optional[TriRepresentationBundle] = None,
        cells: Optional[Dict[str, SpatialCellModel]] = None,
        pois: Optional[List[PointOfInterest]] = None,
        navigation_graph: Optional[NavigationGraph] = None
    ) -> ModelVersion:
        """
        Registers a new model version.
        Guarantees that an existing version cannot be overwritten under any circumstances.
        """
        vid = version.model_version_id
        if vid in self._versions:
            raise ImmutableVersionError(
                f"Model version '{vid}' already exists and is immutable. "
                "Published model versions can never be overwritten."
            )

        # Freeze deep copies to guarantee caller mutations cannot corrupt registered state
        self._versions[vid] = copy.deepcopy(version)

        if bundle is not None:
            self._bundles[vid] = copy.deepcopy(bundle)

        if cells is not None:
            # Store isolated copies of the spatial cells for this specific version
            frozen_cells = {}
            for cid, c in cells.items():
                cell_copy = SpatialCellModel(
                    cell_id=c.cell_id,
                    coordinates=c.coordinates,
                    cell_size_m=c.cell_size_m,
                    margin_m=c.margin_m,
                    origin_world=c.origin_world.copy(),
                    rotation_matrix=c.rotation_matrix.copy()
                )
                cell_copy.points_world = c.points_world.copy()
                cell_copy.colors = c.colors.copy()
                cell_copy.normals = c.normals.copy()
                cell_copy.confidences = c.confidences.copy()
                cell_copy.quality_score = c.quality_score
                cell_copy.version = c.version
                cell_copy.is_dirty = False
                if c.local_mesh_vertices is not None:
                    cell_copy.local_mesh_vertices = c.local_mesh_vertices.copy()
                if c.local_mesh_faces is not None:
                    cell_copy.local_mesh_faces = c.local_mesh_faces.copy()
                frozen_cells[cid] = cell_copy
            self._cells[vid] = frozen_cells
        else:
            self._cells[vid] = {}

        if pois is not None:
            self._pois[vid] = copy.deepcopy(pois)
        else:
            self._pois[vid] = []

        if navigation_graph is not None:
            self._nav_graphs[vid] = copy.deepcopy(navigation_graph)
        else:
            self._nav_graphs[vid] = None

        logger.info(f"Immutable model version '{vid}' successfully registered.")
        return self._versions[vid]

    def get_version(self, version_id: str) -> Optional[ModelVersion]:
        """Retrieves metadata for a specific immutable model version."""
        v = self._versions.get(version_id)
        return copy.deepcopy(v) if v is not None else None

    def get_bundle(self, version_id: str) -> Optional[TriRepresentationBundle]:
        """Retrieves the complete representation bundle for a specific version."""
        b = self._bundles.get(version_id)
        return copy.deepcopy(b) if b is not None else None

    def get_cells(self, version_id: str) -> Dict[str, SpatialCellModel]:
        """Retrieves the spatial cell partition snapshot for a specific version."""
        return self._cells.get(version_id, {})

    def get_pois(self, version_id: str) -> List[PointOfInterest]:
        """Retrieves POIs associated with a specific model version."""
        return copy.deepcopy(self._pois.get(version_id, []))

    def get_navigation(self, version_id: str) -> Optional[NavigationGraph]:
        """Retrieves navigation graph associated with a specific model version."""
        g = self._nav_graphs.get(version_id)
        return copy.deepcopy(g) if g is not None else None

    def list_versions(self, model_id: Optional[str] = None) -> List[ModelVersion]:
        """Lists all registered model versions, optionally filtered by model_id."""
        versions = list(self._versions.values())
        if model_id is not None:
            versions = [v for v in versions if v.model_id == model_id or str(v.project_id) == model_id]
        # Return sorted by creation timestamp
        return sorted(versions, key=lambda v: v.creation_timestamp)

    def get_lineage(self, leaf_version_id: str) -> List[ModelVersion]:
        """Traces backward from leaf version to root parent version."""
        lineage = []
        curr_id: Optional[str] = leaf_version_id
        while curr_id and curr_id in self._versions:
            v = self._versions[curr_id]
            lineage.append(v)
            curr_id = v.parent_version or v.parent_version_id
        return lineage[::-1]
