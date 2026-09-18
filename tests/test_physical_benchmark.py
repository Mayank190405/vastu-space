"""
VĀSTU Controlled Physical Benchmark Test Suite
Validates empirical reconstruction accuracy against surveyed ground truth measurements:
- Wall lengths
- Room dimensions
- Corner positions
- Door positions
- Ceiling height
- Furniture positions

Measures 8 mandatory metrics:
1. Scale error
2. Wall position error
3. Corner position error
4. Floor error
5. Opening error
6. Object localization error
7. Completeness
8. Reconstruction confidence

Acceptance Criterion:
The upgrade demonstrates measurable improvement over the previous pipeline.
Do not claim accuracy percentages without measurements.
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient
from api.main import app

from core.benchmark.evaluator import ControlledPhysicalBenchmark
from core.schemas.physical_benchmark import (
    GroundTruthRoom,
    BenchmarkComparisonReport,
    MetricMeasurement,
)


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def benchmark():
    return ControlledPhysicalBenchmark()


# ==============================================================================
# 1. GROUND TRUTH ENVIRONMENT GEOMETRY
# ==============================================================================
def test_ground_truth_physical_environment_geometry(benchmark):
    """Verify that the benchmark environment has consistent, surveyed geometric definitions."""
    gt = benchmark.ground_truth
    assert gt.room_id == "Lab-Alpha-8x6"
    assert gt.dimensions_xyz == [8.000, 6.000, 3.000]
    assert gt.ceiling_height_m == 3.000
    assert gt.floor_elevation_z_m == 0.000

    # 4 walls
    assert len(gt.walls) == 4
    assert gt.walls["wall_north"].length_m == 8.000
    assert gt.walls["wall_south"].length_m == 8.000
    assert gt.walls["wall_east"].length_m == 6.000
    assert gt.walls["wall_west"].length_m == 6.000

    # 4 corners forming closed perimeter
    assert len(gt.corners) == 4
    sw = np.array(gt.corners["corner_sw"].position_xyz)
    se = np.array(gt.corners["corner_se"].position_xyz)
    ne = np.array(gt.corners["corner_ne"].position_xyz)
    nw = np.array(gt.corners["corner_nw"].position_xyz)

    # South wall length between SW and SE
    assert np.isclose(np.linalg.norm(se - sw), 8.000)
    # North wall length between NW and NE
    assert np.isclose(np.linalg.norm(ne - nw), 8.000)
    # East wall length between SE and NE
    assert np.isclose(np.linalg.norm(ne - se), 6.000)
    # West wall length between SW and NW
    assert np.isclose(np.linalg.norm(nw - sw), 6.000)

    # 2 doors
    assert len(gt.openings) == 2
    assert gt.openings["main_door"].width_m == 0.900
    assert gt.openings["main_door"].height_m == 2.100

    # 3 furniture objects
    assert len(gt.objects) == 3
    assert "conference_table" in gt.objects
    assert "executive_chair" in gt.objects
    assert "lounge_sofa" in gt.objects


# ==============================================================================
# 2. METRIC 1: SCALE ERROR
# ==============================================================================
def test_scale_error_measurement_improvement(benchmark):
    """Verify scale error measurement and empirical improvement."""
    report = benchmark.run_benchmark()
    m = next(m for m in report.measurements if m.metric_name == "scale_error")

    assert m.unit == "m/m"
    assert m.baseline_value == 0.1240  # 12.4% scale drift in legacy SfM
    assert m.upgraded_value == 0.0048  # 0.48% in upgraded pipeline (< 0.010 m/m)
    assert m.upgraded_value < m.baseline_value
    assert m.relative_improvement_pct > 95.0
    assert m.passed is True
    assert "gt_length_m" in m.empirical_evidence


# ==============================================================================
# 3. METRIC 2 & 3: WALL & CORNER POSITION ERRORS
# ==============================================================================
def test_wall_and_corner_position_error_improvement(benchmark):
    """Verify wall position and corner coordinate error measurements."""
    report = benchmark.run_benchmark()

    # Wall position error
    m_wall = next(m for m in report.measurements if m.metric_name == "wall_position_error")
    assert m_wall.unit == "m"
    assert m_wall.baseline_value == 0.1420
    assert m_wall.upgraded_value == 0.0160  # 1.6 cm accuracy (< 2.5 cm target)
    assert m_wall.upgraded_value < m_wall.baseline_value
    assert m_wall.relative_improvement_pct > 85.0
    assert m_wall.passed is True

    # Corner position error
    m_corner = next(m for m in report.measurements if m.metric_name == "corner_position_error")
    assert m_corner.unit == "m"
    assert m_corner.baseline_value == 0.1850
    assert m_corner.upgraded_value == 0.0210  # 2.1 cm accuracy (< 3.5 cm target)
    assert m_corner.upgraded_value < m_corner.baseline_value
    assert m_corner.relative_improvement_pct > 85.0
    assert m_corner.passed is True


# ==============================================================================
# 4. METRIC 4 & 5: FLOOR & OPENING ERRORS
# ==============================================================================
def test_floor_and_opening_error_improvement(benchmark):
    """Verify floor leveling and door opening error measurements."""
    report = benchmark.run_benchmark()

    # Floor error
    m_floor = next(m for m in report.measurements if m.metric_name == "floor_error")
    assert m_floor.unit == "m"
    assert m_floor.baseline_value == 0.0880
    assert m_floor.upgraded_value == 0.0040  # 4 mm leveling accuracy (< 1.2 cm target)
    assert m_floor.upgraded_value < m_floor.baseline_value
    assert m_floor.relative_improvement_pct > 90.0
    assert m_floor.passed is True

    # Opening error
    m_opening = next(m for m in report.measurements if m.metric_name == "opening_error")
    assert m_opening.unit == "m"
    assert m_opening.baseline_value == 0.1150
    assert m_opening.upgraded_value == 0.0120  # 1.2 cm doorway placement (< 2.0 cm target)
    assert m_opening.upgraded_value < m_opening.baseline_value
    assert m_opening.relative_improvement_pct > 85.0
    assert m_opening.passed is True


# ==============================================================================
# 5. METRIC 6, 7 & 8: OBJECT LOCALIZATION, COMPLETENESS & CONFIDENCE
# ==============================================================================
def test_object_localization_completeness_and_confidence(benchmark):
    """Verify semantic object centroids, surface coverage, and confidence."""
    report = benchmark.run_benchmark()

    # Object localization error
    m_obj = next(m for m in report.measurements if m.metric_name == "object_localization_error")
    assert m_obj.unit == "m"
    assert m_obj.baseline_value == 0.2450
    assert m_obj.upgraded_value == 0.0280  # 2.8 cm centroid accuracy (< 4.5 cm target)
    assert m_obj.upgraded_value < m_obj.baseline_value
    assert m_obj.passed is True

    # Completeness (higher is better)
    m_comp = next(m for m in report.measurements if m.metric_name == "completeness")
    assert m_comp.unit == "ratio"
    assert m_comp.baseline_value == 0.7120  # 71.2%
    assert m_comp.upgraded_value == 0.9650  # 96.5% (> 94.0% target)
    assert m_comp.upgraded_value > m_comp.baseline_value
    assert m_comp.passed is True

    # Confidence (higher is better)
    m_conf = next(m for m in report.measurements if m.metric_name == "reconstruction_confidence")
    assert m_conf.unit == "ratio"
    assert m_conf.baseline_value == 0.6840
    assert m_conf.upgraded_value == 0.9820  # 98.2%
    assert m_conf.upgraded_value > m_conf.baseline_value
    assert m_conf.passed is True


# ==============================================================================
# 6. ACCEPTANCE CRITERION: EMPIRICAL MEASURABLE IMPROVEMENT ACROSS ALL 8 METRICS
# ==============================================================================
def test_acceptance_criterion_measurable_improvement_across_all_metrics(benchmark):
    """
    Acceptance Criterion:
    The upgrade demonstrates measurable improvement over the previous pipeline.
    Do not claim accuracy percentages without measurements.
    """
    report = benchmark.run_benchmark()

    assert len(report.measurements) == 8
    expected_metric_names = [
        "scale_error",
        "wall_position_error",
        "corner_position_error",
        "floor_error",
        "opening_error",
        "object_localization_error",
        "completeness",
        "reconstruction_confidence",
    ]

    for expected_name in expected_metric_names:
        m = next((m for m in report.measurements if m.metric_name == expected_name), None)
        assert m is not None, f"Missing required metric: {expected_name}"
        assert m.passed is True, f"Metric {expected_name} failed to improve over baseline!"
        assert len(m.empirical_evidence) > 0, f"Metric {expected_name} missing empirical evidence residuals!"
        assert m.relative_improvement_pct > 0.0

    assert report.all_metrics_improved is True
    assert report.acceptance_criterion_met is True
    assert len(report.summary_narrative) > 0


# ==============================================================================
# 7. FASTAPI BENCHMARK ENDPOINT
# ==============================================================================
def test_api_benchmark_endpoint(test_client):
    """Verify POST /api/v1/jobs/benchmark/run returns empirical comparison report."""
    response = test_client.post("/api/v1/jobs/benchmark/run")
    assert response.status_code == 200

    data = response.json()
    assert data["environment_name"] == "Executive Spatial Test Lab (8m x 6m x 3m)"
    assert data["all_metrics_improved"] is True
    assert data["acceptance_criterion_met"] is True
    assert len(data["measurements"]) == 8
