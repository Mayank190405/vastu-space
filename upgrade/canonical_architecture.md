# VĀSTU / NAMMA SPACE — CANONICAL ARCHITECTURE SPECIFICATION
## SYSTEM BLUEPRINT & FORMAL DATA CONTRACTS

**Document Version:** 1.0.0  
**Status:** CANONICAL STANDARD  
**Domain:** Indoor Spatial Computing & Digital Twin Infrastructure  
**Supersedes:** All previous ad-hoc documentation and prototype scripts  

---

## 1. Canonical Architecture Overview

The VĀSTU / Namma Space platform is standardized on a unified, high-performance, and unambiguous architecture. Every component has strict boundaries, a single source of truth, and explicit input/output contracts.

```
+---------------------------------------------------------------------------------------+
|                                    MOBILE CAPTURE LAYER                               |
|  +--------------------------------------------+  +---------------------------------+  |
|  |           iOS Native (Swift 5.9)           |  |      Android Native (Kotlin)    |  |
|  | - AVCameraManager (60fps, 1080p/4K)        |  | - CameraCaptureManager (CameraX)|  |
|  | - MotionSensorManager (100Hz IMU CSV)      |  | - ImuSensorManager (100Hz IMU)  |  |
|  | - SensorSyncEngine (Monotonic Sync)        |  | - SensorSyncEngine (Sync Engine)|  |
|  | - Audio SOP / TTS Guidance Engine          |  | - Audio SOP / TTS Guidance Engine| |
|  | - Local Storage Buffer (Sandbox)           |  | - Local Storage Buffer (Sandbox)|  |
|  | - ResumableUploadManager (5MB Chunked)     |  | - ResumableUploadWorker         |  |
|  +--------------------------------------------+  +---------------------------------+  |
+-------------------------------------------+-------------------------------------------+
                                            | HTTPS / Chunked Upload + JSON Manifest
                                            v
+---------------------------------------------------------------------------------------+
|                                 BACKEND CONTROL PLANE                                 |
|                                 (Python 3.10 / FastAPI)                               |
|                                                                                       |
|  Endpoints:                                                                           |
|  - /api/v1/auth        (JWT, RBAC: Admin, Operator, Viewer)                           |
|  - /api/v1/projects    (Tenancy, Metadata, Timeline, Chat)                           |
|  - /api/v1/captures    (Ingestion Sessions, Manifest Validation)                      |
|  - /api/v1/uploads     (S3 Presigned Multipart Chunk Ingestion)                       |
|  - /api/v1/jobs        (Job Lifecycle & Celery Task Dispatching)                      |
|  - /api/v1/models      (Spatial Models, Versioning & Artifact Lineage)                |
|  - /api/v1/pois        (3D Points of Interest, Attachments)                           |
|  - /api/v1/navigation  (Collision Meshes, NavMesh Graph, A* Routing)                  |
|  - /api/v1/quality     (7-Metric Gate Reports, Automated Rescan Triggers)             |
|  - /api/v1/search      (PostGIS 3D Spatial Radius & Hybrid Semantic Search)           |
+--------------------+-----------------------------+------------------------------------+
                     |                             |
         SQL / PostGIS 3D Queries      Task Queue / Events
                     v                             v
+------------------------------------+  +-----------------------------------------------+
|       PERSISTENCE & STORAGE        |  |              JOB ORCHESTRATION                |
|                                    |  |                                               |
| - PostgreSQL 16 + PostGIS 3.4      |  | - Redis 7 (Task Broker & Result Backend)      |
|   - Native POINTZ, POLYGONZ, GIST  |  | - Celery / ARQ Distributed Task Workers       |
| - S3-Compatible Object Storage     |  | - Task States: PENDING, STARTED, RETRY,       |
|   (MinIO / AWS S3)                 |  |                SUCCESS, FAILURE               |
|   - Buckets: raw-captures,         |  +-----------------------+-----------------------+
|              artifacts, exports    |                          | Dispatches Stage Jobs
+------------------------------------+                          v
+---------------------------------------------------------------------------------------+
|                             SPATIAL PROCESSING WORKERS                                |
|                             (Python 3.10 + C++17 Engines)                             |
|                                                                                       |
|  Stage 01: Preprocessing & Frame Extraction (OpenCV, FFmpeg, IMU Interpolation)       |
|  Stage 02: Structure-from-Motion (COLMAP / SIFT Feature Extraction, Triangulation, BA)|
|  Stage 03: Camera Pose Estimation & 6-DoF Trajectory Tracking                         |
|  Stage 04: Metric Depth Estimation & Multi-View Scale Alignment (Depth Anything / MiDaS)|
|  Stage 05: Dense Point Cloud Fusion & Spatial Hash Filtering (C++ / Open3D)          |
|  Stage 06: Structure-Aware Meshing & Poisson Surface Reconstruction                   |
|  Stage 07: UV Parameterization & Photographic Atlas Baking (TextureEngine)            |
|  Stage 08: 3D Gaussian Splatting Training (Optional Fidelity Layer)                   |
|  Stage 09: Semantic Scene Parsing & Object Bounding Box Fitting                       |
|  Stage 10: NavMesh Extraction (Walkable Surface Analysis & Collision Hull Baking)    |
|  Stage 11: 7-Metric Quality Gate Evaluation & Automated Rescan Request Generation    |
+---------------------------------------------------------------------------------------+
                                            | Generated glTF/GLB + Splats + NavMesh
                                            v
+---------------------------------------------------------------------------------------+
|                                    WEB CLIENT LAYER                                   |
|                                 (Next.js / React 18)                                  |
|                                                                                       |
|  - Three.js WebGL / WebGPU Viewport                                                   |
|  - glTF / GLB Structural Asset Renderer (LOD0 / LOD1 / LOD2 Streaming)                |
|  - 3D Gaussian Splatting Canvas (PLY / WebSplat Viewer)                               |
|  - Interactive 3D POI Pins, Spatial Measurement Tools & Camera Frustum Visualizer    |
|  - Indoor Route Waypoint Visualizer (Turn-by-turn path rendering)                     |
+---------------------------------------------------------------------------------------+
                                            | Optional Spatial Reference
                                            v
+---------------------------------------------------------------------------------------+
|                                  AUGMENTED REALITY (AR)                               |
|                              (Independent Decoupled Layer)                            |
|                                                                                       |
|  - Tier 1 (Baseline): Marker-Based Localization (ArUco / AprilTag / QR Spatial Anchors)|
|  - Tier 2 (Advanced): Markerless Visual-Inertial Relocalization (VPS via SfM Keypoints)|
|  - Real-time step-by-step pedestrian navigation overlay                               |
+---------------------------------------------------------------------------------------+
```

---

## 2. Component Ownership & System Boundaries

| Subsystem | Canonical Technology | Sole Responsibility | Forbidden Responsibilities |
|---|---|---|---|
| **Mobile Capture** | Native iOS (Swift) / Android (Kotlin) | Hardware sensor recording (RGB, IMU), local FIFO buffering, monotonic synchronization, resumable upload, live audio/haptic SOP scanning guidance. | Must **never** execute 3D reconstruction algorithms or heavy CV feature matching. |
| **Backend API** | Python 3.10 / FastAPI | Authentication, RBAC, tenant isolation, project metadata, S3 presigned URL generation, job submission, PostGIS spatial indexing, graph route solving. | Must **never** execute CPU/GPU-intensive reconstruction tasks synchronously within request-response cycles. |
| **Object Storage** | MinIO / AWS S3 API | Immutable storage of raw video captures, sensor CSVs, chunked uploads, and processed 3D model artifacts (`.glb`, `.ply`, `.bin`). | Must **never** serve files from ephemeral local container disk in production. |
| **Orchestration** | Redis 7 + Celery | Task queuing, worker state machine, retries with exponential backoff, worker heartbeats, task progress streaming. | Must **never** persist core business entities or long-term domain state. |
| **Processing Workers** | Python 3.10 + C++17 (Containerized) | SfM, dense depth estimation, point cloud fusion, Poisson meshing, texture atlas baking, semantic labeling, NavMesh generation, quality gating. | Must **never** communicate directly with frontend clients; communicates strictly via Redis, S3, and DB. |
| **Persistence** | PostgreSQL 16 + PostGIS 3.4 | Relational records, 3D geometry storage (`POINTZ`, `POLYGONZ`), spatial spatial queries (`ST_3DDWithin`), model version registry. | Must **never** store multi-megabyte binary geometry files directly inside tables (BLOBs). |
| **Web Frontend** | React / Next.js + Three.js | Spatial viewing, orbit controls, glTF/GLB structural model rendering, Gaussian Splat display, POI pin interaction, navigation display. | Must **never** re-mesh or run heavy geometric calculations on client thread. |
| **AR Layer** | iOS ARKit / Android ARCore (Decoupled) | Camera relocalization against registered physical markers, spatial anchor projection, AR navigation arrows. | Must **never** be a required runtime dependency for viewing digital twins on web. |

---

## 3. The 13 Formal System Contracts

Every contract in the VĀSTU platform is formally specified with typed schema, producer, consumer, version, mathematical validation rules, and failure behaviors.

---

### Contract 1: Capture Manifest
* **Version:** `1.0.0`
* **Producer:** Mobile Capture App (iOS / Android)
* **Consumer:** Backend API (`UploadService`) & Processing Workers (`Stage 01 Preprocessor`)
* **Purpose:** Describes the complete physical capture session, device calibration, and uploaded file manifests.

#### Schema (JSON Schema / Pydantic)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CaptureManifest",
  "type": "object",
  "required": [
    "manifest_version",
    "capture_id",
    "project_id",
    "device_info",
    "camera_calibration",
    "files",
    "metrics",
    "created_at"
  ],
  "properties": {
    "manifest_version": { "type": "string", "enum": ["1.0.0"] },
    "capture_id": { "type": "string", "format": "uuid" },
    "project_id": { "type": "string", "format": "uuid" },
    "device_info": {
      "type": "object",
      "required": ["manufacturer", "model", "os_name", "os_version", "app_version"],
      "properties": {
        "manufacturer": { "type": "string" },
        "model": { "type": "string" },
        "os_name": { "type": "string", "enum": ["iOS", "Android"] },
        "os_version": { "type": "string" },
        "app_version": { "type": "string" }
      }
    },
    "camera_calibration": {
      "type": "object",
      "required": ["fx", "fy", "cx", "cy", "image_width", "image_height", "distortion_model", "distortion_coefficients"],
      "properties": {
        "fx": { "type": "number", "exclusiveMinimum": 0 },
        "fy": { "type": "number", "exclusiveMinimum": 0 },
        "cx": { "type": "number", "exclusiveMinimum": 0 },
        "cy": { "type": "number", "exclusiveMinimum": 0 },
        "image_width": { "type": "integer", "minimum": 640 },
        "image_height": { "type": "integer", "minimum": 480 },
        "distortion_model": { "type": "string", "enum": ["pinhole", "radtan", "brown_conrady"] },
        "distortion_coefficients": {
          "type": "array",
          "items": { "type": "number" },
          "minItems": 4,
          "maxItems": 8
        }
      }
    },
    "files": {
      "type": "object",
      "required": ["video", "imu"],
      "properties": {
        "video": {
          "type": "object",
          "required": ["filename", "size_bytes", "sha256", "duration_sec", "frame_count", "fps", "codec"],
          "properties": {
            "filename": { "type": "string" },
            "size_bytes": { "type": "integer", "minimum": 102400 },
            "sha256": { "type": "string", "pattern": "^[a-fA-F0-9]{64}$" },
            "duration_sec": { "type": "number", "minimum": 3.0, "maximum": 1800.0 },
            "frame_count": { "type": "integer", "minimum": 90 },
            "fps": { "type": "number", "minimum": 24.0, "maximum": 120.0 },
            "codec": { "type": "string", "enum": ["h264", "h265", "hevc"] }
          }
        },
        "imu": {
          "type": "object",
          "required": ["filename", "size_bytes", "sha256", "sample_count", "sampling_rate_hz"],
          "properties": {
            "filename": { "type": "string" },
            "size_bytes": { "type": "integer", "minimum": 1024 },
            "sha256": { "type": "string", "pattern": "^[a-fA-F0-9]{64}$" },
            "sample_count": { "type": "integer", "minimum": 300 },
            "sampling_rate_hz": { "type": "number", "minimum": 50.0, "maximum": 500.0 }
          }
        }
      }
    },
    "metrics": {
      "type": "object",
      "required": ["dropped_frames", "imu_packet_drops", "average_lux"],
      "properties": {
        "dropped_frames": { "type": "integer", "minimum": 0 },
        "imu_packet_drops": { "type": "integer", "minimum": 0 },
        "average_lux": { "type": "number", "minimum": 0 }
      }
    },
    "created_at": { "type": "string", "format": "date-time" }
  }
}
```

* **Validation Rules:**
  1. `video.duration_sec` must be $\ge 3.0$ seconds.
  2. `video.frame_count` must equal $\approx \text{duration\_sec} \times \text{fps} \pm 5\%$.
  3. `imu.sample_count` must be $\ge \text{duration\_sec} \times 50.0$.
  4. Principal points $(c_x, c_y)$ must fall within $[0.4 \times W, 0.6 \times W]$ and $[0.4 \times H, 0.6 \times H]$.
* **Failure Behavior:** Ingestion rejects payload immediately with HTTP `422 Unprocessable Entity`; session is tagged `REJECTED_INVALID_MANIFEST` in database; quarantine files are scheduled for automatic purge after 2 hours.

---

### Contract 2: Frame Metadata
* **Version:** `1.0.0`
* **Producer:** Mobile Capture App / Stage 01 Video Preprocessor
* **Consumer:** Stage 02 SfM Pipeline & Stage 03 Camera Tracker
* **Purpose:** Per-frame exposure, timestamp, and sharpness metrics.

#### Schema
```json
{
  "frame_index": 0,
  "timestamp_ns": 1725619200123456789,
  "exposure_time_sec": 0.008333,
  "iso": 100,
  "focal_length_px": 1420.5,
  "laplacian_blur_score": 184.2,
  "is_keyframe": true,
  "is_blurry": false,
  "is_underexposed": false
}
```

* **Validation Rules:**
  1. `timestamp_ns` must be strictly monotonically increasing ($t_i > t_{i-1}$).
  2. `exposure_time_sec` must be $> 0$ and $< 0.10$ (prevent extreme motion blur).
  3. `laplacian_blur_score` $< 50.0$ forces `is_blurry = true`.
* **Failure Behavior:** Blurry frames are excluded from SfM feature extraction and keyframe selection; if $> 40\%$ of all frames are blurry, Stage 01 triggers an early pipeline failure with code `ERR_CAPTURE_EXCESSIVE_BLUR`.

---

### Contract 3: IMU Samples
* **Version:** `1.0.0`
* **Producer:** Mobile Sensor Manager (CoreMotion / Android Sensor API)
* **Consumer:** Stage 01 Preprocessor (Monotonic Interpolation) & Stage 03 Camera Tracker (VIO Priors)
* **Purpose:** High-frequency inertial measurement samples formatted as continuous time-series.

#### Schema
```json
{
  "timestamp_ns": 1725619200100000000,
  "accel_m_s2": { "x": 0.042, "y": 9.806, "z": 0.112 },
  "gyro_rad_s": { "x": 0.0012, "y": -0.0045, "z": 0.0008 },
  "magnetic_field_ut": { "x": 18.2, "y": -5.1, "z": 42.0 },
  "gravity_vector": { "x": 0.0, "y": -1.0, "z": 0.0 }
}
```

* **Validation Rules:**
  1. Sampling frequency jitter must not exceed $\pm 20\%$ of expected interval (e.g. $10\text{ms} \pm 2\text{ms}$ for 100Hz).
  2. Stationary norm of `accel_m_s2` must be within $[9.0, 10.6]\,\text{m/s}^2$.
  3. Maximum angular velocity must not exceed $12.0\,\text{rad/s}$ (sensor saturation protection).
* **Failure Behavior:** Dropped samples are linearly interpolated up to a maximum gap of $50\text{ms}$. Gaps $> 50\text{ms}$ flag an `IMU_TRACKING_DISCONTINUITY` warning; if total dropped duration $> 5\%$, the session degrades to visual-only SfM.

---

### Contract 4: Camera Poses
* **Version:** `1.0.0`
* **Producer:** Stage 02 SfM Pipeline / Stage 03 Camera Tracker
* **Consumer:** Stage 04 Depth Estimator, Stage 07 Texture Engine, Web Viewer (Frustum visualization)
* **Purpose:** 6-DoF metric camera trajectory extrinsics for all reconstructed keyframes.

#### Schema
```json
{
  "camera_model": "PINHOLE",
  "intrinsics": [1420.5, 1420.5, 960.0, 540.0],
  "trajectory": [
    {
      "frame_index": 12,
      "timestamp_ns": 1725619200400000000,
      "rotation_matrix": [
        [0.9998, -0.0124,  0.0152],
        [0.0122,  0.9998,  0.0118],
        [-0.0154, -0.0116, 0.9998]
      ],
      "translation_vector_m": [-0.124, 0.045, 1.205],
      "quaternion_xyzw": [-0.0058, 0.0076, 0.0061, 0.9999],
      "camera_center_m": [0.105, -0.032, -1.206],
      "reprojection_error_px": 0.82,
      "inlier_points_count": 642
    }
  ]
}
```

* **Validation Rules:**
  1. $R \in SO(3)$: $\det(R) = 1.0 \pm 10^{-4}$ and $R^T R = I_{3 \times 3}$.
  2. Norm of quaternion $\|q\| = 1.0 \pm 10^{-4}$.
  3. Mean reprojection error across all registered frames must be $< 1.5\,\text{pixels}$.
  4. Minimum registered frame ratio must be $\ge 70\%$ of candidate keyframes.
* **Failure Behavior:** If registered frame count $< 70\%$, Stage 02 triggers bundle adjustment recovery mode. If unrecoverable, job fails with `ERR_SFM_TRACKING_LOST`.

---

### Contract 5: Reconstruction Artifact
* **Version:** `1.0.0`
* **Producer:** Processing Worker Pipeline (All Stages)
* **Consumer:** Backend API (`ModelService`) & Storage Manager (`S3`)
* **Purpose:** Immutable asset manifest registering all physical model outputs, formats, and checksums.

#### Schema
```json
{
  "artifact_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "job_id": "4a2c0f20-1111-4444-8888-abcdefabcdef",
  "project_id": "7b8c9d0e-2222-5555-9999-1234567890ab",
  "model_format": "glTF_2.0",
  "lod_level": "LOD0",
  "s3_bucket": "vastu-artifacts",
  "s3_key": "projects/7b8c9d0e/models/model_lod0.glb",
  "file_size_bytes": 14582910,
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "stats": {
    "vertex_count": 182400,
    "triangle_count": 364200,
    "texture_width": 2048,
    "texture_height": 2048,
    "bounding_box_min": [-4.52, 0.00, -6.12],
    "bounding_box_max": [5.18, 3.10, 4.88]
  },
  "created_at": "2026-09-06T15:00:00Z"
}
```

* **Validation Rules:**
  1. `file_size_bytes` must exactly match the object size in S3.
  2. `triangle_count` must be $> 10,000$ for LOD0.
  3. Bounding box coordinates must satisfy $\min < \max$ in all three axes.
* **Failure Behavior:** If sha256 or byte count mismatch S3, the artifact is marked `CORRUPT` in `model_artifacts` table and client downloads are blocked.

---

### Contract 6: Spatial Cell
* **Version:** `1.0.0`
* **Producer:** Stage 05 Point Cloud Engine & Spatial Cell System
* **Consumer:** Incremental Update Worker, Global Fusion Engine, Rescan Manager
* **Purpose:** Metric 3D cellular unit (standard $1.0\text{m}^3$ voxel) partitioning continuous indoor space.

#### Schema
```json
{
  "cell_id": "cell_004_-002_001",
  "model_id": "4a2c0f20-1111-4444-8888-abcdefabcdef",
  "coordinates": { "cx": 4, "cy": -2, "cz": 1 },
  "cell_size_m": 1.0,
  "bounds": {
    "min_xyz": [4.0, -2.0, 1.0],
    "max_xyz": [5.0, -1.0, 2.0],
    "center_xyz": [4.5, -1.5, 1.5]
  },
  "quality_score": 0.88,
  "is_low_confidence": false,
  "density_points_per_m3": 1420,
  "triangle_count": 284,
  "semantic_object_ids": ["door_entry_01"],
  "nav_node_ids": ["nav_node_104"],
  "version": 1,
  "is_dirty": false
}
```

* **Validation Rules:**
  1. $c_x \times \text{cell\_size\_m} = \min_x$, etc.
  2. `quality_score` must be normalized within $[0.0, 1.0]$.
  3. Cells with `quality_score` $< 0.60$ must have `is_low_confidence = true`.
* **Failure Behavior:** Degraded cells are appended to the low-confidence index and trigger targeted rescan candidate generation.

---

### Contract 7: Structural Geometry
* **Version:** `1.0.0`
* **Producer:** Stage 06 Structure-Aware Reconstruction Engine
* **Consumer:** NavMesh Generator, Web Viewer, CAD / BIM Export
* **Purpose:** Mathematically verified architectural structural planes (walls, floors, ceilings).

#### Schema
```json
{
  "structure_id": "wall_north_01",
  "plane_type": "WALL",
  "plane_equation": { "a": 0.0, "b": 1.0, "c": 0.0, "d": -2.85 },
  "normal_vector": [0.0, 1.0, 0.0],
  "inlier_points_count": 14280,
  "surface_area_m2": 18.52,
  "corners_3d": [
    [-3.20, 0.00, 2.85],
    [3.20, 0.00, 2.85],
    [3.20, 2.90, 2.85],
    [-3.20, 2.90, 2.85]
  ],
  "openings": [
    {
      "opening_type": "DOOR",
      "width_m": 0.92,
      "height_m": 2.10,
      "center_3d": [0.45, 1.05, 2.85]
    }
  ]
}
```

* **Validation Rules:**
  1. Plane normal $\|(a, b, c)\| = 1.0 \pm 10^{-4}$.
  2. For `FLOOR`, normal must be parallel to gravity vector within $5^\circ$ ($y \approx 1.0$ or $z \approx 1.0$ depending on up-axis).
  3. For `WALL`, normal must be perpendicular to floor plane within $90^\circ \pm 5^\circ$.
* **Failure Behavior:** Misaligned planes are discarded or merged back into the raw non-structural mesh.

---

### Contract 8: Semantic Object
* **Version:** `1.0.0`
* **Producer:** Stage 09 Semantic Understanding Engine
* **Consumer:** Search Service, POI Auto-Generator, Spatial Query API
* **Purpose:** Reconstructed physical indoor objects with 3D oriented bounding boxes (OBB) and classifications.

#### Schema
```json
{
  "object_id": "sem_obj_fire_ext_01",
  "class_name": "fire_extinguisher",
  "category": "SAFETY",
  "confidence": 0.94,
  "oriented_bounding_box": {
    "center": [1.45, 1.20, -3.10],
    "extent_dx_dy_dz": [0.25, 0.65, 0.25],
    "rotation_quaternion": [0.0, 0.0, 0.0, 1.0]
  },
  "associated_cell_ids": ["cell_001_001_-003"],
  "parent_surface_id": "wall_north_01"
}
```

* **Validation Rules:**
  1. `confidence` must be within $[0.50, 1.00]$.
  2. `extent_dx_dy_dz` elements must all be $> 0.01\,\text{m}$.
  3. Object center must physically reside inside the spatial envelope of `associated_cell_ids`.
* **Failure Behavior:** Detections with confidence $< 0.50$ are discarded; detections violating geometric bounding envelope are marked `UNVERIFIED`.

---

### Contract 9: Point of Interest (POI)
* **Version:** `1.0.0`
* **Producer:** User via Web UI / Mobile App or Auto-Promoted from Semantic Object
* **Consumer:** Web Viewer, Search Engine, Navigation Routing
* **Purpose:** User-facing interactive pin anchored in 3D metric space with associated metadata.

#### Schema
```json
{
  "poi_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "project_id": "7b8c9d0e-2222-5555-9999-1234567890ab",
  "level_id": "11111111-2222-3333-4444-555555555555",
  "title": "Main Electrical Breaker Panel",
  "description": "400A main service panel. Key required for access.",
  "category": "UTILITY",
  "coordinates_m": { "x": 3.42, "y": 1.45, "z": -2.10 },
  "surface_normal": { "x": -1.0, "y": 0.0, "z": 0.0 },
  "camera_viewpoint": {
    "position": [4.50, 1.50, -2.10],
    "look_at": [3.42, 1.45, -2.10]
  },
  "tags": ["electrical", "power", "emergency", "maintenance"],
  "attachments": [
    {
      "filename": "breaker_schematic.pdf",
      "s3_key": "projects/7b8c9d0e/attachments/schematic.pdf"
    }
  ]
}
```

* **Validation Rules:**
  1. `title` must not be empty and $\le 255$ characters.
  2. Coordinates must resolve within project bounding box.
  3. Corresponding PostGIS `geom` column must be set to `ST_SetSRID(ST_MakePoint(x, y, z), 0)`.
* **Failure Behavior:** API rejects invalid coordinate positions outside the project boundaries with `400 Bad Request`.

---

### Contract 10: Navigation Graph
* **Version:** `1.0.0`
* **Producer:** Stage 10 NavMesh Generator / Backend Navigation Service
* **Consumer:** Backend Routing Engine (`NavigationService.CalculateRoute`) & Web/AR Nav Viewers
* **Purpose:** Topological graph representation of indoor walkable paths, turn points, and barriers.

#### Schema
```json
{
  "project_id": "7b8c9d0e-2222-5555-9999-1234567890ab",
  "nodes": [
    {
      "id": "node_001",
      "position": [0.0, 0.05, 0.0],
      "is_wheelchair_accessible": true,
      "floor_level": 1,
      "connected_edge_ids": ["edge_001_002"]
    },
    {
      "id": "node_002",
      "position": [3.5, 0.05, 0.0],
      "is_wheelchair_accessible": true,
      "floor_level": 1,
      "connected_edge_ids": ["edge_001_002"]
    }
  ],
  "edges": [
    {
      "id": "edge_001_002",
      "from_node": "node_001",
      "to_node": "node_002",
      "distance_meters": 3.50,
      "edge_type": "CORRIDOR",
      "is_wheelchair_accessible": true,
      "clearance_width_meters": 1.40,
      "slope_degrees": 0.5
    }
  ]
}
```

* **Validation Rules:**
  1. All edge node references (`from_node`, `to_node`) must exist in the node set.
  2. `distance_meters` must match the 3D Euclidean distance between nodes $\pm 2\%$.
  3. Wheelchair accessibility requires: `slope_degrees` $\le 4.76^\circ$ (1:12 ADA ramp limit) and `clearance_width_meters` $\ge 0.90\,\text{m}$.
  4. Graph must not have disconnected singleton islands unless demarcated by floors.
* **Failure Behavior:** Validation flags disconnected nodes; pathfinding excludes broken edges and falls back to nearest traversable waypoint.

---

### Contract 11: Quality Report
* **Version:** `1.0.0`
* **Producer:** Stage 11 Quality Engine
* **Consumer:** Orchestrator Service, Rescan Manager, Project Dashboard
* **Purpose:** Authoritative 7-score geometric and optical validation verdict.

#### Schema
```json
{
  "report_id": "d3b07384-d113-4a88-8255-abcdef123456",
  "job_id": "4a2c0f20-1111-4444-8888-abcdefabcdef",
  "project_id": "7b8c9d0e-2222-5555-9999-1234567890ab",
  "verdict": "PASS",
  "scores": {
    "overall": 0.84,
    "geometry_watertightness": 0.88,
    "tracking_vio_drift": 0.92,
    "spatial_coverage": 0.81,
    "texture_sharpness": 0.79,
    "semantic_consistency": 0.85,
    "cell_continuity": 0.82,
    "navigation_connectivity": 1.00
  },
  "low_confidence_cells": ["cell_004_-002_001"],
  "failure_reasons": [],
  "recommended_actions": ["Area cell_004_-002_001 has minor texture blur, non-critical."]
}
```

* **Validation Rules:**
  1. `overall` score is the weighted composite of the 7 sub-scores.
  2. `verdict` determination:
     * `PASS`: All scores $\ge 0.70$.
     * `WARNING`: Non-critical score between $0.55$ and $0.69$.
     * `FAIL`: Critical score $< 0.55$ or `navigation_connectivity` $< 1.00$.
* **Failure Behavior:** If `verdict == "FAIL"`, the job does **not** promote the model to active project LOD; automatically spawns a `RescanRequest`.

---

### Contract 12: Rescan Request
* **Version:** `1.0.0`
* **Producer:** Quality Engine (Automated) or Project Lead (Manual via Dashboard)
* **Consumer:** Backend API (`RescanService`) & Mobile Capture App (Guided Retake Screen)
* **Purpose:** Metric bounding box guidance and waypoint instructions directing the mobile operator to patch deficient spatial cells.

#### Schema
```json
{
  "request_id": "rescan_098234",
  "project_id": "7b8c9d0e-2222-5555-9999-1234567890ab",
  "quality_report_id": "d3b07384-d113-4a88-8255-abcdef123456",
  "target_cells": ["cell_004_-002_001", "cell_004_-002_002"],
  "reason": "Insufficient point density and severe motion blur detected on north-east cabinet corner",
  "target_bounding_box": {
    "min_xyz": [4.0, -2.0, 1.0],
    "max_xyz": [5.0, 0.0, 2.0],
    "center_xyz": [4.5, -1.0, 1.5]
  },
  "operator_guidance": {
    "audio_tts_prompt": "Targeted rescan required for north-east cabinet. Stand 1.5 meters away and slowly orbit clockwise.",
    "haptic_cue": "DOUBLE_VIBRATION",
    "recommended_camera_distance_m": 1.5,
    "recommended_orbit_waypoints": [
      [4.5, -1.0, 3.0],
      [6.0, -1.0, 1.5],
      [4.5, -1.0, 0.0],
      [3.0, -1.0, 1.5]
    ]
  },
  "status": "PENDING",
  "created_at": "2026-09-06T15:15:00Z"
}
```

* **Validation Rules:**
  1. `target_cells` must contain at least 1 valid cell ID.
  2. Waypoints must form a convex circular orbit enclosing `center_xyz`.
* **Failure Behavior:** When fetched by the mobile client, the capture screen switches directly into "Targeted Patch Mode", restricting recording to the target bounding volume.

---

### Contract 13: Model Version
* **Version:** `1.0.0`
* **Producer:** Backend Model Service (`ModelService.PromoteModel`)
* **Consumer:** Client Web Viewer, Mobile Apps, Export Pipeline
* **Purpose:** Semantic versioning, lineage tracking, and immutable historical rollback for digital twins.

#### Schema
```json
{
  "model_version_id": "v1.2.0",
  "project_id": "7b8c9d0e-2222-5555-9999-1234567890ab",
  "parent_version_id": "v1.1.0",
  "semver": "1.2.0",
  "is_active_production": true,
  "change_type": "INCREMENTAL_RESCAN_PATCH",
  "summary_of_changes": "Fused rescan patch rescan_098234 into north-east cabinet area; resolved 2 low confidence cells.",
  "quality_report_id": "d3b07384-d113-4a88-8255-abcdef123456",
  "artifacts": {
    "lod0_glb_s3_key": "projects/7b8c9d0e/models/v1.2.0/model_lod0.glb",
    "lod1_glb_s3_key": "projects/7b8c9d0e/models/v1.2.0/model_lod1.glb",
    "lod2_glb_s3_key": "projects/7b8c9d0e/models/v1.2.0/model_lod2.glb",
    "splat_ply_s3_key": "projects/7b8c9d0e/models/v1.2.0/splat.ply",
    "navmesh_json_s3_key": "projects/7b8c9d0e/models/v1.2.0/navmesh.json"
  },
  "created_at": "2026-09-06T15:30:00Z"
}
```

* **Validation Rules:**
  1. `semver` must follow strict Semantic Versioning (`MAJOR.MINOR.PATCH`).
  2. Only one model version can have `is_active_production = true` per project at any given time.
  3. Artifacts must all resolve to verified S3 keys.
* **Failure Behavior:** If newly promoted model fails client healthchecks, rollback to `parent_version_id` is executed via atomic database pointer update in $< 100\text{ms}$.

---

## 4. Acceptance Criteria & Architecture Invariants

1. **Zero Ambiguous Ownership:**
   * Mobile captures and streams raw files.
   * FastAPI backend coordinates business logic, authentication, and database state.
   * Celery workers execute all CV/ML pipelines inside isolated Linux containers.
   * React Three.js renders verified glTF and Gaussian Splat assets.
2. **Strict Storage Decoupling:**
   * All binary assets transit strictly through S3/MinIO via presigned URLs. No application node or worker relies on shared local disks.
3. **No Unvalidated Ingestion:**
   * Every upload must satisfy Contract 1 (`CaptureManifest`) and pass magic-byte quarantine before task scheduling.
4. **Deterministic Version Lineage:**
   * Digital twins are never overwritten in-place; all updates produce immutable, versioned model releases according to Contract 13.
