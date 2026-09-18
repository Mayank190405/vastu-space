"""
Architectural Plane Graph: Topological graph representation of building structural planes,
wall-to-wall corners, floor/ceiling junctions, and analytical intersection edges.
"""

from typing import Dict, List, Any, Optional
import json
from core.schemas.structural_geometry import (
    StructuralPlane,
    PlaneEquation,
    PlaneIntersectionEdge,
    ArchitecturalPlaneGraphSchema
)

class ArchitecturalPlaneGraph:
    def __init__(self, metadata: Optional[Dict[str, Any]] = None):
        self.metadata = metadata or {}
        self.planes: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[str, Dict[str, Any]] = {}

    def add_plane(
        self,
        plane_id: str,
        plane_type: str,
        plane_equation: List[float],
        normal: List[float],
        inlier_count: int,
        surface_area_m2: float,
        confidence: float = 1.0,
        rmse_m: float = 0.0,
        corners_3d: Optional[List[List[float]]] = None,
        boundary_polygon_3d: Optional[List[List[float]]] = None,
        openings: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Adds or updates a plane node in the architectural graph."""
        self.planes[plane_id] = {
            "structure_id": plane_id,
            "plane_type": plane_type,
            "plane_equation": plane_equation,
            "normal_vector": normal,
            "inlier_points_count": inlier_count,
            "surface_area_m2": surface_area_m2,
            "confidence": confidence,
            "rmse_m": rmse_m,
            "corners_3d": corners_3d or [],
            "boundary_polygon_3d": boundary_polygon_3d or [],
            "openings": openings or []
        }

    def add_intersection_edge(
        self,
        edge_id: str,
        source_plane_id: str,
        target_plane_id: str,
        raw_angle_deg: float,
        adjusted_angle_deg: float,
        angle_confidence: float,
        is_orthogonal_prior_applied: bool,
        intersection_line_start: List[float],
        intersection_line_end: List[float],
        junction_type: str
    ) -> None:
        """Adds an intersection edge between two planes."""
        self.edges[edge_id] = {
            "edge_id": edge_id,
            "source_plane_id": source_plane_id,
            "target_plane_id": target_plane_id,
            "raw_angle_deg": raw_angle_deg,
            "adjusted_angle_deg": adjusted_angle_deg,
            "angle_confidence": angle_confidence,
            "is_orthogonal_prior_applied": is_orthogonal_prior_applied,
            "intersection_line_start": intersection_line_start,
            "intersection_line_end": intersection_line_end,
            "junction_type": junction_type
        }

    def get_plane(self, plane_id: str) -> Optional[Dict[str, Any]]:
        return self.planes.get(plane_id)

    def get_adjacent_planes(self, plane_id: str) -> List[str]:
        neighbors = set()
        for edge in self.edges.values():
            if edge["source_plane_id"] == plane_id:
                neighbors.add(edge["target_plane_id"])
            elif edge["target_plane_id"] == plane_id:
                neighbors.add(edge["source_plane_id"])
        return sorted(list(neighbors))

    def get_room_corners(self) -> List[Dict[str, Any]]:
        """Returns all wall-to-wall vertical intersection corners."""
        return [
            edge for edge in self.edges.values()
            if edge["junction_type"] == "WALL_WALL"
        ]

    def get_non_orthogonal_edges(self) -> List[Dict[str, Any]]:
        """Returns all preserved genuine non-orthogonal edges."""
        return [
            edge for edge in self.edges.values()
            if not edge["is_orthogonal_prior_applied"]
        ]

    def to_contract(self) -> ArchitecturalPlaneGraphSchema:
        """Converts to validated Pydantic Contract 7 model."""
        planes_list = []
        for p in self.planes.values():
            eq = p["plane_equation"]
            plane_obj = StructuralPlane(
                structure_id=p["structure_id"],
                plane_type=p["plane_type"],
                plane_equation=PlaneEquation(a=eq[0], b=eq[1], c=eq[2], d=eq[3]),
                normal_vector=p["normal_vector"],
                inlier_points_count=p["inlier_points_count"],
                surface_area_m2=p["surface_area_m2"],
                confidence=p.get("confidence", 1.0),
                rmse_m=p.get("rmse_m", 0.0),
                corners_3d=p.get("corners_3d", []),
                boundary_polygon_3d=p.get("boundary_polygon_3d", []),
                openings=p.get("openings", [])
            )
            planes_list.append(plane_obj)

        edges_list = []
        for e in self.edges.values():
            edge_obj = PlaneIntersectionEdge(
                edge_id=e["edge_id"],
                source_plane_id=e["source_plane_id"],
                target_plane_id=e["target_plane_id"],
                raw_angle_deg=e["raw_angle_deg"],
                adjusted_angle_deg=e["adjusted_angle_deg"],
                angle_confidence=e["angle_confidence"],
                is_orthogonal_prior_applied=e["is_orthogonal_prior_applied"],
                intersection_line_start=e["intersection_line_start"],
                intersection_line_end=e["intersection_line_end"],
                junction_type=e["junction_type"]
            )
            edges_list.append(edge_obj)

        return ArchitecturalPlaneGraphSchema(
            planes=planes_list,
            intersections=edges_list,
            metadata=self.metadata
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "planes": list(self.planes.values()),
            "intersections": list(self.edges.values()),
            "metadata": self.metadata
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
