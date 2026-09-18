# VĀSTU / NAMMA SPACE — UPGRADE SPECIFICATION
## STAGE 0: REPOSITORY AUDIT, ARCHITECTURAL RECONCILIATION & BASELINE STABILIZATION

**Document Version:** 1.0.0  
**Status:** APPROVED FOR STAGE 0 EXECUTION  
**Author:** Lead Systems & Spatial Computing Engineer  
**Target System:** VĀSTU / Namma Space Spatial Computing Platform  

---

## 1. Executive Summary & Objective

Stage 0 establishes the verifiable ground truth of the VĀSTU / Namma Space repository prior to implementing any feature modifications or upgrades. 

### Core Goals:
1. **Source of Truth Reconciliation:** Isolate what is actually executed and working from what is merely documented, mocked, stubbed, or dead code.
2. **Infrastructure Defect Remediation:** Resolve container definition gaps, missing cloud storage abstractions, and platform-specific C++ / Python dynamic library collisions.
3. **Execution Path Stabilization:** Establish a verified end-to-end integration path from mobile ingestion to background job processing, spatial asset generation, and web rendering.

---

## 2. Comprehensive Subsystem Audit & Truth Matrix

Every subsystem across the repository has been audited against source code, dependencies, build configurations, and runtime behavior:

| # | Subsystem | Ground-Truth Status | Concrete Evidence / Technical Root Cause |
|---|---|---|---|
| **1** | **Repository Structure** | **IMPLEMENTED** | Multi-target mono-repo containing `backend/` (Go + Python workers), `src/` (Next.js 14), `android/` (Kotlin), `ios/` (Swift), `database/migrations/`, `scripts/`, `docs/`. |
| **2** | **Backend (Go Control Plane)** | **PARTIALLY IMPLEMENTED** | Implemented: Auth, Org, Project, Captures, Uploads, Models, POIs, Nav HTTP REST API via chi in [backend/cmd/server/main.go](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/cmd/server/main.go).<br>**Critical Gap:** [orchestrator_service.go](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/service/orchestrator_service.go), [rescan_service.go](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/service/rescan_service.go), and Asynq/Kafka queues are never instantiated or started in `main.go`. |
| **3** | **Workers (Python / C++)** | **PARTIALLY IMPLEMENTED / BROKEN AT RUNTIME** | Standalone Python engines exist in [backend/workers/](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/workers). Running on macOS ARM64 crashes with `Fatal Python error: Aborted` due to Open3D dynamic linking collision. C++ files (`*.cpp`) exist but are unlinked. No worker container is declared in [docker-compose.yml](file:///Users/kradsagency/Desktop/vastu-namma-space/docker-compose.yml). |
| **4** | **Reconstruction Pipeline** | **PARTIALLY IMPLEMENTED** | Production 25-stage monolithic engine implemented in [scripts/generate_video_twin.py](file:///Users/kradsagency/Desktop/vastu-namma-space/scripts/generate_video_twin.py) (2,264 lines). Produces validated OBJ/PLY digital twin models. Modular workers in `backend/workers/` duplicate this logic and are disconnected from the backend queue. |
| **5** | **Geometry Pipeline** | **IMPLEMENTED** | Point cloud back-projection, spatial hash deduplication, Open3D Poisson surface meshing, RANSAC plane extraction, and UV chart atlas projection are implemented. |
| **6** | **Mobile / Frontend Capture** | **IMPLEMENTED** | iOS ([AVCameraManager.swift](file:///Users/kradsagency/Desktop/vastu-namma-space/ios/VastuSpatial/Camera/AVCameraManager.swift), [MotionSensorManager.swift](file:///Users/kradsagency/Desktop/vastu-namma-space/ios/VastuSpatial/Sensors/MotionSensorManager.swift)) and Android ([CameraCaptureManager.kt](file:///Users/kradsagency/Desktop/vastu-namma-space/android/app/src/main/java/com/vastu/spatial/camera/CameraCaptureManager.kt), [ImuSensorManager.kt](file:///Users/kradsagency/Desktop/vastu-namma-space/android/app/src/main/java/com/vastu/spatial/sensor/ImuSensorManager.kt)) capture 60fps video + 100Hz IMU CSV with monotonic timestamp synchronization. |
| **7** | **Upload Pipeline** | **IMPLEMENTED** | 5MB chunked resumable upload implemented across iOS, Android, and Go backend ([upload_service.go](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/service/upload_service.go)). Reassembles chunks, verifies SHA256, validates magic byte signatures in quarantine, and promotes to disk. |
| **8** | **Database** | **PARTIALLY IMPLEMENTED** | 16 migrations in [database/migrations/](file:///Users/kradsagency/Desktop/vastu-namma-space/database/migrations). PostGIS 3.4 enabled in PostgreSQL container.<br>**Flaws:** Migrations 2-14 and 16 have no rollback `.down.sql` files; Go backend ignores PostGIS `geom` columns (leaves them `NULL`). |
| **9** | **Object Storage** | **MOCKED / BROKEN** | Claimed S3/MinIO cloud storage is absent. No AWS or MinIO SDKs in `backend/go.mod`. Ingestion writes directly to local container filesystem `/app/uploads` and serves via raw HTTP `/uploads/*`. |
| **10** | **Job Orchestration** | **STUB / DISCONNECTED** | Asynq and Kafka code exists in `internal/pkg/queue` and `internal/pkg/events`, but `main.go` never initializes them. Submitting `POST /api/v1/jobs` writes a database row in `queued` status and halts indefinitely. Handlers contain no-op `transition` stub. |
| **11** | **Quality Validation** | **PARTIALLY IMPLEMENTED** | Mobile IMU quality checks (motion blur, overlap) and Python 7-metric quality evaluator ([quality_engine.py](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/workers/quality/quality_engine.py)) exist. `quality_reports` table exists in SQL, but has no Go repository, no API routes, and is not written to by any worker. |
| **12** | **POI System** | **IMPLEMENTED** | [POIService](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/service/poi_service.go), [POIRepo](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/repository/postgres/core_repos.go#L726), domain models, and REST endpoints (POST/GET/PUT/DELETE `/api/v1/pois`) are implemented with full JSON metadata and attachment support. |
| **13** | **Search** | **MOCKED** | Documented as "PostGIS ST_DWithin and semantic vector search". Actual code in [core_repos.go](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/repository/postgres/core_repos.go#L875) runs basic SQL `WHERE title ILIKE $2 OR description ILIKE $2`. No vector embeddings, no PostGIS spatial indexing. |
| **14** | **Navigation** | **IMPLEMENTED** | [NavigationService](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/service/navigation_service.go) implements Dijkstra / A* pathfinding over `nav_nodes` and `nav_edges` with wheelchair accessibility, stairs avoidance, and turn-by-turn instruction generation. (Automated navmesh extraction from 3D mesh is missing; graph is manually seeded). |
| **15** | **Web Viewer** | **MOCKED (Web) / DEMO ONLY (Static)** | [src/app/dashboard/viewer/page.tsx](file:///Users/kradsagency/Desktop/vastu-namma-space/src/app/dashboard/viewer/page.tsx) is a mocked placeholder without WebGL/Three.js. A functional Three.js viewer exists only as an isolated static HTML file at [digital_twin_output/20_viewer/index.html](file:///Users/kradsagency/Desktop/vastu-namma-space/digital_twin_output/20_viewer/index.html). |
| **16** | **AR (Augmented Reality)** | **MISSING** | Claimed AR navigation and AR rescan bounding boxes do not exist. Zero references to ARKit in `ios/`, zero references to ARCore in `android/`, zero references to WebXR in `src/`. |
| **17** | **TTS / SOP** | **PARTIALLY IMPLEMENTED** | SOP is implemented as a 12-step guided scanning checklist in mobile capture screens ([CaptureQualityEngine.swift](file:///Users/kradsagency/Desktop/vastu-namma-space/ios/VastuSpatial/Camera/CaptureQualityEngine.swift#L34), [CaptureQualityEngine.kt](file:///Users/kradsagency/Desktop/vastu-namma-space/android/app/src/main/java/com/vastu/spatial/camera/CaptureQualityEngine.kt#L23)). TTS (Text-to-Speech) audio synthesis is completely MISSING (no `AVSpeechSynthesizer`, no Android `TextToSpeech`). |
| **18** | **Tests** | **PARTIALLY IMPLEMENTED / BROKEN** | Go unit tests in `backend/tests/` exist. Python worker tests abort on macOS ARM64 due to Open3D C++ crash. Mobile iOS unit tests exist. Frontend web tests are completely BROKEN (`npm test` fails because `tests/run_tests.js` is missing). |
| **19** | **Docker / Deployment** | **PARTIALLY IMPLEMENTED** | `docker-compose.yml` runs Postgres, Redis, Kafka, Backend. Critical gaps: (a) No `vastu-worker` container in compose; (b) Go backend container cannot run python workers; (c) No frontend Dockerfile; (d) No CI/CD pipelines (`.github/` missing). |
| **20** | **Observability** | **STUB** | Implements basic HTTP request logging and correlation IDs ([chimw.RequestID](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/cmd/server/main.go#L91)). No Prometheus metrics endpoint, no OpenTelemetry tracing, no Sentry error tracking, no dashboard. |

---

## 3. Critical Architectural Blockers to Address

### Blocker 1: Broken Job Execution Flow
* **Symptom:** Submitting a reconstruction job via `POST /api/v1/jobs` persists a record in PostgreSQL with `stage = "queued"`, but no reconstruction work ever executes.
* **Root Cause:** [backend/cmd/server/main.go](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/cmd/server/main.go) does not initialize `AsynqClient`, `AsynqServer`, `KafkaConsumer`, or `OrchestratorService`. [UploadService.CompleteUpload](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/service/upload_service.go#L196) never emits `TopicValidationCompleted`.
* **Resolution:** Wire the event bus and Asynq client into `main.go`. Emit `TopicValidationCompleted` upon chunk validation approval to automatically trigger worker execution.

### Blocker 2: Worker Runtime & Container Isolation Collision
* **Symptom:** Python workers crash with `Fatal Python error: Aborted` when executed on macOS ARM64 due to C++ symbol collisions between Open3D and PyTorch. Inside Docker, `backend/Dockerfile` is built on Alpine Linux without Python, OpenCV, or Open3D.
* **Root Cause:** In [handlers.go](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/pkg/queue/handlers.go#L64), Go executes `exec.CommandContext("python3", ...)`. This cannot execute inside the Alpine backend container.
* **Resolution:** Declare a dedicated `vastu-worker` container in [docker-compose.yml](file:///Users/kradsagency/Desktop/vastu-namma-space/docker-compose.yml) based on `backend/workers/Dockerfile` (Debian/Ubuntu Python 3.10). Workers must consume tasks directly from Redis via Asynq or Celery, decoupling the Go backend from native execution.

### Blocker 3: Lack of Cloud Object Storage (S3 / MinIO)
* **Symptom:** Large video files (500MB - 2GB) and generated 3D meshes are saved directly to local container filesystem `/app/uploads`.
* **Root Cause:** No S3-compatible client exists in `backend/go.mod`.
* **Resolution:** Add a MinIO service to `docker-compose.yml`, integrate the AWS SDK into `backend/internal/service/upload_service.go`, and generate presigned URLs for client uploads and artifact downloads.

### Blocker 4: Mocked Web 3D Viewer
* **Symptom:** [src/app/dashboard/viewer/page.tsx](file:///Users/kradsagency/Desktop/vastu-namma-space/src/app/dashboard/viewer/page.tsx) displays an empty placeholder graphic with static text.
* **Root Cause:** No 3D canvas or rendering library is integrated into Next.js. The only functioning viewer is an unlinked static HTML file at [digital_twin_output/20_viewer/index.html](file:///Users/kradsagency/Desktop/vastu-namma-space/digital_twin_output/20_viewer/index.html).
* **Resolution:** Install Three.js in `package.json`, port the verified camera and shader controls from `digital_twin_output/20_viewer/index.html` into a React Three.js component, and bind it to active project models.

### Blocker 5: Broken Frontend Test Harness
* **Symptom:** Running `npm test` fails immediately: `MODULE_NOT_FOUND: Cannot find module 'tests/run_tests.js'`.
* **Root Cause:** Missing test framework and test files in frontend.
* **Resolution:** Install Vitest and React Testing Library, configure `vitest.config.ts`, and update `package.json` test scripts.

---

## 4. Duplicate Code & Deprecation Inventory

### Pipelines to Consolidate:
1. **Monolithic Script vs. Modular Workers:**
   * Canonical Engine: [scripts/generate_video_twin.py](file:///Users/kradsagency/Desktop/vastu-namma-space/scripts/generate_video_twin.py) (25 stages, verified outputs).
   * Redundant Code: [backend/workers/](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/workers) modular scripts (`depth_estimator.py`, `sfm_pipeline.py`) duplicate parts of `generate_video_twin.py` with divergent implementations.
   * Action: Consolidate `generate_video_twin.py` stages into cleanly packaged worker modules.

### Dead Code to Prune:
1. **Unlinked C++ Bridges:**
   * `backend/workers/preprocessing/video_preprocessor.cpp`
   * `backend/workers/sfm/sfm_colmap_bridge.cpp`
   * `backend/workers/tracking/camera_tracker.cpp`
   * `backend/workers/pointcloud/dense_pointcloud_fuser.cpp`
   * `backend/workers/meshing/mesh_reconstruction_engine.cpp`
   * `backend/workers/texturing/texture_reconstruction_engine.cpp`
   * `backend/workers/semantics/semantic_fuser.cpp`
   * Action: Remove or compile into true Python C-extensions via `pybind11`.
2. **Obsolete Prototype Scripts:**
   * `scripts/build_diorama_twin.py`
   * `scripts/reconstruct_measured_space.py`
   * `scripts/solve_pose_scale_rgbd.py`
   * `scripts/run_first_scan.py`
   * `scripts/test1_two_view.py` through `scripts/test6_reprojection_validation.py`
   * Action: Move to `archive/` or delete to eliminate maintenance overhead.

---

## 5. Migration & Schema Hardening Plan

1. **Add Missing Rollback Migrations (`.down.sql`):**
   * Create matching `.down.sql` scripts for migrations `000002` through `000014` and `000016`.
2. **Reconcile PostGIS Geometry Columns:**
   * Update [POIRepo.Create](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/repository/postgres/core_repos.go#L730) and `POIRepo.Update` to populate `geom = ST_SetSRID(ST_MakePoint(pos_x, pos_y, pos_z), 0)`.
   * Update [SearchService](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/service/search_service.go) to utilize `ST_3DDWithin` for true spatial radius search.
3. **Harmonize Database Drivers:**
   * Refactor [backend/internal/service/rescan_service.go](file:///Users/kradsagency/Desktop/vastu-namma-space/backend/internal/service/rescan_service.go) to use `*pgxpool.Pool` rather than `*sql.DB`.

---

## 6. Stage 0 Verification & Exit Criteria

Before beginning Stage 1 implementation, the following verifiable conditions must be met:

- [ ] **Docker Compose Verification:**
  - `docker-compose up -d` boots PostgreSQL, Redis, Kafka, MinIO, Go Backend, and Worker without exit code errors.
- [ ] **Object Storage Connectivity:**
  - Ingestion successfully uploads 5MB chunks to MinIO/S3 and returns accessible presigned URLs.
- [ ] **Job Queue End-to-End Handshake:**
  - Upload completion automatically enqueues a reconstruction job in Asynq/Redis.
  - The worker container pulls the job, updates Postgres job stage to `preprocessing`, and logs progress to `job_logs`.
- [ ] **Database Integrity:**
  - All migrations apply cleanly (`golang-migrate up`) and roll back cleanly (`golang-migrate down`).
  - POIs created via `POST /api/v1/pois` have non-null `geom` PostGIS values in PostgreSQL.
- [ ] **Interactive Web Viewer:**
  - Visiting `/dashboard/viewer` loads Three.js, retrieves active model assets, and allows orbit control inspection of the 3D digital twin.
- [ ] **Frontend Test Suite:**
  - `npm test` runs and passes using Vitest.
