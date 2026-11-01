# VĀSTU v3.0 — Codebase Audit & Architecture Compliance Report

**Date:** October 2026  
**Status:** Baseline Completed  
**Repository:** `/Users/kradsagency/Desktop/vastu-namma-space`  
**Reference Document:** `docs/VASTU_v3.0_MASTER_ARCHITECTURE.md`

---

## 1. Executive Summary

A comprehensive source inspection of the VĀSTU repository was executed to evaluate compliance against the **VĀSTU v3.0 Master Architecture**. 

The repository contains a substantial, mature foundation across algorithms, schemas, tests, and web components (39 backend/algorithm test suites, 30 Pydantic data contracts, and complete 25-stage reconstruction pipelines). However, significant architectural gaps exist between the current codebase and the v3.0 specification:
1. **iOS Capture (`ios/VastuSpatial`)**: Currently utilizes raw AVFoundation `AVCaptureMovieFileOutput` to record a single `.mov` video file and an independent `.csv` of IMU readings, rather than real-time ARKit 6-DoF camera pose, timestamp, and intrinsics logging per frame.
2. **Coordinate Conventions**: Prior modules used disparate axis conventions (RUB, RDF, FLU) without an authoritative boundary contract; now resolved with the newly implemented `core/coordinates/conventions.py` (Spike S5).
3. **Capture Data Contract**: The existing `core/schemas/capture_manifest.py` (v2.0) is video-centric; v3.0 requires an explicit, synchronized keyframe package format (`capture_<session_id>/`) with JSONL camera poses and integrity checksums.
4. **Visual Radiance Fields (3DGS)**: The web viewer is built around Three.js `OBJLoader` and `PLYLoader`; 3D Gaussian Splatting (`scene.spz`) rendering and training are specified in architecture but not yet integrated into the primary pipeline.
5. **Geometry Regularization**: The TSDF and meshing stages (`stage05_meshing.py`, `generate_video_twin.py`) use soft vertex smoothing rather than hard multi-plane RANSAC snapping with Manhattan/Atlanta orthogonality constraints.

---

## 2. Subsystem Audit Matrix

| Component | Existing Implementation Path | Current Status | V3 Requirement | Action |
| :--- | :--- | :--- | :--- | :--- |
| **ARKit Tracking** | `ios/VastuSpatial/Camera/AVCameraManager.swift` | **PARTIALLY_IMPLEMENTED** | `ARSession` with `ARWorldTrackingConfiguration` logging 6-DoF `T_world_camera` at 30Hz | **Modify** |
| **Camera Calibration** | `core/schemas/capture_manifest.py` (`CameraCalibration`) | **IMPLEMENTED** | Pinhole intrinsics ($f_x, f_y, c_x, c_y$) with lens distortion metadata | **Keep & Extend** |
| **Coordinate Conventions** | `core/coordinates/conventions.py` | **IMPLEMENTED** | S5 Spike: $T_{\text{world\_camera}}$, ARKit RUB ➔ OpenCV RDF, synthetic error $< 1\text{ px}$ | **Keep (Tested)** |
| **Frame Recording** | `ios/VastuSpatial/Camera/AVCameraManager.swift` | **PARTIALLY_IMPLEMENTED** | Bounded async queue saving calibrated JPEG/PNG keyframes + timestamps | **Modify** |
| **Capture Package Schema** | `core/schemas/capture_manifest.py`, `camera_poses.py` | **PARTIALLY_IMPLEMENTED** | V3 schema v1: `manifest.json`, `camera_poses.jsonl`, `checksums.sha256` | **Modify / Extend** |
| **Capture Validator** | `ios/VastuSpatial/Camera/VideoValidator.swift`, `IMUValidator.swift` | **PARTIALLY_IMPLEMENTED** | Comprehensive package validator checking schema, monotonicity, pose matrix orthonormality | **Create / Extend** |
| **Pose Refinement** | `core/tracking/` & `workers/stages/stage02_sfm.py` | **IMPLEMENTED** | LightGlue/SuperPoint feature matching with VIO priors & metric scale constraint | **Keep & Wire** |
| **Depth Estimation** | `ml/depth/estimator.py` | **PARTIALLY_IMPLEMENTED** | Depth Anything V2 Indoor Metric + DSINE normal consistency ($\nabla D \cdot \mathbf{n} = 0$) | **Modify** |
| **Structural Geometry** | `core/structure/`, `core/correction/` | **PARTIALLY_IMPLEMENTED** | Multi-plane RANSAC, Manhattan/Atlanta conditional snapping, 90° intersection seams | **Modify** |
| **3D Gaussian Splatting** | `core/representations/` & `scripts/generate_video_twin.py` | **PARTIALLY_IMPLEMENTED** | `gsplat` optimization (15k–30k steps), SPZ compression, held-out evaluation | **Create / Integrate** |
| **Web Viewer** | `src/components/viewer/Spatial3DViewer.tsx` | **IMPLEMENTED** | Three.js scene with FirstPerson WASD + 3DGS rasterizer (`@mkkellogg/gaussian-splats-3d`) | **Modify** |
| **Collision & NavMesh** | `src/components/viewer/roamingController.ts`, `navigation/` | **PARTIALLY_IMPLEMENTED** | Separate collision geometry (`collision.glb`), capsule sliding, and Recast navmesh | **Modify / Extend** |
| **SOP & Floor Guidance** | `core/sop/sop_engine.py`, `voxel_grid.py` | **PARTIALLY_IMPLEMENTED** | Two-phase SOP: Phase 1 perimeter outline recon + Phase 2 targeted infill | **Modify** |
| **On-Device Mobile ML** | `ios/VastuSpatial/Models/MobileDepthSemanticEngine.swift` | **PARTIALLY_IMPLEMENTED** | CoreML ANE model running blur rejection, anti-pivot detection, and baseboard tracking | **Modify** |

---

## 3. Detailed Component Findings

### 3.1 iOS Capture Application (`ios/VastuSpatial`)
- **Current State**:
  - `AVCameraManager.swift` utilizes standard `AVCaptureSession` with `AVCaptureMovieFileOutput` to record an `.mp4`/`.mov` video file.
  - `MotionSensorManager.swift` polls `CMMotionManager` and dumps timestamps, accelerometer, and gyro to a CSV file.
  - `SensorSyncEngine.swift` attempts post-hoc matching of video frames to IMU timestamps within a 20ms window.
- **Architectural Conflicts with v3.0**:
  - v3.0 strictly mandates **ARKit 6-DoF visual-inertial tracking** (`ARSession`) so that camera-to-world transforms ($T_{\text{world\_camera}}$) are natively estimated in real time at capture, eliminating scale drift and SfM initialization failures.
  - No frame-by-frame poses are currently emitted; only bulk video + separate IMU logs.
- **Required Action**:
  - Add `ARSessionManager.swift` implementing `ARSessionDelegate` to log `ARFrame.camera.transform`, `ARFrame.camera.intrinsics`, and frame image buffers with monotonic timestamps ($t_{\text{ns}}$).
  - Implement the `CapturePackageWriter` emitting the standardized directory structure.

### 3.2 Coordinate Conventions & Spatial Math
- **Current State**:
  - Previously, `core/alignment/transform.py` defined Sim(3) transforms, but lacked explicit ARKit-to-OpenCV camera frame conversion matrices.
  - **Resolution**: Implemented `core/coordinates/conventions.py` with rigorous definitions:
    - World: Right-handed, Y-up, meters.
    - Pose contract: $T_{\text{world\_camera}}$ ($P_{\text{world}} = R \cdot P_{\text{cam}} + t$).
    - ARKit: $-Z$ forward, $+Y$ up, $+X$ right.
    - OpenCV: $+Z$ forward, $+Y$ down, $+X$ right.
    - Explicit axis conversion matrix $C_{\text{opencv}\leftarrow\text{arkit}} = \text{diag}(1, -1, -1)$.
    - Tested via `tests/test_coordinate_conventions.py` (6 unit tests, all passing, synthetic reprojection error $< 10^{-4}\text{ px}$, well within the $< 1.0\text{ px}$ tolerance).

### 3.3 Core Schemas & Data Contracts (`core/schemas/`)
- **Current State**:
  - 30 distinct schemas exist. `capture_manifest.py` defines v2.0 with rich validation.
- **Required Extension**:
  - Ensure schema accommodates the v3.0 package structure:
    `capture_<session_id>/manifest.json`, `camera_poses.jsonl`, `camera_intrinsics.json`, and `checksums.sha256`.

### 3.4 Depth & Normal Estimation (`ml/depth/estimator.py`)
- **Current State**:
  - Implements `DepthEstimator` with Depth Anything V2 Metric, ZoeDepth/MiDaS fallback, and photometric analytical fallback.
- **Gap**:
  - Lacks surface normal consistency integration ($\nabla D \cdot \mathbf{n} = 0$).
  - Does not compute cross-view geometric consensus filtering prior to TSDF integration.

### 3.5 Structural Geometry & Meshing (`core/structure/`, `core/correction/`, `workers/stages/stage05_meshing.py`)
- **Current State**:
  - RANSAC plane fitting exists in `core/structure/extractor.py`.
  - TSDF fusion in `core/dense/tsdf_fusion.py` runs with voxel size $3\text{ cm}$ and truncation $9\text{ cm}$.
  - Snapping in `core/correction/snapping.py` applies soft smoothing.
- **Gap**:
  - Does not enforce strict Manhattan/Atlanta orthogonality or sharp analytical 3D plane-plane intersection lines for corners.
  - Furniture points contaminate wall plane boundaries.

### 3.6 Photorealistic 3DGS Pipeline
- **Current State**:
  - 3DGS is referenced in domain enums (`ModelFormat.GAUSSIAN_SPLAT = "3DGS_PLY"`), but `scripts/generate_video_twin.py` primarily outputs textured OBJ/MTL meshes.
- **Gap**:
  - `gsplat` optimization pipeline, held-out evaluation split, and SPZ compression export need dedicated worker integration.

### 3.7 Web Viewer & Navigation (`src/components/viewer/`)
- **Current State**:
  - `Spatial3DViewer.tsx` has OrbitControls, basic FirstPerson WASD controller (`roamingController.ts`), and OBJ/PLY loaders.
- **Gap**:
  - Missing 3D Gaussian Splatting SPZ loader (`@mkkellogg/gaussian-splats-3d` or PlayCanvas engine).
  - Collision geometry is coupled with rendering mesh rather than a simplified, capsule-tested collision hull.

---

## 4. Technical Debt & Risk Inventory

| Risk ID | Category | Description | Severity | Mitigation |
| :--- | :--- | :--- | :--- | :--- |
| **TD-01** | Capture / Pose | Lack of direct ARKit pose logging causes downstream SfM reliance | **HIGH** | Build `ARSessionManager` with pose logging in Sprint 1 |
| **TD-02** | Coordinate Mismatch | Inconsistent camera conventions between iOS, COLMAP, and Three.js | **CRITICAL** | Enforce `core/coordinates/conventions.py` at all boundaries |
| **TD-03** | Model Licensing | Unverified commercial licenses for third-party depth checkpoints | **HIGH** | Complete Spike S3 and audit licenses before production |
| **TD-04** | Geometry Blobs | Soft TSDF truncation blurs 90° corners | **HIGH** | Tighten TSDF truncation and apply hard RANSAC plane snapping |
| **TD-05** | Viewer Coupling | Viewer couples collision directly to visual mesh | **MEDIUM** | Separate `collision.glb` from `scene.spz` |

## Sprint 1 source re-audit — 2026-10-26 (supersedes unsupported claims above)

The earlier audit is retained as history. Its claims of complete compliance, metric
accuracy, prescribed renderer choice, and tested integration are not evidence.
Architecture sections 1–21 were read before this batch. Existing uncommitted changes
(including coordinates/schema, TSDF, tracking, deployment and API edits) are preserved.

- **ARKit: MISSING at inspection.** `ios/VastuSpatial/Views/Capture/CaptureView.swift`
  owns `AVCameraManager`; its movie output cannot produce ARKit poses. Camera
  intrinsics are estimated from FOV and hardcoded 1920×1080 in `AVCameraManager.swift`.
- **Synchronization: PARTIALLY_IMPLEMENTED.** `SensorSyncEngine.swift` fabricates frame
  times from duration/FPS, rather than recording sample timestamps. It cannot establish
  pose/image synchronization. ARKit must provide image, transform and K from one ARFrame.
- **Schema/calibration: PARTIALLY_IMPLEMENTED.** `core/schemas/capture_package_v1.py`
  exists beside video `capture_manifest.py`. Unsupported versions/units were accepted,
  principal-point limits assumed an uncropped central camera, image orientation was
  ambiguous, and package-level association/integrity checks were absent.
- **Coordinates: PARTIALLY_IMPLEMENTED.** `CameraPose` checked determinant but not
  orthogonality or finite translation; shear with determinant one was accepted.
  `core/tracking/fusion.py` duplicates quaternion conversion. No module is deleted.
- **Pose refinement: PARTIALLY_IMPLEMENTED / metric quality UNVERIFIED.**
  `core/tracking/tracker.py` uses OpenCV features/essential matrices, not LightGlue BA.
  `fusion.py` has a default 0.20 m visual step, minimum hybrid step and interpolation.
  These are heuristics, not metric evidence. `stage02_sfm.py` estimates K as 1.2×width.
  `core/dense/consistency.py` and `evidence_fusion.py` consume OpenCV **world-to-camera**
  R,t. Passing raw ARKit camera-to-world would invert orientation and translation.
- **Depth: PARTIALLY_IMPLEMENTED / licensing UNVERIFIED.** `ml/depth/estimator.py`
  attempts network model loads at construction and has analytical fallback. Backend
  labels alone do not prove metric depth. Exact checkpoint revision/license evidence
  is absent. Do not instantiate inference merely to benchmark package validation.
- **Structure: PARTIALLY_IMPLEMENTED.** `core/structure/extractor.py`, `core/correction/`,
  `core/dense/tsdf_fusion.py` have fitting/fusion paths; real measured topology and
  conditional Manhattan/Atlanta compliance remain UNVERIFIED. Never force all corners.
- **3DGS: MISSING in canonical worker path.** Representation enums are not a trainer.
  `workers/pipeline.py` runs mesh/depth stages; no gsplat/SPZ integration was found.
- **Viewer: IMPLEMENTED mesh rendering; Gaussian rendering MISSING.**
  `Spatial3DViewer.tsx` imports Three.js OBJ/PLY loaders; package.json has only Three.js.
  `roamingController.ts` and `navigationEngine.ts` implement movement/routing, but
  capsule collision and reference-device performance remain UNVERIFIED.
- **Semantic inference: PARTIALLY_IMPLEMENTED.** `MobileDepthSemanticEngine.swift`
  advertises ANE activation independently of loading a verified model; boundary
  precision and thermal latency have not been measured.
- **Packaging/security: PARTIALLY_IMPLEMENTED.** Existing `CapturePackage` handles
  video manifests and uses unrestricted `tar.extractall`; keep legacy path separate,
  do not use it for untrusted V1 ingestion. `api/config.py` has a fallback JWT secret.
  These are P5 security gaps, not proof of a deployed exploit.
- **Performance:** `SensorSyncEngine` scans IMU samples per inferred frame; existing
  depth consistency scales across views/pixels. Bounded AR recording and timing
  measurements are required before throughput claims.
- **Duplication/dead code:** video vs keyframe schemas, two reconstruction entry paths
  (`scripts/generate_video_twin.py`, `workers/pipeline.py`), quaternion helpers and
  archive/upgrade directories need ownership review. Unused status is UNVERIFIED;
  no code removed based solely on search.
- **Infrastructure:** API routes in `api/routers/`, storage adapters in `storage/`,
  Docker manifests, `requirements-api.txt`, `backend/workers/requirements.txt`,
  `ios/Package.swift`, Xcode project, React/Vite package and `.github/workflows/ci.yml`
  are retained. CI runs pytest plus frontend build; native field/GPU tests are absent.

Smallest safe sequence: harden existing math/schema → package writer/validator →
validated adapter using explicit OpenCV extrinsics → isolated ARKit capture mode →
synthetic integration tests and documented physical reference protocol. Later phases
remain gated by Sprint 1 review. No renderer/model replacement is justified yet.
