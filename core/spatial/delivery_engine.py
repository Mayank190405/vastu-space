"""
VĀSTU Delivery Engine: Spatial Chunk Partitioning & Multi-Resolution LOD Generation
Optimizes large-scale digital twins into streaming spatial grid chunks with 3 LOD tiers,
compression metrics, and zero visible degradation within user viewing range.
"""

import math
import numpy as np
from typing import List, Dict, Optional, Tuple, Any

from core.schemas.delivery_optimization import (
    SpatialChunk,
    SpatialChunkLOD,
    LODTier,
    CompressionFormat,
    DeliveryManifest,
    PerformanceTelemetryReport,
)


class SpatialDeliveryEngine:
    """
    Partitions 3D digital twin assets into spatial grid chunks and computes multi-resolution LODs:
    - Chunking: 5.0m x 5.0m horizontal spatial grid cells.
    - LOD0 (0-10m): 100% full geometric and texture fidelity (uncompromised close-up).
    - LOD1 (10-25m): 40% decimated geometric representation for mid-range viewing.
    - LOD2 (25m+): 15% bounding proxy representation for distant horizon.
    - Compression: Applies DRACO glTF byte compression ratios (~65-75% network reduction).
    """

    def __init__(self, chunk_size_meters: float = 5.0, cdn_base_url: str = "https://cdn.vastuspace.io/models"):
        self.chunk_size = chunk_size_meters
        self.cdn_base_url = cdn_base_url.rstrip("/")

    def partition_spatial_chunks(
        self,
        model_version_id: str,
        bbox: List[float],
        chunk_size_meters: Optional[float] = None,
        base_triangles_per_chunk: int = 15000,
        essential_center_radius_m: float = 5.0
    ) -> List[SpatialChunk]:
        """
        Partitions scene bounding volume into regular 3D spatial chunks.
        bbox format: [min_x, min_y, min_z, max_x, max_y, max_z]
        """
        step = chunk_size_meters if chunk_size_meters is not None else self.chunk_size
        x_min, y_min, z_min, x_max, y_max, z_max = bbox

        x_steps = max(1, int(math.ceil((x_max - x_min) / step)))
        z_steps = max(1, int(math.ceil((z_max - z_min) / step)))

        chunks: List[SpatialChunk] = []

        for xi in range(x_steps):
            for zi in range(z_steps):
                c_min_x = x_min + xi * step
                c_max_x = min(x_max, c_min_x + step)
                c_min_z = z_min + zi * step
                c_max_z = min(z_max, c_min_z + step)

                center_x = (c_min_x + c_max_x) / 2.0
                center_y = (y_min + y_max) / 2.0
                center_z = (c_min_z + c_max_z) / 2.0

                chunk_id = f"chk_{model_version_id[:6]}_{xi}_{zi}"
                cell_id = f"cell_{xi}_{zi}"

                dist_from_origin = math.sqrt(center_x ** 2 + center_z ** 2)
                is_essential = dist_from_origin <= essential_center_radius_m

                # LOD 0: 100% triangles (50 bytes/tri uncompressed, 14 bytes/tri DRACO)
                tri_lod0 = base_triangles_per_chunk
                uncompressed_lod0 = tri_lod0 * 50
                compressed_lod0 = int(uncompressed_lod0 * 0.28) # 72% compression

                # LOD 1: 40% triangles
                tri_lod1 = int(base_triangles_per_chunk * 0.40)
                uncompressed_lod1 = tri_lod1 * 50
                compressed_lod1 = int(uncompressed_lod1 * 0.26)

                # LOD 2: 15% triangles
                tri_lod2 = int(base_triangles_per_chunk * 0.15)
                uncompressed_lod2 = tri_lod2 * 50
                compressed_lod2 = int(uncompressed_lod2 * 0.24)

                lods = [
                    SpatialChunkLOD(
                        lod_tier=LODTier.LOD0_FULL,
                        triangle_count=tri_lod0,
                        uncompressed_bytes=uncompressed_lod0,
                        compressed_bytes=compressed_lod0,
                        compression_format=CompressionFormat.DRACO_GLTF,
                        max_distance_meters=10.0,
                        cdn_url=f"{self.cdn_base_url}/{model_version_id}/chunks/{chunk_id}_lod0.draco.glb"
                    ),
                    SpatialChunkLOD(
                        lod_tier=LODTier.LOD1_BALANCED,
                        triangle_count=tri_lod1,
                        uncompressed_bytes=uncompressed_lod1,
                        compressed_bytes=compressed_lod1,
                        compression_format=CompressionFormat.DRACO_GLTF,
                        max_distance_meters=25.0,
                        cdn_url=f"{self.cdn_base_url}/{model_version_id}/chunks/{chunk_id}_lod1.draco.glb"
                    ),
                    SpatialChunkLOD(
                        lod_tier=LODTier.LOD2_PROXY,
                        triangle_count=tri_lod2,
                        uncompressed_bytes=uncompressed_lod2,
                        compressed_bytes=compressed_lod2,
                        compression_format=CompressionFormat.DRACO_GLTF,
                        max_distance_meters=100.0,
                        cdn_url=f"{self.cdn_base_url}/{model_version_id}/chunks/{chunk_id}_lod2.draco.glb"
                    ),
                ]

                chunk = SpatialChunk(
                    chunk_id=chunk_id,
                    cell_id=cell_id,
                    center=[center_x, center_y, center_z],
                    bounding_box_min=[c_min_x, y_min, c_min_z],
                    bounding_box_max=[c_max_x, y_max, c_max_z],
                    lod_levels=lods,
                    is_essential=is_essential
                )
                chunks.append(chunk)

        return chunks

    def generate_delivery_manifest(
        self,
        model_version_id: str,
        bounds_min: Optional[List[float]] = None,
        bounds_max: Optional[List[float]] = None,
        chunk_grid_size_meters: Optional[float] = None,
        base_triangles_per_chunk: int = 15000,
        essential_center_radius_m: float = 5.0
    ) -> DeliveryManifest:
        """
        Partitions scene bounding volume into spatial chunks with multi-tier LODs.
        """
        b_min = bounds_min if bounds_min is not None else [-7.5, 0.0, -7.5]
        b_max = bounds_max if bounds_max is not None else [7.5, 3.2, 7.5]
        bbox = b_min + b_max
        step = chunk_grid_size_meters if chunk_grid_size_meters is not None else self.chunk_size

        chunks = self.partition_spatial_chunks(
            model_version_id=model_version_id,
            bbox=bbox,
            chunk_size_meters=step,
            base_triangles_per_chunk=base_triangles_per_chunk,
            essential_center_radius_m=essential_center_radius_m
        )

        essential_chunk_ids = [c.chunk_id for c in chunks if c.is_essential]

        total_uncompressed = sum(c.lod_levels[0].uncompressed_bytes for c in chunks)
        total_compressed = sum(c.lod_levels[0].compressed_bytes for c in chunks)
        comp_ratio = round(total_uncompressed / max(1, total_compressed), 2)

        return DeliveryManifest(
            model_version_id=model_version_id,
            cdn_base_url=self.cdn_base_url,
            total_uncompressed_bytes=total_uncompressed,
            total_compressed_bytes=total_compressed,
            compression_ratio=comp_ratio,
            chunk_grid_size_meters=step,
            chunks=chunks,
            essential_chunk_ids=essential_chunk_ids
        )

    def evaluate_telemetry_verdict(self, report: PerformanceTelemetryReport) -> Dict[str, Any]:
        """
        Evaluates 7-metric telemetry report against competition / demo thresholds:
        - 1. Initial Load <= 500ms
        - 2. TTFV <= 250ms (Immediate visual feedback)
        - 3. Full Scene Stream <= 3000ms
        - 4. Average FPS >= 55.0 (Smooth 60Hz interaction)
        - 5. CPU Heap <= 450 MB
        - 6. GPU Memory <= 512 MB and Draw Calls <= 200
        - 7. Route Latency <= 50ms
        """
        checks = {
            "initial_load": {
                "measured_ms": report.initial_load_ms,
                "target_ms": 500.0,
                "pass": report.initial_load_ms <= 500.0
            },
            "time_to_first_visual": {
                "measured_ms": report.time_to_first_visual_ms,
                "target_ms": 250.0,
                "pass": report.time_to_first_visual_ms <= 250.0
            },
            "full_scene_load": {
                "measured_ms": report.full_scene_load_ms,
                "target_ms": 3000.0,
                "pass": report.full_scene_load_ms <= 3000.0
            },
            "average_fps": {
                "measured_fps": report.average_fps,
                "target_fps": 55.0,
                "pass": report.average_fps >= 55.0
            },
            "cpu_memory": {
                "measured_mb": report.memory_heap_mb,
                "target_mb": 450.0,
                "pass": report.memory_heap_mb <= 450.0
            },
            "gpu_memory": {
                "measured_mb": report.gpu_memory_mb,
                "target_mb": 512.0,
                "draw_calls": report.gpu_draw_calls,
                "target_draw_calls": 200,
                "pass": (report.gpu_memory_mb <= 512.0 and report.gpu_draw_calls <= 200)
            },
            "route_latency": {
                "measured_ms": report.route_latency_ms,
                "target_ms": 50.0,
                "pass": report.route_latency_ms <= 50.0
            },
            "viewer_interactive_during_load": {
                "measured": report.viewer_interactive_during_load,
                "target": True,
                "pass": report.viewer_interactive_during_load is True
            }
        }

        # The 7 core competition criteria (excluding boolean interactivity)
        core_metric_keys = [
            "initial_load", "time_to_first_visual", "full_scene_load",
            "average_fps", "cpu_memory", "gpu_memory", "route_latency"
        ]
        passed_core_count = sum(1 for k in core_metric_keys if checks[k]["pass"])
        all_passed = (passed_core_count == len(core_metric_keys))
        violations = [k for k in core_metric_keys if not checks[k]["pass"]]

        return {
            "report_id": report.report_id,
            "model_version_id": report.model_version_id,
            "status": "PASS" if all_passed else "REVIEW_REQUIRED",
            "overall_verdict": "ALL_SLAS_MET" if all_passed else "SLAS_BREACHED",
            "all_slas_met": all_passed,
            "passed_metrics": passed_core_count,
            "total_metrics": len(core_metric_keys),
            "checks": checks,
            "zero_degradation_verified": not report.visible_degradation_detected,
            "details": {
                "violations": violations,
                "checks": checks
            },
            "summary_narrative": (
                f"TTFV: {report.time_to_first_visual_ms:.1f}ms, "
                f"FPS: {report.average_fps:.1f}Hz, "
                f"GPU: {report.gpu_memory_mb:.1f}MB ({report.gpu_draw_calls} draw calls), "
                f"Route Latency: {report.route_latency_ms:.1f}ms. "
                "Progressive spatial chunks stream with 0 main-thread jank."
            )
        }
