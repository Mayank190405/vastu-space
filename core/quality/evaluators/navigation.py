"""
Navigation Quality Evaluator:
Evaluates indoor accessibility and pathfinding readiness:
- floor continuity: smooth traversability without unexpected elevation steps
- obstacle validity: obstacle colliders properly bounded and cleared from corridors
- route feasibility: reachable paths connecting origin/entrance to all key POIs
- wheelchair ADA compliance: ramp slopes <= 4.76 degrees (1:12 slope)
"""

from typing import Dict, Any, List, Tuple
from core.schemas.quality_engine import NavigationQualityMetrics

class NavigationQualityEvaluator:
    def __init__(
        self,
        min_floor_continuity: float = 0.85,
        min_obstacle_validity: float = 0.85,
        min_route_feasibility: float = 0.90,
        require_ada_compliance: bool = True,
    ):
        self.min_floor_continuity = min_floor_continuity
        self.min_obstacle_validity = min_obstacle_validity
        self.min_route_feasibility = min_route_feasibility
        self.require_ada_compliance = require_ada_compliance

    def evaluate(self, nav_data: Dict[str, Any]) -> Tuple[NavigationQualityMetrics, List[str], List[str]]:
        """
        Evaluates navigation graph and collision readiness.
        Returns (NavigationQualityMetrics, hard_failures, warnings).
        """
        floor_cont = float(nav_data.get("floor_continuity_ratio", 0.96))
        obs_valid = float(nav_data.get("obstacle_validity_ratio", 0.94))
        route_feas = float(nav_data.get("route_feasibility_ratio", 1.00))
        ada_compliant = bool(nav_data.get("wheelchair_ada_compliant", True))
        disconnected_routes = nav_data.get("disconnected_routes", [])

        issues = []
        hard_failures = []
        warnings = []

        if floor_cont < self.min_floor_continuity:
            msg = f"Discontinuous floor geometry detected ({floor_cont * 100:.1f}% < required: {self.min_floor_continuity * 100:.1f}%)"
            issues.append(msg)
            if floor_cont < 0.60:
                hard_failures.append(f"[HARD_FAIL: NAVIGATION] {msg}")
            else:
                warnings.append(f"[WARN: NAVIGATION] {msg}")

        if obs_valid < self.min_obstacle_validity:
            msg = f"Invalid obstacle collider bounds encroaching traversable corridor ({obs_valid * 100:.1f}% < threshold: {self.min_obstacle_validity * 100:.1f}%)"
            issues.append(msg)
            warnings.append(f"[WARN: NAVIGATION] {msg}")

        if route_feas < self.min_route_feasibility or len(disconnected_routes) > 0:
            routes_str = f": {', '.join(disconnected_routes)}" if disconnected_routes else ""
            msg = f"Disconnected indoor routes detected{routes_str} (reachability: {route_feas * 100:.1f}% < required: {self.min_route_feasibility * 100:.1f}%)"
            issues.append(msg)
            hard_failures.append(f"[HARD_FAIL: NAVIGATION] {msg}")

        if self.require_ada_compliance and not ada_compliant:
            msg = "Wheelchair accessibility violation: ramp slope exceeds ADA maximum 4.76 degrees"
            issues.append(msg)
            warnings.append(f"[WARN: NAVIGATION] {msg}")

        metrics = NavigationQualityMetrics(
            floor_continuity_ratio=floor_cont,
            obstacle_validity_ratio=obs_valid,
            route_feasibility_ratio=route_feas,
            wheelchair_ada_compliant=ada_compliant,
            issues=issues
        )
        return metrics, hard_failures, warnings
