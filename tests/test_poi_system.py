"""
Unit & Integration Tests for POI System (Stage 19)
Validates:
1. POI required schema fields (id, name, aliases, category, coordinates, room, geometry, confidence, metadata, model_version).
2. POI CRUD lifecycle (create, edit, delete, get).
3. Textual & semantic search (name, aliases, tags, room, category, model_version).
4. 3D spatial query (spherical radius and k-nearest neighbors).
5. Raycast placement (3D ray-triangle intersection, surface hit coordinate, surface normal, and confidence).
6. Cross-version spatial validity preservation & migration (drift checking and surface snapping).
7. Acceptance criterion: Visual viewer creation & persistence as a version-aware spatial entity.
"""

import uuid
import pytest
import numpy as np

from core.schemas.poi import PointOfInterest, POICoordinates, POICameraViewpoint
from core.poi.service import POIService

def test_poi_required_fields():
    """Verify each POI contains all 10 required fields."""
    poi = PointOfInterest(
        id=uuid.uuid4(),
        name="Main Boardroom TV",
        aliases=["Display 1", "Zoom Screen"],
        category="AV_EQUIPMENT",
        coordinates=POICoordinates(x=2.5, y=3.0, z=1.2),
        room="Boardroom A",
        geometry={"type": "SURFACE_ANCHOR", "surface_normal": [0, 1, 0]},
        confidence=0.98,
        metadata={"vendor": "Samsung", "screen_size": "75inch"},
        model_version="1.0.0"
    )

    assert poi.id is not None
    assert poi.name == "Main Boardroom TV"
    assert "Display 1" in poi.aliases
    assert poi.category == "AV_EQUIPMENT"
    assert poi.coordinates.x == 2.5
    assert poi.room == "Boardroom A"
    assert poi.geometry["type"] == "SURFACE_ANCHOR"
    assert poi.confidence == 0.98
    assert poi.metadata["vendor"] == "Samsung"
    assert poi.model_version == "1.0.0"

def test_poi_crud_lifecycle():
    """Verify create, edit, delete, and get operations."""
    service = POIService()
    poi = PointOfInterest(
        name="Fire Extinguisher FE-02",
        category="SAFETY",
        coordinates=POICoordinates(x=5.0, y=1.0, z=0.8),
        room="Corridor East",
        model_version="1.0.0"
    )

    # 1. Create
    created = service.create_poi(poi)
    pid = str(created.id)
    assert service.get_poi(pid) is not None

    # 2. Get
    retrieved = service.get_poi(pid)
    assert retrieved.name == "Fire Extinguisher FE-02"

    # 3. Edit
    updated = service.edit_poi(pid, {
        "name": "Fire Extinguisher FE-02 (Inspected)",
        "confidence": 0.99,
        "metadata": {"last_inspection": "2026-09-01"}
    })
    assert updated.name == "Fire Extinguisher FE-02 (Inspected)"
    assert updated.confidence == 0.99
    assert updated.metadata["last_inspection"] == "2026-09-01"

    # 4. Delete
    deleted = service.delete_poi(pid)
    assert deleted is True
    assert service.get_poi(pid) is None

def test_poi_search():
    """Verify search across name, aliases, room, category, and model_version."""
    service = POIService()
    service.create_poi({
        "name": "Conference Room Delta",
        "aliases": ["Delta Rm", "Meeting 4"],
        "category": "ROOM",
        "room": "Floor 2",
        "coordinates": [1.0, 2.0, 0.0],
        "model_version": "1.0.0"
    })
    service.create_poi({
        "name": "First Aid Kit",
        "aliases": ["Medical Cabinet", "Emergency Supplies"],
        "category": "SAFETY",
        "room": "Kitchen",
        "coordinates": [3.0, 4.0, 1.0],
        "model_version": "1.0.0"
    })
    service.create_poi({
        "name": "Smart Thermostat V2",
        "aliases": ["HVAC"],
        "category": "IOT",
        "room": "Floor 2",
        "coordinates": [1.5, 2.2, 1.4],
        "model_version": "2.0.0"
    })

    # Search by alias
    res_alias = service.search_pois("Medical")
    assert len(res_alias) == 1
    assert res_alias[0].name == "First Aid Kit"

    # Search by category and room
    res_cat = service.search_pois("", category="ROOM", room="Floor 2")
    assert len(res_cat) == 1
    assert res_cat[0].name == "Conference Room Delta"

    # Search by model_version
    res_v2 = service.search_pois("", model_version="2.0.0")
    assert len(res_v2) == 1
    assert res_v2[0].name == "Smart Thermostat V2"

def test_poi_spatial_query():
    """Verify 3D spherical radius query and k-nearest neighbors in metric coordinates."""
    service = POIService()
    p1 = service.create_poi({
        "name": "Origin Anchor",
        "coordinates": [0.0, 0.0, 0.0],
        "model_version": "1.0.0"
    })
    p2 = service.create_poi({
        "name": "Close Anchor",
        "coordinates": [1.0, 0.0, 0.0],
        "model_version": "1.0.0"
    })
    p3 = service.create_poi({
        "name": "Far Anchor",
        "coordinates": [10.0, 0.0, 0.0],
        "model_version": "1.0.0"
    })

    # Radius query within 2.0m of [0, 0, 0]
    radius_results = service.spatial_query(center_xyz=[0.0, 0.0, 0.0], radius_m=2.0)
    assert len(radius_results) == 2
    names = [poi.name for poi, dist in radius_results]
    assert "Origin Anchor" in names
    assert "Close Anchor" in names
    assert "Far Anchor" not in names

    # Nearest neighbor query (k=1)
    knn_results = service.spatial_query(center_xyz=[0.9, 0.0, 0.0], radius_m=5.0, k_nearest=1)
    assert len(knn_results) == 1
    assert knn_results[0][0].name == "Close Anchor"

def test_raycast_placement():
    """Verify 3D ray-triangle intersection against surface mesh for visual POI placement."""
    service = POIService()

    # Define a simple vertical wall triangle in the YZ plane at X = 3.0
    vertices = np.array([
        [3.0, -1.0, -1.0],
        [3.0,  1.0, -1.0],
        [3.0,  0.0,  1.0]
    ], dtype=np.float64)
    faces = np.array([[0, 1, 2]], dtype=np.int32)

    # Cast ray along +X axis towards wall
    ray_origin = [0.0, 0.0, 0.0]
    ray_dir = [1.0, 0.0, 0.0]

    placed = service.raycast_placement(
        ray_origin=ray_origin,
        ray_direction=ray_dir,
        mesh_vertices=vertices,
        mesh_faces=faces,
        name="Wall Art Canvas",
        category="DECOR",
        room="Lobby",
        model_version="1.0.0"
    )

    assert placed.name == "Wall Art Canvas"
    # Hit should be at x = 3.0, y = 0.0, z = 0.0
    assert abs(placed.coordinates.x - 3.0) < 1e-3
    assert abs(placed.coordinates.y - 0.0) < 1e-3
    assert abs(placed.coordinates.z - 0.0) < 1e-3
    assert placed.confidence >= 0.90
    assert placed.geometry["type"] == "SURFACE_ANCHOR"
    assert placed.camera_viewpoint is not None

def test_poi_cross_version_spatial_migration():
    """Verify POIs remain spatially valid when model versions change."""
    service = POIService()
    service.create_poi({
        "name": "Reception Desk Bell",
        "coordinates": [2.0, 2.0, 1.0],
        "category": "FURNITURE",
        "model_version": "1.0.0"
    })

    # Updated mesh in V2 with slight 2cm surface refinement
    updated_mesh_vertices = np.array([
        [2.0, 2.0, 1.02],
        [5.0, 5.0, 1.0]
    ], dtype=np.float64)

    migrated = service.migrate_pois_across_versions(
        source_version="1.0.0",
        target_version="1.1.0",
        updated_mesh_vertices=updated_mesh_vertices,
        max_drift_threshold_m=0.10
    )

    assert len(migrated) == 1
    m_poi = migrated[0]
    assert m_poi.model_version == "1.1.0"
    # Verify coordinates gently snapped to refined surface mesh
    assert abs(m_poi.coordinates.z - 1.02) < 1e-3
    assert m_poi.geometry["type"] == "MIGRATED_ANCHOR"
    assert m_poi.geometry["source_version"] == "1.0.0"

def test_acceptance_criterion_visual_creation_and_persistence():
    """Acceptance criterion: A POI can be created visually in the viewer and persisted as a version-aware spatial entity."""
    service = POIService()

    # Visual click on viewer surface mesh
    mesh_v = np.array([[0, 0, 0], [4, 0, 0], [0, 4, 0]], dtype=np.float64)
    mesh_f = np.array([[0, 1, 2]], dtype=np.int32)

    # User clicks ray through canvas
    created_poi = service.raycast_placement(
        ray_origin=[1.0, 1.0, 5.0],
        ray_direction=[0.0, 0.0, -1.0],
        mesh_vertices=mesh_v,
        mesh_faces=mesh_f,
        name="Interactive Floor Tag",
        category="WAYFINDING",
        model_version="1.0.0"
    )

    assert created_poi.id is not None
    assert created_poi.model_version == "1.0.0"
    # Floor hit at z = 0
    assert abs(created_poi.coordinates.z - 0.0) < 1e-3

    # Persisted in service and queryable by version
    loaded = service.get_poi(created_poi.id)
    assert loaded is not None
    assert loaded.name == "Interactive Floor Tag"
    v1_pois = service.list_pois(model_version="1.0.0")
    assert any(p.id == created_poi.id for p in v1_pois)
