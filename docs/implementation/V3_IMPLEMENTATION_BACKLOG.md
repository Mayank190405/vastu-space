# VĀSTU v3.0 — Prioritized Implementation Backlog

**Status:** Active  
**Baseline:** October 2026  
**Reference Document:** `docs/VASTU_v3.0_MASTER_ARCHITECTURE.md`

---

## Priority Classification
- **P0 — Critical Foundations**: Coordinate conventions, calibration, capture schema, pose/frame sync, package validator, reprojection tests.
- **P1 — Capture Reliability**: ARKit 6-DoF logging, tracking-state events, keyframe gating, floor anchoring, coverage HUD.
- **P2 — Metric Geometry**: LightGlue pose refinement, Depth Anything V2 + normal consistency, multi-plane RANSAC 90° snapping.
- **P3 — Appearance**: 3DGS training (`gsplat`), held-out evaluation, SPZ compression, desktop/mobile visual tiers.
- **P4 — Navigation**: Collision mesh (`collision.glb`), NavMesh generation, FirstPerson WASD + touch joysticks.
- **P5 — Production Hardening**: Durable queues, idempotency, checkpoints, privacy redaction, regression benchmarks.

---

## Detailed Task Backlog

### P0 — Critical Foundations

#### [TASK-001] S5 Coordinate Conventions & Spatial Transforms (DONE - TESTED)
- **V3 Section**: Section 3 (S5), Section 19 (Task 1 & 5)
- **Affected Files**: `core/coordinates/conventions.py`, `core/coordinates/__init__.py`, `tests/test_coordinate_conventions.py`
- **Description**: Define authoritative camera and world coordinate contracts ($T_{\text{world\_camera}}$, ARKit RUB ➔ OpenCV RDF, OpenGL RUB).
- **Proposed Changes**: Implement $C_{\text{opencv}\leftarrow\text{arkit}} = \text{diag}(1, -1, -1)$, quaternion/matrix roundtrips, forward/backward pinhole projection.
- **Dependencies**: None
- **Priority**: P0
- **Complexity**: Low
- **Risk**: Critical
- **Acceptance Criteria**: Synthetic reprojection error $< 1.0\text{ px}$ (actual $< 10^{-4}\text{ px}$). Matrix orthonormality strictly checked.
- **Test Strategy**: `python3 -m unittest tests/test_coordinate_conventions.py` (6 unit tests passing).
- **Status**: **DONE — TESTED**

#### [TASK-002] Shared Capture Schema v1.0 Contract
- **V3 Section**: Section 5 (Capture Package), Section 19 (Task 1)
- **Affected Files**: `core/schemas/capture_package_v1.py`, `core/schemas/__init__.py`, `tests/test_capture_package_schema.py`
- **Description**: Establish the formal Pydantic v2 data contract for the v3.0 capture package (`manifest.json`, `camera_poses.jsonl`, `camera_intrinsics.json`, `tracking_events.jsonl`, `checksums.sha256`).
- **Proposed Changes**: Define schemas matching Section 5 with required vs. optional fields, monotonic timestamp validation, and finite float checks.
- **Dependencies**: TASK-001
- **Priority**: P0
- **Complexity**: Medium
- **Risk**: High
- **Acceptance Criteria**: Validates a full session package, rejects unnormalized quaternions, rejects negative timestamps, enforces schema versioning.
- **Test Strategy**: Unit tests with valid and intentionally corrupted mock packages.
- **Status**: **NOT STARTED (Sprint 1)**

#### [TASK-003] Capture Package Validator & Ingest Adapter
- **V3 Section**: Section 5, Section 19 (Task 4 & 7)
- **Affected Files**: `core/validation/package_validator.py`, `core/validation/__init__.py`, `tests/test_package_validator.py`
- **Description**: Validate incoming capture packages before reconstruction; reject corrupt or out-of-order data with actionable error messages; provide backwards-compatibility adapter for existing pipeline.
- **Proposed Changes**: Check SHA-256 hashes, verify frame-pose associations, check timestamp monotonicity, check pose matrix validity.
- **Dependencies**: TASK-002
- **Priority**: P0
- **Complexity**: Medium
- **Risk**: High
- **Acceptance Criteria**: Rejects corrupt captures with explicit codes; converts valid v3 packages to internal worker format.
- **Test Strategy**: Automated validator unit test suite with invalid payloads.
- **Status**: **NOT STARTED (Sprint 1)**

---

### P1 — Capture Reliability (iOS App)

#### [TASK-004] ARKit Session & Pose/Frame Synchronization Logging
- **V3 Section**: Section 4, Section 19 (Task 2 & 3)
- **Affected Files**: `ios/VastuSpatial/Camera/ARSessionManager.swift`, `ios/VastuSpatial/Storage/CapturePackageWriter.swift`
- **Description**: Implement `ARSessionManager` using `ARWorldTrackingConfiguration` (Zero-LiDAR mode). Log frame image, $T_{\text{world\_camera}}$ pose, camera intrinsics ($f_x, f_y, c_x, c_y$), and tracking-state events at 30Hz without blocking the delegate thread.
- **Proposed Changes**: Use a bounded serial background dispatch queue (`DispatchQueue(label: "com.vastu.capture.writer")`). Stream poses to `camera_poses.jsonl`.
- **Dependencies**: TASK-002
- **Priority**: P1
- **Complexity**: High
- **Risk**: High
- **Acceptance Criteria**: Zero frame-drop on reference iPhone; monotonic nanosecond timestamps; valid 4x4 transform matrices emitted.
- **Test Strategy**: Swift unit test with mock `ARFrame` stream; Xcode build validation.
- **Status**: **NOT STARTED (Sprint 1)**

#### [TASK-005] Floor Anchor & Baseboard Raycasting Engine (Phase 1 Outline)
- **V3 Section**: Section 4.2, Section 4.3
- **Affected Files**: `ios/VastuSpatial/Camera/FloorAnchorEstimator.swift`, `core/sop/voxel_grid.py`
- **Description**: Establish metric floor plane via gravity lock ($[0, -1, 0]$); raycast baseboard optical rays to trace 2D room footprint (supports arbitrary L/T shapes).
- **Proposed Changes**: Replace 4-wall static box in `voxel_grid.py` with dynamic 2D polygon footprint accumulator.
- **Dependencies**: TASK-004
- **Priority**: P1
- **Complexity**: High
- **Risk**: Medium
- **Acceptance Criteria**: Correctly reconstructs convex and concave room perimeter polygon on test trajectories.
- **Status**: **NOT STARTED (Phase 1)**

#### [TASK-006] On-Device Keyframe & Anti-Pivot Gating
- **V3 Section**: Section 4.5, Section 7.1
- **Affected Files**: `ios/VastuSpatial/Camera/CaptureQualityEngine.swift`, `ios/VastuSpatial/Models/MobileDepthSemanticEngine.swift`
- **Description**: Drop blurry frames on-device before saving; trigger haptic/audio alert if pure rotation without translation ($b \approx 0$) is detected.
- **Proposed Changes**: Real-time Laplacian variance gating + IMU velocity threshold check.
- **Dependencies**: TASK-004
- **Priority**: P1
- **Complexity**: Medium
- **Risk**: Medium
- **Acceptance Criteria**: Blurry frames discarded automatically; anti-pivot warning triggers within 250ms of pure rotation.
- **Status**: **NOT STARTED (Phase 1)**

---

### P2 — Metric Geometry & Reconstruction

#### [TASK-007] LightGlue Pose Refinement with Metric VIO Priors
- **V3 Section**: Section 6, Section 19 (Task 7)
- **Affected Files**: `core/tracking/pose_refiner.py`, `workers/stages/stage02_sfm.py`
- **Description**: Refine camera poses using LightGlue feature matching while constraining metric scale via VIO pose priors (no unconstrained Sim(3) drift).
- **Dependencies**: TASK-003
- **Priority**: P2
- **Complexity**: High
- **Risk**: High
- **Acceptance Criteria**: Reprojection RMS $< 1.0\text{ px}$; scale change constrained to $\le 2\%$.
- **Status**: **NOT STARTED (Phase 2)**

#### [TASK-008] Depth-Normal Consistency & Multi-View Fusion
- **V3 Section**: Section 7
- **Affected Files**: `ml/depth/estimator.py`, `core/dense/tsdf_fusion.py`
- **Description**: Integrate DSINE surface normal prior into depth estimation; enforce $\nabla D \cdot \mathbf{n} = 0$; multi-view consistency check ($< 3\text{ cm}$).
- **Dependencies**: TASK-007
- **Priority**: P2
- **Complexity**: High
- **Risk**: High
- **Acceptance Criteria**: Flat surfaces exhibit zero outward bowing; noisy depth edges rejected before TSDF.
- **Status**: **NOT STARTED (Phase 2)**

#### [TASK-009] Multi-Plane RANSAC & 90° Manhattan Snapping
- **V3 Section**: Section 9
- **Affected Files**: `core/structure/extractor.py`, `core/correction/snapping.py`, `workers/stages/stage05_meshing.py`
- **Description**: Extract $N$ vertical planes + floor/ceiling; enforce orthogonality; analytical 3D line intersection for knife-edge corners; mask furniture out of wall fitting.
- **Dependencies**: TASK-008
- **Priority**: P2
- **Complexity**: High
- **Risk**: High
- **Acceptance Criteria**: Wall-to-floor angle $= 90.0^\circ \pm 0.5^\circ$; corners are sharp lines without mesh ballooning.
- **Status**: **NOT STARTED (Phase 2)**

---

### P3 — Photorealistic 3D Gaussian Splatting

#### [TASK-010] 3DGS Training Pipeline (`gsplat`) & SPZ Exporter
- **V3 Section**: Section 10
- **Affected Files**: `core/splatting/trainer.py`, `core/splatting/spz_exporter.py`, `scripts/generate_video_twin.py`
- **Description**: Optimize 3D Gaussians (15k–30k steps) from refined poses; prune floaters; export compressed `scene.spz` (~15–30MB).
- **Dependencies**: TASK-007
- **Priority**: P3
- **Complexity**: High
- **Risk**: High
- **Acceptance Criteria**: PSNR $> 28.0\text{ dB}$ on held-out views; SPZ output decodable in Three.js splat viewer.
- **Status**: **NOT STARTED (Phase 3)**

---

### P4 — Navigation & Web Viewer

#### [TASK-011] Free-Roaming Viewer with Collision & SPZ Integration
- **V3 Section**: Section 11, Section 12
- **Affected Files**: `src/components/viewer/Spatial3DViewer.tsx`, `src/components/viewer/roamingController.ts`
- **Description**: Integrate `@mkkellogg/gaussian-splats-3d` for 60+ FPS SPZ rendering; enforce capsule sliding collision against `collision.glb`; desktop WASD + mobile touch joysticks.
- **Dependencies**: TASK-009, TASK-010
- **Priority**: P4
- **Complexity**: Medium
- **Risk**: Medium
- **Acceptance Criteria**: Camera cannot pass through walls; maintains 60 FPS on reference desktop and 30 FPS on mobile.
- **Status**: **NOT STARTED (Phase 4)**

---

### P5 — Production Hardening & Benchmarks

#### [TASK-012] Spike S6 Pipeline Baseline Benchmark Suite
- **V3 Section**: Section 3 (S6), Section 15, Section 19 (Task 8)
- **Affected Files**: `benchmarks/run_baseline_audit.py`, `docs/implementation/V3_BASELINE_REPORT.md`
- **Description**: Run benchmark on captured reference datasets; record wall dimension error, plane flatness RMS, runtime, and failure categories.
- **Dependencies**: TASK-001 through TASK-003
- **Priority**: P5
- **Complexity**: Medium
- **Risk**: Low
- **Acceptance Criteria**: Generates versioned `baseline_audit.json` with explicit ground-truth comparison.
- **Status**: **NOT STARTED (Sprint 1)**

## Sprint 1 reviewed backlog — 2026-10-26

This section supersedes speculative acceptance criteria above: no guaranteed zero
frame drops, model accuracy, universal 3 cm fusion threshold, forced right angles,
SPZ size or FPS. All later phases are NOT STARTED in this batch.

Each entry lists affected files, proposal, dependency, complexity/risk, acceptance,
verification and architecture mapping.

- **V3-01 / P0** Existing `core/coordinates/conventions.py` and schema: reject
  nonrigid/nonfinite inputs; document row-major C2W, pixel orientation and clock.
  Depends: none. Medium/critical. Accept: twelve S5 cases including independent
  synthetic room, orientation and OpenCV extrinsics tests; pytest. §§3 S5,5,19.
- **V3-02 / P0** `core/packaging/capture_package.py`, `core/validation/`:
  add V1 methods without removing legacy video contract; complete checksum coverage,
  decoded dimensions, IDs, calibration and monotonic times. Depends V3-01.
  Medium/high. Accept: roundtrip, corruption/missing file/path traversal rejection;
  temporary-directory integration tests. §§5,19 tasks 1,4.
- **V3-03 / P0** `workers/stages/stage02_sfm.py`, `workers/pipeline.py`:
  deterministic adapter preserving supplied VIO poses and K, avoiding heuristic
  scale changes. Depends V3-02. Medium/critical. Accept: known world points project
  identically through worker R,t; invalid inputs fail before inference. §§6,13,19.7.
- **V3-04 / P0** `ios/VastuSpatial/Camera/`, `Views/Capture/` and Xcode project:
  opt-in ARKit capture from one ARFrame with bounded recording and drop diagnostics.
  Depends V3-01/02. High/high. Accept: native compile and on-device package validated
  by Python; queue exhaustion/recovery checked manually. §§4,5,19 tasks 2,3.
- **V3-05 / P0** `scripts/benchmark_capture_v3.py`, docs/reference protocol:
  repeatable scale/drift and package baseline, three measured room smoke protocol
  (five rooms/two devices/three repeats for full S1). Depends V3-02/03.
  Medium/medium. Accept: machine-readable report; unknown metrics null/NOT MEASURED;
  no invented reference data; pytest runner and manual physical captures. §§3 S1,S6,15,19.
- **V3-06 / P1** existing capture/quality/SOP modules: floor confirmation, tracking
  recovery, quality/coverage and guided infill. Depends V3-04. High/high. Accept:
  measured field sessions and translational diversity while preserving rotation
  appearance observations. Unit geometry + two-device field protocol. §§4,17 phase1.
- **V3-07 / P2** `core/tracking/`, `core/dense/`, `core/structure/`: constrained BA,
  licensed depth/normals, confidence fusion and free-angle topology. Depends V3-05/06,
  S3 license decision. High/critical. Accept: measured dimensions/flatness/corners
  against truth, no independent unbounded per-frame scale. Unit + reference GPU
  regression. §§6–9,15.
- **V3-08 / P3** representation/worker modules: gsplat, held-out views, compressed
  assets; renderer selection only after S2. Depends V3-07 and S2/S3. High/high.
  Accept: independently decoded assets and measured quality/load/frame percentiles;
  GPU/browser benchmarks. §§3 S2,10,12.
- **V3-09 / P4** existing viewer/navigation: separate collision assets, swept capsule,
  touch, navmesh/mini-map. Depends V3-07/08. High/high. Accept: automated no-penetration
  tests plus device navigation; navmesh is not collision geometry. §§11,12.
- **V3-10 / P5** API/storage/orchestrator/CI: remove secret fallback, secure legacy
  archive extraction, durable jobs, signed URLs, deletion/retention, provenance and
  benchmark regression. Depends V3-02, deploy review. High/critical. Accept: malicious
  archive/auth/access tests, worker recovery and retention integration tests. §§13,16.

S2/S3/S4 benchmark preparation and pending decisions are recorded in
`V3_VALIDATION_SPIKES.md`; no large weights will be downloaded for this sprint.
