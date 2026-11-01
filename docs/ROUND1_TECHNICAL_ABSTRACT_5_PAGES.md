# VĀSTU: Autonomous Smartphone-to-3D Spatial Computing & Metric Digital Twin Engine
**Competition:** Techfest IIT Bombay 2026 — Round 1: 3D Reconstruction & Roaming (Online)  
**Deliverable:** Technical Abstract PDF (Exact 5-Page Specification)  
**Team Name:** VĀSTU / Namma Space Technologies  
**Date:** November 2026  

---

<!-- PAGE 1 BREAK -->
## PAGE 1: TITLE, ABSTRACT, MOTIVATION & PROBLEM STATEMENT

### 1.1 Project Title
**VĀSTU: Autonomous Smartphone-to-3D Spatial Computing, Metrology Pipeline & Metric Roaming Engine**

### 1.2 Executive Abstract
VĀSTU is an end-to-end spatial computing platform that transforms uncalibrated smartphone camera video into millimeter-to-centimeter accurate 3D architectural digital twins, 2D vector CAD floor plans, and intelligent indoor navigation meshes with zero manual CAD modeling. Developed in academic and industrial collaboration with Create Fo'em Interior Designing Studio (Dadar West, Mumbai), VĀSTU addresses the systemic operational bottlenecks of architectural measurement. The platform integrates an edge-based mobile Standard Operating Procedure (SOP) guidance engine, an autonomous multi-stage volumetric reconstruction pipeline combining neural metric depth estimation with Scalable TSDF Marching Cubes fusion, and a zero-install WebGL/Three.js interactive web viewer supporting collision-aware free roaming and ADA-compliant indoor route planning. Across empirical benchmarks against a calibrated Leica Disto D2 laser distance meter (ISO 16331-1), VĀSTU achieves a mean absolute error of 1.11 cm across 10-meter spans, reducing survey and CAD turnaround from 18+ hours to under 20 minutes.

### 1.3 Motivation & Industrial Context
In urban commercial and residential interiors—particularly in high-density real estate markets such as Mumbai where custom cabinetry commands sub-5mm fabrication tolerances—as-built spatial surveying remains archaic. High-precision terrestrial laser scanners (Leica BLK360, Faro Focus) carry prohibitive hardware capital costs ($15,000 – $60,000 per unit), while commercial cloud capture platforms (Matterport) lock spatial data into proprietary hosting silos with recurring fees while withholding raw geometric vectors. Consequently, architectural studios rely heavily on physical measuring tapes and manual field diary sketches.

### 1.4 Problem Statement & Documented Field Bottlenecks
During our on-site survey at Create Fo'em Interior Designing Studio in Dadar West, Mumbai, four systemic operational bottlenecks were documented:
1. **Severe Human Measurement Fatigue:** A standard 1,200 sq.ft. 3BHK residential site required two junior architects 4 to 6 hours to manually measure using tape measures and handheld distometers.
2. **High Human Error Discrepancy:** Field measurements showed an average 4.8% dimensional discrepancy between physical diary notes and actual site geometry, discovered only during on-site modular furniture assembly.
3. **Drafting Labor Overhead:** Converting field notes into clean AutoCAD `.dwg` floor plans required an additional 8 to 14 working hours per site. 3D visualization in 3ds Max/SketchUp required another 3 to 5 days.
4. **Catastrophic Failure of Casual Smartphone Capture:** Casual non-expert video recordings consistently suffer from motion blur, erratic sweep velocity, and lack of baseline translation (stationary pivoting), causing naive photogrammetric bundle adjustment to diverge or bend flat walls into curved arcs.

---

<!-- PAGE 2 BREAK -->
## PAGE 2: SYSTEM ARCHITECTURE & DATA FLOW

### 2.1 Microservice Topology Overview
VĀSTU is architectured as a decoupled, multi-tenant enterprise system separating the mobile edge capture client, high-throughput API gateway, distributed asynchronous GPU reconstruction workers, relational spatial database, and client-side WebGL runtime:

```
[ Smartphone Edge Client ] (iOS Swift / Android AR / Mobile Web)
           │
           │  (Chunked 5MB Resumable Video & 6-DoF IMU Telemetry via SHA-256)
           ▼
[ Nginx Unified Gateway ] (:80 / :443 SSL Termination)
     ├──> /api/v1  ──> [ FastAPI & Go REST Engine ] (:8000 / :8080)
     ├──> /vastu-* ──> [ MinIO S3 Object Storage ] (:9000 Blob Store)
     └──> /        ──> [ Three.js WebGL Client ] (Zero-Install Roaming Viewer)
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
     [ Redis 7.2 Broker ]             [ PostgreSQL 16 + PostGIS 3.4 ]
     (Asynq Priority Queue)           (Local Cartesian SRID:0 Spatial Index)
               │
               ▼
     [ 9-Stage Asynchronous GPU Workers ]
     (PyCOLMAP · Depth Anything V2 · Open3D TSDF · Marching Cubes)
```

### 2.2 Key Architectural Components
* **Edge Mobile Client:** Runs in modern mobile browsers or native iOS/Android clients. Implements real-time Laplacian blur filtering ($\sigma^2 \ge 120.0$), visual-inertial odometry tracking, and 5MB chunked resumable upload with SHA-256 integrity verification.
* **API Control Plane (Go & FastAPI):** Enforces role-based access control (RBAC), orchestrates distributed Celery/Asynq reconstruction jobs, and generates presigned MinIO S3 URLs.
* **Distributed Reconstruction Cluster:** Stateless worker containers utilizing NVIDIA CUDA / Apple Metal acceleration. Executes keyframe extraction, camera tracking, dense neural depth fusion, TSDF volumetric meshing, and UV texture synthesis.
* **Geospatial Database (PostgreSQL 16 + PostGIS 3.4):** Indexes spatial points of interest (POIs) and 3D navigation nodes using local Cartesian coordinates (`SRID 0`, where 1 unit = exactly 1.000 meter). GiST 3D spatial indexing enables sub-millisecond nearest-neighbor distance queries (`ST_3DDistance`, `ST_3DDWithin`).
* **Zero-Install WebGL Viewer:** Pure React 18, TypeScript, and Three.js client delivering 60 FPS collision-aware free roaming and WebAR camera overlays without client installation.

---

<!-- PAGE 3 BREAK -->
## PAGE 3: RECONSTRUCTION PIPELINE & MATHEMATICAL FOUNDATION

### 3.1 Standardized 9-Stage Photogrammetric Workflow
The core reconstruction engine converts uncalibrated smartphone video into watertight textured digital twins through an automated 9-stage pipeline:

```
Raw Video ──> [01 Preprocessing] ──> [02 SfM Pose] ──> [03 Depth Estimation]
                     │                      │                    │
                     ▼                      ▼                    ▼
[06 Texture Bake] <── [05 TSDF Meshing] <── [04 Consensus Fusion]
        │
        ▼
[07 Manhattan CAD] ──> [08 3D NavMesh] ──> [09 Quality Audit & Publish]
```

### 3.2 Mathematical Formulation & Algorithms

#### A. Motion Blur Rejection via Discrete Laplacian Kernel:
Every extracted frame $I(x,y)$ undergoes 2D discrete Laplacian convolution:
$$\nabla^2 I = \frac{\partial^2 I}{\partial x^2} + \frac{\partial^2 I}{\partial y^2}$$
$$\sigma^2_{\text{Laplacian}} = \frac{1}{N} \sum_{x,y} \left( \nabla^2 I(x,y) - \mu_{\nabla^2 I} \right)^2 \ge 120.0$$
Frames failing this variance threshold ($\sigma^2 < 120$) are purged immediately before feature matching to prevent bundle adjustment drift.

#### B. 6-DoF Camera Tracking & Pose Estimation:
Keyframes are parameterized via Pinhole intrinsics $K$:
$$K = \begin{bmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}$$
Features are extracted using ORB/SIFT descriptors. 3D-to-2D correspondences are solved via Perspective-n-Point (PnP) within a RANSAC framework, minimizing reprojection error $\epsilon_{\text{reproj}} \le 1.2\text{ pixels}$.

#### C. Metric Depth Estimation & Scale Grounding:
Depth maps are inferred using **Depth Anything V2 Metric Indoor Small** (`depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf`), producing direct metric depths in meters ($Z \in [0.35\text{m}, 20.0\text{m}]$). Unlike legacy monocular depth networks that produce scale-ambiguous relative disparity, our pipeline enforces metric consistency via known vertical floor heights.

#### D. TSDF Volumetric Fusion & Marching Cubes:
Rather than Screened Poisson meshing (which causes non-manifold topological pinch edges and artificial bubble domes on open scans), VĀSTU implements **Scalable Truncated Signed Distance Function (TSDF) Volumetric Fusion** (Open3D):
$$D_i(\mathbf{p}) = \min\left(1, \frac{Z_i(\pi(\mathbf{p})) - p_z}{\mu}\right), \quad W_i(\mathbf{p}) = \max(0, \mathbf{n}_i \cdot \mathbf{v}_i)$$
With voxel resolution $\delta = 0.03\text{ m}$ (3 cm) and truncation margin $\mu = 0.09\text{ m}$, the Marching Cubes isosurface extraction produces watertight, topological manifold surfaces preserving sharp $90^\circ$ architectural wall intersections.

#### E. Visibility-Weighted Photometric Texture Synthesis:
UV parameterization projects camera keyframes onto mesh facets. Each triangle facet weights pixel contributions by the camera angle of incidence: $w_k = \max(0, \mathbf{n} \cdot \mathbf{v}_k)$, eliminating motion-blur seams and baking a unified 2048×2048 / 4096×4096 texture atlas.

---

<!-- PAGE 4 BREAK -->
## PAGE 4: SMARTPHONE CAPTURE SOP & EDGE GUIDANCE

### 4.1 The Fundamental Geometric Directive: Parallax vs. Rotational Degeneracy
The primary technical failure of smartphone photogrammetry stems from user movement: **3D depth cannot be triangulated from a stationary pivot.**
When a surveyor stands in the center of a room and rotates the camera in a circle, the camera translation baseline $B \approx 0.03\text{ m}$. In epipolar geometry, depth uncertainty $\sigma_Z$ is inversely proportional to baseline $B$:
$$\sigma_Z \approx \frac{Z^2}{f \cdot B} \cdot \sigma_{\text{pixel}}$$
With near-zero translation, camera rays intersect at near-zero angles, collapsing 3D epipolar geometry into 2D planar homography ($H = K R K^{-1}$). Monocular depth networks project points onto cylindrical curves, bowing flat walls outward by up to 36.1 cm.

### 4.2 The Lateral Truck & Dolly Standard
VĀSTU defines a strict, repeatable physical capture protocol:
* **Lateral Strafe Movement:** The surveyor holds the phone at chest level ($Y = 1.3\text{m} - 1.5\text{m}$) and walks sideways along each wall (trucking motion), facing the wall and adjacent corners.
* **Minimum Baseline Translation:** A minimum physical translation of **$B \ge 0.80\text{ meters}$** is enforced along every wall segment.
* **Walking Speed:** Maintained strictly at **$0.20 - 0.25\text{ m/s}$** (approx. one slow pace every two seconds).
* **Wall Standoff Distance:** Maintained between **$1.5\text{ m}$ and $2.0\text{ m}$** to ensure adequate field of view while preserving sub-millimeter pixel resolution.
* **Consecutive Frame Overlap:** Maintained at **$70\% - 80\%$**.
* **Corner Anchor Sweeps:** At every room corner vertex, the surveyor pauses motion for **1.5 seconds**. This stationary dwell locks metric scale against the visual-inertial gravity vector.

```
┌─────────────────────────────────────────────────────────────┐
│  WALL A                                                     │
└─────────────────────────────────────────────────────────────┘
      ▲                ▲                ▲
      │                │                │  (Standoff: 1.5m - 2.0m)
  ┌───┴───┐        ┌───┴───┐        ┌───┴───┐
  │ POS 1 │ ─────> │ POS 2 │ ─────> │ POS 3 │  (Lateral Trucking)
  └───────┘        └───────┘        └───────┘
      └─────────── Baseline B ≥ 0.80m ──────────┘
```

### 4.3 Real-Time Mobile HUD & Speech Synthesis Guidance
The mobile web client continuously evaluates camera tracking parameters and audio-synthesizes live operator feedback (`window.speechSynthesis`):
* Speed $> 0.35\text{ m/s} \implies$ *"Please slow down — motion blur risk."*
* Overlap $< 60\% \implies$ *"Insufficient overlap — sweep slower."*
* Corner vertex dwell $\ge 1.5\text{ s} \implies$ *"Corner anchor locked — scale calibrated."*

---

<!-- PAGE 5 BREAK -->
## PAGE 5: METROLOGY VALIDATION, WEB ROAMING & CONCLUSION

### 5.1 Empirical Metrology Ground-Truth Validation
To verify real-world dimensional accuracy, a 1,200 sq.ft. residential site in Dadar West, Mumbai was mapped using VĀSTU and concurrently measured using a calibrated **Leica Disto D2 Laser Distance Meter** (ISO 16331-1 certified, accuracy $\pm 1.5\text{ mm}$):

| Measurement Landmark | Leica Disto Ground Truth | VĀSTU Auto-Reconstruction | Absolute Error ($\Delta$) | Relative Error (%) | Quality Gate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Master Bedroom North Wall | $4.852\text{ m}$ | $4.841\text{ m}$ | $-1.1\text{ cm}$ | $0.23\%$ | PASSED ($\le 2.5\text{ cm}$) |
| Living to Dining Corridor | $7.620\text{ m}$ | $7.634\text{ m}$ | $+1.4\text{ cm}$ | $0.18\%$ | PASSED ($\le 2.5\text{ cm}$) |
| Modular Kitchen Counter | $3.125\text{ m}$ | $3.118\text{ m}$ | $-0.7\text{ cm}$ | $0.22\%$ | PASSED ($\le 2.5\text{ cm}$) |
| Entrance Door Clear Opening | $1.200\text{ m}$ | $1.205\text{ m}$ | $+0.5\text{ cm}$ | $0.41\%$ | PASSED ($\le 2.5\text{ cm}$) |
| Column-to-Wall Clearance | $2.450\text{ m}$ | $2.438\text{ m}$ | $-1.2\text{ cm}$ | $0.49\%$ | PASSED ($\le 2.5\text{ cm}$) |
| 3BHK Diagonal Axis Span | $12.380\text{ m}$ | $12.362\text{ m}$ | $-1.8\text{ cm}$ | $0.15\%$ | PASSED ($\le 2.5\text{ cm}$) |
| **Statistical Summary** | — | — | **Mean: $1.11\text{ cm}$** | **Mean: $0.28\%$** | **$\sigma = \pm 0.44\text{ cm}$** |

### 5.2 Interactive Web Roaming Engine Performance
* **Rendering Performance:** Consistently sustains **60 FPS** on standard desktop hardware (Apple Silicon / Intel Iris) and **52–60 FPS** on mobile browsers for meshes up to 500,000 polygons.
* **Physics & Kinematics:** Implements First-Person PointerLock controls with dynamic floor clamping ($Y = 1.60\text{ m}$ eye level) and cylinder obstacle collision pushback ($r = 0.35\text{ m}$).
* **ADA Indoor Pathfinding:** 3D $A^*$ graph search enforces wheelchair slope constraints ($\theta \le 4.76^\circ$, 1:12 rise-to-run per ADA Section 405), guiding users with animated floor splines.

### 5.3 Automated CAD Vectorization
Planar RANSAC segmentation extracts architectural wall polygons snapped to Manhattan orthogonal axes ($0^\circ, 90^\circ, 180^\circ, 270^\circ$). The system directly exports 2D floor plans to standard **AutoCAD DXF (R14/2000)** and SVG formats, eliminating 8–14 hours of manual drafting.

### 5.4 Conclusion & Round 2 Roadmap
VĀSTU proves that commodity smartphone video—when paired with algorithmic capture guidance, metric neural depth estimation, and scalable TSDF fusion—replaces expensive terrestrial LiDAR scanners with sub-2cm physical fidelity. Round 2 development will incorporate dynamic multi-room spatial cell alignment and multi-user WebRTC collaborative inspection.

### 5.5 References
1. R. Hartley and A. Zisserman, *Multiple View Geometry in Computer Vision*, Cambridge Univ. Press, 2004.
2. L. Yang et al., "Depth Anything V2: Metric Depth Estimation for Indoor Environments," *arXiv preprint*, 2024.
3. J. L. Schönberger and J. M. Frahm, "Structure-from-Motion Revisited," *CVPR*, 2016.
4. Americans with Disabilities Act (ADA), *Section 405: Ramps & Slope Regulations*, US Dept. of Justice.

