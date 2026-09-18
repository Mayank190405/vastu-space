# VĀSTU / Namma Space

> **Spatial Intelligence Platform**: End-to-end 3D indoor reconstruction, structure-aware digital twins, metric indoor navigation, and augmented reality guidance.

---

## 🏛️ System Architecture

VĀSTU is built with a decoupled canonical architecture separating the API control plane, asynchronous workers, pure geometry algorithms, storage adapters, and client viewers.

```
┌─────────────────────────────────────────────────────────────┐
│                 Mobile Capture (iOS / Android)              │
│       RGB Video + 6-DoF IMU + Sparse LiDAR + SOP Guidance   │
└──────────────────────────────┬──────────────────────────────┘
                               │ Contract 1 (CaptureManifest v2.0)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Control Plane (api/)                │
│    Session Ingestion · Job Queue · Quality Verification     │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │ Presigned URLs
  Contract 1-3 │                              ▼
               │                   ┌──────────────────────────┐
               │                   │  S3 / MinIO Storage      │
               │                   │  (storage/adapter)       │
               │                   └──────────┬───────────────┘
               ▼                              │
┌──────────────────────────────┐              │ PLY / GLB / SPLAT
│ 9-Stage Worker Pipeline      │              │
│ (workers/stages/)            │              ▼
│  01. Preprocessing           │   ┌──────────────────────────┐
│  02. Structure-from-Motion   │   │  Three.js Web Viewer     │
│  03. Dense Depth Estimation  │   │  (src/components/viewer) │
│  04. Point Cloud Generation  │   └──────────────────────────┘
│  05. Surface Meshing         │
│  06. Texture Mapping         │              ▲
│  07. Semantics & OBBs        │              │ Navigation Graph
│  08. NavMesh & Accessibility │              │ & Turn Guidance
│  09. Quality Assurance       │              │
└──────────────┬───────────────┘   ┌──────────┴───────────────┐
               │                   │  Indoor A* Router        │
               │ Contracts 4-13    │  Wheelchair Slopes ≤4.76°│
               ▼                   │  (navigation/)           │
┌──────────────────────────────┐   └──────────────────────────┘
│  PostgreSQL 16 + PostGIS 3.4 │
│  (database/migrations)       │
└──────────────────────────────┘
```

---

## 📂 Repository Layout

```
vastu-namma-space/
├── api/                    # FastAPI control plane (captures, jobs, models, routing, quality)
├── core/                   # Core business logic and shared domain
│   ├── domain/             # Authoritative enums (JobStage, QualityVerdict, PlaneType, etc.)
│   ├── schemas/            # Formal Pydantic v2 schemas for all 13 canonical contracts + upload & preprocessing
│   ├── capture/            # Mobile capture engine (lifecycle, ring buffer, session journal, recovery, queue)
│   ├── sop/                # Event-driven capture SOP & prioritized TTS instruction engine
│   ├── upload/             # Resumable multipart upload engine (zero-proxy direct-to-storage, retry, client)
│   ├── preprocessing/      # Frame extraction, quality analysis, duplicate suppression, adaptive keyframes
│   ├── tracking/           # Hierarchical camera tracking (VIO + visual odometry + SfM + anomaly detection)
│   ├── dense/              # Multi-view depth consistency, evidence point cloud fusion, defect detection
│   ├── spatial/            # Spatial-cell decomposition, halo margins, independent cell lifecycle & fusion
│   ├── structure/          # Architectural structure extraction (normals, planes, boundaries, 90° priors, plane graph)
│   ├── correction/         # Geometry correction (controlled snapping, thickness, clipping, phantom pruning, 7 QA audits)
│   ├── semantics/          # Independent semantic reconstruction (10-class taxonomy, rooms, OBBs, ground truth policy)
│   ├── alignment/          # Metric coordinate alignment (canonical Sim(3), 5-tier evidence priority, publishing gate)
│   ├── representations/    # Tri-representation separation (Visual, Structural, Collision bundles and decoupled runtime)
│   ├── quality/            # Central quality engine (6-subsystem audit, spatial confidence map, explanatory decision matrix)
│   ├── validation/         # 6-stage capture integrity validation engine
│   └── packaging/          # Offline self-contained reproducibility engine
├── storage/                # Pluggable StorageAdapter (S3 / MinIO & Local filesystem with multipart support)
│   └── naming.py           # Deterministic artifact naming scheme (CaptureArtifactNaming)
├── workers/                # Pipeline orchestration and BaseWorker standard lifecycle
│   └── stages/             # Stages 01 to 09 (Preprocessing through Quality Assurance)
├── geometry/               # Pure mathematics & computational geometry
│   ├── planes.py           # RANSAC plane fitting and dihedral angle computation
│   ├── spatial_hash.py     # O(1) voxel deduplication and uniform centroid downsampling
│   ├── normals.py          # Covariance PCA normal estimation and camera orientation
│   └── mesh_repair.py      # Manifold topological validation and Poisson density pruning
├── ml/                     # Machine learning inference interfaces
│   ├── depth/              # Dense depth estimation engine & analytical fallback
│   └── semantics/          # 3D Oriented Bounding Box (OBB) object detection
├── navigation/             # Indoor navigation engine
│   ├── graph.py            # NavMesh topological graph (NavNode, NavEdge)
│   ├── router.py           # 3D A* shortest path with wheelchair slope enforcement (≤ 4.76°)
│   └── instructions.py     # Turn-by-turn instruction generator (Straight, Turn, Arrive)
├── database/               # Relational persistence & spatial indexes
│   ├── migrations/         # 16 PostGIS migrations (auth, projects, models, spatial cells)
│   └── README.md           # Database engine documentation and setup instructions
├── archive/                # Legacy and exploratory prototype scripts isolated from core
├── infrastructure/         # Docker Compose (PostGIS, MinIO, Redis, and Worker container)
├── tests/                  # 204 unit & integration tests covering all subsystems
├── upgrade/                # Canonical architecture specifications & audit reports
│   ├── stage0.md           # Reality audit across all 20 subsystems
│   ├── canonical_architecture.md # Formal architecture & contracts 1-13
│   └── README.md           # Upgrade roadmap and index
├── ios/                    # Native iOS capture application (AVFoundation + CoreMotion)
├── android/                # Native Android capture application (Camera2 + SensorManager)
└── src/                    # Next.js & Three.js 3D web viewer frontend
```

---

## 📜 Formal Data Contracts (Pydantic v2)

All pipeline stages, mobile clients, and database persistence adhere to 13 formal schemas located in [`core/schemas/`](./core/schemas):

| # | Contract | Schema File | Producer | Consumer |
| :-: | :--- | :--- | :--- | :--- |
| **1** | **Capture Manifest (v2.0.0)** | [`capture_manifest.py`](./core/schemas/capture_manifest.py) | Mobile Capture | API / Preprocessing Worker |
| **2** | **Frame Metadata** | [`frame_metadata.py`](./core/schemas/frame_metadata.py) | Mobile Capture | SfM / Depth Worker |
| **3** | **IMU Samples** | [`imu_samples.py`](./core/schemas/imu_samples.py) | Mobile Capture | SfM / Visual-Inertial Worker |
| **4** | **Camera Poses** | [`camera_poses.py`](./core/schemas/camera_poses.py) | SfM Worker | Depth / Texturing Worker |
| **5** | **Reconstruction Artifact** | [`reconstruction_artifact.py`](./core/schemas/reconstruction_artifact.py) | Meshing / Splat Worker | Web Viewer / Storage |
| **6** | **Spatial Cell Manifest** | [`spatial_cell.py`](./core/schemas/spatial_cell.py) | Quality Worker | Cell Fusion / Database |
| **7** | **Structural Geometry** | [`structural_geometry.py`](./core/schemas/structural_geometry.py) | Semantics Worker | NavMesh / BIM Exporter |
| **8** | **Semantic Object Set** | [`semantic_object.py`](./core/schemas/semantic_object.py) | Semantics Worker | Search / Web Viewer |
| **9** | **Point of Interest (POI)** | [`poi.py`](./core/schemas/poi.py) | Operator / API | Web Viewer / AR |
| **10**| **Navigation Graph** | [`navigation_graph.py`](./core/schemas/navigation_graph.py) | NavMesh Worker | Indoor Router / Web Viewer |
| **11**| **Quality Report** | [`quality_report.py`](./core/schemas/quality_report.py) | Quality Worker | API / Mobile Operator |
| **12**| **Rescan Request** | [`rescan_request.py`](./core/schemas/rescan_request.py) | Quality Worker | Mobile App Guidance |
| **13**| **Model Version Manifest** | [`model_version.py`](./core/schemas/model_version.py) | Worker Pipeline | Web Viewer / Database |

---

## 🔄 Standardized Worker Lifecycle

Every stage in [`workers/stages/`](./workers/stages) inherits from [`BaseWorker`](./workers/base.py) and executes the standardized 8-step lifecycle:

```
INPUT ──> VALIDATION ──> PROCESSING ──> OUTPUT ARTIFACT ──> OUTPUT MANIFEST ──> METRICS ──> LOGGING ──> ERROR STATE
```

1. **`Stage01_Preprocessing`**: Unpacks video keyframes, validates duration/FPS parity, and decodes IMU streams.
2. **`Stage02_SfM`**: Estimates sparse 3D point cloud and 6-DoF camera poses (Contract 4).
3. **`Stage03_Depth`**: Generates metric per-pixel dense depth maps with bilateral edge preservation.
4. **`Stage04_PointCloud`**: Unprojects RGB-D frames into unified coordinates, applying spatial hash voxel subsampling.
5. **`Stage05_Meshing`**: Executes Screened Poisson surface reconstruction and removes non-manifold edges.
6. **`Stage06_Texturing`**: Computes UV parametrization and projects diffuse texture atlas.
7. **`Stage07_Semantics`**: Detects 3D Oriented Bounding Boxes (OBBs) and fits planar walls/floors/ceilings.
8. **`Stage08_NavMesh`**: Builds walkable topological graph enforcing ADA wheelchair slope limits ($\le 4.76^\circ$).
9. **`Stage09_Quality`**: Computes spatial coverage, reprojection drift, and issues rescan requests for deficient cells.

---

## 🛡️ Capture Data Model & Validation Engine

Captures are governed by **Capture Manifest v2.0.0** and validated via [`CaptureValidator`](./core/validation/capture_validator.py) with 6 strict checks:
- **Missing Files**: Asserts all declared video, IMU, and timing assets are present.
- **Corrupted Media**: Verifies ISO Base Media file format headers (`ftyp`, `moov`, `mdat`) and compares SHA-256 digests.
- **Timestamp Inconsistencies**: Validates strictly monotonic timestamps, measures frame jitter, and confirms IMU temporal coverage spans the entire video interval.
- **Invalid Metadata**: Asserts valid positive focal lengths, principal points within the optical sensor bounds, and plausible gravity vector norm ($\approx 9.81\text{ m/s}^2$).
- **Duplicate Frames**: Detects zero-delta timestamp intervals ($\Delta t \le 1\mu\text{s}$) or identical consecutive PTS values.
- **Incomplete Uploads**: Verifies byte-level parity between stored files and declared manifest sizes.

### Deterministic Artifact Naming
All capture artifacts use collision-free, hierarchical paths via [`CaptureArtifactNaming`](./storage/naming.py):
```
captures/{project_id}/{capture_id}/
├── manifest.json            # Master capture manifest
├── raw_video.mov            # Raw video recording
├── imu_samples.csv          # Synchronized IMU sample stream
├── frame_timestamps.json    # High-precision frame timestamp records
├── sparse_depth.bin         # Optional LiDAR depth points
└── validation_report.json   # Output report from validation engine
```

### Self-Contained Offline Reproducibility
Any capture can be archived, transported, and reproduced offline without relying on undocumented database state:
```python
from core.packaging.capture_package import CapturePackage

# Reproduce and validate a capture entirely from its directory:
manifest, report = CapturePackage.reproduce_from_directory("/path/to/capture_folder")
assert report.is_valid is True
```

---

## 📐 Canonical World System & Metric Alignment

To eliminate arbitrary coordinate frames and scale ambiguities, VĀSTU enforces an explicit **Canonical World Coordinate System**:
- **$+Z$ Axis**: Strictly points upwards along the anti-gravity vector ($\mathbf{g} \approx [0, 0, -9.81]\text{ m/s}^2$).
- **Floor Elevation**: Dominant primary floor plane leveled exactly to $Z = 0.0\text{ m}$.
- **$+X$ Axis**: Primary building facade aligned with the canonical $+X$ direction.

### 5-Tier Evidence Priority Hierarchy
Metric scale is resolved strictly in descending order of authoritative physical grounding via [`MetricCoordinateAligner`](./core/alignment/estimator.py):
1. **`METRIC_LIDAR_AR`** (Priority 1): Hardware ToF LiDAR depth returns and ARKit/ARCore metric VIO.
2. **`MEASURED_PHYSICAL_DIMENSIONS`** (Priority 2): Calibrated physical laser distance measurements between identifiable landmarks.
3. **`KNOWN_FLOORPLAN_DIMENSIONS`** (Priority 3): Verified architectural CAD or blueprint dimensional specifications.
4. **`RELIABLE_KNOWN_OBJECT_DIMENSIONS`** (Priority 4): Standard architectural fixtures (e.g. standard door leaf height $2.032\text{ m}$, counter heights).
5. **`MANUAL_CORRECTION`** (Priority 5): Manual operator scale factor calibration.

### Zero-Silent-Scaling Policy
Geometry is never implicitly or silently scaled. Every model stores an explicit $Sim(3)$ transformation (`scale`, `translation`, `rotation_matrix`, `rotation_quaternion`, `matrix_4x4`) in [`MetricTransformSchema`](./core/schemas/metric_transform.py). The publishing gate ([`ModelPublisher`](./core/alignment/publisher.py)) strictly blocks publication of any model without recorded scale provenance and confidence.

---

## 🎭 Tri-Representation Architecture

Reconstructed spaces are decoupled into three independent, purpose-built representations linked by version metadata and the canonical metric transformation:

```
                          ┌─────────────────────────────┐
                          │   TriRepresentationBundle   │
                          │   (Canonical Sim(3) Frame)  │
                          └──────┬────────┬────────┬────┘
                                 │        │        │
               ┌─────────────────┘        │        └─────────────────┐
               ▼                          ▼                          ▼
     ┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
     │   VISUAL MODEL   │       │ STRUCTURAL MODEL │       │ COLLISION MODEL  │
     │  3DGS / PBR GLB  │       │ BIM Planar Graph │       │ NavMesh Collider │
     └─────────┬────────┘       └─────────┬────────┘       └─────────┬────────┘
               │                          │                          │
               ▼                          ▼                          ▼
     Three.js Web Viewer         Architectural CAD         Indoor A* Pathfinder
     (0 navigation data)        (Floors/Walls/OBBs)        (0 visual splat data)
```

1. **VISUAL MODEL (`3DGS_PLY` / `GLB`)**:
   - Optimized for photorealism, specular reflections, and GPU rasterization.
   - Consumed exclusively by WebGL 2.0 / WebGPU viewers.
   - Endpoint: `GET /api/v1/models/{version_id}/visual`
2. **STRUCTURAL MODEL (`BIM_PLANAR_GRAPH`)**:
   - Analytical plane representations of floors, walls, ceilings, door/window openings, and 3D Oriented Bounding Box (OBB) semantic objects.
   - Optimized for architectural CAD export, area takeoffs, and space planning.
   - Endpoint: `GET /api/v1/models/{version_id}/structural`
3. **COLLISION MODEL (`NAVMESH_COLLIDERS`)**:
   - Simplified convex floor polygons, obstacle bounding colliders, and topological accessibility graphs enforcing ADA wheelchair slope limits ($\le 4.76^\circ$).
   - Consumed exclusively by navigation and routing agents with **0 visual assets loaded**.
   - Endpoint: `GET /api/v1/models/{version_id}/collision`

---

## ⚖️ Central Quality Engine & Explanatory Auditing

Reconstruction quality is evaluated through a centralized multi-subsystem engine ([`CentralQualityEngine`](./core/quality/engine.py)) across 6 core domains:
- **CAPTURE**: Keyframe blur (Laplacian variance), exposure balance, spatial coverage, and consecutive view overlap.
- **POSE**: Bundle adjustment reprojection error, trajectory continuity, loop closure drift, and pose confidence.
- **DEPTH**: Multi-view geometric consistency, volumetric point density, and surface hole percentage.
- **GEOMETRY**: Dominant plane confidence, architectural corner integrity (sharp vs rounded), disconnected walls, phantom reflection surfaces, and watertightness.
- **SEMANTICS**: Mean object detection confidence, room boundary volume confidence, and unclassified element ratio.
- **NAVIGATION**: Walkable floor continuity, obstacle collider clearance, route reachability from entrance to all POIs, and ADA wheelchair slope limits ($\le 4.76^\circ$).

### Non-Arbitrary Decision Making & Explanatory Reasoning
- **No Arbitrary Numerical Score as Sole Decision**: Even if the composite score is high (e.g. 0.88), any critical **Hard Failure** (e.g., disconnected indoor route, phantom reflection surface, or uncorrected tracking break) forces the verdict to `FAIL`.
- **Explanatory Diagnostics**: Generates a detailed narrative explaining **WHY** the model passed, warned, or failed, detailing exact failing metrics, cell IDs, and recommended operational remediations (such as targeted rescan bounding boxes).

---

## 🎯 Targeted Rescan Generation & Localized Fusion

When a cell or region fails QA, Vastu generates an actionable, localized rescan instruction instead of a generic "scan again" message.

### 10-Step Rescan Lifecycle
1. **Identify Failure Region**: Extracts failing cell ID and oriented 3D bounding box ($x, y, z, dx, dy, dz$).
2. **Identify Failure Reason**: Pinpoints the exact root cause (`HOLE`, `LOW_DENSITY`, `BLUR`, `SPECULAR_PHANTOM`, `DISCONNECTED_WALL`, `TRACKING_BREAK`).
3. **Calculate Required Observations**: Formulates target stand-off distances, camera tilt angles, sweep trajectories, and minimum keyframe counts.
4. **Generate Rescan Task**: Produces a Contract 12 (`RescanRequest`) payload containing `cell_id`, `region`, `reason`, `priority`, `required_capture_action`, and `expected_improvement`.
5. **Send Task to Mobile**: Dispatches via mobile control plane API (`/quality/rescan/generate`).
6. **Guide Mobile User (HUD & TTS)**: Mobile coordinator drives visual AR reticles, directional cues, and prioritized audio speech (e.g., *"Step back to 1.5m and sweep slowly along the missing corner"*).
7. **Upload Isolated Delta**: Packages only the new keyframes and IMU telemetry for the target cell (`package_delta_upload`).
8. **Reconstruct Affected Cells**: Runs localized meshing/fusion strictly for the failing cell without rebuilding the entire building.
9. **Validate Cell Boundaries**: Checks spatial halo continuity ($\le 12\text{ mm}$ mean error) between the updated cell and its static neighbors.
10. **Fuse into Existing Model**: Merges the updated cell seamlessly into the canonical visual, structural, and collision models.

---

## 🔒 Immutable Model Versioning & Comparison

When targeted rescans succeed, Vastu synthesizes a new model release without ever mutating or overwriting historical digital twins:
$$\text{V1} \longrightarrow \text{Affected-Cell Reconstruction} \longrightarrow \text{Registration} \longrightarrow \text{Boundary Validation} \longrightarrow \text{Fusion} \longrightarrow \text{V2}$$

### Immutability & Lineage Guarantees
- **Strict Immutability**: Registered versions are permanently frozen; any attempt to mutate V1 raises `ImmutableVersionError` / HTTP 409 Conflict.
- **Lineage Metadata Storage**: Records `model_id`, `version`, `parent_version`, `changed_cells`, `pipeline_version`, `algorithm_versions`, `quality_report`, `artifacts`, and `creation_timestamp`.
- **4-Way Model Comparison Engine**:
  - **Changed Geometry**: Altered/added/removed cells, vertex/face count deltas, volume changes, and mean surface displacement.
  - **Changed POIs**: Added, removed, or spatially relocated POIs.
  - **Changed Navigation**: NavNodes and NavEdges added/removed, walkable area, and wheelchair accessibility transitions.
  - **Changed Confidence**: Global score delta ($Q_{V2} - Q_{V1}$), per-cell improvements, and resolved hard failures.
- **Independent Historical Viewability**: V1 remains independently viewable, retrievable, and renderable in the web viewer even after V2 is published.

---

## 📍 Version-Aware POI System & Raycast Placement

Interactive spatial anchor management deeply coupled with digital twin versioning:
- **10-Field Formal Schema**: `id`, `name`, `aliases`, `category`, `coordinates`, `room`, `geometry`, `confidence`, `metadata`, `model_version`.
- **Full Lifecycle**: Complete Create, Edit, Delete, Search, and 3D Spatial Query (spherical radius and k-nearest neighbors).
- **3D Raycast Surface Hit Placement**: Interactive click in the 3D viewer calculates exact ray-triangle mesh hit coordinates and surface normal vectors via Möller–Trumbore intersection.
- **Cross-Version Spatial Validity Migration**: Preserves spatial anchors across version evolution with drift tolerance checks and adaptive surface mesh snapping.

---

## 🔍 Hybrid Spatial Search Engine

VĀSTU features a 5-stage hybrid spatial search pipeline that unifies exact naming, typo tolerance, semantic reasoning, and 3D spatial proximity:

$$\text{Query} \longrightarrow \text{Lexical Matching} \longrightarrow \text{Semantic Matching} \longrightarrow \text{Spatial Filtering} \longrightarrow \text{Ranking} \longrightarrow \text{Result Coordinates}$$

### Multi-Stage Architecture
1. **Query Intent & Preposition Parsing**:
   - Decomposes natural language queries into target entities and spatial anchors (e.g., `"chairs near reception"` $\rightarrow$ target: `"chairs"`, anchor: `"reception"`).
   - Resolves prepositional room containment (e.g., `"screens in Boardroom A"` $\rightarrow$ target: `"screens"`, room: `"Boardroom A"`).
2. **Lexical Matching**:
   - Case-insensitive exact token matching with confidence scoring.
   - Typo tolerance and pluralization handling via Levenshtein token similarity.
3. **Semantic Matching**:
   - Architectural & furniture taxonomy ontology matching (e.g., `"3-seater sofas"` maps to couches, lounges, and settees).
   - Matches category aliases and metadata attributes (e.g., `seating_capacity: 3`, `material: velvet`).
4. **Spatial Filtering & Metric Proximity**:
   - Resolves anchor entities to 3D metric coordinates.
   - Calculates Euclidean distance in canonical coordinate space ($+Z$ up, floor $Z=0$).
   - Dynamically filters objects outside search radii or prioritizes immediate neighbors.
5. **Multi-Criteria Ranking & Authoritative Coordinate Resolution**:
   - Blends lexical, semantic, spatial proximity, and base model confidence.
   - Returns structured `SearchResultItem` containing:
     - Full POI entity and ID
     - Normalized confidence ($0.0 \dots 1.0$)
     - Authoritative 3D coordinates $[x, y, z]$
     - Room name / containment zone
     - Rich `SearchPreviewMetadata` (match type, distance to anchor, explanation, sub-scores).

---

## 🚶 Navigation Representation from Structural & Collision Geometry

VĀSTU derives the indoor navigation model strictly from analytical BIM structural planes and collision colliders, bypassing Gaussian splats to guarantee metric boundary precision:

$$\text{Floor} \longrightarrow \text{Obstacles} \longrightarrow \text{Footprints} \longrightarrow \text{Human-Radius Inflation} \longrightarrow \text{Walkable Region} \longrightarrow \text{NavMesh / Graph}$$

### 6-Stage Pipeline
1. **Floor Extraction**:
   - Detects horizontal floor surfaces ($n_z > 0.85$, floor elevation clustering).
   - Identifies multi-level elevations and unlinked vertical step boundaries as `DISCONNECTED_FLOOR`.
2. **Obstacle Collection**:
   - **Structural**: Walls (`plane_type == "WALL"`), structural columns, and active doorways (`StructuralOpening`).
   - **Collision**: Furniture (tables, couches, desks) and equipment colliders (`CollisionObstacle`).
3. **Footprint 2D Projection**:
   - Projects 3D bounding geometry onto the 2D canonical floor plane ($XY$).
4. **Human-Radius Inflation**:
   - Expands obstacle envelopes by human body clearance radius $r_{\text{human}} = 0.35\text{ m}$ ($0.70\text{ m}$ body diameter).
   - Carves traversable passage portals across active doorway thresholds to preserve room-to-room egress.
5. **Walkable Region Analysis**:
   - **Narrow Passage Detection**: Identifies physical clearance gaps $< 2 \cdot r_{\text{human}}$ ($< 0.70\text{ m}$) between adjacent obstacles or walls, pinching them out and recording `cause = NARROW_PASSAGE`.
   - **Inaccessible Island Pruning**: Flags isolated floor pockets with no door/entrance connectivity as `cause = INACCESSIBLE_ISLAND`.
6. **Topological NavMesh / Graph Generation**:
   - Discretizes walkable regions into regularized spatial navigation nodes and line-of-sight edges (Contract 10 `NavigationGraph`).
   - Validates wheelchair accessibility slopes ($\le 4.76^\circ$).
   - Explicitly records `derived_from_gaussian_splats: false`.

### Identifiable Geometric Causality Guarantee
Every non-traversable zone in the digital twin is attributed with an identifiable geometric cause:
- `WALL`: Structural perimeter or interior partition boundary.
- `FURNITURE`: Impassable table, desk, sofa, or cabinet collision envelope.
- `COLUMN`: Concrete or steel architectural column.
- `DOOR_CLOSED`: Restricted or locked doorway portal.
- `NARROW_PASSAGE`: Clearance gap smaller than human body width ($< 0.70\text{ m}$).
- `DISCONNECTED_FLOOR`: Elevation step $> 0.50\text{ m}$ without stair or ramp transit.
- `INACCESSIBLE_ISLAND`: Isolated floor patch with no traversable connectivity.

---

## 🚀 Quickstart

### 1. Start Infrastructure Services
Launch PostgreSQL 16 (PostGIS), MinIO S3 object storage, and Redis:
```bash
docker compose up -d
```
- **PostgreSQL / PostGIS**: `localhost:5432` (`vastu` database)
- **MinIO S3 Console**: `http://localhost:9001` (Admin: `minioadmin` / `minioadmin`)
- **MinIO S3 API**: `http://localhost:9000`

### 2. Run Database Migrations
```bash
migrate -path database/migrations -database "postgresql://postgres:postgres@localhost:5432/vastu?sslmode=disable" up
```

### 3. Launch FastAPI Control Plane
```bash
PYTHONPATH=. backend/workers/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation will be available at `http://localhost:8000/docs`.

### 4. Run the 3D Web Viewer Frontend
```bash
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🧪 Testing & Verification

Run the complete test suite across all subsystems:
```bash
PYTHONPATH=. backend/workers/venv/bin/pytest tests/ -v
```

All **204 tests** validate:
- All 13 Pydantic v2 data contracts ([`test_contracts.py`](./tests/test_contracts.py))
- Capture Manifest v2.0.0, deterministic naming, and validation rules ([`test_capture_model.py`](./tests/test_capture_model.py))
- Mobile capture ring buffer, storage safety, and interruption recovery ([`test_mobile_capture.py`](./tests/test_mobile_capture.py))
- Event-driven capture SOP 11 stages, 7 quality signals, and prioritized TTS ([`test_sop_engine.py`](./tests/test_sop_engine.py))
- Resumable direct-to-storage upload pipeline and backoff retry ([`test_upload_pipeline.py`](./tests/test_upload_pipeline.py))
- Preprocessing, feature density, blur detection, adaptive keyframes ([`test_preprocessing.py`](./tests/test_preprocessing.py))
- Hierarchical camera tracking, VIO fusion, anomaly detection ([`test_camera_pose_estimation.py`](./tests/test_camera_pose_estimation.py))
- Multi-view depth consistency, evidence point cloud, density maps ([`test_dense_reconstruction.py`](./tests/test_dense_reconstruction.py))
- Spatial-cell decomposition, boundary halos, independent lifecycle & fusion ([`test_spatial_cells.py`](./tests/test_spatial_cells.py))
- Architectural structure extraction, 4-way plane classification, sharp corners, non-orthogonal angle preservation ([`test_architectural_structure.py`](./tests/test_architectural_structure.py))
- Architectural geometry correction, controlled snapping, thickness estimation, 7 QA audits ([`test_geometry_correction.py`](./tests/test_geometry_correction.py))
- Independent semantic reconstruction, 10-class taxonomy, room containment, ground truth policy ([`test_semantic_reconstruction.py`](./tests/test_semantic_reconstruction.py))
- Metric coordinate alignment, canonical world system, 5-tier evidence priority, explicit transforms, publishing verification ([`test_metric_alignment.py`](./tests/test_metric_alignment.py))
- Tri-representation separation (Visual, Structural, Collision models), explicit bundle linking, decoupled rendering & navigation ([`test_tri_representation.py`](./tests/test_tri_representation.py))
- Central quality engine, 6-subsystem audit, spatial confidence map, non-arbitrary hard failures, explanatory narratives ([`test_central_quality_engine.py`](./tests/test_central_quality_engine.py))
- Targeted rescan generation, actionable mobile HUD/TTS guidance, boundary continuity, and localized cell fusion ([`test_targeted_rescan.py`](./tests/test_targeted_rescan.py))
- Immutable model versioning, rescan evolution pipeline, 4-way comparison, and independent historical viewability ([`test_model_versioning.py`](./tests/test_model_versioning.py))
- Semantic POI system, 10-field schema, CRUD, search, spatial queries, raycast surface placement, and version migration ([`test_poi_system.py`](./tests/test_poi_system.py))
- Hybrid spatial search engine, exact, fuzzy, semantic, relational proximity, and FastAPI endpoints ([`test_hybrid_search.py`](./tests/test_hybrid_search.py))
- Navigation representation from structural & collision geometry, 6-stage pipeline, narrow passages, and geometric causality ([`test_navigation_representation.py`](./tests/test_navigation_representation.py))
- Route planning pipeline, multi-criteria A* (turns, narrow corridors, wheelchair slopes), string-pulling smoothing, and strict collision validation ([`test_route_planning.py`](./tests/test_route_planning.py))
- Interactive Three.js 3D Web Viewer, FPS WASD kinematics, floor grounding, circle-to-AABB collision pushback, POI raycasting, and pure roaming runtime ([`test_web_viewer.py`](./tests/test_web_viewer.py))
- Asset Delivery Optimization & Performance Telemetry, 5m spatial chunks, 3-tier LODs, DRACO compression, 7-metric live telemetry HUD ([`test_delivery_optimization.py`](./tests/test_delivery_optimization.py))
- End-to-End Workflow Orchestrator, continuous 22-stage automated pipeline, observable monotonic 0-100% stage progress events, and web viewer publication ([`test_workflow_orchestrator.py`](./tests/test_workflow_orchestrator.py))
- Deliberate Pipeline Failure Testing across 14 failure injection modes, 7 verification dimensions, and zero silent corruption ([`test_pipeline_failure_injection.py`](./tests/test_pipeline_failure_injection.py))
- Controlled Physical Benchmark Environment, surveyed ground truth room, 8 physical accuracy metrics, and measurable upgrade improvement ([`test_physical_benchmark.py`](./tests/test_physical_benchmark.py))
- Navigation Benchmark Scenarios, 9 geometric scenarios, 6 quantitative metrics, and objective verification ([`test_navigation_benchmark.py`](./tests/test_navigation_benchmark.py))
- AR Localization Independent Layer, marker PnP pose, rigid transform, continuous dead-reckoning, route projection ([`test_ar_localization.py`](./tests/test_ar_localization.py))
- Worker 8-stage lifecycle and error state propagation ([`test_workers.py`](./tests/test_workers.py))
- Pure geometry math (RANSAC, dihedral angles, spatial hash, PCA normals, manifold checks) ([`test_geometry.py`](./tests/test_geometry.py))
- 3D indoor A* routing, wheelchair slope rejection, and turn instructions ([`test_navigation.py`](./tests/test_navigation.py))
- Pluggable storage adapter uploads, downloads, and presigned URLs ([`test_storage.py`](./tests/test_storage.py))
- FastAPI control plane routes and health endpoints ([`test_api.py`](./tests/test_api.py))

