"""
Unit & Integration Tests for Hybrid Spatial Search (Stage 20)
Validates:
1. Exact search ("Meeting Room 4") with exact name token matching.
2. Fuzzy search ("meeting rooms", typo "meting room 4") with plural and typo tolerance.
3. Semantic search ("3-seater sofas") mapping to couches/seating via architectural taxonomy.
4. Spatial filtering ("chairs near reception") computing metric distance to anchor and ranking nearest objects.
5. Room containment filtering ("in Boardroom A").
6. Acceptance Criterion: Both exact names and natural-language object searches resolve to spatially meaningful results (POI, confidence, 3D location [x, y, z], room, preview metadata).
7. FastAPI HTTP Endpoints: POST and GET /api/v1/search/spatial.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from core.schemas.poi import PointOfInterest, POICoordinates
from core.schemas.search import SpatialSearchQuery, SpatialSearchResponse
from core.poi.service import POIService
from core.search.hybrid import HybridSpatialSearchEngine
from api.main import app


@pytest.fixture
def populated_search_engine():
    """Creates a dedicated POIService and HybridSpatialSearchEngine with standard test assets."""
    service = POIService()

    # 1. Exact Meeting Room
    service.create_poi(PointOfInterest(
        id=uuid.uuid4(),
        name="Meeting Room 4",
        aliases=["MR-04", "Hudson Conference"],
        category="ROOM",
        coordinates=POICoordinates(x=12.4, y=8.5, z=0.0),
        room="Meeting Room 4",
        metadata={"capacity": 8, "has_av": True},
        confidence=0.98,
        model_version="1.0.0"
    ))

    # 2. Another Meeting Room
    service.create_poi(PointOfInterest(
        id=uuid.uuid4(),
        name="Meeting Room 2",
        aliases=["MR-02", "East Huddle"],
        category="ROOM",
        coordinates=POICoordinates(x=6.0, y=8.5, z=0.0),
        room="Meeting Room 2",
        metadata={"capacity": 4},
        confidence=0.95,
        model_version="1.0.0"
    ))

    # 3. Reception Anchor
    service.create_poi(PointOfInterest(
        id=uuid.uuid4(),
        name="Main Reception Desk",
        aliases=["Front Desk", "Welcome Area", "Reception"],
        category="ZONE",
        coordinates=POICoordinates(x=1.0, y=2.0, z=0.0),
        room="Lobby",
        metadata={"floor": 1},
        confidence=0.99,
        model_version="1.0.0"
    ))

    # 4. Chair near Reception (1.5m away)
    service.create_poi(PointOfInterest(
        id=uuid.uuid4(),
        name="Reception Guest Armchair",
        aliases=["Lobby Chair 1"],
        category="FURNITURE",
        coordinates=POICoordinates(x=2.2, y=2.8, z=0.0),
        room="Lobby",
        metadata={"type": "armchair", "material": "leather"},
        confidence=0.92,
        model_version="1.0.0"
    ))

    # 5. Chair distant from Reception (25m away in Cafeteria)
    service.create_poi(PointOfInterest(
        id=uuid.uuid4(),
        name="Cafeteria High Stool",
        aliases=["Bar Stool 3"],
        category="FURNITURE",
        coordinates=POICoordinates(x=25.0, y=18.0, z=0.0),
        room="Cafeteria",
        metadata={"type": "stool", "material": "wood"},
        confidence=0.90,
        model_version="1.0.0"
    ))

    # 6. 3-Seater Sofa / Couch (Semantic match)
    service.create_poi(PointOfInterest(
        id=uuid.uuid4(),
        name="Contemporary Velvet Couch",
        aliases=["Lounge Settee", "3-Seater Velvet Sofa"],
        category="FURNITURE",
        coordinates=POICoordinates(x=4.5, y=5.0, z=0.0),
        room="Executive Lounge",
        metadata={"attributes": ["3-seater", "cushioned", "velvet"], "seating_capacity": 3},
        confidence=0.96,
        model_version="1.0.0"
    ))

    # 7. AV Screen in Boardroom
    service.create_poi(PointOfInterest(
        id=uuid.uuid4(),
        name="Samsung 85-inch 4K Display",
        aliases=["Boardroom TV", "Presentation Screen"],
        category="AV_EQUIPMENT",
        coordinates=POICoordinates(x=12.0, y=14.0, z=1.5),
        room="Boardroom A",
        metadata={"resolution": "4K", "type": "screen"},
        confidence=0.97,
        model_version="1.0.0"
    ))

    return HybridSpatialSearchEngine(poi_service=service)


def test_exact_search(populated_search_engine):
    """Verify exact match retrieves 'Meeting Room 4' with highest score and EXACT match type."""
    query = SpatialSearchQuery(query="Meeting Room 4", limit=5)
    response = populated_search_engine.search(query)

    assert response.total_results > 0
    top_result = response.results[0]
    assert top_result.poi.name == "Meeting Room 4"
    assert top_result.preview_metadata.match_type == "EXACT"
    assert top_result.preview_metadata.lexical_score == 1.0
    assert top_result.location == [12.4, 8.5, 0.0]
    assert top_result.room == "Meeting Room 4"
    assert top_result.confidence >= 0.85


def test_fuzzy_search(populated_search_engine):
    """Verify plural forms and typographical errors resolve to candidate rooms."""
    # Typo tolerance
    query_typo = SpatialSearchQuery(query="meting room 4", limit=5)
    res_typo = populated_search_engine.search(query_typo)
    assert res_typo.total_results > 0
    assert res_typo.results[0].poi.name == "Meeting Room 4"

    # Plural form
    query_plural = SpatialSearchQuery(query="meeting rooms", limit=5)
    res_plural = populated_search_engine.search(query_plural)
    assert res_plural.total_results >= 2
    names = [r.poi.name for r in res_plural.results]
    assert "Meeting Room 4" in names
    assert "Meeting Room 2" in names


def test_semantic_search(populated_search_engine):
    """Verify natural-language concept '3-seater sofas' resolves to 'Contemporary Velvet Couch'."""
    query = SpatialSearchQuery(query="3-seater sofas", limit=5)
    response = populated_search_engine.search(query)

    assert response.total_results > 0
    top_result = response.results[0]
    assert "Couch" in top_result.poi.name or "Sofa" in top_result.poi.name
    assert top_result.preview_metadata.semantic_score > 0.6
    assert top_result.preview_metadata.match_type in ["SEMANTIC", "EXACT", "FUZZY"]
    assert top_result.room == "Executive Lounge"
    assert top_result.location == [4.5, 5.0, 0.0]


def test_spatial_relational_filtering(populated_search_engine):
    """Verify 'chairs near reception' parses anchor, calculates 3D distance, and ranks nearby chair first."""
    query = SpatialSearchQuery(query="chairs near reception", limit=5)
    response = populated_search_engine.search(query)

    assert response.parsed_target == "chairs"
    assert response.parsed_anchor == "reception"
    assert response.total_results > 0

    top_result = response.results[0]
    assert top_result.poi.name == "Reception Guest Armchair"
    assert top_result.preview_metadata.match_type == "SPATIAL_PROXIMITY"
    assert top_result.preview_metadata.anchor_name == "Main Reception Desk"
    assert top_result.preview_metadata.distance_to_anchor_m is not None
    # Distance between [1.0, 2.0, 0.0] and [2.2, 2.8, 0.0] = sqrt(1.2^2 + 0.8^2) = ~1.44m
    assert 1.0 <= top_result.preview_metadata.distance_to_anchor_m <= 2.0

    # Ensure distant cafeteria stool ranks significantly lower or is not top
    if len(response.results) > 1:
        assert response.results[0].preview_metadata.composite_rank_score > response.results[1].preview_metadata.composite_rank_score


def test_room_filtering(populated_search_engine):
    """Verify room filter isolates items to the specified room."""
    query = SpatialSearchQuery(query="screen", room_filter="Boardroom A", limit=5)
    response = populated_search_engine.search(query)

    assert response.total_results > 0
    assert response.results[0].poi.name == "Samsung 85-inch 4K Display"
    assert response.results[0].room == "Boardroom A"


def test_acceptance_criterion_spatial_resolution(populated_search_engine):
    """
    ACCEPTANCE CRITERION TEST:
    Both exact names and natural-language object searches resolve to spatially meaningful results.
    """
    test_cases = [
        ("Meeting Room 4", [12.4, 8.5, 0.0], "Meeting Room 4"),
        ("3-seater sofas", [4.5, 5.0, 0.0], "Executive Lounge"),
        ("chairs near reception", [2.2, 2.8, 0.0], "Lobby"),
    ]

    for q_text, expected_coords, expected_room in test_cases:
        res = populated_search_engine.search(SpatialSearchQuery(query=q_text))
        assert res.total_results > 0, f"Query '{q_text}' returned 0 results"
        top = res.results[0]

        # 1. POI Entity
        assert top.poi is not None
        assert top.poi.id is not None

        # 2. Confidence Score
        assert 0.0 <= top.confidence <= 1.0

        # 3. 3D Coordinates
        assert len(top.location) == 3
        assert pytest.approx(top.location[0], 0.1) == expected_coords[0]
        assert pytest.approx(top.location[1], 0.1) == expected_coords[1]
        assert pytest.approx(top.location[2], 0.1) == expected_coords[2]

        # 4. Room Name
        assert top.room == expected_room

        # 5. Preview Metadata
        assert top.preview_metadata is not None
        assert top.preview_metadata.match_type in ["EXACT", "FUZZY", "SEMANTIC", "SPATIAL_PROXIMITY"]
        assert top.preview_metadata.match_explanation != ""


def test_fastapi_search_endpoints():
    """Verify HTTP POST and GET /api/v1/search/spatial endpoints."""
    client = TestClient(app)

    # Pre-seed a POI via POI API
    poi_payload = {
        "name": "Panoramic Terrace Bench",
        "aliases": ["Skyline Bench"],
        "category": "FURNITURE",
        "coordinates": {"x": 30.0, "y": 10.0, "z": 15.0},
        "room": "Sky Terrace",
        "confidence": 0.95,
        "model_version": "1.0.0",
        "metadata": {"outdoor": True}
    }
    create_res = client.post("/api/v1/pois", json=poi_payload)
    assert create_res.status_code == 201

    # Test POST /api/v1/search/spatial
    post_res = client.post("/api/v1/search/spatial", json={
        "query": "Panoramic Terrace Bench",
        "limit": 5
    })
    assert post_res.status_code == 200
    post_data = post_res.json()
    assert post_data["total_results"] > 0
    assert post_data["results"][0]["poi"]["name"] == "Panoramic Terrace Bench"
    assert post_data["results"][0]["location"] == [30.0, 10.0, 15.0]

    # Test GET /api/v1/search/spatial
    get_res = client.get("/api/v1/search/spatial?q=Skyline+Bench&limit=5")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["total_results"] > 0
    assert get_data["results"][0]["poi"]["name"] == "Panoramic Terrace Bench"
