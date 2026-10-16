"""
Unit Tests for VĀSTU Phase 2: Mobile AR Capture Co-Pilot & Blueprint Guidance System
Tests:
1. Floorplan-to-SOP Blueprint Parser (vector walls, doors, windows, metric targets).
2. Translation Baseline Quality Signal (pure rotation without translation alert).
3. 3D Voxel Coverage Grid (occupancy, floor/wall surface tracking).
4. 85% Metric Gated Completion Rule (blocks early finish until floor & walls covered).
5. CaptureSOPEngine full AR Co-Pilot integration.
"""

import pytest
import numpy as np

from core.sop.floorplan_parser import FloorplanSOPParser
from core.sop.voxel_grid import VoxelCoverageGrid
from core.sop.signals import (
    QualitySignalType,
    LiveTelemetrySnapshot,
    QualitySignalEvaluator
)
from core.sop.sop_engine import CaptureSOPEngine
from core.sop.stages import SOPStage, SOP_STAGES_SEQUENCE
from core.sop.tts_engine import TTSPriority


def test_floorplan_parser_drawn_vector_walls():
    """
    Verifies parser accurately translates 2D canvas drawing objects into metric SOP zones and targets.
    """
    drawing_data = {
        "objects": [
            {
                "id": "w1",
                "type": "wall",
                "points": [{"x": 100, "y": 100}, {"x": 400, "y": 100}]  # 300px @ 50px/m = 6.0m
            },
            {
                "id": "w2",
                "type": "wall",
                "points": [{"x": 400, "y": 100}, {"x": 400, "y": 350}]  # 250px @ 50px/m = 5.0m
            },
            {
                "id": "w3",
                "type": "wall",
                "points": [{"x": 400, "y": 350}, {"x": 100, "y": 350}]  # 300px @ 50px/m = 6.0m
            },
            {
                "id": "w4",
                "type": "wall",
                "points": [{"x": 100, "y": 350}, {"x": 100, "y": 100}]  # 250px @ 50px/m = 5.0m
            },
            {
                "id": "door_main",
                "type": "door",
                "points": [{"x": 120, "y": 100}, {"x": 170, "y": 100}]
            },
            {
                "id": "win_east",
                "type": "window",
                "points": [{"x": 400, "y": 180}, {"x": 400, "y": 260}]
            }
        ]
    }

    sop = FloorplanSOPParser.parse(
        drawing_data=drawing_data,
        scale_ratio=1.0,
        floor_name="Luxury Master Suite",
        height_ft=10.0
    )

    assert "Luxury Master Suite" in sop["summary"]
    assert sop["recommended_start_zone"] == "zone_1_entry"
    assert len(sop["zones"]) == 5
    assert len(sop["mistakes_to_avoid"]) >= 4

    # Check metric targets
    mt = sop["metric_targets"]
    assert len(mt["walls"]) == 4
    assert mt["room_dimensions_m"]["width"] == 6.0
    assert mt["room_dimensions_m"]["length"] == 5.0
    assert mt["room_dimensions_m"]["height"] == 3.05
    assert mt["required_coverage_fraction"] == 0.85
    assert mt["required_floor_fraction"] == 0.80


def test_floorplan_parser_metric_fallback():
    """
    Verifies parser synthesizes standard 4-wall metric model when no drawing objects are present.
    """
    sop = FloorplanSOPParser.parse(
        drawing_data=None,
        floor_name="Executive Boardroom",
        area_sqft=540.0,
        height_ft=11.0
    )

    mt = sop["metric_targets"]
    dims = mt["room_dimensions_m"]
    assert dims["area_sqm"] > 45.0
    assert len(mt["walls"]) == 4
    assert dims["width"] > 0
    assert dims["length"] > 0


def test_translation_baseline_alert_on_pure_rotation():
    """
    Acceptance Criterion:
    Alerts user if camera rotates in place without translation baseline (v < 0.15 m/s and w > 15 deg/s).
    """
    # 1. Degenerate pure rotation (pivoting on heels)
    pivoting_telemetry = LiveTelemetrySnapshot(
        linear_velocity_mps=0.08,     # < 0.15 m/s
        angular_velocity_radps=0.45   # > 0.26 rad/s (~26 deg/s)
    )
    evals = QualitySignalEvaluator.evaluate(pivoting_telemetry)
    assert any(
        e.signal_type == QualitySignalType.PURE_ROTATION_WITHOUT_TRANSLATION and
        "Walk sideways along room perimeter" in e.instruction
        for e in evals
    )

    # 2. Healthy normal walking with steady translation
    nominal_telemetry = LiveTelemetrySnapshot(
        linear_velocity_mps=0.35,     # >= 0.15 m/s
        angular_velocity_radps=0.20   # steady
    )
    evals_nominal = QualitySignalEvaluator.evaluate(nominal_telemetry)
    assert not any(
        e.signal_type == QualitySignalType.PURE_ROTATION_WITHOUT_TRANSLATION
        for e in evals_nominal
    )


def test_voxel_coverage_grid_accumulation():
    """
    Verifies 3D voxel grid tracks camera view frustum observations across floor and walls.
    """
    grid = VoxelCoverageGrid(width_m=4.0, length_m=5.0, height_m=2.5, grid_dim=10)

    # Initial state: 0% coverage
    assert grid.floor_coverage_fraction == 0.0
    assert grid.overall_coverage_fraction == 0.0

    # Step 1: Aim camera down at floor from chest height (z = 1.3m)
    for x in np.linspace(0.5, 3.5, 7):
        for y in np.linspace(0.5, 4.5, 7):
            # Look downward toward floor
            grid.update_pose(position=(x, y, 1.3), look_direction=(0.0, 0.0, -1.0), max_range_m=3.0)

    # Floor coverage should now be substantial
    assert grid.floor_coverage_fraction > 0.60

    # Step 2: Aim camera at North wall (y = 0)
    for x in np.linspace(0.5, 3.5, 7):
        grid.update_pose(position=(x, 1.5, 1.3), look_direction=(0.0, -1.0, 0.0), max_range_m=3.0)

    assert grid.wall_coverage_fractions["north"] > 0.50
    assert grid.overall_coverage_fraction > 0.30


def test_85_percent_completion_gate_enforcement():
    """
    Acceptance Criterion:
    Blocks finishing until >= 85% coverage is achieved (specifically requiring floor >= 80% and walls >= 70%).
    """
    grid = VoxelCoverageGrid(width_m=4.0, length_m=4.0, height_m=2.5, grid_dim=10)

    # 1. Incomplete scan: only floor scanned partially
    for x in np.linspace(0.5, 3.5, 5):
        grid.update_pose(position=(x, 2.0, 1.3), look_direction=(0.0, 0.0, -1.0))

    is_complete, defects = grid.is_gated_complete(min_overall=0.85, min_floor=0.80, min_wall=0.70)
    assert is_complete is False
    assert len(defects) > 0
    assert any("required: 85%" in d for d in defects)

    # 2. Complete thorough scan: sweep all floor, 4 walls, ceiling
    # Simulate full room perimeter and surface sweep
    grid.floor_grid[:, :] = 1
    grid.wall_north[:, :] = 1
    grid.wall_south[:, :] = 1
    grid.wall_east[:, :] = 1
    grid.wall_west[:, :] = 1
    grid.ceiling_grid[:, :] = 1
    grid.grid_3d[:, :, :] = 1

    is_complete_now, defects_now = grid.is_gated_complete(min_overall=0.85, min_floor=0.80, min_wall=0.70)
    assert is_complete_now is True
    assert len(defects_now) == 0
    assert grid.overall_coverage_fraction >= 0.85


def test_sop_engine_with_voxel_grid_and_gate():
    """
    Verifies full event loop of CaptureSOPEngine with floorplan blueprint and 85% completion gate.
    """
    engine = CaptureSOPEngine()
    engine.load_floorplan(
        drawing_data=None,
        floor_name="Living Room",
        area_sqft=350.0,
        height_ft=9.0
    )

    assert engine.capture_sop is not None
    assert engine.voxel_grid is not None

    t = 100.0
    engine.start_session(current_time_sec=t)

    # Fast-forward through stages 1 to 10
    target_metric_values = {
        "baseline_frames_accumulated": 50.0,
        "perimeter_path_length_m": 9.0,
        "wall_surface_observed_fraction": 0.85,
        "corners_captured_count": 4.0,
        "doorway_frames_captured": 35.0,
        "windows_frames_captured": 35.0,
        "floor_surface_observed_fraction": 0.80,
        "ceiling_surface_observed_fraction": 0.75,
        "center_cross_distance_m": 3.5,
        "distance_to_origin_m": 0.30
    }

    nominal_telemetry = LiveTelemetrySnapshot()

    for s_idx in range(10):
        t += 3.0
        stage_def = SOP_STAGES_SEQUENCE[s_idx]
        key = stage_def.target_metric_key
        val = target_metric_values[key]
        engine.update(telemetry=nominal_telemetry, metrics_update={key: val}, current_time_sec=t)

    # Now at Stage 11 (COMPLETION_VERIFICATION)
    assert engine.current_stage.stage == SOPStage.COMPLETION_VERIFICATION

    # Attempt to complete while voxel grid is unobserved: MUST FAIL GATE!
    t += 3.0
    prompts = engine.update(
        telemetry=nominal_telemetry,
        metrics_update={"overall_spatial_completeness": 0.90},
        current_time_sec=t
    )
    assert engine.is_completed is False
    assert any("Capture incomplete" in p.text for p in prompts)

    # Now fulfill voxel coverage requirements
    engine.voxel_grid.floor_grid[:, :] = 1
    engine.voxel_grid.wall_north[:, :] = 1
    engine.voxel_grid.wall_south[:, :] = 1
    engine.voxel_grid.wall_east[:, :] = 1
    engine.voxel_grid.wall_west[:, :] = 1
    engine.voxel_grid.ceiling_grid[:, :] = 1
    engine.voxel_grid.grid_3d[:, :, :] = 1

    t += 3.0
    prompts_finish = engine.update(
        telemetry=nominal_telemetry,
        metrics_update={"overall_spatial_completeness": 0.95},
        current_time_sec=t
    )
    assert engine.is_completed is True
    assert any("Capture complete" in p.text or "digitized" in p.text for p in prompts_finish)
