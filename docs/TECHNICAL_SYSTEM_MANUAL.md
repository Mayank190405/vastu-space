# VĀSTU Spatial — Complete Technical System Manual

**Audience**: An engineer who has never seen this repo. After this document they should be able to implement, debug, or extend the stack without guessing constants, contracts, or why a hop exists.  
**Companion maps**: [SERVICE_TO_SERVICE_ARCHITECTURE.md](./SERVICE_TO_SERVICE_ARCHITECTURE.md) (who calls whom), [API_INVENTORY.md](./API_INVENTORY.md) (route table), [BACKEND_API_REQUEST_RESPONSE.md](./BACKEND_API_REQUEST_RESPONSE.md) (HTTP examples).  
**Source of numeric truth**: the files cited. If code and this document diverge, **code wins** — update this file.

---

## 0. What the product is, technically

VĀSTU turns a **smartphone RGB video + IMU log** (optionally LiDAR) of an indoor space into a **metric digital twin**: triangle mesh + photographic texture + indoor navigation graph + POIs, quality-gated before publish.

The hard constraints that drive every design choice:

1. **Field networks fail.** Recording cannot depend on a cloud inference API. All live coaching is on-device.
2. **Monocular video has no scale and hates pure rotation.** Pivot-in-place produces bowed walls. Floor/ceiling skip produces holes. Motion blur kills SFM. The phone must refuse bad motion; the worker must not invent geometry to hide holes.
3. **A pretty but wrong twin is worse than a crash.** Quality cannot PASS because a file exists. Hard failures override high scores.
4. **Tenancy is real.** One company’s mesh must never leak into another’s JWT or project list.

Seven reconstruction laws encoded in `scripts/generate_video_twin.py`:

1. No invented geometry (only multi-view evidence).  
2. No fake depth (report uncertainty; no extrusion).  
3. No fixed camera translation (PnP RANSAC from features).  
4. No fake metric calibration (`METRIC_SCALE_UNCERTAIN` if unanchored).  
5. No Poisson-as-repair (meshing only consensus points, support ≥ 2).  
6. No fabricated quality numbers (all from measurements).  
7. No PASS based on file existence.

---

## 1. Runtime topology (ports, processes, disks)

| Process | Bind | Image / entry | Why |
|---|---|---|---|
| `vastu-postgres` | 5432 | `postgis/postgis:16-3.4` | Tenant data + PostGIS `GEOMETRY` for cells/POI radius. DB `vastu_db`, user `vastu_user`. |
| `vastu-migrate` | — | `migrate/migrate` | Applies `database/migrations/*.up.sql` in order `000001`…`000019`. |
| `vastu-redis` | 6379 | `redis:7-alpine` | Asynq queues. Reconstruction must not run inside HTTP. |
| `vastu-minio` | 9000 API, 9001 console | MinIO | S3 for large binaries. |
| `vastu-minio-init` | — | `mc` | Buckets: `vastu-raw-captures`, `vastu-artifacts`, `vastu-exports`. Artifacts bucket is anonymous-download in compose (dev convenience). |
| `vastu-backend` | **8080** | Go `backend/cmd/server/main.go` | Product API for web/iOS/Android. Chi timeout **60 seconds**. |
| `vastu-api` | **8000** | FastAPI `api/main.py` | Spatial engines, 22-stage orchestrator, AR localize, websockets. |
| `vastu-worker` | — | `backend/workers` Python | Invoked by Asynq via `python3 <worker>.py ...`. Compose currently `tail -f /dev/null` until the Asynq server process is attached. |
| `asynq-web` | 8081 | asynqmon | Queue inspection. |
| `vastu-kafka` | 9092 | Kafka KRaft | Optional mirror of in-process EventBus topics. |

**Local files (Go):** `UPLOAD_DIR` default `./uploads` (container `/app/uploads`). Floor plans, cover images, assembled videos. Served at `GET /uploads/{fileID}` **without JWT** (treat URLs as capability-bearing in production).

**Work dirs (workers):** `ReconstructionPayload.work_dir` holds `frames/`, `sfm/`, `depth/`, etc. Twin engine writes `digital_twin_output/` (or job-specific out dir) with 25 numbered folders.

### 1.1 Environment variables

**Go (`backend/internal/config/config.go`):**

| Variable | Default in code | Meaning |
|---|---|---|
| `DATABASE_URL` | local postgres DSN | pgx pool |
| `PORT` | `8080` | listen |
| `NEXT_PUBLIC_APP_URL` | `http://localhost:3000` | invite/OTP links |
| `UPLOAD_DIR` | `./uploads` | disk store |
| `JWT_SECRET` | (must override in prod) | HS256 key |
| `JWT_ACCESS_EXPIRY_MINUTES` | **15** | access TTL |
| `JWT_REFRESH_EXPIRY_DAYS` | **7** | refresh TTL |
| `SMTP_HOST` / `SMTP_PORT` | hostinger / **465** | OTP mail |
| `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM_*` | env | never commit real secrets |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | empty | ID-token audience |
| `APPLE_CLIENT_ID` | empty | Apple token audience |

**Python FastAPI (`api/config.py`):** `PORT` default **8000**, same `JWT_SECRET` / `DATABASE_URL`, plus `REDIS_URL` (`redis://localhost:6379/0`), `S3_ENDPOINT_URL` (`http://localhost:9000`), `S3_BUCKET` (`vastu-artifacts`).

**Worker:** `PYTHONPATH`, `S3_*`, `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (MinIO), `REDIS_URL`, `DATABASE_URL`. Twin engine forces `OMP_NUM_THREADS=1`, `torch.set_num_threads(1)` to avoid Open3D/PyTorch segfaults on macOS; **run reconstruction in the Linux worker container**.

### 1.2 HTTP conventions (Go)

- Base: `http://<host>:8080/api/v1`
- Auth header: `Authorization: Bearer <access_token>`
- Chi middleware: RequestID, RealIP, Logger, Recoverer, Timeout(60s), CORS `*` with methods GET/POST/PUT/PATCH/DELETE/OPTIONS and headers Accept, Authorization, Content-Type, X-CSRF-Token. Credentials allowed.
- Success envelope: `{ "success": true, "message": "...", "data": { ... } }`
- Error envelope: `{ "error": "..." }` with 4xx/5xx
- Health: `GET /health` → `{ status, service: "vastu-backend-control-plane", version }`

**FastAPI** `:8000/api/v1` uses native JSON (not always the Go envelope). OpenAPI at `/docs`. Health: `{ service: "vastu-canonical-control-plane" }`.

Web `src/services/api.ts` unwraps `data.data` when present, retries once on 401 via `POST /auth/token/refresh`.

---

## 2. Coordinate systems, cameras, metric scale

### 2.1 World frame (twin engine)

Documented in stage 06 projection report:

- **Right-handed**
- **+Y is world-up**
- **Floor target Y = 0.00 m**
- Camera model: **pinhole**
- Pixel → camera:  
  `X_c = (u - cx) * Z / fx`  
  `Y_c = (v - cy) * Z / fy`  
  `Z_c = Z`
- Camera → world: `X_w = R^T * (X_c - t)`  
  Helpers: `world_to_camera`, `camera_to_world` in `generate_video_twin.py`.

Default processing resolution: **540×960** (`target_width`, `target_height`). Default keyframes: **16**.

### 2.2 Manifest conventions (`core/domain/enums.py`, `core/schemas/capture_manifest.py`)

| Enum | Values |
|---|---|
| `CoordinateSystem` | `RDF_RIGHT_DOWN_FORWARD` (OpenCV default), `RUB_RIGHT_UP_BACK` (OpenGL), `FLU_FORWARD_LEFT_UP` (ROS) |
| Gravity | `gravity_aligned: true`, vector length must be ~1 or ~9.81 (range 0.8–1.2 or 8.0–11.5) |
| Distortion | `pinhole`, `radtan`, `brown_conrady`, `fisheye` |
| Calibration type | `factory`, `runtime_ar`, `manual_chessboard`, `unverified` |

Intrinsics: `fx, fy, cx, cy`; `cx` must lie in `[0.35W, 0.65W]`, `cy` in `[0.35H, 0.65H]`; `image_width ≥ 640`, `image_height ≥ 480`.

### 2.3 Scale priority (`core/alignment/priorities.py`)

First non-null evidence wins:

| Priority | Class | Typical confidence | Scale formula |
|---|---|---|---|
| 1 | `LiDAREvidence` | 0.98 | `scale_factor` from ToF/ARKit |
| 2 | `PhysicalMeasurementEvidence` | 0.92 | `measured_m / ||B-A||` |
| 3 | `FloorplanDimensionEvidence` | 0.85 | `reference_distance_m / ||featB-featA||` using drawing id |
| 4 | `KnownObjectEvidence` | 0.75 | `standard_dim / observed_dim` (door width, etc.) |
| 5 | `ManualCorrectionEvidence` | 0.60 | operator `manual_scale_factor` |

If none: report **unscaled / METRIC_SCALE_UNCERTAIN**. Do not silently assume 1.0 as truth.

---

## 3. Identity and tenancy

### 3.1 JWT (`backend/internal/domain/token.go`)

Algorithm: **HS256**. Access claims JSON keys:

| Claim | JSON | Meaning |
|---|---|---|
| User UUID | `uid` | subject |
| Email | `email` | |
| Name | `name` | |
| Global role | `grole` | platform-level |
| Org UUID | `oid` | active tenant (optional) |
| Member role | `mrole` | role **inside that org** |
| RegisteredClaims | `exp`, `iat`, … | access TTL 15 min |

Refresh tokens are **hashed in DB** (`refresh_tokens.token_hash`), 7-day expiry, revocable (`revoked_at`). Pair response:

```json
{ "access_token": "...", "refresh_token": "...", "expires_in": 900, "token_type": "Bearer" }
```

`expires_in` is seconds (15×60).

### 3.2 OTP

- 6-digit (generator in `pkg/utils`)
- Purpose includes signup and login (`000013_add_login_to_otp_purpose`)
- Expiry **10 minutes**, single-use (`is_used`)
- SMTP send via `OTPService.GenerateAndSendOTP`

### 3.3 SSO

- `GoogleService.ValidateIDToken`: official `idtoken.Validate` against `GOOGLE_CLIENT_ID` when token has 3 JWT segments.
- `AppleService`: Apple client id audience.
- Why separate services: the app never asserts identity; Go verifies the vendor.

### 3.4 Organizations

Org is the **tenant root**. Projects `org_id` scoped. Join: invite code + token (`GET /organizations/invites/{orgCode}/{inviteToken}`), or employee join + admin approve (`join_requests`). Documents/GST/address live on org, not on user.

---

## 4. Projects, floors, floor plans

### 4.1 Project lifecycle statuses (`backend/internal/domain/project.go`)

`DRAFT` → `SETUP` → `READY FOR CAPTURE` → `CAPTURE IN PROGRESS` → `PROCESSING` → `QUALITY VALIDATION` → `REVIEW REQUIRED` / `RESCAN REQUIRED` → `READY FOR APPROVAL` → `APPROVED` → `PUBLISHED` / `ACTIVE` → `ARCHIVED`. Soft-delete: trash 30 days then permanent.

Typologies: Commercial, Residential, Industrial, Institutional, Healthcare, Education, Hospitality, Retail, Government, Office, Other.

### 4.2 Floors (`project_floors`)

Created in `CreateProjectFull`. Fields used by SOP generation: `name`, `area_value`, `area_unit`, `height_value`. Sequence index for ordering.

### 4.3 Floor plans (`floor_plans`, unique per `floor_id`)

| Column | Role |
|---|---|
| `plan_type` | `UPLOADED` or `DRAWN` |
| `file_url` / `file_id` | PNG/JPG/JPEG/PDF, max **50 MB** multipart |
| `drawing_data` | JSON `{ "objects": [ ... ] }` vector canvas |
| `canvas_width` / `canvas_height` | default 1200×800 |
| `scale_ratio` | drawing units → meters |
| `preview_url` | PNG from `preview_base64` on draw |

APIs (JWT):

- `POST /projects/{projectId}/floors/{floorId}/floor-plan/upload` form field `floor_plan` or `file`
- `POST|PATCH .../floor-plan/draw` body `DrawFloorPlanInput`
- `GET` / `DELETE` same path

**Why:** this is the only cheap metric prior for walls/rooms. Parser target: write graph into `captures.capture_sop` (JSONB from migration 000019). Live recording must **not** re-call a vision API.

Accepted upload extensions: `.png`, `.jpg`, `.jpeg`, `.pdf` only.

---

## 5. Capture: on-device packet and cloud row

### 5.1 Postgres `captures`

Created at session start (`POST /api/v1/captures`). Required: `project_id`, `device_model`, `device_os`. Defaults: `capture_mode=rgb_imu`, `imu_rate_hz=100`, `status=recording`.

Statuses: `recording` → `uploaded` → `validating` → `processing` → `completed` | `failed`.

Modes: `rgb_imu`, `rgb_lidar`, `rescan_targeted`.

Intrinsics JSON: `{ fx, fy, cx, cy, distortion[], width, height }`.

Migration **000019** extra columns: `floor_id`, `assigned_to`, `recon_video_url`, `capture_sop` JSONB, `current_phase` default `ASSIGNED`, `zone_progress` JSONB default `[]`.

### 5.2 On-disk session (iOS `LocalCaptureStorageManager`; Android equivalent)

App Support `captures/{captureId}/`:

| File | Role |
|---|---|
| video (`.mov` / `.mp4`) | RGB evidence |
| IMU file | timed samples |
| `manifest` (JSON) | Contract 1 `CaptureManifest` |
| `metadata.json` | small string map |

Index: `vastu_captures_store.json`. Record fields: paths, `checksumSha256` of video, `fileSizeBytes`, `totalChunks` at 5 MiB, status `pending_upload|uploading|uploaded|failed`, retry count.

Journal/recovery: `CaptureSessionJournal` + `CaptureRecoveryManager` resume after kill.

Battery gate on iOS capture UI: recording discouraged below **80%** unless dev bypass. Why: thermal/throttle → dropped frames → SFM failure.

### 5.3 CaptureManifest v1.0.0 / v2.0.0 (`core/schemas/capture_manifest.py`)

Producer: phone. Consumer: preprocessor + reproducibility.

**Video:** size ≥ 10 KiB, duration **1–1800 s**, frames ≥ 30, fps **15–120**, codec `h264|h265|hevc|prores`, SHA-256 64 hex. Frame count must be within **15%** of `duration * fps`.

**IMU:** size ≥ 512 B, samples ≥ 100, rate **25–1000 Hz**, SHA-256. Optional 4×4 `camera_to_imu_matrix` (identity default). Accel range default 16 g, gyro 2000 dps.

**IMU sample** (`core/schemas/imu_samples.py`): `timestamp_ns > 0`, `accel_m_s2 {x,y,z}`, `gyro_rad_s {x,y,z}`, optional magnetometer µT and gravity.

**Frame timestamps:** `monotonic_timestamp_ns`, optional PTS, exposure, ISO.

**Quality metrics in manifest:** dropped frames, IMU drops, average lux, motion_blur_score 0–1, operator_speed_mps, feature_density_score.

**Coverage:** area m², path length m, AABB, keyframe_count, `loop_closure_detected`.

**Upload status enum:** PENDING, UPLOADING, UPLOADED, VALIDATING, VALIDATED, FAILED, ABORTED.

### 5.4 Zero-cloud recording rule

Allowed before Record: JWT, `GET` project/floor-plan, `POST` capture row.  
Forbidden until Confirm: SOP generation HTTP, `/jobs`, `/quality`, reconstruction, FastAPI orchestrator.  
After Confirm: chunked upload only.

---

## 6. On-device SOP and quality (exact thresholds)

Canonical engine: `core/sop/` mirrored in:

- iOS `CaptureQualityEngine.swift`
- Android `CaptureQualityEngine.kt`

TTS priority enum: CRITICAL=1, WARNING=2, GUIDANCE=3, CONFIRMATION=4. Higher priority preempts.

### 6.1 Eleven stages (`core/sop/stages.py`)

| # | Stage enum | Completion metric | Threshold | Timeout s | Why this stage exists |
|---|---|---|---|---|---|
| 1 | `ROOM_ENTRY` | `baseline_frames_accumulated` | 45 (~1.5 s @ 30 fps) | 15 | Lock tracking before motion |
| 2 | `PERIMETER_COVERAGE` | `perimeter_path_length_m` | 8.0 m | 90 | Translation baseline for depth |
| 3 | `WALL_COVERAGE` | `wall_surface_observed_fraction` | 0.80 | 90 | Vertical planes for architecture |
| 4 | `CORNERS` | `corners_captured_count` | 4 | 60 | Dihedral / 90° corners |
| 5 | `DOORWAY` | `doorway_frames_captured` | 30 | 40 | Portals for nav graph |
| 6 | `WINDOWS` | `windows_frames_captured` | 30 | 45 | Openings; avoid sun glare |
| 7 | `FLOOR` | `floor_surface_observed_fraction` | 0.75 | 60 | Prevents center floor holes |
| 8 | `CEILING` | `ceiling_surface_observed_fraction` | 0.70 | 60 | Lights/beams; upward tilt |
| 9 | `CENTER_TRAVERSAL` | `center_cross_distance_m` | 3.0 m | 45 | Connect opposite walls |
| 10 | `RETURN_LOOP_CLOSURE` | `distance_to_origin_m` | **≤ 0.50 m** | 40 | Close visual loop / reduce drift |
| 11 | `COMPLETION_VERIFICATION` | `overall_spatial_completeness` | 0.85 | 20 | Finish gate |

Guidance strings are the TTS copy. Target: overlay `capture_sop` zone polygons on this sequence (same engine).

### 6.2 Live telemetry (`core/sop/signals.py`)

Snapshot fields: `linear_velocity_mps`, `angular_velocity_radps`, `blur_laplacian_variance`, `motion_blur_score`, `inter_frame_rotation_deg`, `inter_frame_translation_m`, `ambient_lux`, `glare_saturation_fraction`, `tracked_feature_count`, `unobserved_area_fraction`, `tracking_inlier_count`, `reprojection_error_px`, `is_tracking_lost`.

| Signal | Trigger | Threshold | Operator instruction |
|---|---|---|---|
| EXCESSIVE_MOTION | lin vel **> 0.80 m/s** or ang vel **> 1.20 rad/s** | WARNING | Slow down |
| BLUR | Laplacian var **< 100** or motion_blur **> 0.40** | WARNING | Hold steady |
| INSUFFICIENT_OVERLAP | Δrot **> 15°** or Δtrans **> 0.60 m** | WARNING | Move more gradually |
| POOR_LIGHTING | lux **< 30** (glare if fraction **> 0.15**; max lux 2000) | | Add light / avoid glare |
| LOW_FEATURE_DENSITY | features **< 80** | | Aim at textured surfaces |
| INADEQUATE_COVERAGE | unobserved **> 0.30** | | Cover remaining volume |
| TRACKING_DEGRADATION | inliers **< 30** or reproj **> 2.50 px** or `is_tracking_lost` | CRITICAL | Pause, reacquire |

Default “healthy” snapshot in schema: 0.40 m/s, 0.25 rad/s, Laplacian 250, lux 180, 240 features, 150 inliers, 0.85 px reproj.

Pivot-without-walk (product rule, engine + HUD): translation-to-rotation ratio too low → “walk sideways, do not twist in place.” Twin parallax gate later uses **0.10 m** min baseline (stage 01b).

---

## 7. Resumable upload protocol (byte-level)

Chunk size: **5 × 1024 × 1024 = 5,242,880 bytes** (Go default if client omits; iOS/Android same).

Session expiry: **24 hours** (`upload_sessions.expires_at`).

### 7.1 Init — `POST /api/v1/uploads/init`

Body (`InitUploadInput`):

```json
{
  "capture_id": "<uuid optional>",
  "file_name": "capture.mov",
  "file_type": "video",
  "total_size_bytes": 123456789,
  "chunk_size_bytes": 5242880,
  "total_chunks": 24,
  "sha256_checksum": "<64 hex>"
}
```

Aliases accepted: `file_size_bytes` → total size; `checksum_sha256` → sha256.

`file_type` inferred from extension if omitted: video (`mp4|mov|m4v|avi`), `imu` (`.csv`), `manifest` (`.json`), `3d_model` (`.ply|.splat|.glb|.gltf`).

Response session includes `upload_url_template`: `/api/v1/uploads/{sessionId}/chunk/{chunkIndex}`.

### 7.2 Chunk — `POST` or `PUT /uploads/{sessionId}/chunk/{chunkIndex}`

Raw body bytes. Server stores under session dir, records `upload_chunks` unique `(session_id, chunk_index)`, SHA-256 of chunk. Client also stores per-chunk SHA in `LocalChunkState`.

### 7.3 Progress — `GET /uploads/{sessionId}/progress`

`uploaded_chunks`, `missing_chunks[]`, `status`. Client only retries missing indices.

### 7.4 Complete — `POST /uploads/{sessionId}/complete`

Optional `final_checksum_sha256`. Server: assemble → `UploadSecurityValidator` quarantine (MIME/malware) → promote to clean path `/uploads/clean/{basename}` → capture URLs updated → status `completed`.

EventBus: `validation.completed` with `capture_id`, `project_id` → `OrchestratorService.SpawnReconstructionJob`.

Statuses: `in_progress | assembling | completed | aborted | expired`.

Python twin: `core/upload/session_manager.py` can mint **presigned part URLs** against MinIO for the FastAPI plane (`storage/s3_adapter.py` / `local_adapter.py`). Same 5 MB idea; two implementations — product phones use **Go chunk API**.

---

## 8. Domain events

In-process (`backend/internal/pkg/events/event_bus.go`). Kafka producer prefixes `vastu.` when enabled.

| Topic | When | Typical subscriber |
|---|---|---|
| `capture.created` | capture row | analytics |
| `upload.started` | init | |
| `upload.completed` | assemble | |
| `validation.completed` | quarantine pass | **OrchestratorService** |
| `frames.extracted` | preprocess handler | |
| `reconstruction.started` / `.completed` | pipeline | UI |
| `quality.started` / `.failed` | QA | Rescan |
| `rescan.required` | FAIL | mobile cards |
| `model.created` / `.published` | registry | viewer |
| `job.failed` | Asynq exhaust | ops |

History ring: last 1000 events in memory.

---

## 9. Jobs and Asynq

### 9.1 `processing_jobs`

`stage` string, `progress_percentage` 0–100, `priority` 1–10 default **5**, `stage_durations` JSON, `worker_node_id`, error code/message.

Go stages (`domain/jobs.go`): `queued`, `preprocessing`, `tracking`, `sfm_tracking`, `depth_estimation`, `point_cloud`, `meshing`, `texturing`, `semantic_segmentation`, `cell_fusion`, `quality`, `completed`, `failed`.

Python `JobStage` enum is similar plus `navmesh_generation`.

HTTP: `POST /jobs`, `GET /jobs/{id}`, `GET /jobs/project/{projectId}`, `PUT /jobs/{id}/progress` (workers), `POST|GET /jobs/{id}/logs`.

### 9.2 Asynq (`backend/internal/pkg/queue/`)

Queues: `critical` if `priority >= 8`, else `default`; `low` for cleanup.

First task: `vastu:reconstruction:preprocess_video`. TaskID `reconstruct:{jobID}`, Unique **30 min**, Timeout **4 h**, MaxRetry **3**. Subsequent stages Timeout **2 h**, MaxRetry **3**.

Shared payload:

```json
{
  "job_id": "...",
  "project_id": "...",
  "capture_id": "...",
  "video_url": "...",
  "imu_url": "...",
  "lidar_url": "",
  "work_dir": "/scratch/job-...",
  "priority": 5,
  "retry_count": 0
}
```

Handler chain (subprocess → enqueue next):

| Task type | Script | Writes |
|---|---|---|
| preprocess_video | `workers/preprocessing/video_preprocessor.py --video --imu --work-dir` | frames + quality |
| run_sfm | `sfm/sfm_pipeline.py --frames-dir --output-dir` | poses |
| run_depth_estimation | `depth/depth_estimator.py --frames-dir --sfm-dir --output-dir` | depth |
| fuse_point_cloud | `pointcloud/dense_pointcloud_engine.py` | cloud |
| run_mesh_reconstruction | `meshing/mesh_reconstruction_engine.py` | mesh |
| run_texturing | `texturing/texture_reconstruction_engine.py` | atlas |
| run_semantic_segmentation | `semantics/semantic_understanding_engine.py` | labels |
| run_quality_assurance | `quality/quality_engine.py` | scores |
| finalize_model | Go-side register | `spatial_models` + artifacts |

Also: `vastu:notification:send`, `vastu:maintenance:cleanup_expired_uploads`.

**Target production body:** `python3 backend/workers/pipeline/v3_reconstruction_engine.py <video> [out_dir]` → `VastuDigitalTwinPipeline.run()` (25 stages + supervisor). Asynq should eventually call **v3** instead of keeping a third mesher.

FastAPI `POST /api/v1/jobs/orchestrated` runs `EndToEndWorkflowOrchestrator` 22 `WorkflowStage`s (MOBILE_CAPTURE … WEB_VIEWER) for contract tests / progress events 0–100%. In-memory `_WORKFLOW_JOBS`. Failure injection types map onto stages (`core/testing/failure_injector.py`).

---

## 10. 25-stage twin engine (artifacts and gates)

Entry: `VastuDigitalTwinPipeline(video_path, output_dir, target_width=540, target_height=960, num_keyframes=16)`. Device: **CPU** in current script (`torch.device("cpu")`).

Open3D/PyTorch/OpenCV must run in **Linux Docker** (`docs/PROCESSING_PIPELINE_VERIFICATION.md`) — native macOS ARM can segfault.

### 10.1 Directory contract

Every run creates `00_capture` … `24_provenance` plus flattened copies of key JSON at output root (`quality_gate.json`, `camera_poses.json`, …).

### 10.2 Stage catalog

| Stage | Folder | What it computes | Gate / recovery |
|---|---|---|---|
| 00 | `00_capture` | Signal integrity, usable frame % | Low usable % tanks later CAPTURE score |
| 01 | `01_keyframes` | Motion-aware keyframes, blur filter | Sharpest ~16 frames, translation spaced |
| 01b | same | Parallax: rotation vs metric translation | Fail if total baseline **< 0.10 m**; recovery: flag metric uncertainty + planar prior; quality multiplies camera score × **0.85** |
| 02 | `02_calibration` | Pinhole K | fx, fy, cx, cy |
| 04 (runs before 03) | `05_depth` | Neural depth, Canny edges, clutter/opening masks | Per-frame `confidence_ratio` |
| 03 | `03_features`, `04_camera_poses` | Features + **3D–2D PnP RANSAC** poses | Trajectory confidence |
| 05 | `06_depth_alignment` | Temporal scale/shift of depth | |
| 06 | same | Projection equations dump | Always documented |
| 07 | `07_two_view_validation` | Two-view overlap | Need overlap_ratio **≥ 0.40**; else adaptive_relaxation RECOVERED |
| 08 | `08_local_reconstruction` | Incremental chunk pyramid 2,4,8,N | |
| 09 | `09_global_registration` | Multi-view consensus | `consensus_support_ratio`; only support≥2 to mesh |
| 10 | `10_dense_pointcloud` | Dense PLY + metrics | Need **≥ 20 000** points; width_x **> 0.5 m** |
| 11 | `11_architecture` | Planes (walls/floor) | Floor seal prior |
| 12 | `12_openings` | Doors/windows | |
| 13 | `13_normals` | Normal estimation | radius default **0.12 m**, max_nn **50** |
| 14 | `14_mesh` | Mesh; Taubin smooth | default **12** iterations, λ=0.5, μ=−0.53 in one path |
| 15 | `15_mesh_validation` | Non-manifold, bubbles, dihedral | triangles **≥ 15 000**, non-manifold edges **< 200**; 90° corners ±3° |
| 16 | `16_uv` | UV unwrap | |
| 17 | `17_texture` | Multi-view bake OBJ+atlas | `TextureReconstructionEngine` |
| 18 | `18_texture_validation` | Coverage % | **≥ 70%** |
| 19 | `19_mipmaps` | 128/256/512/1024 | Viewer LODs |
| 20 | `20_viewer` | `index.html` | |
| 21 | `21_reprojection` | Render vs RGB | mean pixel RMSE **< 35** PASS/WARNING, gate **< 40** |
| 22 | `22_quality` | Composite | see §11 |
| 23 | `23_recovery` | `recovery_log.json` | every adaptation |
| 24 | `24_provenance` | Inputs, versions, principles flags | audit |

CLI: `python3 scripts/generate_video_twin.py <video> [output_dir]`.

---

## 11. Quality: three stacked evaluators (know all three)

### 11.1 CloudAISupervisor (`generate_video_twin.py`)

Target score **0.98**. Inputs: mesh, point cloud, `planes_data` (`left_wall_plane`, `back_wall_plane` as `[nx,ny,nz,d]`).

**Tin-foil walls:** triangles within **0.045 m** of wall plane, Y **> 0.15 m**, away from other wall **> 0.15 m**. Mean/std of arccos(|n·n_plane|). Defect `CRUMPLED_WALL_FACETING` if jitter **> 0.09 rad** or std **> 0.09**.

**Floor holes:** PCD points with Y **< 0.08**; 16×16 grid; mesh tris with Y in **[-0.02, 0.06]** and ny **> 0.65**. Defect `FLOOR_HOLE_DEFECT` if coverage **< 0.95**.

**Bubbles:** non-floor centroids Y **> 0.06** farther than **0.16 m** from PCD. Defect `FLOATING_BUBBLE_DEFECT` if ratio **> 0.03**.

Score:

```
jitter_penalty = min(0.35, max(0, jitter - 0.03) * 3.5)
hole_penalty   = max(0, 0.98 - floor_coverage) * 1.5
bubble_penalty = min(0.20, max(0, bubble_ratio - 0.01) * 5)
quality        = clip(1 - sum(penalties), 0, 1)
approved       = quality >= 0.98 AND defects empty
```

**Commands** (`MeshHyperparameters` defaults: `linear_fit=True`, `scale=1.10`, `poisson_depth=8`, `normal_radius=0.12`, `normal_max_nn=50`, `taubin_iterations=12`, `solid_floor_seal=True`, `floor_seal_y_max=0.050`, `consensus_distance_thresh=0.15`):

| Defect | Adjustment (capped) |
|---|---|
| crumple | Taubin += 6 (max 24); radius += 0.03 (max 0.18); max_nn += 15 (max 80) |
| floor hole | seal on; `floor_seal_y_max` += 0.015 (max 0.080); consensus += 0.04 (max 0.22) |
| bubbles | scale -= 0.03 (min 1.02); consensus -= 0.02 (min 0.10) |

`core/correction/ArchitecturalGeometryCorrector` is the same idea as reusable library: snap, thickness 0.15 m default, clip, phantom prune, QA report. Min snap confidence **0.60**.

### 11.2 Stage 22 quality_gate (descriptive score)

Category scores (mean = `overall_descriptive_score`):

| Key | Formula / pass |
|---|---|
| CAPTURE | `usable_frame_pct/100`, pass ≥ **0.50** |
| CAMERA | mean trajectory confidence × (1.0 or **0.85** if parallax fail), pass ≥ **0.35** |
| PARALLAX | from 01b |
| DEPTH | mean frame `confidence_ratio`, pass ≥ **0.50** |
| REGISTRATION | `consensus_support_ratio`, pass ≥ **0.35** |
| POINT_CLOUD | `min(1, points/50000)`, pass points ≥ **20000** |
| GEOMETRY | 0.98 if bubbles clipped and corner ~90° else 0.90; pass width_x > **0.5** |
| MESH | `min(1, tris/30000)`, pass tris≥15000 and non-manifold **< 200** |
| TEXTURE | coverage/100, pass ≥ **70%** |
| REPROJECTION | `max(0, 1 - rmse/50)`, pass rmse **< 40** |
| COVERAGE | currently constant **0.95**, pass ≥ **0.70** |

Verdict: all critical gates true → `PASS` unless parallax failed (`WARNING` if others pass else `FAIL`).

### 11.3 CentralQualityEngine (`core/quality/engine.py`)

Weights (sum 1.0): capture **0.15**, pose **0.20**, depth **0.15**, geometry **0.20**, semantics **0.10**, navigation **0.20**.

Capture subscore: blur 0.30 + exposure 0.20 + coverage 0.30 + overlap 0.20. Capture evaluator min coverage fraction **0.80** (hard fail < 0.60).

Pose: reproj mapped `1 - err/3px`; loop closure 1.0 vs 0.5.

Depth: consistency 0.40 + density/1000 pts/m³ 0.30 + (1−holes) 0.30.

**DecisionEngine:** PASS threshold **0.75**, WARNING **0.65**. Any **hard failure → FAIL** even if score is high. Unverified/inferred area **> 5%** blocks clean PASS. Geometric uncertainty **> 20 mm** → targeted rescan. Rescan instruction: 1.5 m standoff, **30 s** arc, **< 15 °/s**, diffuse light, target XYZ.

Postgres `quality_reports`: seven scores (geometry, tracking, coverage, texture, semantic, cell_consistency, navigation) + `low_confidence_cells` JSON + `failure_reasons[]`.

---

## 12. Spatial cells, rescan, models, POI, nav, search, viewer, AR

### 12.1 Cells (`spatial_cells`)

Default cell size **1.00 m**. Integer `cell_x,y,z` unique per (project, model). AABB + optional `GEOMETRY(POLYHEDRALSURFACEZ)`. `observation_views`, `is_low_confidence`, `is_dirty`, `version` for incremental fusion. Why: isolate a closet failure without invalidating the building.

### 12.2 Rescan (`rescan_requests`)

`area_name`, `failure_reason`, `mobile_instruction`, target center XYZ, `target_radius_m` default **2.50**. Status `pending` → assigned → done. APIs: `POST /rescan-requests`, `GET /rescan-requests/project/{id}`, `PATCH .../status`. Worker: `targeted_rescan_manager.py` + `core/versioning/rescan_pipeline.py` + `incremental_update_engine.py`.

Capture mode for the patch: `rescan_targeted`.

### 12.3 Models

`spatial_models`: version semver default `v1.0.0`, bbox JSON, coordinate_frame JSON, vertex/face counts, `is_active_version`. Artifacts: types `point_cloud_ply`, `mesh_gltf`, `mesh_obj`, `gaussian_splat`, `texture_atlas`, `lod0|1|2`; formats ply/gltf/glb/obj/splat/las; SHA-256.

`GET /models/project/{id}/active` is what viewers load.

### 12.4 POIs

`spatial_pois`: title, category (`GENERAL|UTILITY|SAFETY|NAVIGATION|ASSET|STRUCTURAL|HAZARD`), `x,y,z`, floor_level, icon_key default `map-pin`.

### 12.5 Navigation

Tables `navigation_nodes`, `navigation_edges`. Edge types: CORRIDOR, DOORWAY, STAIRS, ELEVATOR, RAMP, OPEN_SPACE. Go `NavigationService` Dijkstra/A* with wheelchair / floor filters. Python `core/navigation/planner.py` for engine-generated graphs from floor planes. Do **not** A* on raw triangles at request time.

### 12.6 Search

Go: POI text + PostGIS `ST_DWithin`. Python: `HybridSpatialSearchEngine`.

### 12.7 Viewer

Bookmarks: camera pose + FOV default **60°** (clamp 10–150) + visible layers. Annotations separate from mesh files. Project `GET /projects/{id}/render` and `/view-link`.

### 12.8 AR (`api/routers/ar.py`, `core/ar/`)

After a twin exists: register `SpatialMarkerAnchor`, `POST /ar/localize` PnP + filter_alpha **0.35**, project nav polyline into camera. This is **not** the capture co-pilot; it is relocalization against the published model.

---

## 13. Web and mobile clients (technical)

| Client | API | Auth storage |
|---|---|---|
| Web Vite | `fetch /api/v1` via proxy | `localStorage` `vastu_access_token` / refresh |
| iOS | `VastuAPIClient` | Keychain account `com.vastu.spatial.jwt_token` |
| Android | Retrofit `VastuApiService` | EncryptedSharedPreferences |

QR: pair phone to web capture studio (`QRScannerView` / `QRScannerScreen` / `MobilePairingModal`).

Guided Capture Studio phases: `WAITING_FOR_MOBILE` → `RECON_PHASE` → `SOP_ANALYSIS` → `SOP_READY` → `ACTIVE_CAPTURE` → `COMPLETE`. Must read **stored** `capture_sop`. `SpatialSOPService` + `VITE_SPATIAL_API_KEY` is a **pre-capture** parser fallback only.

Location wizard: `GET /api/v1/locations/search?q=` and `/locations/reverse` → Nominatim, User-Agent `VastuSpatial/1.0`, timeout **6 s**, limit **7**.

---

## 14. Dual-plane cheat sheet (do not invent a fourth)

| Concern | Source of truth |
|---|---|
| Users, orgs, projects, floor files, captures metadata, chunk upload, job rows, published models, POI/nav CRUD | **Go :8080 + Postgres** |
| Scientific reconstruction, 25-stage artifacts, supervisor loop | **`generate_video_twin.py` in worker** |
| 22-stage contract, AR localize, hybrid search engines, failure injection | **FastAPI :8000 + `core/`** |
| Live SOP/TTS/blur | **Phone CaptureQualityEngine** (`core/sop` is the spec twin) |

If you add a feature, add a row to the call matrix in SERVICE_TO_SERVICE_ARCHITECTURE.md first.

---

## 15. Implementation gaps (so a new engineer does not assume they are done)

1. Floorplan vectorization worker after upload/draw is **specified, not fully wired** to `capture_sop`.  
2. Mobile SOP is **hardcoded 11 steps**, not yet zone polygons from JSON. Blueprint attach on iOS/Android wizard is still **simulated** in places.  
3. No CoreML/TFLite 60 FPS model in apps; quality is classical telemetry. Capture camera is AVFoundation/CameraX, not AR pose-in-plan.  
4. `main.go` constructs JobService; Asynq/Orchestrator must be **process-wired** for auto-start after upload. Worker compose command is idle until Asynq server is the entrypoint.  
5. FastAPI quality/job stores are **in-memory** for some routes; durable cards are Postgres `rescan_requests` / `quality_reports`.  
6. Three pipeline shapes (Asynq workers, v3 25-stage, 22-stage orchestrator) overlap; converge on **v3 + Asynq + Go job rows**.

---

## 16. How to verify you understood this document

You should be able to answer without opening the repo:

- Why HTTP is 60 s but reconstruction is a 4-hour Asynq task.  
- Why floor SOP threshold is 0.75 observed fraction.  
- Why consensus support ≥ 2 is non-negotiable.  
- The exact JWT claim keys (`uid`, `oid`, `grole`, `mrole`).  
- Chunk size 5242880 and session TTL 24 h.  
- Supervisor crumple threshold 0.09 rad and floor grid 16×16.  
- Scale evidence order LiDAR → tape → floorplan → object → manual.  
- Which process owns tenant data vs mesh math vs live coaching.

If any answer requires invention, this manual is incomplete — patch it from the cited file.
