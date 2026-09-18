# VĀSTU System Upgrade Documentation

This directory contains the canonical specifications, audits, architecture contracts, and implementation reports for the VĀSTU / Namma Space platform upgrade.

---

## Upgrade Stages & Artifact Index

| Stage | Document | Purpose & Contents | Status |
| :--- | :--- | :--- | :--- |
| **Stage 0** | [`stage0.md`](./stage0.md) | **Repository Audit & Reality Matrix**: Line-by-line audit of all 20 subsystems (Implemented vs Mocked vs Missing vs Broken), execution tracing, and critical blockers. | **COMPLETE** |
| **Stage 1** | [`canonical_architecture.md`](./canonical_architecture.md) | **Canonical Architecture & Formal Contracts**: Architecture boundaries (Mobile, Backend, Processing, Navigation, Web Viewer, AR), and formal Pydantic v2 schemas for Contracts 1 through 13. | **COMPLETE** |
| **Stage 2** | *Architecture Spec & Test Suite* | **Repository Refactoring & Subsystem Modularization**: Execution of architectural separation, BaseWorker 8-stage lifecycle, pure geometry/navigation engines, and test validation. | **COMPLETE** |
| **Stage 3** | *Architecture Spec & Test Suite* | **Upgraded Capture Data Model**: Versioned manifest (v2.0.0), deterministic naming, 6-stage validation engine, and self-contained offline reproducibility. | **COMPLETE** |
| **Stage 4** | *Architecture Spec & Test Suite* | **Mobile Capture System**: RGB & IMU sync, zero-loss ring buffer, persistent journal recovery, storage safety thresholds, and upload queue packaging. | **COMPLETE** |
| **Stage 5** | *Architecture Spec & Test Suite* | **Event-Driven Capture SOP Engine**: 11 spatial stages, 7 real-time quality signals, 4-tier prioritized TTS guidance with anti-repetition cooldowns. | **COMPLETE** |
| **Stage 6** | *Architecture Spec & Test Suite* | **Resumable Direct-to-Storage Upload Pipeline**: 7 explicit states, chunked multipart uploads, presigned storage URLs (zero proxying), duplicate prevention, deliberate network interruption & resumption without restarting from zero. | **COMPLETE** |
| **Stage 7** | *Architecture Spec & Test Suite* | **Upgraded Preprocessing Pipeline**: Frame extraction, sharpness/exposure/feature analysis, duplicate suppression, content-adaptive keyframe selection (high-motion, corners, doors, windows, loop closure), 100% discard reasons, `keyframes/`, `quality.json`, `frame_manifest.json`. | **COMPLETE** |
| **Stage 8** | *Architecture Spec & Test Suite* | **Hierarchical Camera Pose Estimation**: Fusion of Device VIO, visual odometry, SfM, and bundle adjustment; `camera_poses.json` with tracking source, confidence, and detection of tracking loss, low parallax, disconnected trajectory, high reprojection error, loop closure drift. | **COMPLETE** |
| **Stage 9** | *Architecture Spec & Test Suite* | **Dense Reconstruction & Evidence Fusion**: Multi-view geometric consistency, evidence dense point cloud (`dense_pointcloud.ply`) with confidence and source observation traceability, `density_map.json`, defect auditing (holes, isolated clusters, floating geometry, noise, inconsistent depth). | **COMPLETE** |
| **Stage 10** | *Architecture Spec & Test Suite* | **Spatial-Cell Decomposition & Independent Lifecycle**: Partitioning 3D reconstruction into versioned cells with local coordinate systems, source frames/poses, boundary halo margins, independent reconstruction, validation, rescan, update, and seamless fusion. | **COMPLETE** |
| **Stage 11** | *Architecture Spec & Test Suite* | **Architectural Structure Extraction**: Normal estimation, dominant plane detection, 4-way classification (floor/wall/ceiling/other), confidence & boundaries, intersection analysis, selective 90° architectural prior evaluation, non-orthogonal angle preservation, and topological plane graph. | **COMPLETE** |
| **Stage 12** | *Architecture Spec & Test Suite* | **Geometry Correction Using Architectural Constraints**: Controlled geometric snapping, wall thickness estimation, floor/ceiling clipping, opening regularization, phantom/floating removal, 7-point QA validation audits, and measurable QA reporting. | **COMPLETE** |
| **Stage 13** | *Architecture Spec & Test Suite* | **Independent Semantic Reconstruction**: 10-class architectural taxonomy (rooms, doors, windows, furniture, tables, chairs, sofas, desks, signage, architectural objects), 3D OBB fitting, room containment mapping, source observation provenance, and strict ground truth confidence policy. | **COMPLETE** |
| **Stage 14** | *Architecture Spec & Test Suite* | **Metric Coordinate Alignment & Canonical World System**: Canonical world frame (+Z up, floor Z=0), 5-tier evidence priority resolution (LiDAR -> Physical -> Floorplan -> Known Objects -> Manual), explicit Sim(3) storage, no silent scaling, and publishing enforcement. | **COMPLETE** |
| **Stage 15** | *Architecture Spec & Test Suite* | **Tri-Representation Separation**: Decoupled Visual (3DGS/textured mesh), Structural (BIM/planar graph), and Collision (NavMesh/obstacles) models; explicit linking via TriRepresentationBundle and coordinate transforms; runtime decoupled rendering & navigation. | **COMPLETE** |
| **Stage 16** | *Architecture Spec & Test Suite* | **Central Quality Engine**: 6-subsystem audit (Capture, Pose, Depth, Geometry, Semantics, Navigation), global & per-cell scores, spatial confidence maps, hard failure gating, and explanatory narratives explaining WHY models pass or fail. | **COMPLETE** |
| **Stage 17** | *Architecture Spec & Test Suite* | **Targeted Rescan Generation**: Automated 10-step localized retake workflow (identify region/reason, calculate observations, mobile visual/TTS guidance, delta uploads, local cell reconstruction & boundary fusion without rebuilding the building). | **COMPLETE** |
| **Stage 18** | *Architecture Spec & Test Suite* | **Immutable Model Versioning & Comparison**: Strict immutability guarantee (never overwrite V1), V1 -> cell reconstruction -> registration -> boundary validation -> fusion -> V2, metadata completeness, and 4-way comparison (geometry, POIs, navigation, confidence). | **COMPLETE** |
| **Stage 19** | *Architecture Spec & Test Suite* | **Semantic POI System & Raycast Placement**: 10-field POI schema, CRUD, textual & alias search, 3D metric spatial queries, 3D raycast hit placement against surface mesh, and cross-version spatial validity migration. | **COMPLETE** |
| **Stage 20** | *Architecture Spec & Test Suite* | **Hybrid Spatial Search**: 5-stage search pipeline (lexical, semantic taxonomy, spatial filtering, composite ranking, 3D coordinate resolution), exact/fuzzy/semantic/relational queries, and interactive viewer pins. | **COMPLETE** |
| **Stage 21** | *Architecture Spec & Test Suite* | **Navigation Representation from Structural/Collision Geometry**: 6-stage pipeline (floor -> obstacles -> footprints -> human-radius inflation -> walkable region -> NavMesh), zero-derivation from Gaussian splats, narrow-passage/disconnected-floor detection, and identifiable geometric causality. | **COMPLETE** |
| **Stage 22** | *Architecture Spec & Test Suite* | **Route Planning Pipeline & Collision Validation**: 5-stage pipeline (nearest valid point -> multi-criteria A* [turns, narrow paths, slopes] -> waypoint extraction -> string-pulling shortcut smoothing -> dense metric collision validation), POI resolution, and strict collision rejection policy. | **COMPLETE** |
| **Stage 23** | *Architecture Spec & Test Suite* | **Three.js Web Viewer Upgrade & Pure Roaming**: WebGL rendering with decoupled Tri-Representation layers, FPS WASD kinematics, mouse look, floor grounding, continuous collision pushback, POI raycasting, search highlights, dynamic route visualization, and pure roaming runtime. | **COMPLETE** |
| **Stage 24** | *Architecture Spec & Test Suite* | **Delivery Optimization for Competition/Demo**: Asset compression (DRACO GLTF), 5m spatial chunks, 3-tier LODs, lazy/progressive streaming, GPU memory budgets, and 7-metric live telemetry HUD. | **COMPLETE** |
| **Stage 25** | *Architecture Spec & Test Suite* | **End-to-End Workflow Orchestrator**: Automated continuous 22-stage pipeline connecting mobile capture, SOP, upload, reconstruction, semantics, alignment, registry, and viewer; observable monotonic 0–100% progress events. | **COMPLETE** |
| **Stage 26** | *Architecture Spec & Test Suite* | **Deliberate Pipeline Failure Testing**: 14 failure injection modes (network drop, corrupted video, missing frames, timestamps, overlap, tracking, COLMAP, depth, cell, GPU OOM, geometry, fusion, navigation, assets), 7-dimension verification, zero silent corruption. | **COMPLETE** |
| **Stage 27** | *Architecture Spec & Test Suite* | **Controlled Physical Benchmark Environment**: Surveyed Lab-Alpha-8x6 ground truth (walls, room, corners, doors, ceiling, furniture), 8 physical accuracy metrics (scale, wall, corner, floor, opening, objects, completeness, confidence), empirical baseline vs upgraded comparison. | **COMPLETE** |
| **Stage 28** | *Architecture Spec & Test Suite* | **Navigation Benchmark Scenarios & Quantitative Validation**: 9 geometric test scenarios (direct path, left/right obstacle detours, narrow corridor, furniture cluster, doorway, disconnected partition, start/dest near obstacles), 6 quantitative metrics (success rate, collision rate, path length, computation time, waypoint smoothness, invalid rejection). | **COMPLETE** |
| **Stage 29** | *Architecture Spec & Test Suite* | **AR Localization as an Independent Layer**: Reliable marker-based localization pipeline (camera -> detection -> PnP pose -> model anchor -> rigid transform -> device-to-model -> route projection), 5 quantitative error metrics, zero pipeline intrusion. | **COMPLETE** |


---

## Architecture Overview

The system is organized into decoupled layers to prevent ambiguous ownership and isolated dependencies:

```
                  ┌─────────────────────────────────┐
                  │    Mobile Capture (iOS/Android) │
                  └────────────────┬────────────────┘
                                   │ Contract 1 (CaptureManifest)
                                   ▼
                  ┌─────────────────────────────────┐
                  │   FastAPI Control Plane (api/)   │
                  └────────┬──────────────┬─────────┘
                           │              │
              Contract 1-3 │              │ Presigned URLs
                           ▼              ▼
              ┌──────────────────┐   ┌───────────────────────────┐
              │ Workers Pipeline │   │ S3 / Object Storage       │
              │ (workers/)       │   │ (storage/)                │
              └────────┬─────────┘   └─────────────┬─────────────┘
                       │                           │
          Artifacts 4-8│                           │ PLY / GLB / SPLAT
                       ▼                           ▼
              ┌──────────────────┐   ┌───────────────────────────┐
              │ PostgreSQL/PostGIS│  │ Web Viewer (Three.js)     │
              │ (database/)      │   │ (src/)                    │
              └──────────────────┘   └───────────────────────────┘
```

---

## 13 Formal Data Contracts

All data interchange between capture devices, workers, databases, and clients is governed by formal schemas in [`core/schemas/`](../core/schemas):

1. **Contract 1: Capture Manifest** ([`capture_manifest.py`](../core/schemas/capture_manifest.py))
2. **Contract 2: Frame Metadata** ([`frame_metadata.py`](../core/schemas/frame_metadata.py))
3. **Contract 3: IMU Samples** ([`imu_samples.py`](../core/schemas/imu_samples.py))
4. **Contract 4: Camera Poses** ([`camera_poses.py`](../core/schemas/camera_poses.py))
5. **Contract 5: Reconstruction Artifact** ([`reconstruction_artifact.py`](../core/schemas/reconstruction_artifact.py))
6. **Contract 6: Spatial Cell Manifest** ([`spatial_cell.py`](../core/schemas/spatial_cell.py))
7. **Contract 7: Structural Geometry** ([`structural_geometry.py`](../core/schemas/structural_geometry.py))
8. **Contract 8: Semantic Object Set** ([`semantic_object.py`](../core/schemas/semantic_object.py))
9. **Contract 9: POI Collection** ([`poi.py`](../core/schemas/poi.py))
10. **Contract 10: Navigation Graph** ([`navigation_graph.py`](../core/schemas/navigation_graph.py))
11. **Contract 11: Quality Report** ([`quality_report.py`](../core/schemas/quality_report.py))
12. **Contract 12: Rescan Request** ([`rescan_request.py`](../core/schemas/rescan_request.py))
13. **Contract 13: Model Version Manifest** ([`model_version.py`](../core/schemas/model_version.py))

---

## Standardized Worker Execution Lifecycle

Every pipeline stage in [`workers/stages/`](../workers/stages) inherits from [`BaseWorker`](../workers/base.py) and executes the standardized lifecycle:

```
INPUT ──> VALIDATION ──> PROCESSING ──> OUTPUT ARTIFACT ──> OUTPUT MANIFEST ──> METRICS ──> LOGGING ──> ERROR STATE
```

- `Stage 01: Preprocessing` (Frames, IMU unpack)
- `Stage 02: SfM` (Sparse reconstruction, Contract 4)
- `Stage 03: Depth` (Dense metric depth estimation)
- `Stage 04: PointCloud` (RGB-D unprojection, spatial hash downsampling)
- `Stage 05: Meshing` (Poisson reconstruction, manifold topological check)
- `Stage 06: Texturing` (UV unwrapping & texture projection)
- `Stage 07: Semantics` (Oriented Bounding Box extraction, Contracts 7 & 8)
- `Stage 08: NavMesh` (Walkable graph & wheelchair accessibility, Contract 10)
- `Stage 09: Quality` (Coverage & drift metrics, Contracts 11 & 12)

---

## Verification & Testing

To run the complete test suite:

```bash
PYTHONPATH=. backend/workers/venv/bin/pytest tests/ -v
```

All 158 unit and integration tests validate:
- All 13 Pydantic v2 data contracts.
- The 8-stage worker execution lifecycle and error handlers.
- Pure geometry engine (RANSAC planes, dihedral angles, spatial hashing, normal PCA, mesh repair).
- Indoor A* pathfinding and ADA wheelchair slope rejection ($> 4.76^\circ$).
- Storage adapter (upload, download, multipart, presigned URLs, byte streams).
- Mobile capture engine (sync, ring buffer, storage alerts, journal recovery, packaging).
- SOP engine (11 spatial stages, 7 quality signals, prioritized anti-repetition TTS).
- Resumable upload pipeline (7-state machine, direct-to-storage presigned URLs, network interruption & resumption).
- Stage 01 Preprocessing (blur, exposure, features, duplicate suppression, adaptive keyframes, 100% discard reasons).
- Stage 02 Camera Pose Estimation (hierarchical VIO/visual fusion, anomaly flags, tracking loss, unreliable segments).
- Stages 03-04 Dense Reconstruction (multi-view consistency, evidence fusion, point confidence, observation traceability, density mapping, defect auditing).
- Spatial-Cell Decomposition (local coordinate systems, halo boundary continuity, independent reconstruction, validation, rescan, and global fusion).
- Architectural Structure Extraction (dominant floor/ceiling planes, 4-wall orthogonalization, sharp corners, ceiling-height confidence).
- Geometric Correction & 7 QA Audits (floor flattening, wall plumb, corner orthogonality, planarity, drift, leakage, and multi-resolution mesh alignment).
- Independent Semantic Reconstruction & Ground Truth Policy (10-class taxonomy, 3D oriented bounding boxes, ground-truth strict policy, and room containment).
- Metric Coordinate Alignment & 5-Tier Priority (canonical frame alignment, gravity-aligned Z-up, zero-drift origin, explicit inversion, metric scale consistency).
- Tri-Representation Separation (visual photorealism, structural BIM, and collision clearance, independently viewable and coupled via TriRepresentationBundle).
- Central Quality Engine & Targeted Rescan Generation (defect classification, actionable TTS/visual guidance, and localized cell fusion without full rebuild).
- Immutable Model Versioning & Comparison (linear lineage, parent references, unchanged cells preservation, and 4-way differential comparison).
- Version-Aware POI System (spatial anchoring, CRUD, fuzzy & semantic search, raycast visual creation, and cross-version coordinate migration).
- Hybrid Spatial Search Engine (exact, fuzzy, semantic embeddings, and spatial/room relational filtering).
- Navigation Representation from Structural & Collision Geometry (zero Gaussian splat derivation, human radius inflation, and clear geometric causality).
- Route Planning Pipeline (multi-criteria A*, turn penalties, narrow passage avoidance, wheelchair accessibility, and collision validation).
- Interactive Three.js Web Viewer & Pure Roaming Runtime (WASD kinematic roaming, continuous circle-to-AABB collision pushback, and decoupled render loop).
- Asset Delivery Optimization & Performance Telemetry (5m spatial chunking, 3-tier distance-based LODs, DRACO glTF compression ~72%, and 7-metric live telemetry HUD).
- FastAPI endpoints (health check, capture manifest ingestion, route generation, upload sessions, models, search, navigation, delivery manifest, and telemetry).



