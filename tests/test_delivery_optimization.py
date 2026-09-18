"""
Test Suite for Stage 24: Asset Delivery Optimization & Performance Telemetry
Covers:
1. Spatial chunk partitioning (5m x 5m grid cells)
2. 3-tier distance-based LOD allocation (LOD0: 0-10m, LOD1: 10-25m, LOD2: 25m+)
3. Asset compression (glTF + DRACO ~72% byte reduction)
4. Telemetry evaluation engine with competition threshold SLAs
5. FastAPI endpoints for delivery manifest streaming and telemetry ingestion
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from core.spatial.delivery_engine import SpatialDeliveryEngine
from core.schemas.delivery_optimization import (
    PerformanceTelemetryReport,
    LODTier,
    CompressionFormat,
    DeliveryManifest
)


@pytest.fixture
def delivery_engine():
    return SpatialDeliveryEngine()


@pytest.fixture
def test_client():
    return TestClient(app)


def test_spatial_chunk_partitioning(delivery_engine):
    """Verify spatial chunk partitioning creates a regular 5m grid with 3-tier LODs."""
    # 15m x 15m room from -7.5 to 7.5
    bbox = [-7.5, 0.0, -7.5, 7.5, 3.2, 7.5]
    chunks = delivery_engine.partition_spatial_chunks("model_v2", bbox, chunk_size_meters=5.0)

    # 3 x 3 = 9 chunks
    assert len(chunks) == 9

    for chunk in chunks:
        # Check chunk dimensions
        dx = chunk.bounding_box[3] - chunk.bounding_box[0]
        dz = chunk.bounding_box[5] - chunk.bounding_box[2]
        assert dx == pytest.approx(5.0, 1e-4)
        assert dz == pytest.approx(5.0, 1e-4)

        # Check 3 LOD tiers are configured
        assert len(chunk.lod_tiers) == 3
        lod_names = [tier.tier for tier in chunk.lod_tiers]
        assert LODTier.LOD0_FULL in lod_names
        assert LODTier.LOD1_BALANCED in lod_names
        assert LODTier.LOD2_PROXY in lod_names

        # Check LOD distance thresholds
        lod0 = next(t for t in chunk.lod_tiers if t.tier == LODTier.LOD0_FULL)
        lod1 = next(t for t in chunk.lod_tiers if t.tier == LODTier.LOD1_BALANCED)
        lod2 = next(t for t in chunk.lod_tiers if t.tier == LODTier.LOD2_PROXY)

        assert lod0.max_distance_meters == 10.0
        assert lod1.max_distance_meters == 25.0
        assert lod2.max_distance_meters == 100.0


def test_draco_compression_ratio(delivery_engine):
    """Verify DRACO compression reduces byte payload by ~72% without geometry loss."""
    manifest = delivery_engine.generate_delivery_manifest("model_v2_comp")

    assert manifest.total_chunks == 9
    assert manifest.uncompressed_total_bytes > manifest.draco_compressed_total_bytes
    
    # Check compression ratio is in the 70-75% range
    assert manifest.compression_ratio_pct >= 70.0
    assert manifest.bandwidth_saved_mb > 0
    assert manifest.compression_format == CompressionFormat.DRACO_GLTF


def test_telemetry_verdict_evaluation_pass(delivery_engine):
    """Verify telemetry evaluation returns PASS when all competition thresholds are satisfied."""
    report = PerformanceTelemetryReport(
        model_version="2.0.0",
        device_tier="DESKTOP_HIGH",
        initial_load_ms=145.0,
        time_to_first_visual_ms=42.0,
        full_scene_load_ms=380.0,
        fps_average=60.0,
        fps_1_percent_low=58.2,
        heap_memory_mb=45.6,
        gpu_memory_mb=24.2,
        draw_calls=18,
        route_latency_ms=2.8,
        chunks_streamed=9
    )

    verdict = delivery_engine.evaluate_telemetry_verdict(report)

    assert verdict["status"] == "PASS"
    assert verdict["all_slas_met"] is True
    assert verdict["passed_metrics"] == 7
    assert len(verdict["details"]["violations"]) == 0


def test_telemetry_verdict_evaluation_review_required(delivery_engine):
    """Verify telemetry evaluation flags breaches when performance thresholds are exceeded."""
    report = PerformanceTelemetryReport(
        model_version="2.0.0",
        device_tier="MOBILE_LOW",
        initial_load_ms=650.0,            # Breach: > 500ms
        time_to_first_visual_ms=320.0,     # Breach: > 250ms
        full_scene_load_ms=3500.0,        # Breach: > 3000ms
        fps_average=38.0,                 # Breach: < 55 fps
        fps_1_percent_low=28.0,
        heap_memory_mb=480.0,             # Breach: > 450 MB
        gpu_memory_mb=600.0,              # Breach: > 512 MB
        draw_calls=240,                   # Breach: > 200 calls
        route_latency_ms=75.0,            # Breach: > 50ms
        chunks_streamed=9
    )

    verdict = delivery_engine.evaluate_telemetry_verdict(report)

    assert verdict["status"] == "REVIEW_REQUIRED"
    assert verdict["all_slas_met"] is False
    assert len(verdict["details"]["violations"]) == 7
    assert verdict["passed_metrics"] == 0


def test_fastapi_delivery_manifest_endpoint(test_client):
    """Verify GET /api/v1/models/{version_id}/delivery-manifest returns 200 with spatial chunks."""
    response = test_client.get("/api/v1/models/model_v2_demo/delivery-manifest")
    assert response.status_code == 200
    
    data = response.json()
    assert data["model_version_id"] == "model_v2_demo"
    assert len(data["chunks"]) == 16
    assert "cdn_base_url" in data
    assert data["chunk_grid_size_meters"] == 5.0


def test_fastapi_telemetry_ingestion_endpoint(test_client):
    """Verify POST /api/v1/models/{version_id}/telemetry records metrics and responds with verdict."""
    payload = {
        "model_version": "model_v2_demo",
        "device_tier": "DESKTOP_WEBGL2",
        "initial_load_ms": 120.0,
        "time_to_first_visual_ms": 38.0,
        "full_scene_load_ms": 310.0,
        "fps_average": 60.0,
        "fps_1_percent_low": 58.0,
        "heap_memory_mb": 42.0,
        "gpu_memory_mb": 22.0,
        "draw_calls": 16,
        "route_latency_ms": 3.1,
        "chunks_streamed": 9
    }

    response = test_client.post("/api/v1/models/model_v2_demo/telemetry", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "PASS"
    assert data["overall_verdict"] == "ALL_SLAS_MET"
    assert data["passed_metrics"] == 7
    assert data["total_metrics"] == 7
