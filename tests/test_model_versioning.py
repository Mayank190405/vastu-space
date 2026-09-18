"""
Unit & Integration Tests for Immutable Model Versioning & Comparison (Stage 18)
Validates:
1. Immutability guarantee: Overwriting V1 raises ImmutableVersionError.
2. Rescan evolution lifecycle: V1 -> affected-cell reconstruction -> registration -> boundary validation -> fusion -> V2.
3. Metadata completeness: model_id, version, parent_version, changed_cells, pipeline_version, algorithm_versions, quality_report, artifacts, creation_timestamp.
4. Model comparison: changed geometry, changed POIs, changed navigation, changed confidence.
5. Acceptance criterion: V1 remains independently viewable after V2 is published.
"""

import uuid
import pytest
import numpy as np

from core.schemas.model_version import ModelVersion, ModelArtifactKeys
from core.schemas.metric_transform import MetricTransformSchema, MetricScaleSource
from core.schemas.representation_bundle import (
    TriRepresentationBundle,
    VisualRepresentationMeta,
    StructuralRepresentationMeta,
    CollisionRepresentationMeta,
)
from core.representations.builder import TriRepresentationBuilder
from core.schemas.rescan_request import RescanRequest, RescanRegion, RequiredCaptureAction, ExpectedImprovement
from core.schemas.poi import PointOfInterest, POICoordinates
from core.schemas.navigation_graph import NavigationGraph, NavigationNode, NavigationEdge
from core.spatial.cell import SpatialCellModel
from core.versioning.registry import ImmutableModelRegistry, ImmutableVersionError
from core.versioning.rescan_pipeline import RescanVersioningPipeline
from core.versioning.comparator import ModelComparator
from core.quality.rescan_generator import TargetedRescanGenerator

def create_sample_v1_model():
    """Helper to construct a fully populated immutable V1 model version."""
    model_id = f"model_{uuid.uuid4().hex[:8]}"
    project_id = uuid.uuid4()
    v1_id = "v1_release_001"

    v1_artifacts = ModelArtifactKeys(
        lod0_glb_s3_key=f"models/{v1_id}/lod0.glb",
        splat_ply_s3_key=f"models/{v1_id}/splat.ply",
        navmesh_json_s3_key=f"models/{v1_id}/navmesh.json"
    )

    metric_transform = MetricTransformSchema(
        scale=1.0,
        translation=[0.0, 0.0, 0.0],
        rotation_matrix=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        rotation_quaternion=[0.0, 0.0, 0.0, 1.0],
        matrix_4x4=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        scale_source=MetricScaleSource.METRIC_LIDAR_AR,
        scale_confidence=0.98,
        canonical_frame="RIGHT_HANDED_Z_UP",
        floor_elevation_m=0.0
    )

    v1_model = ModelVersion(
        model_version_id=v1_id,
        model_id=model_id,
        project_id=project_id,
        version="1.0.0",
        semver="1.0.0",
        parent_version=None,
        changed_cells=[],
        pipeline_version="2.0.0",
        algorithm_versions={"sfm": "2.0.0", "depth": "1.2.0", "meshing": "3.1.0"},
        quality_report={"overall_score": 0.72, "status": "WARNING", "failure_reasons": ["HOLE in cell_c"]},
        artifacts=v1_artifacts,
        metric_transform=metric_transform,
        creation_timestamp="2026-09-06T10:00:00Z",
        created_at="2026-09-06T10:00:00Z",
        is_active_production=True,
        is_immutable=True
    )

    builder = TriRepresentationBuilder(project_id=project_id)
    vis = builder.build_visual_representation(
        artifact_uri=v1_artifacts.lod0_glb_s3_key,
        model_format="GLB",
        element_count=5000
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
        navmesh_graph_uri=v1_artifacts.navmesh_json_s3_key,
        walkable_floors=[{"surface_area_m2": 40.0}],
        obstacles=[]
    )
    v1_bundle = builder.create_bundle(
        model_version_id=v1_id,
        metric_transform=metric_transform,
        visual_model=vis,
        structural_model=struc,
        collision_model=col
    )

    # Spatial Cells for V1
    cell_a = SpatialCellModel("cell_a", (0, 0, 0), cell_size_m=1.5)
    cell_a.points_world = np.array([[0.2, 0.2, 0.5], [0.4, 0.4, 0.5]], dtype=np.float64)
    cell_a.colors = np.array([[200, 200, 200], [210, 210, 210]], dtype=np.uint8)
    cell_a.normals = np.array([[0, 0, 1], [0, 0, 1]], dtype=np.float64)
    cell_a.confidences = np.array([0.95, 0.95], dtype=np.float64)
    cell_a.version = 1

    cell_c = SpatialCellModel("cell_c", (1, 0, 0), cell_size_m=1.5)
    cell_c.points_world = np.array([[1.2, 0.2, 0.5]], dtype=np.float64)
    cell_c.colors = np.array([[100, 100, 100]], dtype=np.uint8)
    cell_c.normals = np.array([[0, 0, 1]], dtype=np.float64)
    cell_c.confidences = np.array([0.55], dtype=np.float64)
    cell_c.version = 1

    cells = {"cell_a": cell_a, "cell_c": cell_c}

    # Sample POI in V1
    poi1 = PointOfInterest(
        id=uuid.uuid4(),
        project_id=project_id,
        name="Lobby Entrance",
        category="ENTRANCE",
        coordinates=POICoordinates(x=0.2, y=0.2, z=0.5),
        model_version="1.0.0"
    )

    # Sample Navigation in V1
    nav_graph = NavigationGraph(
        project_id=project_id,
        nodes=[NavigationNode(id="node_01", position=[0.2, 0.2, 0.0])],
        edges=[NavigationEdge(id="edge_01", from_node="node_01", to_node="node_01", distance_meters=1.0)]
    )

    return v1_model, v1_bundle, cells, [poi1], nav_graph

def test_immutability_guarantee():
    """Verify that an existing model version cannot be overwritten."""
    registry = ImmutableModelRegistry()
    v1, bundle, cells, pois, nav = create_sample_v1_model()

    # 1. First registration succeeds
    registered = registry.register_version(v1, bundle=bundle, cells=cells, pois=pois, navigation_graph=nav)
    assert registered.model_version_id == v1.model_version_id

    # 2. Attempting to overwrite V1 must raise ImmutableVersionError
    with pytest.raises(ImmutableVersionError, match="already exists and is immutable"):
        registry.register_version(v1, bundle=bundle)

def test_targeted_rescan_evolution_v1_to_v2():
    """Verify V1 -> affected-cell reconstruction -> registration -> boundary validation -> fusion -> V2."""
    registry = ImmutableModelRegistry()
    v1, bundle, cells, pois, nav = create_sample_v1_model()
    registry.register_version(v1, bundle=bundle, cells=cells, pois=pois, navigation_graph=nav)

    pipeline = RescanVersioningPipeline(registry)

    # Target rescan task for cell_c
    generator = TargetedRescanGenerator()
    rescan_req = generator.generate_rescan_task(
        project_id=v1.project_id,
        cell_id="cell_c",
        region_bounds={
            "center_xyz": [1.2, 0.2, 0.5],
            "min_xyz": [0.5, -0.5, 0.0],
            "max_xyz": [2.0, 1.0, 1.5]
        },
        defect_type="HOLE",
        detailed_reason="Surface gap in cell_c",
        current_metric_value=0.25,
        priority="CRITICAL"
    )

    # High quality delta points captured for cell_c
    delta_points = np.array([
        [1.1, 0.1, 0.5],
        [1.2, 0.2, 0.5],
        [1.3, 0.3, 0.5],
        [1.4, 0.4, 0.5]
    ], dtype=np.float64)
    delta_colors = np.array([[220, 220, 220]] * 4, dtype=np.uint8)
    delta_normals = np.array([[0.0, 0.0, 1.0]] * 4, dtype=np.float64)
    delta_confidences = np.array([0.96] * 4, dtype=np.float64)

    # Execute evolution
    result = pipeline.execute_rescan_evolution(
        base_version_id=v1.model_version_id,
        rescan_request=rescan_req,
        new_points_world=delta_points,
        new_colors=delta_colors,
        new_normals=delta_normals,
        new_confidences=delta_confidences,
        target_version_semver="1.1.0"
    )

    assert result["status"] == "SUCCESS"
    assert result["base_version"] == "1.0.0"
    assert result["new_version"] == "1.1.0"
    assert result["changed_cells"] == ["cell_c"]
    assert result["boundary_validation"]["continuous"] is True
    assert result["boundary_validation"]["max_observed_gap_m"] <= 0.05
    assert result["v1_preserved_intact"] is True

    # Check V2 in registry
    v2_id = result["new_version_id"]
    v2_model = registry.get_version(v2_id)
    assert v2_model is not None
    assert v2_model.parent_version == v1.version or v2_model.parent_version == v1.model_version_id
    assert v2_model.changed_cells == ["cell_c"]

def test_metadata_storage_completeness():
    """Verify all required metadata fields are stored on model version."""
    v1, _, _, _, _ = create_sample_v1_model()

    # Must store: model_id, version, parent_version, changed_cells, pipeline_version,
    # algorithm_versions, quality_report, artifacts, creation_timestamp
    assert v1.model_id is not None
    assert v1.version == "1.0.0"
    assert v1.parent_version is None
    assert isinstance(v1.changed_cells, list)
    assert v1.pipeline_version == "2.0.0"
    assert "sfm" in v1.algorithm_versions
    assert v1.quality_report["overall_score"] == 0.72
    assert v1.artifacts.lod0_glb_s3_key.endswith("lod0.glb")
    assert v1.creation_timestamp == "2026-09-06T10:00:00Z"

def test_model_comparison_engine():
    """Verify 4-way comparison across geometry, POIs, navigation, and confidence."""
    registry = ImmutableModelRegistry()
    v1, bundle, cells, pois, nav = create_sample_v1_model()
    registry.register_version(v1, bundle=bundle, cells=cells, pois=pois, navigation_graph=nav)

    pipeline = RescanVersioningPipeline(registry)
    generator = TargetedRescanGenerator()
    rescan_req = generator.generate_rescan_task(
        project_id=v1.project_id,
        cell_id="cell_c",
        region_bounds={
            "center_xyz": [1.2, 0.2, 0.5],
            "min_xyz": [0.5, -0.5, 0.0],
            "max_xyz": [2.0, 1.0, 1.5]
        },
        defect_type="HOLE",
        detailed_reason="Hole in cell_c",
        current_metric_value=0.25
    )

    delta_pts = np.array([[1.2, 0.2, 0.55], [1.3, 0.3, 0.55]], dtype=np.float64)
    res = pipeline.execute_rescan_evolution(
        base_version_id=v1.model_version_id,
        rescan_request=rescan_req,
        new_points_world=delta_pts,
        new_colors=np.array([[200, 200, 200], [200, 200, 200]], dtype=np.uint8),
        new_normals=np.array([[0, 0, 1], [0, 0, 1]], dtype=np.float64),
        new_confidences=np.array([0.95, 0.95], dtype=np.float64),
        target_version_semver="1.1.0"
    )
    v2_id = res["new_version_id"]

    comparator = ModelComparator(registry)
    diff = comparator.compare(v1.model_version_id, v2_id)

    # 1. Changed Geometry
    assert "cell_c" in diff.geometry.changed_cells
    assert diff.geometry.is_geometry_altered is True

    # 2. Changed POIs
    assert diff.pois.unaltered_poi_count == 1

    # 3. Changed Navigation
    assert diff.navigation.walkable_nodes_delta == 0

    # 4. Changed Confidence
    assert diff.confidence.score_before == 0.72
    assert diff.confidence.score_after == 0.94
    assert diff.confidence.global_score_delta > 0

def test_acceptance_criterion_v1_independently_viewable():
    """Acceptance criterion: V1 remains independently viewable after V2 is published."""
    registry = ImmutableModelRegistry()
    v1, bundle, cells, pois, nav = create_sample_v1_model()
    registry.register_version(v1, bundle=bundle, cells=cells, pois=pois, navigation_graph=nav)

    pipeline = RescanVersioningPipeline(registry)
    generator = TargetedRescanGenerator()
    rescan_req = generator.generate_rescan_task(
        project_id=v1.project_id,
        cell_id="cell_c",
        region_bounds={
            "center_xyz": [1.2, 0.2, 0.5],
            "min_xyz": [0.5, -0.5, 0.0],
            "max_xyz": [2.0, 1.0, 1.5]
        },
        defect_type="HOLE",
        detailed_reason="Hole in cell_c",
        current_metric_value=0.25
    )
    res = pipeline.execute_rescan_evolution(
        base_version_id=v1.model_version_id,
        rescan_request=rescan_req,
        new_points_world=np.array([[1.2, 0.2, 0.5]], dtype=np.float64),
        new_colors=np.array([[200, 200, 200]], dtype=np.uint8),
        new_normals=np.array([[0, 0, 1]], dtype=np.float64),
        new_confidences=np.array([0.9], dtype=np.float64),
        target_version_semver="1.1.0"
    )
    v2_id = res["new_version_id"]

    # Retrieve V1 and V2 independently
    v1_retrieved = registry.get_version(v1.model_version_id)
    v2_retrieved = registry.get_version(v2_id)

    assert v1_retrieved is not None
    assert v2_retrieved is not None
    assert v1_retrieved.version == "1.0.0"
    assert v2_retrieved.version == "1.1.0"

    # Verify V1's visual bundle was NOT modified
    v1_bundle_retrieved = registry.get_bundle(v1.model_version_id)
    v2_bundle_retrieved = registry.get_bundle(v2_id)

    assert v1_bundle_retrieved.visual_model.artifact_uri == "models/v1_release_001/lod0.glb"
    assert v2_bundle_retrieved.visual_model.artifact_uri == f"models/{v2_id}/lod0.glb"
    assert v1_bundle_retrieved.visual_model.artifact_uri != v2_bundle_retrieved.visual_model.artifact_uri
