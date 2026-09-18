"""
Unit & Integration Tests for Navigation Benchmark Scenarios & Quantitative Validation (Stage 28)
Validates:
1. All 9 mandated geometric scenarios:
   - Direct path
   - Obstacle around left
   - Obstacle around right
   - Narrow corridor
   - Furniture cluster
   - Doorway
   - Disconnected region
   - Start near obstacle
   - Destination near obstacle
2. All 6 quantitative performance metrics:
   - Route success rate (>= 95% on valid routes)
   - Collision rate (0.0% across all generated routes)
   - Path length & efficiency
   - Route computation time (< 50ms)
   - Waypoint smoothness (turn angles and curvature)
   - Invalid-route rejection (100% deterministic rejection)
3. Acceptance Criterion: Navigation is validated quantitatively rather than judged only visually.
4. FastAPI HTTP Endpoint: POST /api/v1/navigation/benchmark/run.
"""

import pytest
from fastapi.testclient import TestClient

from core.schemas.navigation_benchmark import (
    NavigationScenarioType,
    NavigationScenarioResult,
    NavigationBenchmarkSummary,
    NavigationBenchmarkReport,
)
from core.benchmark.navigation_evaluator import NavigationBenchmarkSuite
from api.main import app


@pytest.fixture
def benchmark_suite():
    """Provides an instantiated NavigationBenchmarkSuite."""
    return NavigationBenchmarkSuite(human_radius_m=0.35)


@pytest.fixture
def client():
    """FastAPI TestClient for navigation API."""
    return TestClient(app)


def test_navigation_benchmark_all_9_scenarios_configured(benchmark_suite):
    """Verifies that all 9 mandated navigation benchmark scenarios are configured."""
    scenarios = benchmark_suite.build_all_scenarios()
    assert len(scenarios) == 9

    scenario_types = [s.scenario_type for s in scenarios]
    assert NavigationScenarioType.DIRECT_PATH in scenario_types
    assert NavigationScenarioType.OBSTACLE_AROUND_LEFT in scenario_types
    assert NavigationScenarioType.OBSTACLE_AROUND_RIGHT in scenario_types
    assert NavigationScenarioType.NARROW_CORRIDOR in scenario_types
    assert NavigationScenarioType.FURNITURE_CLUSTER in scenario_types
    assert NavigationScenarioType.DOORWAY in scenario_types
    assert NavigationScenarioType.DISCONNECTED_REGION in scenario_types
    assert NavigationScenarioType.START_NEAR_OBSTACLE in scenario_types
    assert NavigationScenarioType.DESTINATION_NEAR_OBSTACLE in scenario_types


def test_scenario_direct_path_and_smoothness(benchmark_suite):
    """Scenario 1: Direct path in unobstructed space has optimal length and maximum smoothness."""
    scenario = benchmark_suite._scenario_direct_path()
    result = benchmark_suite.evaluate_scenario(scenario)

    assert result.success is True
    assert result.path_found is True
    assert result.collision_detected is False
    assert 7.9 <= result.path_length_meters <= 8.5
    assert result.waypoint_smoothness_score >= 0.95
    assert result.mean_turn_angle_degrees <= 5.0
    assert result.computation_time_ms < 50.0


def test_scenario_obstacles_left_and_right_detours(benchmark_suite):
    """Scenarios 2 & 3: Central obstacle triggers collision-free detours around left and right."""
    # Left Detour
    scen_left = benchmark_suite._scenario_obstacle_around_left()
    res_left = benchmark_suite.evaluate_scenario(scen_left)
    assert res_left.success is True
    assert res_left.collision_detected is False
    assert res_left.path_length_meters > res_left.direct_euclidean_distance_meters
    # Path waypoints should veer into positive Y (left)
    assert any(wp[1] > 0.6 for wp in res_left.waypoints)

    # Right Detour
    scen_right = benchmark_suite._scenario_obstacle_around_right()
    res_right = benchmark_suite.evaluate_scenario(scen_right)
    assert res_right.success is True
    assert res_right.collision_detected is False
    assert res_right.path_length_meters > res_right.direct_euclidean_distance_meters
    # Path waypoints should veer into negative Y (right)
    assert any(wp[1] < -0.6 for wp in res_right.waypoints)


def test_scenario_narrow_corridor_and_doorway(benchmark_suite):
    """Scenarios 4 & 6: Constrained passageways maintain corridor alignment and clearance."""
    # Narrow Corridor
    scen_corr = benchmark_suite._scenario_narrow_corridor()
    res_corr = benchmark_suite.evaluate_scenario(scen_corr)
    assert res_corr.success is True
    assert res_corr.collision_detected is False
    # Path should stay along hallway centerline (|y| < 0.5)
    for wp in res_corr.waypoints:
        assert abs(wp[1]) < 0.5

    # Doorway
    scen_door = benchmark_suite._scenario_doorway()
    res_door = benchmark_suite.evaluate_scenario(scen_door)
    assert res_door.success is True
    assert res_door.collision_detected is False
    # Doorway partition is at x=3.5. Path starts in Room 1 (x=1.0) and terminates in Room 2 (x=6.0)
    assert res_door.waypoints[0][0] <= 1.5
    assert res_door.waypoints[-1][0] >= 5.5


def test_scenario_furniture_cluster_weaving(benchmark_suite):
    """Scenario 5: Multi-obstacle furniture cluster navigated without collision."""
    scen_furn = benchmark_suite._scenario_furniture_cluster()
    res_furn = benchmark_suite.evaluate_scenario(scen_furn)

    assert res_furn.success is True
    assert res_furn.collision_detected is False
    assert res_furn.path_length_meters >= 7.0
    assert res_furn.waypoint_count >= 2


def test_scenario_start_and_destination_near_obstacles(benchmark_suite):
    """Scenarios 8 & 9: Endpoints adjacent to obstacles resolve and execute safely."""
    # Start near obstacle
    scen_start = benchmark_suite._scenario_start_near_obstacle()
    res_start = benchmark_suite.evaluate_scenario(scen_start)
    assert res_start.success is True
    assert res_start.collision_detected is False

    # Destination near obstacle
    scen_dest = benchmark_suite._scenario_destination_near_obstacle()
    res_dest = benchmark_suite.evaluate_scenario(scen_dest)
    assert res_dest.success is True
    assert res_dest.collision_detected is False


def test_scenario_disconnected_region_deterministic_rejection(benchmark_suite):
    """Scenario 7: Completely partitioned space without traversable path is cleanly rejected."""
    scen_disc = benchmark_suite._scenario_disconnected_region()
    res_disc = benchmark_suite.evaluate_scenario(scen_disc)

    assert res_disc.success is False
    assert res_disc.path_found is False
    assert res_disc.rejection_correctly_enforced is True
    assert res_disc.is_valid is True  # Rejection of invalid path is correct behavior
    assert res_disc.rejection_reason is not None
    assert len(res_disc.waypoints) == 0


def test_acceptance_criterion_quantitative_validation(benchmark_suite):
    """
    Acceptance Criterion:
    Navigation is validated quantitatively rather than judged only visually.
    Validates all 6 quantitative metrics across the complete 9-scenario benchmark.
    """
    report = benchmark_suite.run_full_benchmark()

    # 1. Structural Completeness
    assert len(report.scenarios) == 9
    assert report.summary.total_scenarios_evaluated == 9
    assert report.summary.valid_scenarios_count == 8
    assert report.summary.invalid_scenarios_count == 1

    # 2. Metric 1: Route Success Rate (>= 95% on valid paths)
    assert report.summary.route_success_rate == 1.0

    # 3. Metric 2: Collision Rate (Strictly 0.0%)
    assert report.summary.collision_rate == 0.0

    # 4. Metric 3: Mean Path Length
    assert report.summary.mean_path_length_meters > 0.0

    # 5. Metric 4: Route Computation Time (< 50ms)
    assert report.summary.mean_computation_time_ms < 50.0
    assert report.summary.max_computation_time_ms < 100.0

    # 6. Metric 5: Waypoint Smoothness
    assert report.summary.mean_waypoint_smoothness >= 0.70
    assert report.summary.mean_turn_angle_degrees <= 45.0

    # 7. Metric 6: Invalid Route Rejection Rate (100%)
    assert report.summary.invalid_route_rejection_rate == 1.0

    # Acceptance Criterion
    assert report.acceptance_criterion_met is True
    assert report.summary.quantitative_validation_passed is True
    assert "Navigation is validated quantitatively" in report.acceptance_criterion


def test_fastapi_navigation_benchmark_endpoint(client):
    """Verifies POST /api/v1/navigation/benchmark/run endpoint."""
    response = client.post("/api/v1/navigation/benchmark/run")
    assert response.status_code == 200

    data = response.json()
    assert "benchmark_id" in data
    assert "summary" in data
    assert "scenarios" in data
    assert len(data["scenarios"]) == 9

    summary = data["summary"]
    assert summary["route_success_rate"] == 1.0
    assert summary["collision_rate"] == 0.0
    assert summary["invalid_route_rejection_rate"] == 1.0
    assert summary["acceptance_criterion_met"] is True
    assert data["acceptance_criterion_met"] is True
