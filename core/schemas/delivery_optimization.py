"""
VĀSTU Delivery Optimization & Performance Telemetry Schemas
Defines formal Pydantic v2 contracts for spatial chunking, multi-resolution LODs,
progressive asset streaming, and 7-metric runtime performance telemetry.
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Optional, Any
from enum import Enum
import uuid
import datetime


class LODTier(str, Enum):
    LOD0_FULL = "LOD0_FULL"         # High fidelity (0 - 10m): 100% triangles, full PBR materials
    LOD1_BALANCED = "LOD1_BALANCED" # Medium fidelity (10 - 25m): ~40% triangles, simplified textures
    LOD2_PROXY = "LOD2_PROXY"       # Low fidelity (25m+): ~15% triangles, bounding geometry


class CompressionFormat(str, Enum):
    DRACO_GLTF = "DRACO_GLTF"
    QUANTIZED_BIN = "QUANTIZED_BIN"
    MESHOPT_EXT = "MESHOPT_EXT"
    UNCOMPRESSED_GLB = "UNCOMPRESSED_GLB"


class SpatialChunkLOD(BaseModel):
    lod_tier: LODTier
    triangle_count: int
    uncompressed_bytes: int
    compressed_bytes: int
    compression_format: CompressionFormat = CompressionFormat.DRACO_GLTF
    max_distance_meters: float
    cdn_url: str

    @property
    def tier(self) -> LODTier:
        return self.lod_tier


class SpatialChunk(BaseModel):
    chunk_id: str
    cell_id: str
    center: List[float] = Field(min_length=3, max_length=3)
    bounding_box_min: List[float] = Field(min_length=3, max_length=3)
    bounding_box_max: List[float] = Field(min_length=3, max_length=3)
    lod_levels: List[SpatialChunkLOD]
    is_essential: bool = False  # e.g., structural floor & core perimeter loaded in phase 1

    @property
    def bounding_box(self) -> List[float]:
        return self.bounding_box_min + self.bounding_box_max

    @property
    def lod_tiers(self) -> List[SpatialChunkLOD]:
        return self.lod_levels


class DeliveryManifest(BaseModel):
    manifest_id: str = Field(default_factory=lambda: f"dlv_{uuid.uuid4().hex[:8]}")
    model_version_id: str
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    cdn_base_url: str = "https://cdn.vastuspace.io/models"
    total_uncompressed_bytes: int
    total_compressed_bytes: int
    compression_ratio: float
    chunk_grid_size_meters: float = 5.0
    chunks: List[SpatialChunk]
    essential_chunk_ids: List[str]

    @property
    def model_version(self) -> str:
        return self.model_version_id

    @property
    def total_chunks(self) -> int:
        return len(self.chunks)

    @property
    def uncompressed_total_bytes(self) -> int:
        return self.total_uncompressed_bytes

    @property
    def draco_compressed_total_bytes(self) -> int:
        return self.total_compressed_bytes

    @property
    def compression_ratio_pct(self) -> float:
        if self.total_uncompressed_bytes <= 0:
            return 0.0
        return round((1.0 - (self.total_compressed_bytes / self.total_uncompressed_bytes)) * 100, 1)

    @property
    def bandwidth_saved_mb(self) -> float:
        return round((self.total_uncompressed_bytes - self.total_compressed_bytes) / (1024 * 1024), 2)

    @property
    def compression_format(self) -> CompressionFormat:
        return CompressionFormat.DRACO_GLTF


class PerformanceTelemetryReport(BaseModel):
    """
    Mandated 7-metric telemetry report evaluating competition & demo performance:
    1. initial_load_ms
    2. time_to_first_visual_ms (TTFV)
    3. full_scene_load_ms
    4. average_fps
    5. memory_heap_mb (CPU)
    6. gpu_memory_mb & draw_calls (GPU)
    7. route_latency_ms
    """
    report_id: str = Field(default_factory=lambda: f"tel_{uuid.uuid4().hex[:8]}")
    client_timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    model_version_id: str = "1.0.0"
    device_tier: str = "DESKTOP_WEBGL2"
    user_agent: str = "Mozilla/5.0 Three.js WebGL"
    
    # 1. Initial network handshake / script load
    initial_load_ms: float = 120.0
    # 2. Time until first visual frame is painted (structural wireframe & ground)
    time_to_first_visual_ms: float = 40.0
    # 3. Time until all spatial chunks are fully streamed and resolved
    full_scene_load_ms: float = 350.0
    # 4. Runtime frame rate & smoothness
    average_fps: float = 60.0
    min_fps_1_percent_low: float = 54.0
    # 5. CPU heap memory footprint
    memory_heap_mb: float = 45.0
    # 6. GPU video memory & rendering load
    gpu_memory_mb: float = 24.0
    gpu_draw_calls: int = 18
    gpu_triangles_rendered: int = 4200
    # 7. Indoor A* route calculation latency
    route_latency_ms: float = 2.5
    chunks_streamed: int = 9

    # Qualitative verdict
    viewer_interactive_during_load: bool = True
    visible_degradation_detected: bool = False
    tradeoff_notes: str = "Multi-resolution geometric decimation applied smoothly based on distance thresholds (d > 10m)."

    @model_validator(mode='before')
    @classmethod
    def map_incoming_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            mapped = dict(data)
            if "model_version" in mapped and "model_version_id" not in mapped:
                mapped["model_version_id"] = mapped["model_version"]
            if "fps_average" in mapped and "average_fps" not in mapped:
                mapped["average_fps"] = mapped["fps_average"]
            if "fps" in mapped and "average_fps" not in mapped:
                mapped["average_fps"] = mapped["fps"]
            if "heap_memory_mb" in mapped and "memory_heap_mb" not in mapped:
                mapped["memory_heap_mb"] = mapped["heap_memory_mb"]
            if "draw_calls" in mapped and "gpu_draw_calls" not in mapped:
                mapped["gpu_draw_calls"] = mapped["draw_calls"]
            if "triangles" in mapped and "gpu_triangles_rendered" not in mapped:
                mapped["gpu_triangles_rendered"] = mapped["triangles"]
            if "fps_1_percent_low" in mapped and "min_fps_1_percent_low" not in mapped:
                mapped["min_fps_1_percent_low"] = mapped["fps_1_percent_low"]
            return mapped
        return data
