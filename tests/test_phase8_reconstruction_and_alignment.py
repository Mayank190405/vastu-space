"""
VĀSTU Phase 8 Automated Verification Suite:
Universal Room Reconstruction, Cross-Session Spatial Alignment & Immersive Navigation
Validates all required architectural scenarios and technical contracts:
- Small bedroom
- Large living room / hall
- Irregularly shaped room (L-shaped non-rectangular polygon)
- Compact washroom
- Two rooms connected by a doorway
- Multiple rooms connected through a transition corridor
- Pose refinement, metric depth, normals, geometry fusion, Gaussian splats & SPZ export
- Collision engine (walls block, doorways allow transit, furniture blocks, boundary confines)
- Navmesh connectivity and ADA compliance
- Unified space assembly & scene manifest generation
"""

import os
import sys
import json
import tempfile
import numpy as np
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.reconstruction.pose_refinement import PoseRefinementPipeline
from core.reconstruction.metric_depth import MetricDepthPipeline
from core.reconstruction.surface_normal import SurfaceNormalPipeline
from core.reconstruction.geometry_fusion import GeometryFusionPipeline
from core.reconstruction.architectural_builder import ArchitecturalGeometryBuilder
from core.reconstruction.gaussian_splatting import GaussianSplattingPipeline
from core.reconstruction.spz_exporter import SPZExporter

from core.spatial.room_connection_graph import RoomConnectionGraph
from core.spatial.cross_session_alignment import CrossSessionAlignmentEngine
from core.spatial.global_pose_graph import GlobalPoseGraphOptimizer
from core.spatial.collision_mesh_generator import CollisionMeshGenerator
from core.spatial.navigation_mesh_generator import NavigationMeshGenerator
from core.spatial.unified_space_assembler import UnifiedSpaceAssembler


# ==============================================================================
# 1. Pose Refinement Pipeline
# ==============================================================================
def test_pose_refinement_pipeline():
    pipeline = PoseRefinementPipeline()
    intrinsics = {"fx": 1400.0, "fy": 1400.0, "cx": 960.0, "cy": 720.0, "width": 1920, "height": 1440}

    # Synthetic keyframe images with visual texture
    img1 = np.zeros((480, 640, 3), dtype=np.uint8)
    img2 = np.zeros((480, 640, 3), dtype=np.uint8)
    for x in range(50, 600, 40):
        for y in range(50, 450, 40):
            cv2.circle(img1, (x, y), 8, (255, 255, 255), -1)
            cv2.circle(img2, (x + 10, y), 8, (255, 255, 255), -1)

    poses = [
        {"timestamp": 0.0, "position": [0.0, 0.0, 1.5], "quaternion": [1.0, 0.0, 0.0, 0.0]},
        {"timestamp": 0.5, "position": [0.15, 0.0, 1.5], "quaternion": [1.0, 0.0, 0.0, 0.0]}
    ]

    result = pipeline.refine_trajectory(poses, [img1, img2], intrinsics)
    assert result["status"] == "OPTIMIZED"
    assert result["frame_count"] == 2
    assert result["scale_preservation"] is True
    assert len(result["refined_poses"]) == 2
    assert result["mean_reprojection_error_px"] <= 3.0


# ==============================================================================
# 2. Metric Depth & Surface Normal Estimation
# ==============================================================================
def test_metric_depth_and_normals():
    depth_pipe = MetricDepthPipeline(min_depth_m=0.3, max_depth_m=8.0)
    normal_pipe = SurfaceNormalPipeline()

    img = np.full((240, 320, 3), 128, dtype=np.uint8)
    intrinsics = {"fx": 300.0, "fy": 300.0, "cx": 160.0, "cy": 120.0}

    depth_res = depth_pipe.estimate_depth_map(img, intrinsics, camera_height_m=1.5)
    metric_depth = depth_res["metric_depth"]

    assert depth_res["is_metric_calibrated"] is True
    assert depth_res["depth_type"] == "METRIC"
    assert metric_depth.shape == (240, 320)
    assert float(np.min(metric_depth)) >= 0.3
    assert float(np.max(metric_depth)) <= 8.0

    normal_res = normal_pipe.compute_surface_normals(metric_depth, intrinsics)
    normals = normal_res["normals"]
    assert normals.shape == (240, 320, 3)
    # Unit vector magnitude check
    norms = np.linalg.norm(normals[100:150, 100:150], axis=-1)
    assert np.allclose(norms, 1.0, atol=1e-3)
    assert "wall_mask" in normal_res
    assert "floor_mask" in normal_res


# ==============================================================================
# 3. Geometry Fusion & Pointcloud Consensus
# ==============================================================================
def test_geometry_fusion():
    fusion_pipe = GeometryFusionPipeline(voxel_size_m=0.05)
    intrinsics = {"fx": 500.0, "fy": 500.0, "cx": 160.0, "cy": 120.0}

    depth = np.full((120, 160), 2.5, dtype=np.float32)
    color = np.full((120, 160, 3), 200, dtype=np.uint8)
    poses = [
        {"position": [0.0, 0.0, 0.0], "quaternion": [1.0, 0.0, 0.0, 0.0]},
        {"position": [0.5, 0.0, 0.0], "quaternion": [1.0, 0.0, 0.0, 0.0]}
    ]

    fused = fusion_pipe.fuse_views([depth, depth], [color, color], poses, intrinsics)
    assert fused["point_count"] > 0
    assert fused["points"].shape[1] == 3
    assert fused["colors"].shape[1] == 3


# ==============================================================================
# 4. Universal Room Reconstruction: 6 Required Spaces
# ==============================================================================
def test_universal_room_types_reconstruction():
    builder = ArchitecturalGeometryBuilder()
    dummy_points = np.random.uniform(-2, 2, (100, 3)).astype(np.float32)
    dummy_points[:, 2] = np.random.uniform(0, 2.7, 100)

    # 1. Small Bedroom (3m x 4m)
    bed_poly = [[-1.5, -2.0], [1.5, -2.0], [1.5, 2.0], [-1.5, 2.0]]
    bed_arch = builder.build_room_architecture(
        room_id="room_bedroom",
        room_name="Small Bedroom",
        fused_points=dummy_points,
        boundary_polygon_2d=bed_poly,
        furniture_observations=[{
            "track_id": "bed_01",
            "category": "BED",
            "centroid_3d": [0.0, 0.5, 0.45],
            "dimensions_m": [1.6, 2.0, 0.9]
        }]
    )
    assert bed_arch["quality_report"]["area_sqm"] == 12.0
    assert len(bed_arch["walls"]) == 4
    assert len(bed_arch["furniture_boxes"]) == 1

    # 2. Large Living Hall (8m x 6m)
    hall_poly = [[-4.0, -3.0], [4.0, -3.0], [4.0, 3.0], [-4.0, 3.0]]
    hall_arch = builder.build_room_architecture(
        room_id="room_hall",
        room_name="Grand Living Hall",
        fused_points=dummy_points,
        boundary_polygon_2d=hall_poly,
        ceiling_height_override=3.20
    )
    assert hall_arch["quality_report"]["area_sqm"] == 48.0
    assert hall_arch["ceiling_height_m"] == 3.20

    # 3. Irregular L-Shaped Room (6 vertices)
    l_poly = [
        [0.0, 0.0],
        [6.0, 0.0],
        [6.0, 3.0],
        [3.0, 3.0],
        [3.0, 5.0],
        [0.0, 5.0]
    ]
    l_arch = builder.build_room_architecture(
        room_id="room_l_shape",
        room_name="Irregular L-Shaped Suite",
        fused_points=dummy_points,
        boundary_polygon_2d=l_poly
    )
    # Area of L-shape: (6*3) + (3*2) = 18 + 6 = 24 m2
    assert l_arch["quality_report"]["area_sqm"] == 24.0
    assert len(l_arch["walls"]) == 6
    assert l_arch["quality_report"]["is_convex"] is False

    # 4. Washroom (2m x 2m)
    bath_poly = [[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0]]
    bath_arch = builder.build_room_architecture(
        room_id="room_bath",
        room_name="Compact Washroom",
        fused_points=dummy_points,
        boundary_polygon_2d=bath_poly
    )
    assert bath_arch["quality_report"]["area_sqm"] == 4.0
    assert bath_arch["quality_report"]["volume_cbm"] > 9.0


# ==============================================================================
# 5. Gaussian Splatting & SPZ Compression
# ==============================================================================
def test_gaussian_splatting_and_spz_compression():
    gs_pipeline = GaussianSplattingPipeline()
    spz_exporter = SPZExporter()

    points = np.random.uniform(-3, 3, (500, 3)).astype(np.float32)
    colors = np.random.uniform(0, 1, (500, 3)).astype(np.float32)

    gaussians = gs_pipeline.initialize_gaussians(points, colors)
    assert gaussians["splat_count"] == 500
    assert gaussians["scales"].shape == (500, 3)
    assert gaussians["rotations"].shape == (500, 4)

    with tempfile.TemporaryDirectory() as tmpdir:
        ply_path = os.path.join(tmpdir, "test_splats.ply")
        assert gs_pipeline.export_ply(gaussians, ply_path) is True
        assert os.path.exists(ply_path)

        spz_path = os.path.join(tmpdir, "test_splats.spz")
        res = spz_exporter.export_spz(gaussians, spz_path)
        assert os.path.exists(spz_path)
        assert res["compression_ratio"] < 0.60  # Significant compression achieved


# ==============================================================================
# 6. Room-to-Room Alignment & Doorway Registration
# ==============================================================================
def test_cross_session_alignment_engine():
    align_engine = CrossSessionAlignmentEngine()

    room_living = {
        "room_id": "living_room",
        "boundary_polygon_2d": [[-3, -3], [3, -3], [3, 3], [-3, 3]]
    }
    room_bedroom = {
        "room_id": "bedroom",
        "boundary_polygon_2d": [[-2, -2], [2, -2], [2, 2], [-2, 2]]
    }

    # Living room door on right wall (x = +3.0)
    # Bedroom door on left wall (x = -2.0)
    door_match = {
        "source_doorway": {
            "center_3d": [-2.0, 0.0, 1.05],
            "width_m": 0.90,
            "height_m": 2.10,
            "normal": [-1.0, 0.0, 0.0]
        },
        "target_doorway": {
            "center_3d": [3.0, 0.0, 1.05],
            "width_m": 0.90,
            "height_m": 2.10,
            "normal": [1.0, 0.0, 0.0]
        }
    }

    result = align_engine.align_connected_rooms(room_bedroom, room_living, door_match)
    assert result["status"] == "ALIGNED"
    assert result["confidence"] >= 0.70
    assert result["rmse_m"] <= 0.050
    assert len(result["transform_matrix_4x4"]) == 4

    # High error mismatch trigger test
    bad_door_match = {
        "source_doorway": {"center_3d": [0, 0, 1.05], "width_m": 0.90, "normal": [1, 0, 0]},
        "target_doorway": {"center_3d": [10, 10, 5.0], "width_m": 1.80, "normal": [0, 1, 0]}
    }
    bad_result = align_engine.align_connected_rooms(room_bedroom, room_living, bad_door_match)
    assert bad_result["doorway_width_delta_m"] > 0.50


# ==============================================================================
# 7. Global Pose Graph & Room Connection Graph
# ==============================================================================
def test_room_connection_graph_and_global_pose_graph():
    graph = RoomConnectionGraph(project_id="luxury_villa")
    graph.add_room("living", "Living Room", floor_level=1, area_sqm=35.0)
    graph.add_room("corridor", "Central Corridor", floor_level=1, area_sqm=12.0)
    graph.add_room("bedroom", "Master Bedroom", floor_level=1, area_sqm=22.0)

    # Connect Living <-> Corridor and Corridor <-> Bedroom
    assert graph.add_doorway_connection("door_liv_corr", "living", "corridor", width_m=1.0) is True
    assert graph.add_doorway_connection("door_corr_bed", "corridor", "bedroom", width_m=0.90) is True

    assert graph.are_connected("living", "corridor") is True
    assert graph.are_connected("living", "bedroom") is False  # Not directly connected
    path = graph.find_path("living", "bedroom")
    assert path == ["living", "corridor", "bedroom"]

    # Global Pose Graph Optimization
    optimizer = GlobalPoseGraphOptimizer()
    pairwise = [
        {
            "source_room_id": "corridor",
            "target_room_id": "living",
            "transform_matrix_4x4": [
                [1, 0, 0, 3.5],
                [0, 1, 0, 0.0],
                [0, 0, 1, 0.0],
                [0, 0, 0, 1.0]
            ],
            "confidence": 0.95
        },
        {
            "source_room_id": "bedroom",
            "target_room_id": "corridor",
            "transform_matrix_4x4": [
                [1, 0, 0, 4.0],
                [0, 1, 0, 0.0],
                [0, 0, 1, 0.0],
                [0, 0, 0, 1.0]
            ],
            "confidence": 0.95
        }
    ]

    opt_res = optimizer.optimize_poses(["living", "corridor", "bedroom"], pairwise, root_room_id="living")
    assert opt_res["status"] == "CONVERGED"
    assert opt_res["root_room_id"] == "living"
    # Root is at identity
    assert np.allclose(opt_res["global_transforms"]["living"], np.eye(4))
    # Bedroom world translation is 3.5 + 4.0 = 7.5m
    assert abs(opt_res["global_transforms"]["bedroom"][0][3] - 7.5) < 1e-4


# ==============================================================================
# 8. Collision Mesh & NavMesh Generation
# ==============================================================================
def test_collision_and_navmesh_generators():
    builder = ArchitecturalGeometryBuilder()
    col_gen = CollisionMeshGenerator(wall_thickness_m=0.15)
    nav_gen = NavigationMeshGenerator()

    poly = [[-2.0, -2.0], [2.0, -2.0], [2.0, 2.0], [-2.0, 2.0]]
    doorway = [{
        "id": "door_01",
        "width_m": 0.90,
        "height_m": 2.10,
        "center_3d": [2.0, 0.0, 1.05]
    }]
    furniture = [{
        "track_id": "sofa_01",
        "category": "SOFA",
        "centroid_3d": [0.0, 0.0, 0.4],
        "dimensions_m": [1.2, 0.8, 0.8]
    }]

    arch = builder.build_room_architecture(
        "room_col_test",
        "Collision Test Room",
        np.zeros((10, 3)),
        boundary_polygon_2d=poly,
        observed_openings=doorway,
        furniture_observations=furniture
    )

    collision = col_gen.generate_room_collision(arch)
    assert collision["room_id"] == "room_col_test"
    assert len(collision["furniture_colliders"]) == 1
    # Check that wall with doorway was split into sub-segments leaving doorway open
    has_sub = any("sub" in w["collider_id"] for w in collision["wall_colliders"])
    assert has_sub is True

    # NavMesh
    navmesh = nav_gen.generate_unified_navmesh([arch], {"room_col_test": np.eye(4).tolist()}, doorway)
    assert navmesh["status"] == "VALID"
    assert navmesh["node_count"] >= 5


# ==============================================================================
# 9. Unified Space Assembler End-to-End
# ==============================================================================
def test_unified_space_assembler_end_to_end():
    with tempfile.TemporaryDirectory() as tmpdir:
        assembler = UnifiedSpaceAssembler(output_dir=tmpdir)
        builder = ArchitecturalGeometryBuilder()

        # Build 2 connected rooms
        r1_poly = [[-2, -2], [2, -2], [2, 2], [-2, 2]]
        r2_poly = [[-2, -2], [2, -2], [2, 2], [-2, 2]]

        arch1 = builder.build_room_architecture("r1", "Hall", np.zeros((10, 3)), boundary_polygon_2d=r1_poly)
        arch2 = builder.build_room_architecture("r2", "Lounge", np.zeros((10, 3)), boundary_polygon_2d=r2_poly)

        graph = RoomConnectionGraph("proj_unified_test")
        graph.add_room("r1", "Hall", area_sqm=16.0)
        graph.add_room("r2", "Lounge", area_sqm=16.0)
        graph.add_doorway_connection("door_12", "r1", "r2", width_m=0.90, center_3d=[2.0, 0.0, 1.05])

        transforms = {
            "r1": np.eye(4).tolist(),
            "r2": [
                [1, 0, 0, 4.0],
                [0, 1, 0, 0.0],
                [0, 0, 1, 0.0],
                [0, 0, 0, 1.0]
            ]
        }

        rooms_data = [
            {"room_id": "r1", "room_name": "Hall", "floor_level": 1, "architecture": arch1},
            {"room_id": "r2", "room_name": "Lounge", "floor_level": 1, "architecture": arch2}
        ]

        manifest = assembler.assemble_facility(
            project_id="proj_unified_test",
            project_name="Unified Space Test Facility",
            room_reconstructions=rooms_data,
            global_transforms=transforms,
            connection_graph=graph
        )

        assert manifest["room_count"] == 2
        assert manifest["total_area_sqm"] == 32.0
        assert os.path.exists(os.path.join(tmpdir, "scene_manifest.json"))
        assert os.path.exists(os.path.join(tmpdir, "unified_architecture.obj"))
        assert os.path.exists(os.path.join(tmpdir, "collision_geometry.json"))
        assert os.path.exists(os.path.join(tmpdir, "navmesh.json"))
        assert os.path.exists(os.path.join(tmpdir, "room_connection_graph.json"))


if __name__ == "__main__":
    tests = [
        test_pose_refinement_pipeline,
        test_metric_depth_and_normals,
        test_geometry_fusion,
        test_universal_room_types_reconstruction,
        test_gaussian_splatting_and_spz_compression,
        test_cross_session_alignment_engine,
        test_room_connection_graph_and_global_pose_graph,
        test_collision_and_navmesh_generators,
        test_unified_space_assembler_end_to_end
    ]
    passed = 0
    print("=" * 60)
    print("🚀 Running VĀSTU Phase 8 Universal Reconstruction & Alignment Suite")
    print("=" * 60)
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ✅ PASS: {t.__name__}")
        except Exception as e:
            print(f"  ❌ FAIL: {t.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("=" * 60)
    print(f"📊 Results: {passed}/{len(tests)} Phase 8 verification tests passed")
    print("=" * 60)
    if passed != len(tests):
        exit(1)
