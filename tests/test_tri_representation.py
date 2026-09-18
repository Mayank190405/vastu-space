"""
Test Suite: Tri-Representation Separation (Visual, Structural, and Collision Models)
Verifies:
1. Purpose-built decoupled models: Visual (photoreal), Structural (BIM/planes), Collision (NavMesh/obstacles).
2. Explicit linking through canonical metric transform and version metadata.
3. Acceptance Criterion:
   The web viewer can render the visual model while navigation operates exclusively on the collision/spatial model.
"""

import pytest
import uuid
import numpy as np

from core.schemas.representation_bundle import (
    VisualRepresentationMeta,
    StructuralRepresentationMeta,
    CollisionRepresentationMeta,
    TriRepresentationBundle
)
from core.schemas.metric_transform import MetricTransformSchema, MetricScaleSource
from core.representations.builder import TriRepresentationBuilder
from core.representations.runtime import RepresentationRuntimeCoordinator

def test_independent_three_representations_generation():
    """Verifies that Visual, Structural, and Collision models are constructed independently."""
    builder = TriRepresentationBuilder()

    # 1. Visual Model
    vis = builder.build_visual_representation(
        artifact_uri="s3://vastu-artifacts/projects/p1/models/lod0.glb",
        model_format="GLB",
        element_count=45000,
        texture_resolution="2048x2048"
    )
    assert vis.model_format == "GLB"
    assert vis.element_count == 45000
    assert vis.render_pipeline == "PBR_METALLIC_ROUGHNESS"

    # 2. Structural Model
    walls = [{"surface_area_m2": 12.0}, {"surface_area_m2": 15.0}]
    floors = [{"surface_area_m2": 25.0}]
    ceilings = [{"surface_area_m2": 25.0}]
    openings = [{"opening_type": "DOOR"}, {"opening_type": "WINDOW"}]
    rooms = [{"room_id": "r1"}]

    struc = builder.build_structural_representation(
        plane_graph_uri="s3://vastu-artifacts/projects/p1/structural/plane_graph.json",
        walls=walls,
        floors=floors,
        ceilings=ceilings,
        openings=openings,
        rooms=rooms
    )
    assert struc.wall_count == 2
    assert struc.floor_count == 1
    assert struc.total_surface_area_m2 == 52.0
    assert struc.format_type == "ANALYTICAL_PLANE_GRAPH"

    # 3. Collision Model
    obstacles = [
        {"obstacle_type": "DESK", "center": [1.5, 2.0, 0.4], "extent": [1.2, 0.6, 0.8]},
        {"obstacle_type": "COLUMN", "center": [3.0, 3.0, 1.4], "extent": [0.4, 0.4, 2.8]}
    ]
    col = builder.build_collision_representation(
        navmesh_graph_uri="s3://vastu-artifacts/projects/p1/navigation/navmesh.json",
        walkable_floors=floors,
        obstacles=obstacles,
        nav_nodes_count=80,
        nav_edges_count=160
    )
    assert col.walkable_surface_area_m2 == 25.0
    assert len(col.obstacles) == 2
    assert col.max_wheelchair_slope_deg == 4.76
    assert col.is_collision_simplified is True

def test_explicit_linking_via_bundle_and_canonical_transform():
    """Verifies that all three representations are explicitly linked via TriRepresentationBundle."""
    builder = TriRepresentationBuilder()

    vis = builder.build_visual_representation(
        artifact_uri="s3://vastu-artifacts/splats/splat.ply",
        model_format="3DGS_PLY",
        element_count=500000
    )
    struc = builder.build_structural_representation(
        plane_graph_uri="s3://vastu-artifacts/structural/graph.json",
        walls=[{"surface_area_m2": 10.0}],
        floors=[{"surface_area_m2": 20.0}],
        ceilings=[{"surface_area_m2": 20.0}],
        openings=[],
        rooms=[]
    )
    col = builder.build_collision_representation(
        navmesh_graph_uri="s3://vastu-artifacts/nav/navmesh.json",
        walkable_floors=[{"surface_area_m2": 20.0}],
        obstacles=[]
    )

    canonical_transform = MetricTransformSchema(
        scale=1.000,
        translation=[0.0, 0.0, 0.0],
        rotation_matrix=[[1,0,0],[0,1,0],[0,0,1]],
        rotation_quaternion=[0,0,0,1],
        matrix_4x4=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
        scale_source=MetricScaleSource.METRIC_LIDAR_AR,
        scale_confidence=0.99,
        canonical_frame="RIGHT_HANDED_Z_UP",
        floor_elevation_m=0.0
    )

    bundle = builder.create_bundle(
        model_version_id="mod_ver_2026_01",
        metric_transform=canonical_transform,
        visual_model=vis,
        structural_model=struc,
        collision_model=col
    )

    assert isinstance(bundle, TriRepresentationBundle)
    assert bundle.model_version_id == "mod_ver_2026_01"
    assert bundle.canonical_metric_transform.scale_source == MetricScaleSource.METRIC_LIDAR_AR
    assert bundle.visual_model.model_format == "3DGS_PLY"
    assert bundle.structural_model.wall_count == 1
    assert bundle.collision_model.walkable_surface_area_m2 == 20.0

def test_acceptance_criterion_web_viewer_renders_visual_while_navigation_uses_collision():
    """
    Acceptance Criterion:
    The web viewer can render the visual model while navigation operates exclusively on the collision/spatial model.
    """
    builder = TriRepresentationBuilder()
    coordinator = RepresentationRuntimeCoordinator()

    vis = builder.build_visual_representation(
        artifact_uri="s3://vastu-artifacts/models/pbr_mesh.glb",
        model_format="GLB",
        element_count=60000
    )
    struc = builder.build_structural_representation(
        plane_graph_uri="s3://vastu-artifacts/structural/graph.json",
        walls=[{"surface_area_m2": 15.0}],
        floors=[{"surface_area_m2": 30.0}],
        ceilings=[{"surface_area_m2": 30.0}],
        openings=[],
        rooms=[]
    )
    col = builder.build_collision_representation(
        navmesh_graph_uri="s3://vastu-artifacts/nav/navmesh.json",
        walkable_floors=[{"surface_area_m2": 30.0}],
        obstacles=[{"obstacle_id": "obs_table_01", "obstacle_type": "TABLE", "center": [2, 2, 0], "extent": [1, 1, 0.8]}]
    )

    canonical_transform = MetricTransformSchema(
        scale=1.025,
        translation=[2.0, 3.0, 0.0],
        rotation_matrix=[[1,0,0],[0,1,0],[0,0,1]],
        rotation_quaternion=[0,0,0,1],
        matrix_4x4=[[1.025,0,0,2.0],[0,1.025,0,3.0],[0,0,1.025,0.0],[0,0,0,1]],
        scale_source=MetricScaleSource.METRIC_LIDAR_AR,
        scale_confidence=0.98,
        canonical_frame="RIGHT_HANDED_Z_UP",
        floor_elevation_m=0.0
    )

    bundle = builder.create_bundle(
        model_version_id="mod_production_v1",
        metric_transform=canonical_transform,
        visual_model=vis,
        structural_model=struc,
        collision_model=col
    )

    # 1. Web Viewer loads ONLY the visual model
    render_result = coordinator.render_visual_model_in_web_viewer(bundle)
    assert render_result["is_rendered"] is True
    assert render_result["client"] == "ThreeJS_WebViewer"
    assert render_result["model_format"] == "GLB"
    assert render_result["loaded_collision_assets"] is False  # Zero collision overhead

    # 2. Indoor Navigation operates EXCLUSIVELY on the collision model
    nav_result = coordinator.navigate_on_collision_model(
        bundle=bundle,
        start_xyz=[0.0, 0.0, 0.0],
        goal_xyz=[4.0, 4.0, 0.0],
        wheelchair_mode=True
    )
    assert nav_result["path_found"] is True
    assert nav_result["client"] == "Navigation_Collision_Agent"
    assert nav_result["node_count"] == 3
    assert nav_result["obstacles_checked"] == 1
    assert nav_result["loaded_visual_assets"] is False  # Zero visual mesh/texture overhead
