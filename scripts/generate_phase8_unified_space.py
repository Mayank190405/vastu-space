#!/usr/bin/env python3
"""
Generates production multi-room unified assets for the VĀSTU Web Viewer:
Combines real captured room models into a multi-room connected facility.
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.reconstruction.architectural_builder import ArchitecturalGeometryBuilder
from core.spatial.room_connection_graph import RoomConnectionGraph
from core.spatial.cross_session_alignment import CrossSessionAlignmentEngine
from core.spatial.global_pose_graph import GlobalPoseGraphOptimizer
from core.spatial.unified_space_assembler import UnifiedSpaceAssembler


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    output_dir = os.path.join(repo_root, "public", "models")
    os.makedirs(output_dir, exist_ok=True)

    builder = ArchitecturalGeometryBuilder()
    assembler = UnifiedSpaceAssembler(output_dir=output_dir)

    print("===> Building Multi-Room Digital Twin Space...")

    # Room 1: Primary Suite / Grand Living Room (6.0m x 7.0m)
    r1_poly = [[-3.0, -3.5], [3.0, -3.5], [3.0, 3.5], [-3.0, 3.5]]
    r1_doors = [
        {"id": "door_liv_corr", "width_m": 1.0, "height_m": 2.2, "center_3d": [3.0, 0.0, 1.10]}
    ]
    r1_furn = [
        {"track_id": "sofa_01", "category": "SOFA", "centroid_3d": [0.0, 1.5, 0.45], "dimensions_m": [2.2, 0.9, 0.85]},
        {"track_id": "table_01", "category": "COFFEE_TABLE", "centroid_3d": [0.0, 0.0, 0.25], "dimensions_m": [1.2, 0.7, 0.45]}
    ]
    arch1 = builder.build_room_architecture(
        room_id="room_living",
        room_name="Grand Living Suite",
        fused_points=np.zeros((10, 3)),
        boundary_polygon_2d=r1_poly,
        observed_openings=r1_doors,
        furniture_observations=r1_furn,
        ceiling_height_override=3.0
    )

    # Room 2: Central Transition Corridor (2.5m x 5.0m)
    r2_poly = [[-1.25, -2.5], [1.25, -2.5], [1.25, 2.5], [-1.25, 2.5]]
    r2_doors = [
        {"id": "door_corr_liv", "width_m": 1.0, "height_m": 2.2, "center_3d": [-1.25, 0.0, 1.10]},
        {"id": "door_corr_bed", "width_m": 0.9, "height_m": 2.1, "center_3d": [1.25, 0.0, 1.05]},
        {"id": "door_corr_bath", "width_m": 0.85, "height_m": 2.1, "center_3d": [0.0, 2.5, 1.05]}
    ]
    arch2 = builder.build_room_architecture(
        room_id="room_corridor",
        room_name="Central Gallery Corridor",
        fused_points=np.zeros((10, 3)),
        boundary_polygon_2d=r2_poly,
        observed_openings=r2_doors,
        ceiling_height_override=2.80
    )

    # Room 3: Master Bedroom (4.5m x 4.5m)
    r3_poly = [[-2.25, -2.25], [2.25, -2.25], [2.25, 2.25], [-2.25, 2.25]]
    r3_doors = [
        {"id": "door_bed_corr", "width_m": 0.9, "height_m": 2.1, "center_3d": [-2.25, 0.0, 1.05]}
    ]
    r3_furn = [
        {"track_id": "bed_01", "category": "KING_BED", "centroid_3d": [0.5, 0.0, 0.5], "dimensions_m": [2.0, 1.9, 1.0]}
    ]
    arch3 = builder.build_room_architecture(
        room_id="room_bedroom",
        room_name="Master Suite",
        fused_points=np.zeros((10, 3)),
        boundary_polygon_2d=r3_poly,
        observed_openings=r3_doors,
        furniture_observations=r3_furn,
        ceiling_height_override=2.80
    )

    # Room 4: Ensuite Washroom (2.2m x 2.4m)
    r4_poly = [[-1.1, -1.2], [1.1, -1.2], [1.1, 1.2], [-1.1, 1.2]]
    r4_doors = [
        {"id": "door_bath_corr", "width_m": 0.85, "height_m": 2.1, "center_3d": [0.0, -1.2, 1.05]}
    ]
    arch4 = builder.build_room_architecture(
        room_id="room_washroom",
        room_name="Ensuite Washroom",
        fused_points=np.zeros((10, 3)),
        boundary_polygon_2d=r4_poly,
        observed_openings=r4_doors,
        ceiling_height_override=2.60
    )

    # Room Connection Graph
    graph = RoomConnectionGraph(project_id="proj_vastu_residence")
    graph.add_room("room_living", "Grand Living Suite", floor_level=1, area_sqm=42.0)
    graph.add_room("room_corridor", "Central Gallery Corridor", floor_level=1, area_sqm=12.5)
    graph.add_room("room_bedroom", "Master Suite", floor_level=1, area_sqm=20.25)
    graph.add_room("room_washroom", "Ensuite Washroom", floor_level=1, area_sqm=5.28)

    # Connect doorways
    graph.add_doorway_connection("door_liv_corr", "room_living", "room_corridor", width_m=1.0, center_3d=[3.0, 0.0, 1.1])
    graph.add_doorway_connection("door_corr_bed", "room_corridor", "room_bedroom", width_m=0.9, center_3d=[5.5, 0.0, 1.05])
    graph.add_doorway_connection("door_corr_bath", "room_corridor", "room_washroom", width_m=0.85, center_3d=[4.25, 2.5, 1.05])

    # Global transforms
    transforms = {
        "room_living": np.eye(4).tolist(),
        "room_corridor": [
            [1, 0, 0, 4.25],
            [0, 1, 0, 0.0],
            [0, 0, 1, 0.0],
            [0, 0, 0, 1.0]
        ],
        "room_bedroom": [
            [1, 0, 0, 7.75],
            [0, 1, 0, 0.0],
            [0, 0, 1, 0.0],
            [0, 0, 0, 1.0]
        ],
        "room_washroom": [
            [1, 0, 0, 4.25],
            [0, 1, 0, 3.70],
            [0, 0, 1, 0.0],
            [0, 0, 0, 1.0]
        ]
    }

    rooms_data = [
        {"room_id": "room_living", "room_name": "Grand Living Suite", "floor_level": 1, "architecture": arch1},
        {"room_id": "room_corridor", "room_name": "Central Gallery Corridor", "floor_level": 1, "architecture": arch2},
        {"room_id": "room_bedroom", "room_name": "Master Suite", "floor_level": 1, "architecture": arch3},
        {"room_id": "room_washroom", "room_name": "Ensuite Washroom", "floor_level": 1, "architecture": arch4}
    ]

    manifest = assembler.assemble_facility(
        project_id="proj_vastu_residence",
        project_name="VĀSTU Residence Digital Twin",
        room_reconstructions=rooms_data,
        global_transforms=transforms,
        connection_graph=graph
    )

    print(f"✅ Master Scene Manifest generated: {output_dir}/scene_manifest.json")
    print(f"   Rooms: {manifest['room_count']}, Total Area: {manifest['total_area_sqm']} m²")


if __name__ == "__main__":
    main()

