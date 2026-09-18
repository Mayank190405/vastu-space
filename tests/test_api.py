from fastapi.testclient import TestClient
import uuid
from api.main import app

client = TestClient(app)

def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "vastu-canonical-control-plane"

def test_create_capture_job():
    payload = {
        "manifest_version": "1.0.0",
        "capture_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "device_info": {
            "manufacturer": "Apple",
            "model": "iPhone 15 Pro",
            "os_name": "iOS",
            "os_version": "17.4",
            "app_version": "1.0.0"
        },
        "camera_calibration": {
            "fx": 1400.0,
            "fy": 1400.0,
            "cx": 960.0,
            "cy": 540.0,
            "image_width": 1920,
            "image_height": 1080
        },
        "files": {
            "video": {
                "filename": "capture.mov",
                "size_bytes": 1048576,
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "duration_sec": 10.0,
                "frame_count": 300,
                "fps": 30.0,
                "codec": "h264"
            },
            "imu": {
                "filename": "imu.csv",
                "size_bytes": 2048,
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "sample_count": 1000,
                "sampling_rate_hz": 100.0
            }
        },
        "metrics": {
            "dropped_frames": 0,
            "imu_packet_drops": 0,
            "average_lux": 150.0
        },
        "created_at": "2026-09-06T10:00:00Z"
    }
    res = client.post("/api/v1/captures/", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "ACCEPTED"
    assert "capture_id" in data

def test_navigation_plan_endpoint():
    payload = {
        "project_id": str(uuid.uuid4()),
        "start_pos": [0.0, 0.0, 0.0],
        "target_pos": [5.0, 0.0, 0.0],
        "require_wheelchair": True,
        "avoid_stairs": True
    }
    res = client.post("/api/v1/navigation/route", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "waypoints" in data
    assert "steps" in data
    assert data["total_distance_meters"] == 5.0

def test_tri_representation_endpoints():
    from core.representations.builder import TriRepresentationBuilder
    from core.schemas.metric_transform import MetricTransformSchema, MetricScaleSource
    
    version_id = "v2.0-tri-test"
    builder = TriRepresentationBuilder()
    vis = builder.build_visual_representation(
        artifact_uri="s3://vastu/visual/model.ply",
        model_format="3DGS_PLY",
        element_count=250000,
        file_size_bytes=1048576
    )
    struc = builder.build_structural_representation(
        plane_graph_uri="s3://vastu/structural/graph.json",
        walls=[{"surface_area_m2": 15.0}],
        floors=[{"surface_area_m2": 45.0}],
        ceilings=[{"surface_area_m2": 45.0}],
        openings=[],
        rooms=[]
    )
    col = builder.build_collision_representation(
        navmesh_graph_uri="s3://vastu/nav/graph.json",
        walkable_floors=[{"surface_area_m2": 45.0}],
        obstacles=[{"obstacle_type": "furniture", "center": [1.0, 1.0, 0.4], "extent": [1.0, 1.0, 0.8]}]
    )
    canonical_transform = MetricTransformSchema(
        scale=1.0,
        translation=[0.0, 0.0, 0.0],
        rotation_matrix=[[1,0,0],[0,1,0],[0,0,1]],
        rotation_quaternion=[0,0,0,1],
        matrix_4x4=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
        scale_source=MetricScaleSource.METRIC_LIDAR_AR,
        scale_confidence=0.99
    )
    bundle = builder.create_bundle(
        model_version_id=version_id,
        metric_transform=canonical_transform,
        visual_model=vis,
        structural_model=struc,
        collision_model=col
    )
    bundle_payload = bundle.model_dump(mode="json")

    # Register bundle
    res = client.post(f"/api/v1/models/{version_id}/bundle", json=bundle_payload)
    assert res.status_code == 201

    # Web viewer fetches ONLY visual model
    vis_res = client.get(f"/api/v1/models/{version_id}/visual")
    assert vis_res.status_code == 200
    vis_data = vis_res.json()
    assert vis_data["model_format"] == "3DGS_PLY"
    assert vis_data["element_count"] == 250000
    assert "walkable_surface_area_m2" not in vis_data
    assert "floor_count" not in vis_data

    # Architectural CAD fetches ONLY structural model
    struct_res = client.get(f"/api/v1/models/{version_id}/structural")
    assert struct_res.status_code == 200
    struct_data = struct_res.json()
    assert struct_data["floor_count"] == 1
    assert struct_data["wall_count"] == 1
    assert "element_count" not in struct_data

    # Navigation client fetches ONLY collision model
    col_res = client.get(f"/api/v1/models/{version_id}/collision")
    assert col_res.status_code == 200
    col_data = col_res.json()
    assert col_data["walkable_surface_area_m2"] == 45.0
    assert len(col_data["obstacles"]) == 1
    assert "element_count" not in col_data

def test_central_quality_evaluate_endpoint():
    project_id = str(uuid.uuid4())
    payload = {
        "capture_data": {"blur_score": 0.90, "exposure_score": 0.88, "coverage_fraction": 0.92, "overlap_ratio": 0.85},
        "pose_data": {"reprojection_error_px": 0.95, "tracking_continuity_ratio": 0.99, "loop_closure_detected": True, "loop_closure_residual_m": 0.02, "mean_pose_confidence": 0.92},
        "depth_data": {"consistency_ratio": 0.90, "density_pts_per_m3": 1200.0, "hole_fraction": 0.03},
        "geometry_data": {"plane_confidence": 0.90, "corner_integrity_score": 0.92, "disconnected_geometry_count": 0, "phantom_geometry_count": 0, "structural_consistency_score": 0.92},
        "semantics_data": {"mean_object_confidence": 0.88, "room_confidence": 0.92, "unclassified_ratio": 0.08},
        "navigation_data": {"floor_continuity_ratio": 0.95, "obstacle_validity_ratio": 0.94, "route_feasibility_ratio": 1.00, "wheelchair_ada_compliant": True}
    }
    res = client.post(f"/api/v1/quality/evaluate?project_id={project_id}&model_version_id=mod_v1", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["verdict"] == "PASS"
    assert data["global_score"] >= 0.80
    assert "explanation" in data
    assert "PASS" in data["explanation"]

def test_immutable_model_versioning_endpoints():
    """Verify API enforcement of immutability, lineage, and 4-way comparison."""
    project_id = str(uuid.uuid4())
    model_id = f"model_{uuid.uuid4().hex[:8]}"
    v1_id = f"mod_{uuid.uuid4().hex[:8]}"

    v1_payload = {
        "model_version_id": v1_id,
        "model_id": model_id,
        "project_id": project_id,
        "version": "1.0.0",
        "semver": "1.0.0",
        "changed_cells": [],
        "pipeline_version": "2.0.0",
        "algorithm_versions": {"sfm": "2.0.0", "depth": "1.2.0"},
        "quality_report": {"overall_score": 0.75, "status": "WARNING"},
        "artifacts": {
            "lod0_glb_s3_key": f"models/{v1_id}/lod0.glb",
            "splat_ply_s3_key": f"models/{v1_id}/splat.ply"
        },
        "creation_timestamp": "2026-09-07T10:00:00Z",
        "created_at": "2026-09-07T10:00:00Z",
        "is_active_production": True,
        "is_immutable": True,
        "change_type": "INITIAL_RECONSTRUCTION",
        "summary_of_changes": "Initial release"
    }

    # 1. Register V1
    res1 = client.post("/api/v1/models/", json=v1_payload)
    assert res1.status_code == 201

    # 2. Overwrite attempt MUST raise 409 Conflict
    res_overwrite = client.post("/api/v1/models/", json=v1_payload)
    assert res_overwrite.status_code == 409

    # 3. Register V2 with parent_version = 1.0.0
    v2_id = f"mod_{uuid.uuid4().hex[:8]}"
    v2_payload = dict(v1_payload)
    v2_payload["model_version_id"] = v2_id
    v2_payload["version"] = "1.1.0"
    v2_payload["semver"] = "1.1.0"
    v2_payload["parent_version"] = "1.0.0"
    v2_payload["parent_version_id"] = v1_id
    v2_payload["changed_cells"] = ["cell_c"]
    v2_payload["quality_report"] = {"overall_score": 0.94, "status": "PASS", "resolved_failures": ["Fixed cell_c"]}
    v2_payload["change_type"] = "INCREMENTAL_RESCAN_PATCH"
    v2_payload["artifacts"] = {
        "lod0_glb_s3_key": f"models/{v2_id}/lod0.glb",
        "splat_ply_s3_key": f"models/{v2_id}/splat.ply"
    }

    res2 = client.post("/api/v1/models/", json=v2_payload)
    assert res2.status_code == 201

    # 4. Verify V1 remains independently viewable
    get_v1 = client.get(f"/api/v1/models/{v1_id}")
    assert get_v1.status_code == 200
    assert get_v1.json()["version"] == "1.0.0"

    get_v2 = client.get(f"/api/v1/models/{v2_id}")
    assert get_v2.status_code == 200
    assert get_v2.json()["version"] == "1.1.0"
    assert get_v2.json()["parent_version"] == "1.0.0"

    # 5. Compare V1 and V2
    comp_res = client.get(f"/api/v1/models/{v1_id}/compare/{v2_id}")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert "cell_c" in comp_data["geometry"]["changed_cells"]
    assert comp_data["confidence"]["global_score_delta"] > 0

    # 6. Check lineage
    lineage_res = client.get(f"/api/v1/models/{model_id}/lineage")
    assert lineage_res.status_code == 200
    assert lineage_res.json()["version_count"] >= 2

def test_poi_endpoints():
    """Verify API endpoints for POI management, spatial query, and raycast placement."""
    project_id = str(uuid.uuid4())
    poi_payload = {
        "name": "Fire Exit Door North",
        "aliases": ["Emergency Door", "North Stairwell"],
        "category": "SAFETY",
        "coordinates": {"x": 4.5, "y": 2.0, "z": 0.0},
        "coordinates_m": {"x": 4.5, "y": 2.0, "z": 0.0},
        "room": "Corridor 1",
        "confidence": 0.98,
        "metadata": {"access": "PUSH_BAR"},
        "model_version": "1.0.0",
        "project_id": project_id
    }

    # 1. Create POI
    create_res = client.post("/api/v1/pois/", json=poi_payload)
    assert create_res.status_code == 201
    poi_id = create_res.json()["poi_id"]

    # 2. Get POI
    get_res = client.get(f"/api/v1/pois/{poi_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Fire Exit Door North"

    # 3. Spatial Query
    query_res = client.post("/api/v1/pois/spatial-query", json={
        "center_xyz": [4.0, 2.0, 0.0],
        "radius_meters": 2.0,
        "model_version": "1.0.0"
    })
    assert query_res.status_code == 200
    assert len(query_res.json()) >= 1

    # 4. Raycast Placement
    raycast_res = client.post("/api/v1/pois/raycast-placement", json={
        "ray_origin": [0.0, 0.0, 0.0],
        "ray_direction": [1.0, 0.0, 0.0],
        "name": "Raycast Wall Pin",
        "mesh_vertices": [[2.0, -1.0, -1.0], [2.0, 1.0, -1.0], [2.0, 0.0, 1.0]],
        "mesh_faces": [[0, 1, 2]],
        "model_version": "1.0.0"
    })
    assert raycast_res.status_code == 201
    placed_poi = raycast_res.json()["poi"]
    assert abs(placed_poi["coordinates"]["x"] - 2.0) < 1e-2




