"""
Unit & Integration Tests: Spatial-Cell Decomposition
Validates:
1. Scene partitioning into independent spatial cells
2. Local coordinate system transformations (world <-> local)
3. Boundary continuity and halo margin preservation
4. Independent lifecycle: reconstruct, validate, rescan, update, and fuse
5. Acceptance Criterion: A failed region can be reconstructed independently without rebuilding the entire building
"""

import uuid
import pytest
import numpy as np

from core.dense.evidence_fusion import DenseEvidencePoint
from core.spatial.cell import SpatialCellModel
from core.spatial.decomposer import SpatialCellDecomposer
from core.spatial.lifecycle import SpatialCellLifecycleManager
from core.schemas.spatial_cell import SpatialCell


def _generate_synthetic_building_points(cell_size: float = 1.5) -> list:
    """
    Generates synthetic 3D points spanning a 2-room corridor across 3 spatial cells:
    Cell (0, 0, 0): [0.0, 1.5]
    Cell (1, 0, 0): [1.5, 3.0]
    Cell (2, 0, 0): [3.0, 4.5]
    """
    points = []
    # Continuous wall along x from 0.0 to 4.5 meters
    for x in np.linspace(0.1, 4.4, 150):
        for y in np.linspace(0.1, 1.4, 20):
            pt = DenseEvidencePoint(
                position=np.array([x, y, 1.0]),
                color=np.array([180, 180, 180], dtype=np.uint8),
                normal=np.array([0.0, 0.0, 1.0]),
                confidence=0.88,
                source_frames=[int(x // cell_size)]
            )
            points.append(pt)
    return points


def test_spatial_cell_model_local_coordinates():
    origin = np.array([1.5, 1.5, 1.5])
    cell = SpatialCellModel(
        cell_id="cell_001_001_001",
        coordinates=(1, 1, 1),
        cell_size_m=1.5,
        margin_m=0.08,
        origin_world=origin
    )

    world_pts = np.array([
        [1.5, 1.5, 1.5],   # Cell origin -> local [0, 0, 0]
        [2.0, 1.5, 1.5],   # Local [+0.5, 0, 0]
        [1.0, 1.0, 1.0]    # Local [-0.5, -0.5, -0.5]
    ])

    local_pts = cell.to_local(world_pts)
    assert np.allclose(local_pts[0], [0.0, 0.0, 0.0])
    assert np.allclose(local_pts[1], [0.5, 0.0, 0.0])
    assert np.allclose(local_pts[2], [-0.5, -0.5, -0.5])

    # Round-trip back to world coordinates
    reprojected_world = cell.to_world(local_pts)
    assert np.allclose(reprojected_world, world_pts)


def test_spatial_cell_decomposition_and_boundary_continuity():
    decomposer = SpatialCellDecomposer(cell_size_m=1.5, margin_m=0.08)
    points = _generate_synthetic_building_points(cell_size=1.5)

    poses = [
        {"frame_index": 0, "camera_center_m": [0.75, 0.75, 1.0]},
        {"frame_index": 1, "camera_center_m": [2.25, 0.75, 1.0]},
        {"frame_index": 2, "camera_center_m": [3.75, 0.75, 1.0]}
    ]

    planes = [{"structure_id": "wall_main", "plane_type": "WALL"}]
    semantics = [{"object_id": "door_corridor", "label": "DOOR"}]

    cells = decomposer.decompose(
        evidence_points=points,
        camera_poses=poses,
        structural_planes=planes,
        semantic_objects=semantics
    )

    # 3 spatial cells along x-axis
    assert len(cells) == 3

    # Check that each cell contains all required components
    for cid, cell in cells.items():
        assert cell.cell_id.startswith("cell_")
        assert len(cell.points_world) > 50
        assert cell.origin_world.shape == (3,)
        assert len(cell.source_frames) > 0
        assert len(cell.structural_observations) > 0
        assert len(cell.semantic_observations) > 0

        # Contract serialization check
        contract = cell.to_contract(model_id=uuid.uuid4())
        assert isinstance(contract, SpatialCell)
        assert contract.cell_id == cell.cell_id
        assert contract.point_count == len(cell.points_world)
        assert contract.boundary_info is not None

    # Spatial Continuity check: Points in halo margin [1.5 - 0.08, 1.5 + 0.08]
    # are shared by both cell (0, 0, 0) and cell (1, 0, 0)
    c0 = list(cells.values())[0]
    c1 = list(cells.values())[1]

    # Adjacent cells reference each other
    assert c1.cell_id in c0.neighbor_cell_ids
    assert c0.cell_id in c1.neighbor_cell_ids

    # Both cells have halo boundary points
    assert np.sum(c0.get_halo_mask()) > 0
    assert np.sum(c1.get_halo_mask()) > 0


def test_independent_reconstruction_validation_and_update():
    decomposer = SpatialCellDecomposer(cell_size_m=1.5, margin_m=0.08)
    points = _generate_synthetic_building_points(cell_size=1.5)
    cells = decomposer.decompose(points, camera_poses=[])
    manager = SpatialCellLifecycleManager(cells)

    first_cid = list(cells.keys())[0]

    # 1. Independent validation
    val = manager.validate_cell(first_cid)
    assert val["is_valid"] is True
    assert val["quality_score"] > 0.60

    # 2. Independent reconstruction
    recon = manager.reconstruct_cell(first_cid)
    assert recon["status"] == "RECONSTRUCTED"
    assert recon["triangle_count"] > 0

    # 3. Independent update
    cell = manager.get_cell(first_cid)
    initial_ver = cell.version
    manager.update_cell_annotations(
        first_cid,
        semantic_observations=[{"object_id": "updated_desk", "label": "DESK"}]
    )
    assert cell.version == initial_ver + 1
    assert cell.semantic_observations[0]["label"] == "DESK"


def test_acceptance_criterion_independent_region_reconstruction_without_rebuilding_entire_building():
    """
    Acceptance Criterion:
    A failed region can be reconstructed independently without rebuilding the entire building.
    """
    decomposer = SpatialCellDecomposer(cell_size_m=1.5, margin_m=0.08)
    points = _generate_synthetic_building_points(cell_size=1.5)
    cells = decomposer.decompose(points, camera_poses=[])
    manager = SpatialCellLifecycleManager(cells)

    cell_ids = sorted(list(cells.keys()))
    cell_0_id, cell_failed_id, cell_2_id = cell_ids[0], cell_ids[1], cell_ids[2]

    # Initial full reconstruction of all 3 cells
    for cid in cell_ids:
        manager.reconstruct_cell(cid)
        manager.validate_cell(cid)

    # Record baseline state of cells 0 and 2
    c0 = manager.get_cell(cell_0_id)
    c2 = manager.get_cell(cell_2_id)
    c0_initial_version = c0.version
    c2_initial_version = c2.version
    c0_initial_points_count = len(c0.points_world)
    c2_initial_points_count = len(c2.points_world)

    # Step 1: Deliberately inject failure/corruption into cell 1
    failed_cell = manager.get_cell(cell_failed_id)
    failed_cell.points_world = np.empty((0, 3), dtype=np.float64)  # Zero points = corrupted/failed region
    failed_cell.confidences = np.empty((0,), dtype=np.float64)

    # Validate cell 1 reports failure
    val_fail = manager.validate_cell(cell_failed_id)
    assert val_fail["is_valid"] is False

    # Step 2: Rescan ONLY the failed region (Cell 1) independently
    rescan_pts = np.random.uniform(1.5, 3.0, (120, 3))
    rescan_cols = np.ones((120, 3), dtype=np.uint8) * 190
    rescan_norms = np.ones((120, 3), dtype=np.float64) * 0.5
    rescan_confs = np.ones((120,), dtype=np.float64) * 0.95

    rescan_res = manager.rescan_cell(
        cell_id=cell_failed_id,
        new_points_world=rescan_pts,
        new_colors=rescan_cols,
        new_normals=rescan_norms,
        new_confidences=rescan_confs
    )
    assert rescan_res["status"] == "UPDATED"
    assert failed_cell.version > 1

    # Step 3: Reconstruct ONLY cell 1 independently
    recon_res = manager.reconstruct_cell(cell_failed_id)
    assert recon_res["status"] == "RECONSTRUCTED"
    val_repaired = manager.validate_cell(cell_failed_id)
    assert val_repaired["is_valid"] is True

    # Critical Assertion: Cells 0 and 2 were NOT modified or rebuilt!
    assert c0.version == c0_initial_version
    assert c2.version == c2_initial_version
    assert len(c0.points_world) == c0_initial_points_count
    assert len(c2.points_world) == c2_initial_points_count
    assert c0.is_dirty is False
    assert c2.is_dirty is False

    # Step 4: Re-fuse into global model with boundary blending
    fused_pts, fused_cols, fused_norms, fused_confs = manager.fuse_cells(blend_halo_margin=True)
    assert len(fused_pts) > 0
    # Complete building model is restored without seams!
    assert np.min(fused_pts[:, 0]) < 0.5
    assert np.max(fused_pts[:, 0]) > 4.0
