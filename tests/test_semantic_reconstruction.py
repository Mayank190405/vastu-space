"""
Test Suite: Semantic Reconstruction Independent from Geometry
Verifies:
1. Detection and classification of all 10 required classes:
   rooms, doors, windows, furniture, tables, chairs, sofas, desks, signage, architectural objects.
2. Complete object schema storage:
   object_id, class, label, position, bounding geometry, room_id, confidence, source observations.
3. Ground Truth Policy: Low-confidence detections are NEVER treated as ground truth.
4. Acceptance Criterion: Every semantic object has spatial coordinates and confidence
   and can be linked back to the reconstructed space.
"""

import pytest
import numpy as np

from core.schemas.semantic_object import (
    SemanticObject,
    OrientedBoundingBox,
    RoomSemanticVolume,
    SemanticSceneManifest
)
from core.semantics.taxonomy import SemanticClass, CLASS_TO_CATEGORY
from core.semantics.room_partitioner import RoomSemanticDetector
from core.semantics.detector import SemanticReconstructionEngine
from core.semantics.manager import SemanticSceneManager

def generate_box_points(center: np.ndarray, extent: np.ndarray, num_points: int = 20) -> np.ndarray:
    """Generates synthetic 3D points inside an axis-aligned box."""
    min_pt = center - extent / 2.0
    max_pt = center + extent / 2.0
    return np.random.uniform(min_pt, max_pt, size=(num_points, 3))

def test_10_required_semantic_classes_taxonomy():
    """Verifies that all 10 requested semantic classes are defined and mapped to valid categories."""
    required_classes = [
        "room",
        "door",
        "window",
        "furniture",
        "table",
        "chair",
        "sofa",
        "desk",
        "signage",
        "architectural_object"
    ]
    for c in required_classes:
        assert c in [sc.value for sc in SemanticClass], f"Missing required class: {c}"
        assert c in CLASS_TO_CATEGORY, f"Missing category mapping for: {c}"

def test_object_attributes_and_bounding_geometry():
    """Verifies that reconstructed objects store all 8 required fields."""
    engine = SemanticReconstructionEngine()

    # Synthetic desk at [2.0, 1.5, 0.4] with extent [1.2, 0.6, 0.75]
    desk_pts = generate_box_points(np.array([2.0, 1.5, 0.4]), np.array([1.2, 0.6, 0.75]), num_points=30)
    source_obs = ["frame_0012.jpg", "frame_0015.jpg", "frame_0018.jpg"]

    obj = engine.reconstruct_object(
        class_name="desk",
        points_3d=desk_pts,
        source_observations=source_obs,
        base_detection_confidence=0.88,
        label="Executive Work Desk",
        room_id="room_office_01",
        associated_cell_ids=["cell_001_001_000"]
    )

    # 1. object_id
    assert obj.object_id.startswith("sem_desk_")
    # 2. class
    assert obj.class_name == "desk"
    # 3. label
    assert obj.label == "Executive Work Desk"
    # 4. position
    assert len(obj.position) == 3
    assert pytest.approx(obj.position[0], 0.1) == 2.0
    assert pytest.approx(obj.position[1], 0.1) == 1.5
    # 5. bounding geometry (oriented_bounding_box)
    assert isinstance(obj.oriented_bounding_box, OrientedBoundingBox)
    assert len(obj.oriented_bounding_box.center) == 3
    assert len(obj.oriented_bounding_box.extent_dx_dy_dz) == 3
    assert len(obj.oriented_bounding_box.rotation_quaternion) == 4
    # 6. room_id
    assert obj.room_id == "room_office_01"
    # 7. confidence
    assert 0.0 <= obj.confidence <= 1.0
    assert obj.confidence >= 0.85
    # 8. source observations
    assert obj.source_observations == source_obs

def test_ground_truth_policy_rejects_low_confidence():
    """
    Never treat low-confidence detections as ground truth:
    Detections with confidence < 0.70 must have is_ground_truth_candidate = False and status = 'PROVISIONAL'.
    """
    engine = SemanticReconstructionEngine(ground_truth_confidence_threshold=0.70)
    pts = generate_box_points(np.array([0, 0, 0]), np.array([0.5, 0.5, 0.5]))

    # Case 1: High confidence detection (0.90) -> CONFIRMED Ground Truth Candidate
    high_obj = engine.reconstruct_object(
        class_name="chair",
        points_3d=pts,
        source_observations=["frame_01.jpg", "frame_02.jpg"],
        base_detection_confidence=0.90
    )
    assert high_obj.confidence >= 0.70
    assert high_obj.is_ground_truth_candidate is True
    assert high_obj.status == "CONFIRMED"

    # Case 2: Low confidence detection (0.55) -> PROVISIONAL, NEVER Ground Truth
    low_obj = engine.reconstruct_object(
        class_name="signage",
        points_3d=pts,
        source_observations=["frame_99.jpg"],
        base_detection_confidence=0.55
    )
    assert low_obj.confidence < 0.70
    assert low_obj.is_ground_truth_candidate is False
    assert low_obj.status == "PROVISIONAL"

def test_room_partitioning_and_containment():
    """Verifies room volume creation and automatic containment mapping for objects."""
    room_detector = RoomSemanticDetector()
    r1 = room_detector.register_room(
        room_id="room_conf_a",
        name="Boardroom A",
        boundary_min=[0.0, 0.0, 0.0],
        boundary_max=[6.0, 5.0, 3.0]
    )
    r2 = room_detector.register_room(
        room_id="room_hallway",
        name="Corridor 1",
        boundary_min=[6.0, 0.0, 0.0],
        boundary_max=[8.0, 10.0, 3.0]
    )

    # Point inside Boardroom A
    pos_inside_r1 = [3.0, 2.5, 1.0]
    assert room_detector.find_enclosing_room(pos_inside_r1) == "room_conf_a"

    # Point inside Corridor
    pos_inside_r2 = [7.0, 4.0, 1.2]
    assert room_detector.find_enclosing_room(pos_inside_r2) == "room_hallway"

def test_acceptance_criterion_all_objects_have_coordinates_confidence_and_spatial_links():
    """
    Acceptance Criterion:
    Every semantic object has spatial coordinates and confidence and can be linked back to the reconstructed space.
    """
    manager = SemanticSceneManager(scene_id="building_42_level_1")

    # Register 2 rooms
    manager.register_room(
        room_id="room_101",
        name="Conference Room 101",
        boundary_min=[0.0, 0.0, 0.0],
        boundary_max=[5.0, 5.0, 3.0],
        associated_cell_ids=["cell_000_000_000", "cell_001_000_000"]
    )
    manager.register_room(
        room_id="room_102",
        name="Executive Office 102",
        boundary_min=[5.0, 0.0, 0.0],
        boundary_max=[10.0, 5.0, 3.0],
        associated_cell_ids=["cell_002_000_000"]
    )

    engine = SemanticReconstructionEngine(room_detector=manager.room_detector)

    # Reconstruct 6 diverse objects across classes
    test_objects_specs = [
        ("table", [2.5, 2.5, 0.4], [1.8, 1.0, 0.75], ["f01", "f02"], 0.92, "Conference Table"),
        ("chair", [2.0, 1.5, 0.4], [0.5, 0.5, 0.9], ["f02", "f03"], 0.88, "Ergonomic Chair 1"),
        ("sofa", [7.0, 3.0, 0.4], [2.0, 0.8, 0.85], ["f08", "f09"], 0.85, "Office Lounge Sofa"),
        ("door", [5.0, 2.0, 1.05], [0.1, 0.9, 2.1], ["f04", "f05"], 0.95, "Room Connecting Door"),
        ("window", [0.0, 2.5, 1.5], [0.1, 1.5, 1.2], ["f06"], 0.80, "Exterior Window"),
        ("signage", [5.05, 2.2, 1.8], [0.05, 0.3, 0.2], ["f05"], 0.65, "Exit Sign")  # Low confidence
    ]

    for c_name, pos, ext, obs, conf, lbl in test_objects_specs:
        pts = generate_box_points(np.array(pos), np.array(ext))
        obj = engine.reconstruct_object(
            class_name=c_name,
            points_3d=pts,
            source_observations=obs,
            base_detection_confidence=conf,
            label=lbl,
            associated_cell_ids=["cell_000_000_000"]
        )
        manager.add_object(obj)

    # Verify Acceptance Criterion for EVERY object:
    manifest = manager.export_manifest()
    assert len(manifest.objects) == 6

    for obj in manifest.objects:
        # 1. Spatial coordinates present
        assert isinstance(obj.position, list)
        assert len(obj.position) == 3
        assert all(isinstance(v, (int, float)) for v in obj.position)

        # 2. Measurable confidence present
        assert isinstance(obj.confidence, float)
        assert 0.0 <= obj.confidence <= 1.0

        # 3. Linked back to reconstructed space:
        # a) linked to a room
        assert obj.room_id in ["room_101", "room_102"]
        # b) linked to spatial cell
        assert len(obj.associated_cell_ids) > 0
        # c) linked to source camera observations
        assert len(obj.source_observations) > 0

    # 4. Strict ground truth policy verification:
    # High confidence objects (5) are ground truth candidates; signage (conf 0.65 < 0.70) is PROVISIONAL
    gt_objs = manager.get_ground_truth_objects()
    prov_objs = manager.get_provisional_objects()
    assert len(gt_objs) == 5
    assert len(prov_objs) == 1
    assert prov_objs[0].class_name == "signage"
    assert prov_objs[0].is_ground_truth_candidate is False
    assert prov_objs[0].status == "PROVISIONAL"
