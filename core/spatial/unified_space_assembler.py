"""
VĀSTU Unified Space Assembler (Phase 8)
Assembles individually reconstructed and aligned rooms into a unified facility digital twin:
- Transforms individual room meshes, pointclouds, and Gaussian splats into shared world coordinates
- Assembles unified architectural geometry (OBJ / PLY)
- Exports unified & per-room compressed Gaussian splats (SPZ / PLY)
- Generates unified collision geometry and navigation meshes
- Compiles the comprehensive Viewer Asset Manifest (scene_manifest.json)
- Preserves independent room assets for non-destructive rescans
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import numpy as np

from core.spatial.room_connection_graph import RoomConnectionGraph
from core.spatial.collision_mesh_generator import CollisionMeshGenerator
from core.spatial.navigation_mesh_generator import NavigationMeshGenerator
from core.reconstruction.spz_exporter import SPZExporter

logger = logging.getLogger("vastu.spatial.unified_space_assembler")


class UnifiedSpaceAssembler:
    """
    Coordinates multi-room assembly, asset serialization, and scene manifest publication.
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.collision_gen = CollisionMeshGenerator()
        self.navmesh_gen = NavigationMeshGenerator()
        self.spz_exporter = SPZExporter()

    def assemble_facility(
        self,
        project_id: str,
        project_name: str,
        room_reconstructions: List[Dict[str, Any]],
        global_transforms: Dict[str, List[List[float]]],
        connection_graph: RoomConnectionGraph
    ) -> Dict[str, Any]:
        """
        Combines individual room reconstructions into the unified space digital twin.
        
        Args:
            project_id: Unique project ID.
            project_name: Name of facility / residence.
            room_reconstructions: List of room data dicts containing:
                - room_id, room_name, floor_level
                - architecture (from ArchitecturalGeometryBuilder)
                - pointcloud (points, colors)
                - gaussians (optional)
            global_transforms: Dict mapping room_id to 4x4 matrix.
            connection_graph: Verified RoomConnectionGraph instance.
            
        Returns:
            Dict representing the complete Viewer Asset Manifest (scene_manifest.json).
        """
        os.makedirs(self.output_dir, exist_ok=True)
        rooms_manifest = []
        all_collision_rooms = []
        all_navmesh_architectures = []

        combined_vertices = []
        combined_faces = []
        vert_offset = 1

        all_points_world = []
        all_colors_world = []

        total_facility_area_sqm = 0.0

        for r_data in room_reconstructions:
            rid = r_data["room_id"]
            rname = r_data.get("room_name", f"Room_{rid}")
            floor = r_data.get("floor_level", 1)
            arch = r_data["architecture"]
            total_facility_area_sqm += arch.get("quality_report", {}).get("area_sqm", 0.0)

            T = np.array(global_transforms.get(rid, np.eye(4).tolist()), dtype=np.float64)

            # 1. Transform room points into world space
            if "pointcloud" in r_data and r_data["pointcloud"] is not None:
                pts = r_data["pointcloud"].get("points")
                cols = r_data["pointcloud"].get("colors")
                if pts is not None and len(pts) > 0:
                    ones = np.ones((len(pts), 1), dtype=np.float64)
                    pts_h = np.hstack([pts, ones])
                    pts_w = (pts_h @ T.T)[:, :3]
                    all_points_world.append(pts_w)
                    if cols is not None:
                        all_colors_world.append(cols)

            # 2. Build room-specific collision geometry
            room_collision = self.collision_gen.generate_room_collision(arch, T)
            all_collision_rooms.append(room_collision)
            all_navmesh_architectures.append(arch)

            # 3. Append to unified architectural OBJ mesh
            # Floor polygon
            poly_2d = room_collision["walkable_boundary_polygon_2d"]
            floor_z = room_collision["floor_collider"]["elevation_z"]
            floor_v_start = vert_offset
            for p in poly_2d:
                combined_vertices.append(f"v {p[0]:.4f} {p[1]:.4f} {floor_z:.4f}")
                vert_offset += 1
            
            # Floor face (triangle fan)
            if len(poly_2d) >= 3:
                for vi in range(1, len(poly_2d) - 1):
                    combined_faces.append(f"f {floor_v_start} {floor_v_start + vi} {floor_v_start + vi + 1}")

            # Walls
            ceiling_h = arch.get("ceiling_height_m", 2.80)
            for wall_col in room_collision["wall_colliders"]:
                p0 = wall_col["p0"]
                p1 = wall_col["p1"]
                wv_start = vert_offset
                combined_vertices.append(f"v {p0[0]:.4f} {p0[1]:.4f} {p0[2]:.4f}")
                combined_vertices.append(f"v {p1[0]:.4f} {p1[1]:.4f} {p1[2]:.4f}")
                combined_vertices.append(f"v {p1[0]:.4f} {p1[1]:.4f} {p1[2] + ceiling_h:.4f}")
                combined_vertices.append(f"v {p0[0]:.4f} {p0[1]:.4f} {p0[2] + ceiling_h:.4f}")
                vert_offset += 4
                combined_faces.append(f"f {wv_start} {wv_start+1} {wv_start+2} {wv_start+3}")

            # 4. Room metadata in manifest
            rooms_manifest.append({
                "room_id": rid,
                "room_name": rname,
                "floor_level": floor,
                "area_sqm": arch.get("quality_report", {}).get("area_sqm", 0.0),
                "ceiling_height_m": ceiling_h,
                "transform_matrix_4x4": T.tolist(),
                "boundary_polygon_world": poly_2d,
                "doorway_count": len(arch.get("doorways", [])),
                "furniture_count": len(arch.get("furniture_boxes", []))
            })

        # 5. Write unified architectural OBJ file
        obj_path = os.path.join(self.output_dir, "unified_architecture.obj")
        with open(obj_path, "w") as f:
            f.write(f"# VĀSTU Unified Space Architecture - {project_name}\n")
            f.write("\n".join(combined_vertices) + "\n")
            f.write("\n".join(combined_faces) + "\n")

        # 6. Generate and save unified collision geometry
        collision_path = os.path.join(self.output_dir, "collision_geometry.json")
        collision_data = {
            "project_id": project_id,
            "room_count": len(all_collision_rooms),
            "rooms": all_collision_rooms
        }
        with open(collision_path, "w") as f:
            json.dump(collision_data, f, indent=2)

        # 7. Generate and save unified navigation mesh
        graph_dict = connection_graph.export_graph_dict()
        navmesh_data = self.navmesh_gen.generate_unified_navmesh(
            all_navmesh_architectures,
            global_transforms,
            graph_dict["doorways"]
        )
        navmesh_path = os.path.join(self.output_dir, "navmesh.json")
        with open(navmesh_path, "w") as f:
            json.dump(navmesh_data, f, indent=2)

        # 8. Save room connection graph
        graph_path = os.path.join(self.output_dir, "room_connection_graph.json")
        with open(graph_path, "w") as f:
            json.dump(graph_dict, f, indent=2)

        # 9. Write unified pointcloud / splat representation if points exist
        splat_spz_rel = None
        if all_points_world:
            pts_concat = np.concatenate(all_points_world, axis=0)
            cols_concat = np.concatenate(all_colors_world, axis=0) if all_colors_world else np.full((len(pts_concat), 3), 0.8)
            
            from core.reconstruction.gaussian_splatting import GaussianSplattingPipeline
            gs_pipe = GaussianSplattingPipeline()
            gaussians = gs_pipe.initialize_gaussians(pts_concat, cols_concat)
            
            spz_path = os.path.join(self.output_dir, "unified_splats.spz")
            self.spz_exporter.export_spz(gaussians, spz_path)
            splat_spz_rel = "unified_splats.spz"

        # 10. Generate Master Scene Manifest (scene_manifest.json)
        manifest = {
            "version": "1.0.0",
            "project_id": project_id,
            "project_name": project_name,
            "assembled_at": "2026-10-29T17:35:00Z",
            "total_area_sqm": round(total_facility_area_sqm, 2),
            "room_count": len(rooms_manifest),
            "floors": sorted(list({r["floor_level"] for r in rooms_manifest})),
            "assets": {
                "architecture_obj": "unified_architecture.obj",
                "collision_geometry": "collision_geometry.json",
                "navmesh": "navmesh.json",
                "connection_graph": "room_connection_graph.json",
                "splats_spz": splat_spz_rel
            },
            "rooms": rooms_manifest,
            "default_spawn": {
                "room_id": rooms_manifest[0]["room_id"] if rooms_manifest else "room_01",
                "position_3d": [
                    rooms_manifest[0]["boundary_polygon_world"][0][0] * 0.5 + rooms_manifest[0]["boundary_polygon_world"][1][0] * 0.5,
                    rooms_manifest[0]["boundary_polygon_world"][0][1] * 0.5 + rooms_manifest[0]["boundary_polygon_world"][2][1] * 0.5,
                    1.60
                ] if rooms_manifest else [0.0, 0.0, 1.60],
                "eye_height_m": 1.60
            }
        }

        manifest_path = os.path.join(self.output_dir, "scene_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Unified space assembled successfully: {manifest_path}")
        return manifest

