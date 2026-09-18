"""
VĀSTU Route Planning Engine (Stage 22)
Implements the 5-stage route planning pipeline:
nearest valid navigation point
-> multi-criteria A*
-> waypoint extraction
-> path smoothing (string pulling)
-> collision validation against collision model
-> route result.

Multi-factor cost considers:
- Distance
- Excessive turns
- Narrow passages
- Wheelchair accessibility (slopes <= 4.76 deg, width >= 0.90m, no stairs)
- Invalid/unsafe areas

Strict Rule: Rejects invalid/colliding routes rather than returning them.
Acceptance Criterion: Every returned route is collision-free against the current collision model.
"""

import math
import uuid
import heapq
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
import numpy as np

from core.schemas.route_planning import (
    RoutePlanningRequest,
    RouteTurnStep,
    RoutePlanningResult
)
from core.schemas.representation_bundle import CollisionObstacle
from core.poi.service import POIService
from navigation.graph import NavigationGraphModel, NavNode, NavEdge

logger = logging.getLogger("vastu.navigation.planner")


class RoutePlanningEngine:
    """
    Multi-criteria indoor route planning engine.
    Derives collision-free, smoothed paths with turn-by-turn navigation.
    """

    def __init__(self, default_human_radius_m: float = 0.35):
        self.default_human_radius_m = default_human_radius_m

    def plan_route(
        self,
        request: RoutePlanningRequest,
        graph: NavigationGraphModel,
        obstacles: Optional[List[CollisionObstacle]] = None,
        poi_service: Optional[POIService] = None
    ) -> RoutePlanningResult:
        """
        Executes the 5-stage route planning pipeline:
        nearest valid point -> A* -> waypoint extraction -> path smoothing -> collision validation.
        """
        route_id = f"route_{uuid.uuid4().hex[:8]}"
        start_pt = np.array(request.start_position, dtype=np.float64)
        human_r = request.human_radius_m or self.default_human_radius_m
        obs_list = obstacles or []

        # ---------------------------------------------------------------------
        # STAGE 1: Nearest Valid Navigation Point & Endpoint Resolution
        # ---------------------------------------------------------------------
        target_pt, dest_poi_name = self._resolve_target_endpoint(request, poi_service)
        if target_pt is None:
            return RoutePlanningResult(
                success=False,
                route_id=route_id,
                rejection_reason="REJECTED_DESTINATION_NOT_FOUND: POI could not be resolved in spatial service.",
                start_position=request.start_position,
                destination_position=[0.0, 0.0, 0.0],
                collision_validated=False
            )

        # Check if start or target is inside an obstacle
        if self._point_inside_any_obstacle(start_pt, obs_list, margin=0.05):
            return RoutePlanningResult(
                success=False,
                route_id=route_id,
                rejection_reason="REJECTED_START_INSIDE_OBSTACLE: Start position is located inside an impassable collision obstacle.",
                start_position=request.start_position,
                destination_position=target_pt.tolist(),
                collision_validated=False
            )

        if self._point_inside_any_obstacle(target_pt, obs_list, margin=0.05):
            return RoutePlanningResult(
                success=False,
                route_id=route_id,
                rejection_reason="REJECTED_DESTINATION_INSIDE_OBSTACLE: Destination position is located inside an impassable collision obstacle.",
                start_position=request.start_position,
                destination_position=target_pt.tolist(),
                collision_validated=False
            )

        # Find nearest graph nodes
        start_node = graph.find_nearest_node(start_pt, require_wheelchair=request.require_wheelchair)
        target_node = graph.find_nearest_node(target_pt, require_wheelchair=request.require_wheelchair)

        if not start_node or not target_node:
            return RoutePlanningResult(
                success=False,
                route_id=route_id,
                rejection_reason="REJECTED_OUTSIDE_WALKABLE_NETWORK: No reachable navigation nodes found within walkable network.",
                start_position=request.start_position,
                destination_position=target_pt.tolist(),
                collision_validated=False
            )

        # Ensure start and target are not too far from valid nodes (> 10m indicates disconnected floor/island)
        if np.linalg.norm(start_node.position - start_pt) > 10.0 or np.linalg.norm(target_node.position - target_pt) > 10.0:
            return RoutePlanningResult(
                success=False,
                route_id=route_id,
                rejection_reason="REJECTED_DISCONNECTED_REGION: Endpoints exceed maximum access threshold to walkable network.",
                start_position=request.start_position,
                destination_position=target_pt.tolist(),
                collision_validated=False
            )

        # ---------------------------------------------------------------------
        # STAGE 2: Multi-Criteria A* Search
        # ---------------------------------------------------------------------
        astar_res = self._run_multi_criteria_astar(
            graph=graph,
            start_node=start_node,
            target_node=target_node,
            request=request
        )

        if not astar_res:
            return RoutePlanningResult(
                success=False,
                route_id=route_id,
                rejection_reason="REJECTED_NO_TRAVERSABLE_ROUTE: Pathfinding could not find a traversable route meeting slope/clearance constraints.",
                start_position=request.start_position,
                destination_position=target_pt.tolist(),
                collision_validated=False
            )

        path_nodes, path_edges = astar_res

        # ---------------------------------------------------------------------
        # STAGE 3: Waypoint Extraction
        # ---------------------------------------------------------------------
        unfiltered_pts = [start_pt.tolist()] + [n.position.tolist() for n in path_nodes] + [target_pt.tolist()]
        raw_waypoints = []
        for pt in unfiltered_pts:
            if not raw_waypoints or np.linalg.norm(np.array(pt) - np.array(raw_waypoints[-1])) > 1e-4:
                raw_waypoints.append(pt)

        # ---------------------------------------------------------------------
        # STAGE 4: Path Smoothing (String-Pulling Shortcut Algorithm)
        # ---------------------------------------------------------------------
        if request.enable_smoothing and len(raw_waypoints) > 2:
            smoothed_waypoints = self._smooth_path_string_pulling(raw_waypoints, obs_list, human_r)
        else:
            smoothed_waypoints = raw_waypoints

        # ---------------------------------------------------------------------
        # STAGE 5: Strict Collision Validation Against Current Collision Model
        # ---------------------------------------------------------------------
        is_safe, min_clearance, coll_diag = self._validate_collision_safety(
            waypoints=smoothed_waypoints,
            obstacles=obs_list,
            human_radius_m=human_r
        )

        if not is_safe:
            # Rejection policy: Never return an unsafe route!
            return RoutePlanningResult(
                success=False,
                route_id=route_id,
                rejection_reason=f"REJECTED_COLLISION_DETECTED: {coll_diag}",
                start_position=request.start_position,
                destination_position=target_pt.tolist(),
                raw_waypoints=raw_waypoints,
                min_obstacle_clearance_meters=round(min_clearance, 2),
                collision_validated=False
            )

        # ---------------------------------------------------------------------
        # STAGE 6: Route Result Assembly & Turn Instructions
        # ---------------------------------------------------------------------
        total_dist = sum(
            float(np.linalg.norm(np.array(smoothed_waypoints[i+1]) - np.array(smoothed_waypoints[i])))
            for i in range(len(smoothed_waypoints) - 1)
        )
        est_seconds = int(total_dist / 1.2)  # ~1.2 m/s avg walking speed

        turn_steps, turn_count = self._generate_turn_steps(smoothed_waypoints)
        narrow_count = sum(1 for e in path_edges if e.clearance_width_meters < 1.20)
        max_slope = max([e.slope_degrees for e in path_edges] or [0.0])

        return RoutePlanningResult(
            success=True,
            route_id=route_id,
            start_position=request.start_position,
            destination_poi_id=request.destination_poi_id,
            destination_poi_name=dest_poi_name,
            destination_position=target_pt.tolist(),
            waypoints=smoothed_waypoints,
            raw_waypoints=raw_waypoints,
            total_distance_meters=round(total_dist, 2),
            estimated_duration_seconds=est_seconds,
            turn_count=turn_count,
            narrow_passage_count=narrow_count,
            is_wheelchair_accessible=all(e.is_wheelchair_accessible for e in path_edges),
            max_slope_degrees=round(float(max_slope), 2),
            min_obstacle_clearance_meters=round(float(min_clearance), 2),
            collision_validated=True,  # Acceptance criterion: Verified collision-free
            steps=turn_steps,
            metadata={
                "smoothed_node_reduction": len(raw_waypoints) - len(smoothed_waypoints),
                "graph_nodes_traversed": len(path_nodes),
                "human_clearance_radius_m": human_r
            }
        )

    # -------------------------------------------------------------------------
    # Helper: Endpoint Resolution
    # -------------------------------------------------------------------------
    def _resolve_target_endpoint(
        self,
        request: RoutePlanningRequest,
        poi_service: Optional[POIService]
    ) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """Resolves target coordinate from POI ID or explicit coordinates."""
        if request.destination_poi_id and poi_service:
            poi = poi_service.get_poi(request.destination_poi_id)
            if poi:
                # If camera viewpoint exists, use viewpoint coordinates for optimal approach
                vp = getattr(poi, "camera_viewpoint", None) or getattr(poi, "viewpoint", None)
                if vp:
                    if hasattr(vp, "position"):
                        target_coords = list(vp.position)
                    elif hasattr(vp, "x"):
                        target_coords = [vp.x, vp.y, vp.z]
                    else:
                        target_coords = [poi.coordinates.x, poi.coordinates.y, poi.coordinates.z]
                else:
                    target_coords = [poi.coordinates.x, poi.coordinates.y, poi.coordinates.z]
                return np.array(target_coords, dtype=np.float64), poi.name

        if request.destination_coordinates:
            return np.array(request.destination_coordinates, dtype=np.float64), None

        return None, None

    # -------------------------------------------------------------------------
    # Helper: Multi-Criteria A* Pathfinding
    # -------------------------------------------------------------------------
    def _run_multi_criteria_astar(
        self,
        graph: NavigationGraphModel,
        start_node: NavNode,
        target_node: NavNode,
        request: RoutePlanningRequest
    ) -> Optional[Tuple[List[NavNode], List[NavEdge]]]:
        """
        A* pathfinding with multi-factor edge cost:
        cost = distance + w_turn * turn_penalty + w_narrow * narrow_penalty + wheelchair_constraints.
        """
        # (f_score, counter, current_node_id, incoming_edge_id)
        counter = 0
        open_set = []
        heapq.heappush(open_set, (0.0, counter, start_node.node_id, None))

        came_from: Dict[str, Tuple[str, NavEdge]] = {}
        g_score: Dict[str, float] = {node_id: float("inf") for node_id in graph.nodes}
        g_score[start_node.node_id] = 0.0

        visited = set()

        while open_set:
            _, _, current_id, in_edge_id = heapq.heappop(open_set)
            if current_id in visited:
                continue
            visited.add(current_id)

            if current_id == target_node.node_id:
                # Reconstruct path
                return self._reconstruct_path(graph, came_from, target_node.node_id)

            current_node = graph.nodes[current_id]
            in_edge = graph.edges.get(in_edge_id) if in_edge_id else None

            for edge in current_node.edges:
                neighbor = edge.to_node

                # Wheelchair & Accessibility Constraints
                if request.require_wheelchair:
                    if not edge.is_wheelchair_accessible:
                        continue
                    if edge.slope_degrees > 4.76:  # ADA 1:12 slope threshold
                        continue
                    if edge.clearance_width_meters < 0.90:  # Minimum wheelchair hallway width
                        continue
                    if edge.edge_type == "STAIRS":
                        continue

                if request.avoid_stairs and edge.edge_type == "STAIRS":
                    continue

                # Impassable narrow passage (< 2 * human_radius)
                if edge.clearance_width_meters < (2.0 * request.human_radius_m):
                    continue

                # 1. Base Distance
                edge_cost = edge.distance_meters

                # 2. Excessive Turns Penalty
                turn_penalty = 0.0
                if in_edge is not None:
                    v_in = in_edge.to_node.position - in_edge.from_node.position
                    v_out = edge.to_node.position - edge.from_node.position
                    norm_in = np.linalg.norm(v_in[:2])
                    norm_out = np.linalg.norm(v_out[:2])
                    if norm_in > 1e-4 and norm_out > 1e-4:
                        cos_angle = float(np.clip(np.dot(v_in[:2], v_out[:2]) / (norm_in * norm_out), -1.0, 1.0))
                        turn_rad = math.acos(cos_angle)
                        # Penalize sharp angles
                        turn_penalty = (turn_rad / math.pi) ** 2 * request.turn_penalty_weight * edge.distance_meters

                # 3. Narrow Passage Penalty (if clearance < 1.20m)
                narrow_penalty = 0.0
                if edge.clearance_width_meters < 1.20:
                    narrow_penalty = (1.20 - edge.clearance_width_meters) ** 2 * request.narrow_passage_penalty_weight * edge.distance_meters

                total_edge_cost = edge_cost + turn_penalty + narrow_penalty

                tentative_g = g_score[current_id] + total_edge_cost
                if tentative_g < g_score[neighbor.node_id]:
                    came_from[neighbor.node_id] = (current_id, edge)
                    g_score[neighbor.node_id] = tentative_g
                    h_val = float(np.linalg.norm(neighbor.position - target_node.position))
                    f_val = tentative_g + h_val

                    counter += 1
                    heapq.heappush(open_set, (f_val, counter, neighbor.node_id, edge.edge_id))

        return None

    def _reconstruct_path(
        self,
        graph: NavigationGraphModel,
        came_from: Dict[str, Tuple[str, NavEdge]],
        target_id: str
    ) -> Tuple[List[NavNode], List[NavEdge]]:
        curr = target_id
        path_nodes = []
        path_edges = []
        while curr in came_from:
            prev_id, edge = came_from[curr]
            path_nodes.append(graph.nodes[curr])
            path_edges.append(edge)
            curr = prev_id

        path_nodes.append(graph.nodes[curr])
        path_nodes.reverse()
        path_edges.reverse()
        return path_nodes, path_edges

    # -------------------------------------------------------------------------
    # STAGE 4: Path Smoothing (String-Pulling Shortcut Algorithm)
    # -------------------------------------------------------------------------
    def _smooth_path_string_pulling(
        self,
        waypoints: List[List[float]],
        obstacles: List[CollisionObstacle],
        human_radius_m: float
    ) -> List[List[float]]:
        """
        Applies greedy line-of-sight shortcutting:
        Reduces unnecessary zig-zag lattice steps without violating obstacle clearances.
        """
        if len(waypoints) <= 2:
            return waypoints

        smoothed = [waypoints[0]]
        curr_idx = 0

        while curr_idx < len(waypoints) - 1:
            best_next = curr_idx + 1
            # Check furthest reachable waypoint with direct line-of-sight
            for test_idx in range(len(waypoints) - 1, curr_idx + 1, -1):
                p1 = np.array(waypoints[curr_idx])
                p2 = np.array(waypoints[test_idx])
                if self._line_of_sight_clear(p1, p2, obstacles, human_radius_m):
                    best_next = test_idx
                    break

            smoothed.append(waypoints[best_next])
            curr_idx = best_next

        return smoothed

    def _line_of_sight_clear(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        obstacles: List[CollisionObstacle],
        human_radius_m: float
    ) -> bool:
        """Tests if direct line segment p1 -> p2 maintains clearance from all obstacles."""
        dist = float(np.linalg.norm(p2 - p1))
        if dist < 1e-4:
            return True

        # Check sample steps every 0.15m
        num_samples = max(2, int(dist / 0.15))
        for step in range(num_samples + 1):
            t = step / float(num_samples)
            pt = (1.0 - t) * p1 + t * p2
            for obs in obstacles:
                d = self._distance_point_to_obstacle_2d(pt[:2], obs)
                if d < human_radius_m:
                    return False
        return True

    # -------------------------------------------------------------------------
    # STAGE 5: Strict Collision Validation Against Current Collision Model
    # -------------------------------------------------------------------------
    def _validate_collision_safety(
        self,
        waypoints: List[List[float]],
        obstacles: List[CollisionObstacle],
        human_radius_m: float
    ) -> Tuple[bool, float, str]:
        """
        Densely samples every path segment (every 0.10m) against all 3D obstacles.
        Acceptance criterion: Every returned route must be collision-free.
        """
        min_clearance = float("inf")

        if not obstacles:
            return True, 5.0, "No obstacles present in model."

        for i in range(len(waypoints) - 1):
            p1 = np.array(waypoints[i])
            p2 = np.array(waypoints[i + 1])
            seg_len = float(np.linalg.norm(p2 - p1))
            steps = max(2, int(seg_len / 0.10))

            for s in range(steps + 1):
                t = s / float(steps)
                pt = (1.0 - t) * p1 + t * p2

                for obs in obstacles:
                    d = self._distance_point_to_obstacle_2d(pt[:2], obs)
                    if d < min_clearance:
                        min_clearance = d

                    if d < human_radius_m:
                        diag = (
                            f"Path segment {i}->{i+1} at coordinate [{pt[0]:.2f}, {pt[1]:.2f}] "
                            f"collides with obstacle '{obs.obstacle_id}' ({obs.obstacle_type}). "
                            f"Clearance {d:.2f}m < required human radius {human_radius_m:.2f}m."
                        )
                        return False, min_clearance, diag

        return True, min_clearance, "Route verified 100% collision-free."

    def _distance_point_to_obstacle_2d(self, pt: np.ndarray, obs: CollisionObstacle) -> float:
        """Computes Euclidean distance from a 2D point to an axis-aligned bounding box."""
        cx, cy = obs.center[0], obs.center[1]
        hx, hy = obs.extent[0] / 2.0, obs.extent[1] / 2.0

        dx = max(0.0, abs(pt[0] - cx) - hx)
        dy = max(0.0, abs(pt[1] - cy) - hy)
        return float(math.sqrt(dx * dx + dy * dy))

    def _point_inside_any_obstacle(
        self,
        pt: np.ndarray,
        obstacles: List[CollisionObstacle],
        margin: float = 0.0
    ) -> bool:
        """Checks if point is inside any obstacle volume."""
        for obs in obstacles:
            cx, cy = obs.center[0], obs.center[1]
            hx, hy = obs.extent[0] / 2.0 + margin, obs.extent[1] / 2.0 + margin
            if abs(pt[0] - cx) <= hx and abs(pt[1] - cy) <= hy:
                return True
        return False

    # -------------------------------------------------------------------------
    # STAGE 6: Turn Step Guidance Generation
    # -------------------------------------------------------------------------
    def _generate_turn_steps(self, waypoints: List[List[float]]) -> Tuple[List[RouteTurnStep], int]:
        """Formulates turn-by-turn guidance steps from sequential waypoints."""
        if len(waypoints) < 2:
            return [], 0

        steps: List[RouteTurnStep] = []
        turn_count = 0

        # Step 1: Start
        p0 = np.array(waypoints[0])
        p1 = np.array(waypoints[1])
        d0 = float(np.linalg.norm(p1 - p0))
        steps.append(RouteTurnStep(
            step_number=1,
            instruction=f"Depart start location and proceed forward {d0:.1f} meters.",
            distance_meters=round(d0, 1),
            action="START",
            turn_angle_deg=0.0,
            coordinate=waypoints[0]
        ))

        # Intermediate turn steps
        for i in range(1, len(waypoints) - 1):
            prev_p = np.array(waypoints[i - 1])
            curr_p = np.array(waypoints[i])
            next_p = np.array(waypoints[i + 1])

            v1 = curr_p[:2] - prev_p[:2]
            v2 = next_p[:2] - curr_p[:2]
            dist_next = float(np.linalg.norm(v2))

            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)

            if norm1 > 1e-4 and norm2 > 1e-4:
                cross_z = v1[0] * v2[1] - v1[1] * v2[0]
                dot_prod = np.dot(v1, v2)
                angle_deg = math.degrees(math.atan2(cross_z, dot_prod))

                if abs(angle_deg) > 20.0:
                    turn_count += 1
                    if angle_deg > 65.0:
                        action = "TURN_LEFT"
                        action_text = "Turn left"
                    elif angle_deg > 20.0:
                        action = "SLIGHT_LEFT"
                        action_text = "Turn slightly left"
                    elif angle_deg < -65.0:
                        action = "TURN_RIGHT"
                        action_text = "Turn right"
                    else:
                        action = "SLIGHT_RIGHT"
                        action_text = "Turn slightly right"

                    steps.append(RouteTurnStep(
                        step_number=len(steps) + 1,
                        instruction=f"{action_text} and walk {dist_next:.1f} meters.",
                        distance_meters=round(dist_next, 1),
                        action=action,
                        turn_angle_deg=round(abs(angle_deg), 1),
                        coordinate=curr_p.tolist()
                    ))
                else:
                    steps.append(RouteTurnStep(
                        step_number=len(steps) + 1,
                        instruction=f"Continue straight for {dist_next:.1f} meters.",
                        distance_meters=round(dist_next, 1),
                        action="CONTINUE",
                        turn_angle_deg=0.0,
                        coordinate=curr_p.tolist()
                    ))

        # Final Step: Arrive
        steps.append(RouteTurnStep(
            step_number=len(steps) + 1,
            instruction="You have arrived at your destination.",
            distance_meters=0.0,
            action="ARRIVE",
            turn_angle_deg=0.0,
            coordinate=waypoints[-1]
        ))

        return steps, turn_count
