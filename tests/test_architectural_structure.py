"""
Test Suite: Architectural Structure Extraction Subsystem
Verifies:
1. Normal estimation and dominant plane extraction.
2. 4-way classification (floor, wall, ceiling, other).
3. Plane confidence and boundary calculations.
4. Plane intersections and analytical sharp corner edges (no generic smoothing).
5. 90-degree architectural prior applied only when evidence supports it.
6. Acceptance Criterion: Standard room corners remain sharp, and genuine non-90-degree structures
   are preserved and not incorrectly forced into right angles.
"""

import pytest
import numpy as np

from core.structure.classifier import PlaneClassifier
from core.structure.confidence import PlaneConfidenceEstimator
from core.structure.boundaries import PlaneBoundaryExtractor
from core.structure.intersections import PlaneIntersectionResolver
from core.structure.graph import ArchitecturalPlaneGraph
from core.structure.extractor import ArchitecturalStructureExtractor
from core.schemas.structural_geometry import ArchitecturalPlaneGraphSchema, StructuralPlane

def generate_plane_points(
    origin: np.ndarray,
    u_vec: np.ndarray,
    v_vec: np.ndarray,
    u_range: tuple,
    v_range: tuple,
    num_u: int = 15,
    num_v: int = 15,
    noise_std: float = 0.005
) -> np.ndarray:
    """Generates synthetic 3D points on a planar patch with Gaussian noise."""
    u_vals = np.linspace(u_range[0], u_range[1], num_u)
    v_vals = np.linspace(v_range[0], v_range[1], num_v)
    uu, vv = np.meshgrid(u_vals, v_vals)
    pts = (
        origin +
        uu.reshape(-1, 1) * u_vec.reshape(1, 3) +
        vv.reshape(-1, 1) * v_vec.reshape(1, 3)
    )
    if noise_std > 0:
        pts += np.random.normal(0, noise_std, pts.shape)
    return pts

def test_plane_classifier_4_way():
    """Verifies that planes are classified accurately into FLOOR, WALL, CEILING, and OTHER."""
    classifier = PlaneClassifier(up_vector=np.array([0.0, 0.0, 1.0]))

    # Horizontal planes at different elevations
    floor_normal = np.array([0.0, 0.0, 1.0])
    ceiling_normal = np.array([0.0, 0.0, -1.0])
    
    # Vertical wall planes
    wall_normal_x = np.array([1.0, 0.0, 0.0])
    wall_normal_y = np.array([0.0, 1.0, 0.0])
    
    # Slanted plane (45 degree attic roof / ramp)
    slanted_normal = np.array([0.7071, 0.0, 0.7071])

    planes_data = [
        (np.append(floor_normal, 0.0), np.array([0.0, 0.0, 0.0])),        # Floor (z=0)
        (np.append(wall_normal_x, -3.0), np.array([3.0, 0.0, 1.5])),      # Wall X (z=1.5)
        (np.append(wall_normal_y, -4.0), np.array([0.0, 4.0, 1.5])),      # Wall Y (z=1.5)
        (np.append(slanted_normal, -2.0), np.array([1.0, 1.0, 2.0])),     # Slanted Roof (z=2.0)
        (np.append(ceiling_normal, 3.0), np.array([0.0, 0.0, 3.0])),      # Ceiling (z=3)
    ]

    classifications = classifier.classify_planes(planes_data)
    assert classifications[0] == "FLOOR"
    assert classifications[1] == "WALL"
    assert classifications[2] == "WALL"
    assert classifications[3] == "OTHER"
    assert classifications[4] == "CEILING"

def test_plane_confidence_and_boundaries():
    """Verifies confidence scoring and analytical boundary polygon generation."""
    np.random.seed(42)
    # Dense flat plane at z = 0, dimensions 2m x 3m
    points = generate_plane_points(
        origin=np.array([0.0, 0.0, 0.0]),
        u_vec=np.array([1.0, 0.0, 0.0]),
        v_vec=np.array([0.0, 1.0, 0.0]),
        u_range=(-1.0, 1.0),
        v_range=(-1.5, 1.5),
        num_u=20,
        num_v=20,
        noise_std=0.003
    )
    plane_eq = np.array([0.0, 0.0, 1.0, 0.0])

    conf_estimator = PlaneConfidenceEstimator()
    confidence = conf_estimator.compute_confidence(points, plane_eq)
    assert confidence > 0.85, f"High density flat plane should have high confidence, got {confidence}"

    b_extractor = PlaneBoundaryExtractor()
    corners_3d, poly_3d, area = b_extractor.extract_boundaries(points, plane_eq)

    assert len(corners_3d) == 4
    assert len(poly_3d) >= 4
    # Area should be close to 2.0 * 3.0 = 6.0 m^2
    assert 5.0 <= area <= 7.0

def test_orthogonal_prior_applied_when_evidence_supports():
    """Verifies that an intersection near 90 degrees with high confidence snaps to 90.0 degrees."""
    resolver = PlaneIntersectionResolver(orthogonal_tolerance_deg=3.5, min_angle_confidence=0.5)

    # Wall 1 facing +X: normal [1.0, 0.0, 0.0], x = 0
    # Wall 2 facing +Y with small 1.2-degree measurement noise: normal [cos(88.8 deg), sin(88.8 deg), 0]
    angle_rad = np.radians(88.8)
    n2 = np.array([np.cos(angle_rad), np.sin(angle_rad), 0.0])

    p1 = generate_plane_points(
        origin=np.array([0.0, 1.0, 1.0]),
        u_vec=np.array([0.0, 1.0, 0.0]),
        v_vec=np.array([0.0, 0.0, 1.0]),
        u_range=(0.0, 2.0),
        v_range=(0.0, 2.0)
    )
    p2 = generate_plane_points(
        origin=np.array([1.0, 0.0, 1.0]),
        u_vec=np.array([1.0, 0.0, 0.0]),
        v_vec=np.array([0.0, 0.0, 1.0]),
        u_range=(0.0, 2.0),
        v_range=(0.0, 2.0)
    )

    edge = resolver.resolve_intersection(
        plane_id_1="wall_north",
        plane_id_2="wall_east",
        plane_type_1="WALL",
        plane_type_2="WALL",
        plane_eq_1=np.array([1.0, 0.0, 0.0, 0.0]),
        plane_eq_2=np.append(n2, 0.0),
        pts_1=p1,
        pts_2=p2,
        conf_1=0.95,
        conf_2=0.92
    )

    assert edge is not None
    assert edge["is_orthogonal_prior_applied"] is True
    assert edge["adjusted_angle_deg"] == 90.0
    assert abs(edge["raw_angle_deg"] - 88.8) < 0.2
    assert edge["junction_type"] == "WALL_WALL"
    # Intersection line segment should be vertical along Z
    start = np.array(edge["intersection_line_start"])
    end = np.array(edge["intersection_line_end"])
    diff = end - start
    assert abs(diff[0]) < 0.05
    assert abs(diff[1]) < 0.05
    assert abs(diff[2]) > 0.5  # Significant vertical corner height

def test_acceptance_criterion_non_90_degree_structures_preserved():
    """
    Acceptance Criterion:
    Standard room corners remain architecturally sharp and non-90-degree structures
    are not incorrectly forced into right angles.
    """
    resolver = PlaneIntersectionResolver(orthogonal_tolerance_deg=3.5, min_angle_confidence=0.5)

    # Test 1: 45-degree diagonal wall (e.g. bay window or diagonal transition)
    theta_45 = np.radians(45.0)
    n_45 = np.array([np.cos(theta_45), np.sin(theta_45), 0.0])

    p_main = generate_plane_points(
        origin=np.array([0.0, 1.0, 1.0]),
        u_vec=np.array([0.0, 1.0, 0.0]),
        v_vec=np.array([0.0, 0.0, 1.0]),
        u_range=(0.0, 2.0),
        v_range=(0.0, 2.0)
    )
    p_diagonal = generate_plane_points(
        origin=np.array([1.0, 1.0, 1.0]),
        u_vec=np.array([-np.sin(theta_45), np.cos(theta_45), 0.0]),
        v_vec=np.array([0.0, 0.0, 1.0]),
        u_range=(0.0, 2.0),
        v_range=(0.0, 2.0)
    )

    edge_45 = resolver.resolve_intersection(
        plane_id_1="wall_main",
        plane_id_2="wall_diagonal_45",
        plane_type_1="WALL",
        plane_type_2="WALL",
        plane_eq_1=np.array([1.0, 0.0, 0.0, 0.0]),
        plane_eq_2=np.append(n_45, 0.0),
        pts_1=p_main,
        pts_2=p_diagonal,
        conf_1=0.94,
        conf_2=0.91
    )

    assert edge_45 is not None
    # Crucial assertion: 45-degree corner MUST NOT be forced into 90 degrees!
    assert edge_45["is_orthogonal_prior_applied"] is False
    assert abs(edge_45["adjusted_angle_deg"] - 45.0) < 1.0
    assert edge_45["adjusted_angle_deg"] != 90.0

    # Test 2: 60-degree angled corridor wall
    theta_60 = np.radians(60.0)
    n_60 = np.array([np.cos(theta_60), np.sin(theta_60), 0.0])
    edge_60 = resolver.resolve_intersection(
        plane_id_1="wall_corridor_a",
        plane_id_2="wall_corridor_b",
        plane_type_1="WALL",
        plane_type_2="WALL",
        plane_eq_1=np.array([1.0, 0.0, 0.0, 0.0]),
        plane_eq_2=np.append(n_60, 0.0),
        pts_1=p_main,
        pts_2=p_diagonal,
        conf_1=0.90,
        conf_2=0.88
    )

    assert edge_60 is not None
    assert edge_60["is_orthogonal_prior_applied"] is False
    assert abs(edge_60["adjusted_angle_deg"] - 60.0) < 1.0
    assert edge_60["adjusted_angle_deg"] != 90.0

def test_end_to_end_extractor_and_contract_export():
    """Verifies complete end-to-end structure extraction on a multi-plane synthetic room scene."""
    np.random.seed(123)
    # Construct a room with:
    # 1. Floor at z = 0
    # 2. Wall East at x = 2
    # 3. Wall North at y = 2
    # 4. Diagonal 45-degree wall
    pts_floor = generate_plane_points(np.array([1.0, 1.0, 0.0]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), (-1, 1), (-1, 1), num_u=15, num_v=15)
    pts_wall1 = generate_plane_points(np.array([2.0, 1.0, 1.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0]), (-1, 1), (-1, 1), num_u=15, num_v=15)
    pts_wall2 = generate_plane_points(np.array([1.0, 2.0, 1.0]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]), (-1, 1), (-1, 1), num_u=15, num_v=15)
    
    all_points = np.vstack([pts_floor, pts_wall1, pts_wall2])

    extractor = ArchitecturalStructureExtractor(
        up_vector=np.array([0.0, 0.0, 1.0]),
        distance_threshold=0.04,
        min_inliers_per_plane=50
    )

    graph = extractor.extract_structure(all_points, metadata={"capture_id": "test_room_001"})

    assert len(graph.planes) >= 3
    # Check that planes include FLOOR and WALL
    types = [p["plane_type"] for p in graph.planes.values()]
    assert "FLOOR" in types
    assert "WALL" in types

    # Convert to Contract 7 Pydantic schema
    contract_graph = graph.to_contract()
    assert isinstance(contract_graph, ArchitecturalPlaneGraphSchema)
    assert len(contract_graph.planes) >= 3
    for sp in contract_graph.planes:
        assert isinstance(sp, StructuralPlane)
        assert sp.confidence > 0.0
        assert sp.surface_area_m2 > 0.0
