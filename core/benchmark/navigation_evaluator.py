"""
VĀSTU Navigation Benchmark Suite (Stage 28)
Implements quantitative benchmarking of route planning across 9 geometric scenarios:
1. Direct Path
2. Obstacle Around Left
3. Obstacle Around Right
4. Narrow Corridor
5. Furniture Cluster
6. Doorway
7. Disconnected Region
8. Start Near Obstacle
9. Destination Near Obstacle

Measures:
1. Route success rate
2. Collision rate (must be 0.0%)
3. Path length & efficiency
4. Route computation time (ms)
5. Waypoint smoothness (turn angles and curvature)
6. Invalid-route rejection (100% deterministic rejection)

Acceptance Criterion:
Navigation is validated quantitatively rather than judged only visually.
"""

import time
import uuid
import math
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from core.schemas.navigation_benchmark import (
    NavigationScenarioType,
    NavigationScenarioConfig,
    NavigationScenarioResult,
    NavigationBenchmarkSummary,
    NavigationBenchmarkReport,
)
from core.schemas.representation_bundle import CollisionObstacle
from core.schemas.route_planning import RoutePlanningRequest, RoutePlanningResult
from core.navigation.planner import RoutePlanningEngine
from navigation.graph import NavigationGraphModel, NavNode, NavEdge

logger = logging.getLogger("vastu.navigation.benchmark")


class NavigationBenchmarkSuite:
    """
    Evaluates indoor navigation systems under 9 controlled geometric benchmark scenarios.
    Calculates quantitative metrics with zero reliance on subjective visual inspection.
    """

    def __init__(self, human_radius_m: float = 0.35):
        self.human_radius_m = human_radius_m
        self.planner = RoutePlanningEngine(default_human_radius_m=human_radius_m)

    def run_full_benchmark(self) -> NavigationBenchmarkReport:
        """Runs all 9 benchmark scenarios and compiles the quantitative report."""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        benchmark_id = f"nav_bench_{uuid.uuid4().hex[:8]}"

        scenarios = self.build_all_scenarios()
        results: List[NavigationScenarioResult] = []

        for scenario in scenarios:
            res = self.evaluate_scenario(scenario)
            results.append(res)

        summary = self.calculate_summary_metrics(results)
        
        # Narrative generation
        narrative = (
            f"Navigation Benchmark completed with {summary.total_scenarios_evaluated} scenarios. "
            f"Route success rate on valid paths: {summary.route_success_rate * 100:.1f}%. "
            f"Collision rate across all routes: {summary.collision_rate * 100:.1f}%. "
            f"Invalid route rejection rate: {summary.invalid_route_rejection_rate * 100:.1f}%. "
            f"Mean computation time: {summary.mean_computation_time_ms:.2f}ms. "
            f"Mean waypoint smoothness score: {summary.mean_waypoint_smoothness:.3f}."
        )

        return NavigationBenchmarkReport(
            benchmark_id=benchmark_id,
            timestamp=timestamp,
            summary=summary,
            scenarios=results,
            acceptance_criterion="Navigation is validated quantitatively rather than judged only visually.",
            acceptance_criterion_met=summary.acceptance_criterion_met,
            narrative=narrative
        )

    def evaluate_scenario(self, scenario: NavigationScenarioConfig) -> NavigationScenarioResult:
        """Executes and quantitatively analyzes a single navigation scenario."""
        # 1. Build local navigation graph tailored to the scenario
        graph = self._build_scenario_graph(
            scenario=scenario,
            bounds_x=(-2.0, 9.0),
            bounds_y=(-4.0, 4.0),
            grid_resolution=0.40
        )

        # 2. Measure route computation time
        start_time = time.perf_counter()
        req = RoutePlanningRequest(
            start_position=scenario.start_position,
            destination_coordinates=scenario.destination_position,
            human_radius_m=scenario.human_radius_m,
            require_wheelchair=False
        )
        plan_result = self.planner.plan_route(
            request=req,
            graph=graph,
            obstacles=scenario.obstacles
        )
        computation_time_ms = (time.perf_counter() - start_time) * 1000.0

        direct_dist = float(np.linalg.norm(
            np.array(scenario.destination_position) - np.array(scenario.start_position)
        ))

        # 3. Handle Scenario Result
        if not plan_result.success:
            # Scenario failed to find a path
            rejection_correct = (not scenario.expected_to_succeed)
            return NavigationScenarioResult(
                scenario_type=scenario.scenario_type,
                name=scenario.name,
                success=False,
                rejection_reason=plan_result.rejection_reason,
                path_found=False,
                is_valid=rejection_correct,
                collision_detected=False,
                path_length_meters=0.0,
                direct_euclidean_distance_meters=direct_dist,
                path_efficiency_ratio=0.0,
                computation_time_ms=round(computation_time_ms, 3),
                waypoint_count=0,
                mean_turn_angle_degrees=0.0,
                max_turn_angle_degrees=0.0,
                waypoint_smoothness_score=0.0,
                rejection_correctly_enforced=rejection_correct,
                waypoints=[]
            )

        # 4. Quantitative Analysis on Generated Path
        waypoints = plan_result.waypoints
        path_length = plan_result.total_distance_meters or self._calculate_path_length(waypoints)
        efficiency = (path_length / direct_dist) if direct_dist > 0.0 else 1.0

        # Collision Check: Discretize path into 5cm steps and check against obstacles
        collision_detected = self._verify_path_collision(
            waypoints=waypoints,
            obstacles=scenario.obstacles,
            human_radius=scenario.human_radius_m,
            sample_step_m=0.05
        )

        # Waypoint Smoothness
        mean_turn, max_turn, smoothness_score = self._calculate_smoothness(waypoints)

        # Validity check
        is_valid = (not collision_detected) and (
            scenario.max_acceptable_path_length_m is None or path_length <= scenario.max_acceptable_path_length_m
        )

        return NavigationScenarioResult(
            scenario_type=scenario.scenario_type,
            name=scenario.name,
            success=True,
            rejection_reason=None,
            path_found=True,
            is_valid=is_valid,
            collision_detected=collision_detected,
            path_length_meters=round(path_length, 3),
            direct_euclidean_distance_meters=round(direct_dist, 3),
            path_efficiency_ratio=round(efficiency, 3),
            computation_time_ms=round(computation_time_ms, 3),
            waypoint_count=len(waypoints),
            mean_turn_angle_degrees=round(mean_turn, 2),
            max_turn_angle_degrees=round(max_turn, 2),
            waypoint_smoothness_score=round(smoothness_score, 3),
            rejection_correctly_enforced=False,
            waypoints=waypoints
        )

    def calculate_summary_metrics(
        self,
        results: List[NavigationScenarioResult]
    ) -> NavigationBenchmarkSummary:
        """Aggregates individual scenario results into a quantitative summary."""
        total = len(results)
        valid_scenarios = [r for r in results if r.scenario_type != NavigationScenarioType.DISCONNECTED_REGION]
        invalid_scenarios = [r for r in results if r.scenario_type == NavigationScenarioType.DISCONNECTED_REGION]

        successful_valid = [r for r in valid_scenarios if r.success and r.is_valid]
        success_rate = len(successful_valid) / len(valid_scenarios) if valid_scenarios else 0.0

        # Collision rate: ratio of generated paths that have collisions
        generated_paths = [r for r in results if r.path_found]
        colliding_paths = [r for r in generated_paths if r.collision_detected]
        collision_rate = len(colliding_paths) / len(generated_paths) if generated_paths else 0.0

        # Invalid route rejection rate
        rejected_invalid = [r for r in invalid_scenarios if r.rejection_correctly_enforced]
        rejection_rate = len(rejected_invalid) / len(invalid_scenarios) if invalid_scenarios else 1.0

        # Mean metrics across successful routes
        path_lengths = [r.path_length_meters for r in successful_valid]
        mean_path_len = float(np.mean(path_lengths)) if path_lengths else 0.0

        comp_times = [r.computation_time_ms for r in results]
        mean_comp_time = float(np.mean(comp_times)) if comp_times else 0.0
        max_comp_time = float(np.max(comp_times)) if comp_times else 0.0

        smoothness_scores = [r.waypoint_smoothness_score for r in successful_valid]
        mean_smoothness = float(np.mean(smoothness_scores)) if smoothness_scores else 0.0

        turn_angles = [r.mean_turn_angle_degrees for r in successful_valid]
        mean_turn = float(np.mean(turn_angles)) if turn_angles else 0.0

        # Acceptance Criterion:
        # 1. Success rate on valid routes >= 95%
        # 2. Collision rate == 0.0%
        # 3. Invalid rejection rate == 100.0%
        # 4. Mean computation time < 50ms
        quantitative_passed = (
            success_rate >= 0.95 and
            collision_rate == 0.0 and
            rejection_rate == 1.0 and
            mean_comp_time < 50.0
        )

        return NavigationBenchmarkSummary(
            total_scenarios_evaluated=total,
            valid_scenarios_count=len(valid_scenarios),
            invalid_scenarios_count=len(invalid_scenarios),
            route_success_rate=round(success_rate, 4),
            collision_rate=round(collision_rate, 4),
            mean_path_length_meters=round(mean_path_len, 3),
            mean_computation_time_ms=round(mean_comp_time, 3),
            max_computation_time_ms=round(max_comp_time, 3),
            mean_waypoint_smoothness=round(mean_smoothness, 3),
            mean_turn_angle_degrees=round(mean_turn, 2),
            invalid_route_rejection_rate=round(rejection_rate, 4),
            quantitative_validation_passed=quantitative_passed,
            acceptance_criterion_met=quantitative_passed
        )

    # -------------------------------------------------------------------------
    # SCENARIO BUILDERS
    # -------------------------------------------------------------------------

    def build_all_scenarios(self) -> List[NavigationScenarioConfig]:
        """Constructs the 9 required benchmark scenario configurations."""
        return [
            self._scenario_direct_path(),
            self._scenario_obstacle_around_left(),
            self._scenario_obstacle_around_right(),
            self._scenario_narrow_corridor(),
            self._scenario_furniture_cluster(),
            self._scenario_doorway(),
            self._scenario_disconnected_region(),
            self._scenario_start_near_obstacle(),
            self._scenario_destination_near_obstacle(),
        ]

    def _scenario_direct_path(self) -> NavigationScenarioConfig:
        """1. Direct path in unobstructed space."""
        return NavigationScenarioConfig(
            scenario_type=NavigationScenarioType.DIRECT_PATH,
            name="1. Direct Path",
            description="Unobstructed 8-meter direct line across open space.",
            start_position=[0.0, 0.0, 0.0],
            destination_position=[8.0, 0.0, 0.0],
            obstacles=[],
            expected_to_succeed=True,
            human_radius_m=self.human_radius_m,
            max_acceptable_path_length_m=8.5
        )

    def _scenario_obstacle_around_left(self) -> NavigationScenarioConfig:
        """2. Obstacle blocking direct line, left clearway open."""
        obs = CollisionObstacle(
            obstacle_id="obs_left_block",
            obstacle_type="WALL",
            center=[4.0, -0.6, 1.0],
            extent=[1.6, 2.4, 2.0],  # covers y from -1.8 to +0.6, leaving +y open
            is_walkable=False
        )
        return NavigationScenarioConfig(
            scenario_type=NavigationScenarioType.OBSTACLE_AROUND_LEFT,
            name="2. Obstacle Around Left",
            description="Central obstacle blocking right/center, requiring leftward detour around +Y.",
            start_position=[0.0, 0.0, 0.0],
            destination_position=[8.0, 0.0, 0.0],
            obstacles=[obs],
            expected_to_succeed=True,
            human_radius_m=self.human_radius_m,
            max_acceptable_path_length_m=12.0
        )

    def _scenario_obstacle_around_right(self) -> NavigationScenarioConfig:
        """3. Obstacle blocking direct line, right clearway open."""
        obs = CollisionObstacle(
            obstacle_id="obs_right_block",
            obstacle_type="WALL",
            center=[4.0, 0.6, 1.0],
            extent=[1.6, 2.4, 2.0],  # covers y from -0.6 to +1.8, leaving -y open
            is_walkable=False
        )
        return NavigationScenarioConfig(
            scenario_type=NavigationScenarioType.OBSTACLE_AROUND_RIGHT,
            name="3. Obstacle Around Right",
            description="Central obstacle blocking left/center, requiring rightward detour around -Y.",
            start_position=[0.0, 0.0, 0.0],
            destination_position=[8.0, 0.0, 0.0],
            obstacles=[obs],
            expected_to_succeed=True,
            human_radius_m=self.human_radius_m,
            max_acceptable_path_length_m=12.0
        )

    def _scenario_narrow_corridor(self) -> NavigationScenarioConfig:
        """4. Constricted 1.2m hallway bounded by longitudinal walls."""
        wall_north = CollisionObstacle(
            obstacle_id="corridor_wall_north",
            obstacle_type="WALL",
            center=[4.0, 1.1, 1.0],
            extent=[6.0, 1.0, 2.0],  # y from 0.6 to 1.6
            is_walkable=False
        )
        wall_south = CollisionObstacle(
            obstacle_id="corridor_wall_south",
            obstacle_type="WALL",
            center=[4.0, -1.1, 1.0],
            extent=[6.0, 1.0, 2.0],  # y from -1.6 to -0.6
            is_walkable=False
        )
        return NavigationScenarioConfig(
            scenario_type=NavigationScenarioType.NARROW_CORRIDOR,
            name="4. Narrow Corridor",
            description="1.2m narrow hallway requiring precise human-clearance tracking along centerline.",
            start_position=[0.0, 0.0, 0.0],
            destination_position=[8.0, 0.0, 0.0],
            obstacles=[wall_north, wall_south],
            expected_to_succeed=True,
            human_radius_m=self.human_radius_m,
            max_acceptable_path_length_m=9.0
        )

    def _scenario_furniture_cluster(self) -> NavigationScenarioConfig:
        """5. Cluster of office desks and chairs requiring multi-turn weaving."""
        desk_1 = CollisionObstacle(
            obstacle_id="desk_1",
            obstacle_type="FURNITURE",
            center=[2.4, 1.2, 0.4],
            extent=[1.2, 0.8, 0.8],
            is_walkable=False
        )
        desk_2 = CollisionObstacle(
            obstacle_id="desk_2",
            obstacle_type="FURNITURE",
            center=[4.4, -1.2, 0.4],
            extent=[1.2, 0.8, 0.8],
            is_walkable=False
        )
        chair = CollisionObstacle(
            obstacle_id="chair_1",
            obstacle_type="FURNITURE",
            center=[2.4, -1.1, 0.4],
            extent=[0.6, 0.6, 0.8],
            is_walkable=False
        )
        return NavigationScenarioConfig(
            scenario_type=NavigationScenarioType.FURNITURE_CLUSTER,
            name="5. Furniture Cluster",
            description="Staggered furniture layout requiring multi-obstacle avoidance and weaving.",
            start_position=[0.0, 0.0, 0.0],
            destination_position=[7.0, 0.0, 0.0],
            obstacles=[desk_1, desk_2, chair],
            expected_to_succeed=True,
            human_radius_m=self.human_radius_m,
            max_acceptable_path_length_m=11.0
        )

    def _scenario_doorway(self) -> NavigationScenarioConfig:
        """6. Wall partition with a standard 0.90m doorway clearance."""
        wall_north = CollisionObstacle(
            obstacle_id="door_wall_north",
            obstacle_type="WALL",
            center=[3.5, 2.25, 1.0],
            extent=[0.4, 3.5, 2.0],  # y from 0.5 to 4.0
            is_walkable=False
        )
        wall_south = CollisionObstacle(
            obstacle_id="door_wall_south",
            obstacle_type="WALL",
            center=[3.5, -2.25, 1.0],
            extent=[0.4, 3.5, 2.0],  # y from -4.0 to -0.5
            is_walkable=False
        )
        # Doorway gap between y = -0.5 and y = +0.5 (1.0m clearance)
        return NavigationScenarioConfig(
            scenario_type=NavigationScenarioType.DOORWAY,
            name="6. Doorway",
            description="Navigating from Room 1 to Room 2 through a 1.0m architectural doorway.",
            start_position=[1.0, 0.0, 0.0],
            destination_position=[6.0, 0.0, 0.0],
            obstacles=[wall_north, wall_south],
            expected_to_succeed=True,
            human_radius_m=self.human_radius_m,
            max_acceptable_path_length_m=7.5
        )

    def _scenario_disconnected_region(self) -> NavigationScenarioConfig:
        """7. Completely partitioned space without doorway (must reject cleanly)."""
        solid_wall = CollisionObstacle(
            obstacle_id="solid_wall",
            obstacle_type="WALL",
            center=[3.5, 0.0, 1.0],
            extent=[0.5, 10.0, 2.0],  # unbroken wall across whole y domain
            is_walkable=False
        )
        return NavigationScenarioConfig(
            scenario_type=NavigationScenarioType.DISCONNECTED_REGION,
            name="7. Disconnected Region",
            description="Completely partitioned room without opening. Must cleanly reject without returning route.",
            start_position=[1.0, 0.0, 0.0],
            destination_position=[6.0, 0.0, 0.0],
            obstacles=[solid_wall],
            expected_to_succeed=False,
            human_radius_m=self.human_radius_m
        )

    def _scenario_start_near_obstacle(self) -> NavigationScenarioConfig:
        """8. Start position situated adjacent to an obstacle."""
        credenza = CollisionObstacle(
            obstacle_id="credenza",
            obstacle_type="FURNITURE",
            center=[0.0, 1.0, 0.4],
            extent=[1.2, 0.8, 0.8],  # y from 0.6 to 1.4, x from -0.6 to +0.6
            is_walkable=False
        )
        # Start at (0.0, 0.15, 0.0) -> 0.45m from front edge at y=0.6 (10cm clearance > human radius 0.35m)
        return NavigationScenarioConfig(
            scenario_type=NavigationScenarioType.START_NEAR_OBSTACLE,
            name="8. Start Near Obstacle",
            description="Start position adjacent to furniture. Tests nearest node resolution and safe departure.",
            start_position=[0.0, 0.15, 0.0],
            destination_position=[5.0, -1.0, 0.0],
            obstacles=[credenza],
            expected_to_succeed=True,
            human_radius_m=self.human_radius_m,
            max_acceptable_path_length_m=8.5
        )

    def _scenario_destination_near_obstacle(self) -> NavigationScenarioConfig:
        """9. Destination positioned adjacent to wall boundary."""
        back_wall = CollisionObstacle(
            obstacle_id="back_wall",
            obstacle_type="WALL",
            center=[6.0, 1.5, 1.0],
            extent=[0.4, 2.0, 2.0],  # x from 5.8 to 6.2
            is_walkable=False
        )
        # Target at (5.35, 1.5, 0.0) -> 0.45m from front face at x=5.8 (10cm clearance > human radius 0.35m)
        return NavigationScenarioConfig(
            scenario_type=NavigationScenarioType.DESTINATION_NEAR_OBSTACLE,
            name="9. Destination Near Obstacle",
            description="Destination POI adjacent to wall. Tests endpoint arrival and clearance validation.",
            start_position=[0.0, 0.0, 0.0],
            destination_position=[5.35, 1.5, 0.0],
            obstacles=[back_wall],
            expected_to_succeed=True,
            human_radius_m=self.human_radius_m,
            max_acceptable_path_length_m=8.5
        )

    # -------------------------------------------------------------------------
    # GRAPH GENERATION & QUANTITATIVE HELPERS
    # -------------------------------------------------------------------------

    def _build_scenario_graph(
        self,
        scenario: NavigationScenarioConfig,
        bounds_x: Tuple[float, float],
        bounds_y: Tuple[float, float],
        grid_resolution: float = 0.40
    ) -> NavigationGraphModel:
        """
        Builds a 2.5D metric NavigationGraphModel with obstacle clearance.
        Edges that collide with obstacle boundaries within human_radius are omitted.
        """
        graph = NavigationGraphModel()
        x_min, x_max = bounds_x
        y_min, y_max = bounds_y

        xs = np.arange(x_min, x_max + grid_resolution, grid_resolution)
        ys = np.arange(y_min, y_max + grid_resolution, grid_resolution)

        nodes: Dict[Tuple[int, int], NavNode] = {}
        node_id_counter = 1

        for i, x in enumerate(xs):
            for j, y in enumerate(ys):
                pt = np.array([x, y, 0.0])
                # Filter out nodes that fall inside an obstacle
                if self._point_inside_any_obstacle(pt, scenario.obstacles, margin=scenario.human_radius_m * 0.7):
                    continue
                nid = f"n_{node_id_counter}"
                node_id_counter += 1
                n = NavNode(nid, float(x), float(y), 0.0, is_wheelchair_accessible=True, floor_level=1)
                graph.add_node(n)
                nodes[(i, j)] = n

        # Add 4-connected edges if edge does not intersect any obstacle
        edge_counter = 1
        for (i, j), n in nodes.items():
            for di, dj in [(1, 0), (0, 1)]:
                neighbor_idx = (i + di, j + dj)
                if neighbor_idx in nodes:
                    neighbor = nodes[neighbor_idx]
                    p1 = n.position
                    p2 = neighbor.position
                    
                    if not self._segment_collides_with_obstacles(p1, p2, scenario.obstacles, scenario.human_radius_m * 0.8):
                        dist = float(np.linalg.norm(p2 - p1))
                        e1 = NavEdge(f"e_{edge_counter}", n, neighbor, clearance_width_meters=1.5)
                        e2 = NavEdge(f"e_{edge_counter+1}", neighbor, n, clearance_width_meters=1.5)
                        graph.add_edge(e1)
                        graph.add_edge(e2)
                        edge_counter += 2

        return graph

    def _point_inside_any_obstacle(
        self,
        pt: np.ndarray,
        obstacles: List[CollisionObstacle],
        margin: float = 0.0
    ) -> bool:
        """Determines if a 3D point is inside an obstacle AABB (with margin)."""
        for obs in obstacles:
            cx, cy, _ = obs.center
            ex, ey, _ = obs.extent
            hx = (ex / 2.0) + margin
            hy = (ey / 2.0) + margin
            if (cx - hx) <= pt[0] <= (cx + hx) and (cy - hy) <= pt[1] <= (cy + hy):
                return True
        return False

    def _segment_collides_with_obstacles(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        obstacles: List[CollisionObstacle],
        radius: float
    ) -> bool:
        """Checks if line segment p1 -> p2 collides with obstacles (swept sphere)."""
        seg_vec = p2 - p1
        seg_len = float(np.linalg.norm(seg_vec))
        if seg_len < 1e-4:
            return self._point_inside_any_obstacle(p1, obstacles, margin=radius)

        steps = max(2, int(math.ceil(seg_len / 0.10)))
        for s in range(steps + 1):
            t = s / float(steps)
            sample_pt = p1 + t * seg_vec
            if self._point_inside_any_obstacle(sample_pt, obstacles, margin=radius):
                return True
        return False

    def _verify_path_collision(
        self,
        waypoints: List[List[float]],
        obstacles: List[CollisionObstacle],
        human_radius: float,
        sample_step_m: float = 0.05
    ) -> bool:
        """
        Rigorously checks if any segment of the computed waypoints collides with
        obstacle bounding boxes taking human radius into account.
        """
        if not obstacles or len(waypoints) < 2:
            return False

        for i in range(len(waypoints) - 1):
            p1 = np.array(waypoints[i])
            p2 = np.array(waypoints[i+1])
            vec = p2 - p1
            dist = float(np.linalg.norm(vec))
            if dist < 1e-4:
                continue

            steps = max(2, int(math.ceil(dist / sample_step_m)))
            for s in range(steps + 1):
                t = s / float(steps)
                pt = p1 + t * vec
                # Check against each obstacle
                for obs in obstacles:
                    cx, cy, _ = obs.center
                    ex, ey, _ = obs.extent
                    hx = ex / 2.0
                    hy = ey / 2.0
                    # Distance from pt (x, y) to AABB [cx-hx, cx+hx] x [cy-hy, cy+hy]
                    dx = max(0.0, abs(pt[0] - cx) - hx)
                    dy = max(0.0, abs(pt[1] - cy) - hy)
                    d_to_aabb = math.sqrt(dx * dx + dy * dy)
                    if d_to_aabb < human_radius:
                        return True
        return False

    def _calculate_smoothness(
        self,
        waypoints: List[List[float]]
    ) -> Tuple[float, float, float]:
        """
        Calculates waypoint smoothness:
        - Mean turn angle (degrees)
        - Max turn angle (degrees)
        - Waypoint smoothness score in [0.0, 1.0] (1.0 = straight line)
        """
        if len(waypoints) <= 2:
            return 0.0, 0.0, 1.0

        angles: List[float] = []
        for i in range(1, len(waypoints) - 1):
            v_in = np.array(waypoints[i]) - np.array(waypoints[i-1])
            v_out = np.array(waypoints[i+1]) - np.array(waypoints[i])

            # 2D projection
            v_in_2d = v_in[:2]
            v_out_2d = v_out[:2]

            norm_in = float(np.linalg.norm(v_in_2d))
            norm_out = float(np.linalg.norm(v_out_2d))

            if norm_in < 1e-4 or norm_out < 1e-4:
                continue

            cos_theta = np.dot(v_in_2d, v_out_2d) / (norm_in * norm_out)
            cos_theta = np.clip(cos_theta, -1.0, 1.0)
            angle_rad = math.acos(cos_theta)
            angles.append(math.degrees(angle_rad))

        if not angles:
            return 0.0, 0.0, 1.0

        mean_turn = float(np.mean(angles))
        max_turn = float(np.max(angles))
        # Smoothness factor: decays with high turning angles
        smoothness = max(0.0, 1.0 - (mean_turn / 90.0))
        return mean_turn, max_turn, smoothness

    def _calculate_path_length(self, waypoints: List[List[float]]) -> float:
        """Computes total 3D path length across waypoints."""
        if len(waypoints) < 2:
            return 0.0
        tot = 0.0
        for i in range(len(waypoints) - 1):
            tot += float(np.linalg.norm(
                np.array(waypoints[i+1]) - np.array(waypoints[i])
            ))
        return tot
