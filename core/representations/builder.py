"""
Tri-Representation Builder:
Constructs Visual, Structural, and Collision models as decoupled entities,
linked by a shared canonical metric transformation and version metadata.
"""

from typing import List, Dict, Any, Optional
import uuid
import numpy as np

from core.schemas.representation_bundle import (
    VisualRepresentationMeta,
    StructuralRepresentationMeta,
    CollisionRepresentationMeta,
    CollisionObstacle,
    TriRepresentationBundle
)
from core.schemas.metric_transform import MetricTransformSchema

class TriRepresentationBuilder:
    def __init__(self, project_id: Optional[uuid.UUID] = None):
        self.project_id = project_id or uuid.uuid4()

    def build_visual_representation(
        self,
        artifact_uri: str,
        model_format: str = "GLB",
        lod_level: str = "LOD0",
        element_count: int = 50000,
        file_size_bytes: int = 15000000,
        texture_resolution: str = "2048x2048"
    ) -> VisualRepresentationMeta:
        """Constructs the photorealistic visual model metadata."""
        return VisualRepresentationMeta(
            model_format=model_format,
            artifact_uri=artifact_uri,
            lod_level=lod_level,
            element_count=element_count,
            texture_resolution=texture_resolution,
            file_size_bytes=file_size_bytes,
            render_pipeline="PBR_METALLIC_ROUGHNESS" if model_format == "GLB" else "3D_GAUSSIAN_RASTERIZER"
        )

    def build_structural_representation(
        self,
        plane_graph_uri: str,
        walls: List[Dict[str, Any]],
        floors: List[Dict[str, Any]],
        ceilings: List[Dict[str, Any]],
        openings: List[Dict[str, Any]],
        rooms: List[Dict[str, Any]],
        bim_export_uri: Optional[str] = None
    ) -> StructuralRepresentationMeta:
        """Constructs the architectural BIM/CAD structural model metadata."""
        total_area = sum(w.get("surface_area_m2", 0.0) for w in walls) + sum(f.get("surface_area_m2", 0.0) for f in floors)
        return StructuralRepresentationMeta(
            plane_graph_uri=plane_graph_uri,
            bim_export_uri=bim_export_uri,
            wall_count=len(walls),
            floor_count=len(floors),
            ceiling_count=len(ceilings),
            opening_count=len(openings),
            room_count=len(rooms),
            total_surface_area_m2=float(round(total_area, 2)),
            format_type="ANALYTICAL_PLANE_GRAPH"
        )

    def build_collision_representation(
        self,
        navmesh_graph_uri: str,
        walkable_floors: List[Dict[str, Any]],
        obstacles: List[Dict[str, Any]],
        nav_nodes_count: int = 120,
        nav_edges_count: int = 240,
        collision_mesh_uri: Optional[str] = None
    ) -> CollisionRepresentationMeta:
        """Constructs the lightweight collision and navigation spatial model."""
        walkable_area = sum(f.get("surface_area_m2", 0.0) for f in walkable_floors)
        obs_list = []
        for o in obstacles:
            obs_list.append(CollisionObstacle(
                obstacle_id=o.get("obstacle_id", f"obs_{uuid.uuid4().hex[:6]}"),
                obstacle_type=o.get("obstacle_type", "FURNITURE"),
                center=o.get("center", [0.0, 0.0, 0.0]),
                extent=o.get("extent", [0.5, 0.5, 0.5]),
                is_walkable=False
            ))

        return CollisionRepresentationMeta(
            navmesh_graph_uri=navmesh_graph_uri,
            collision_mesh_uri=collision_mesh_uri,
            walkable_surface_area_m2=float(round(walkable_area, 2)),
            nav_nodes_count=nav_nodes_count,
            nav_edges_count=nav_edges_count,
            obstacles=obs_list,
            max_wheelchair_slope_deg=4.76,
            is_collision_simplified=True
        )

    def create_bundle(
        self,
        model_version_id: str,
        metric_transform: MetricTransformSchema,
        visual_model: VisualRepresentationMeta,
        structural_model: StructuralRepresentationMeta,
        collision_model: CollisionRepresentationMeta,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TriRepresentationBundle:
        """
        Assembles all three decoupled models under a unified bundle linked by canonical transform.
        """
        return TriRepresentationBundle(
            bundle_id=f"bundle_{uuid.uuid4().hex[:8]}",
            model_version_id=model_version_id,
            project_id=self.project_id,
            canonical_metric_transform=metric_transform,
            visual_model=visual_model,
            structural_model=structural_model,
            collision_model=collision_model,
            created_at="2026-09-06T17:20:00Z",
            metadata=metadata or {}
        )
