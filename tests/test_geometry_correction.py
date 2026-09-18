"""
Test Suite: Geometry Correction Using Architectural Constraints
Verifies:
1. Controlled geometric snapping is confidence-gated (applied on high conf, skipped on low conf).
2. Wall thickness estimation for parallel opposite-facing walls.
3. Floor and ceiling intersection snapping and opening regularization.
4. Boundary extent clipping.
5. Removal of phantom geometry and floating surfaces.
6. 7 structural validation audits (watertightness, self-intersections, disconnected walls, floating vertices,
   rounded corners, excessive smoothing, incorrect extents).
7. Acceptance Criterion: Output is structurally cleaner than raw reconstruction and every correction is measurable.
"""

import pytest
import numpy as np
import uuid

from core.correction.thickness import WallThicknessEstimator
from core.correction.snapping import ControlledGeometricSnapper
from core.correction.clipping import StructuralClipper
from core.correction.pruning import PhantomPruner
from core.correction.validator import GeometryQAValidator
from core.correction.corrector import ArchitecturalGeometryCorrector
from core.schemas.geometry_qa import GeometryQAReport, CorrectionRecord

def test_controlled_snapping_confidence_gated():
    """Verifies that snapping is strictly applied when confidence >= 0.60 and skipped when < 0.60."""
    snapper = ControlledGeometricSnapper(min_confidence_threshold=0.60)

    # Wall corners with slight vertical drift (+0.04m above floor, -0.05m below ceiling)
    corners_raw = [
        [0.0, 0.0, 0.04],
        [2.0, 0.0, 0.04],
        [2.0, 0.0, 2.75],
        [0.0, 0.0, 2.75]
    ]
    floor_z = 0.00
    ceiling_z = 2.80

    # Case 1: High confidence (0.85) -> Snapping MUST occur
    snapped_high, corrs_high = snapper.snap_wall_to_floor_and_ceiling(
        wall_id="wall_high_conf",
        wall_corners_3d=corners_raw,
        floor_z=floor_z,
        ceiling_z=ceiling_z,
        confidence=0.85
    )
    assert len(corrs_high) == 2
    types_high = [c["correction_type"] for c in corrs_high]
    assert "SNAP_FLOOR_INTERSECTION" in types_high
    assert "SNAP_CEILING_INTERSECTION" in types_high
    # Vertices must now be exactly at floor and ceiling levels
    assert snapped_high[0][2] == 0.00
    assert snapped_high[1][2] == 0.00
    assert snapped_high[2][2] == 2.80
    assert snapped_high[3][2] == 2.80
    assert corrs_high[0]["delta_metric_value"] > 0
    assert corrs_high[0]["delta_metric_unit"] == "mm"

    # Case 2: Low confidence (0.45) -> Snapping MUST BE SKIPPED
    snapped_low, corrs_low = snapper.snap_wall_to_floor_and_ceiling(
        wall_id="wall_low_conf",
        wall_corners_3d=corners_raw,
        floor_z=floor_z,
        ceiling_z=ceiling_z,
        confidence=0.45
    )
    assert len(corrs_low) == 1
    assert corrs_low[0]["correction_type"] == "SKIPPED_LOW_CONFIDENCE"
    # Vertices must NOT have moved
    assert snapped_low[0][2] == 0.04
    assert snapped_low[2][2] == 2.75

def test_wall_thickness_estimation():
    """Verifies physical wall thickness estimation between parallel opposite-facing surfaces."""
    estimator = WallThicknessEstimator(min_thickness_m=0.08, max_thickness_m=0.50)

    # Surface 1: x = 0 (normal [+1, 0, 0], d = 0)
    eq1 = np.array([1.0, 0.0, 0.0, 0.0])
    pts1 = np.array([[0.0, y, z] for y in np.linspace(0, 2, 5) for z in np.linspace(0, 2, 5)])

    # Surface 2: x = 0.20 (opposite facing normal [-1, 0, 0], d = 0.20)
    eq2 = np.array([-1.0, 0.0, 0.0, 0.20])
    pts2 = np.array([[0.20, y, z] for y in np.linspace(0, 2, 5) for z in np.linspace(0, 2, 5)])

    res = estimator.estimate_thickness_between_planes(eq1, eq2, pts1, pts2)
    assert res is not None
    thickness_m, conf, config = res
    assert pytest.approx(thickness_m, 0.005) == 0.20
    assert conf > 0.8
    assert config == "OPPOSITE_FACING"

def test_clipping_and_opening_regularization():
    """Verifies boundary clipping and door/window opening alignment."""
    clipper = StructuralClipper()

    # Opening test: Door threshold floating 50mm above floor
    openings = [
        {"opening_type": "DOOR", "width_m": 0.9, "height_m": 2.1, "center_3d": [1.0, 0.0, 1.10]},
        {"opening_type": "WINDOW", "width_m": 1.2, "height_m": 1.0, "center_3d": [3.0, 0.0, 0.50]}  # sill too low
    ]
    floor_z = 0.0

    reg_openings, corrs = clipper.regularize_openings("wall_entry", openings, floor_z)
    assert len(corrs) >= 1
    # Door center should now be floor_z + 2.1/2 = 1.05m
    assert pytest.approx(reg_openings[0]["center_3d"][2], 0.01) == 1.05

    # Extents clipping test: Corner overshooting room bounding box by 0.15m
    corners = [
        [-0.15, 0.0, 0.0],
        [4.20, 0.0, 0.0],
        [4.20, 0.0, 2.8],
        [-0.15, 0.0, 2.8]
    ]
    clipped, clip_corrs = clipper.clip_wall_extents("wall_long", corners, [0.0, 0.0, 0.0], [4.0, 4.0, 2.8])
    assert len(clip_corrs) == 1
    assert clip_corrs[0]["correction_type"] == "CLIP_EXTENTS"
    assert clip_corrs[0]["delta_metric_unit"] == "mm"
    assert clipped[0][0] == 0.0
    assert clipped[1][0] == 4.0

def test_phantom_and_floating_surface_pruning():
    """Verifies that reflection phantoms, slivers, and floating surfaces are pruned with measurable metrics."""
    pruner = PhantomPruner()

    planes = [
        {"structure_id": "wall_valid", "surface_area_m2": 8.5, "inlier_points_count": 800, "confidence": 0.92, "plane_type": "WALL"},
        {"structure_id": "sliver_phantom", "surface_area_m2": 0.04, "inlier_points_count": 8, "confidence": 0.20, "plane_type": "OTHER"}
    ]

    valid_planes, corrs = pruner.prune_phantom_planes(planes)
    assert len(valid_planes) == 1
    assert valid_planes[0]["structure_id"] == "wall_valid"
    assert len(corrs) == 1
    assert corrs[0]["correction_type"] == "REMOVE_PHANTOM_GEOMETRY"
    assert corrs[0]["delta_metric_value"] == 0.04
    assert corrs[0]["delta_metric_unit"] == "m2"

    # Floating point cloud test: points attached to wall vs floating far in mid-air
    pts_on_wall = np.array([[0.01, 1.0, 1.0], [0.02, 1.5, 1.2]])
    pts_floating = np.array([[5.0, 5.0, 1.0], [6.0, 6.0, 1.0]])
    all_pts = np.vstack([pts_on_wall, pts_floating])

    clean_pts, pt_corrs = pruner.prune_floating_points_and_vertices(
        all_pts,
        [{"plane_equation": [1.0, 0.0, 0.0, 0.0]}]
    )
    assert len(clean_pts) == 2
    assert len(pt_corrs) == 1
    assert pt_corrs[0]["delta_metric_value"] == 2.0
    assert pt_corrs[0]["delta_metric_unit"] == "points"

def test_geometry_qa_validator_7_audits():
    """Verifies that all 7 structural validation audits execute and detect issues accurately."""
    validator = GeometryQAValidator()

    walls = [
        {"structure_id": "w1", "plane_equation": [1, 0, 0, 0], "corners_3d": [[0,0,0], [0,2,0], [0,2,2.8], [0,0,2.8]]},
        {"structure_id": "w2", "plane_equation": [0, 1, 0, 0], "corners_3d": [[0,0,0], [2,0,0], [2,0,2.8], [0,0,2.8]]},
        {"structure_id": "w3", "plane_equation": [1, 0, 0, -2], "corners_3d": [[2,0,0], [2,2,0], [2,2,2.8], [2,0,2.8]]},
        {"structure_id": "w4", "plane_equation": [0, 1, 0, -2], "corners_3d": [[0,2,0], [2,2,0], [2,2,2.8], [0,2,2.8]]},
    ]

    edges = [
        {"edge_id": "e1", "source_plane_id": "w1", "target_plane_id": "w2", "junction_type": "WALL_WALL", "raw_angle_deg": 90.0},
        {"edge_id": "e2", "source_plane_id": "w2", "target_plane_id": "w3", "junction_type": "WALL_WALL", "raw_angle_deg": 90.0},
        {"edge_id": "e3", "source_plane_id": "w3", "target_plane_id": "w4", "junction_type": "WALL_WALL", "raw_angle_deg": 90.0},
        {"edge_id": "e4", "source_plane_id": "w4", "target_plane_id": "w1", "junction_type": "WALL_WALL", "raw_angle_deg": 90.0},
    ]

    report = validator.run_audits(
        walls=walls,
        intersection_edges=edges,
        floor_z=0.0,
        ceiling_z=2.8,
        room_bounds_min=[0,0,0],
        room_bounds_max=[2,2,2.8]
    )

    # 1. Watertightness: 4 walls with 4 closed corners -> PASS
    assert report.watertightness_status == "PASS"
    assert report.boundary_edges_count == 0

    # 2. Self intersections: 0
    assert report.self_intersections_count == 0

    # 3. Disconnected walls: 0
    assert report.disconnected_walls_count == 0

    # 4. Floating vertices: 0
    assert report.floating_vertices_count == 0

    # 5. Rounded corners: 0
    assert report.rounded_architectural_corners_count == 0

    # 6. Excessive smoothing: False
    assert report.excessive_smoothing_detected is False

    # 7. Incorrect wall extents: 0
    assert report.incorrect_wall_extents_count == 0

def test_acceptance_criterion_structurally_cleaner_and_measurable():
    """
    Acceptance Criterion:
    The output is structurally cleaner than the raw point-cloud reconstruction and every correction is measurable.
    """
    corrector = ArchitecturalGeometryCorrector(min_snapping_confidence=0.60)

    # Build a noisy synthetic room:
    # 4 walls with slight vertex noise (+/- 30mm) and an unaligned door opening
    # Plus a floating noise cluster and a mirror phantom plane
    raw_walls = [
        {
            "structure_id": "floor_main",
            "plane_type": "FLOOR",
            "plane_equation": [0.0, 0.0, 1.0, 0.0],
            "surface_area_m2": 9.0,
            "inlier_points_count": 600,
            "confidence": 0.95,
            "corners_3d": [[0.0, 0.0, 0.0], [3.0, 0.0, 0.0], [3.0, 3.0, 0.0], [0.0, 3.0, 0.0]]
        },
        {
            "structure_id": "ceiling_main",
            "plane_type": "CEILING",
            "plane_equation": [0.0, 0.0, 1.0, -2.8],
            "surface_area_m2": 9.0,
            "inlier_points_count": 600,
            "confidence": 0.95,
            "corners_3d": [[0.0, 0.0, 2.8], [3.0, 0.0, 2.8], [3.0, 3.0, 2.8], [0.0, 3.0, 2.8]]
        },
        {
            "structure_id": "wall_south",
            "plane_type": "WALL",
            "plane_equation": [0.0, 1.0, 0.0, 0.0],
            "surface_area_m2": 8.0,
            "inlier_points_count": 500,
            "confidence": 0.92,
            "corners_3d": [[0.0, 0.0, 0.03], [3.0, 0.0, 0.03], [3.0, 0.0, 2.76], [0.0, 0.0, 2.76]],
            "openings": [{"opening_type": "DOOR", "width_m": 0.9, "height_m": 2.1, "center_3d": [1.5, 0.0, 1.12]}]
        },
        {
            "structure_id": "wall_east",
            "plane_type": "WALL",
            "plane_equation": [1.0, 0.0, 0.0, -3.0],
            "surface_area_m2": 8.0,
            "inlier_points_count": 500,
            "confidence": 0.90,
            "corners_3d": [[3.0, 0.0, 0.02], [3.0, 3.0, 0.02], [3.0, 3.0, 2.78], [3.0, 0.0, 2.78]]
        },
        {
            "structure_id": "wall_north",
            "plane_type": "WALL",
            "plane_equation": [0.0, 1.0, 0.0, -3.0],
            "surface_area_m2": 8.0,
            "inlier_points_count": 500,
            "confidence": 0.91,
            "corners_3d": [[3.0, 3.0, 0.04], [0.0, 3.0, 0.04], [0.0, 3.0, 2.75], [0.0, 3.0, 2.75]]
        },
        {
            "structure_id": "wall_west",
            "plane_type": "WALL",
            "plane_equation": [1.0, 0.0, 0.0, 0.0],
            "surface_area_m2": 8.0,
            "inlier_points_count": 500,
            "confidence": 0.89,
            "corners_3d": [[0.0, 3.0, 0.02], [0.0, 0.0, 0.02], [0.0, 0.0, 2.77], [0.0, 3.0, 2.77]]
        },
        # Mirror reflection phantom
        {
            "structure_id": "mirror_phantom_01",
            "plane_type": "OTHER",
            "plane_equation": [0.7, 0.7, 0.0, -10.0],
            "surface_area_m2": 0.08,
            "inlier_points_count": 12,
            "confidence": 0.15,
            "corners_3d": []
        }
    ]

    edges = [
        {
            "edge_id": "edge_s_e",
            "source_plane_id": "wall_south",
            "target_plane_id": "wall_east",
            "junction_type": "WALL_WALL",
            "raw_angle_deg": 90.0,
            "adjusted_angle_deg": 90.0,
            "is_orthogonal_prior_applied": True,
            "intersection_line_start": [3.0, 0.0, 0.0],
            "intersection_line_end": [3.0, 0.0, 2.8]
        },
        {
            "edge_id": "edge_e_n",
            "source_plane_id": "wall_east",
            "target_plane_id": "wall_north",
            "junction_type": "WALL_WALL",
            "raw_angle_deg": 90.0,
            "adjusted_angle_deg": 90.0,
            "is_orthogonal_prior_applied": True,
            "intersection_line_start": [3.0, 3.0, 0.0],
            "intersection_line_end": [3.0, 3.0, 2.8]
        },
        {
            "edge_id": "edge_n_w",
            "source_plane_id": "wall_north",
            "target_plane_id": "wall_west",
            "junction_type": "WALL_WALL",
            "raw_angle_deg": 90.0,
            "adjusted_angle_deg": 90.0,
            "is_orthogonal_prior_applied": True,
            "intersection_line_start": [0.0, 3.0, 0.0],
            "intersection_line_end": [0.0, 3.0, 2.8]
        },
        {
            "edge_id": "edge_w_s",
            "source_plane_id": "wall_west",
            "target_plane_id": "wall_south",
            "junction_type": "WALL_WALL",
            "raw_angle_deg": 90.0,
            "adjusted_angle_deg": 90.0,
            "is_orthogonal_prior_applied": True,
            "intersection_line_start": [0.0, 0.0, 0.0],
            "intersection_line_end": [0.0, 0.0, 2.8]
        }
    ]

    # Points: 100 points on walls + 10 floating noise points
    wall_pts = np.array([[1.5, 0.01, 1.0], [3.0, 1.5, 1.2], [1.5, 2.99, 1.5], [0.01, 1.5, 1.1]])
    floating_noise = np.array([[8.0, 8.0, 2.0], [9.0, 9.0, 1.5]])
    raw_points = np.vstack([wall_pts, floating_noise])

    clean_planes, clean_edges, clean_points, qa_report = corrector.correct_structural_region(
        planes=raw_walls,
        intersection_edges=edges,
        raw_evidence_points=raw_points
    )

    # 1. Output is structurally cleaner than raw input:
    assert qa_report.cleanliness_score_after > qa_report.cleanliness_score_before
    assert qa_report.measurable_improvement_percent > 0.0
    assert qa_report.verdict == "PASS"

    # 2. Phantom plane pruned:
    plane_ids = [p["structure_id"] for p in clean_planes]
    assert "mirror_phantom_01" not in plane_ids
    assert len(clean_planes) == 6

    # 3. Floating points pruned:
    assert len(clean_points) < len(raw_points)

    # 4. Corners & bounds are cleanly snapped to floor (0.00m) and ceiling (2.80m):
    walls_only = [p for p in clean_planes if p["plane_type"] == "WALL"]
    assert len(walls_only) == 4
    for p in walls_only:
        for c in p["corners_3d"]:
            assert c[2] == 0.00 or c[2] == 2.80

    # 5. Door opening threshold is aligned:
    door_wall = next(w for w in walls_only if w["structure_id"] == "wall_south")
    door_op = door_wall["openings"][0]
    assert pytest.approx(door_op["center_3d"][2], 0.01) == 1.05

    # 6. EVERY correction is measurable:
    assert qa_report.corrections_count > 0
    for corr in qa_report.corrections:
        assert isinstance(corr, CorrectionRecord)
        assert corr.delta_metric_unit in ["mm", "deg", "points", "m2", "m3"]
        assert corr.confidence > 0.0
        assert len(corr.description) > 0
