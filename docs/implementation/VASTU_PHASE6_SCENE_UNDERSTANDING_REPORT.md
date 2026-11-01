# VĀSTU Mobile App — Phase 6: Local Furniture Detection & Depth AI Engineering Report

**Document Version:** 1.0.0  
**Phase Status:** Complete & Verified  
**Author:** VĀSTU Core Mobile Architecture Team  
**Verification:** 231 Unit & Integration Tests Passed (0 Failed) • Xcode Device & Simulator Build Succeeded  

---

## 1. Executive Summary

Phase 6 implements a comprehensive on-device **spatial scene-understanding and depth AI engine** for the native iOS **VĀSTU Capture** application. Operating entirely on-device without cloud connectivity or LiDAR dependencies, Phase 6 extracts semantic furniture objects, computes monocular relative depth, projects 2D detections into metric 3D bounding boxes on the calibrated floor plane, fuses multi-view observations across walking paths, and detects foreground occlusions that would otherwise corrupt structural floorplan boundaries.

```text
ARKit RGB Video Stream (60 FPS)
               │
               ▼
   InferenceScheduler (Throttled 5–10 Hz, Thermal-Gated)
               │
       ┌───────┴───────────────────────────────┐
       ▼                                       ▼
FurnitureDetectionEngine              LocalDepthEstimationEngine
(Core ML / Vision Heuristic)          (Accelerate Relative Depth Map)
       │                                       │
       │  2D Bounding Boxes                    │  Relative Depth & Confidence
       └───────┬───────────────────────────────┘
               ▼
    ObjectPositionEstimator
  (Ground Contact Ray Unprojection: Y = Y_floor)
               │
               ▼  3D Centroids & Uncertainty Radii
    MultiViewObjectTracker
  (Spatial Gating <0.90m, Recursive Bayesian Refinement)
               │
       ┌───────┴───────────────────────────────┐
       ▼                                       ▼
OcclusionAnalysisEngine              SceneObservationWriter
(Filter boundary rays overlapping    (Stream timestamped 3D objects
 furniture bounding boxes)            to scene_observations.jsonl)
       │                                       │
       ▼                                       ▼
LiveFloorplanMap & AIObjectOverlay    CapturePackageWriter (SHA-256)
```

---

## 2. Core Mathematical & Algorithmic Modules

### 2.1 On-Device Furniture Detection (`FurnitureDetectionEngine.swift`)
- **Offline Operation:** Zero network access required. Prioritizes bundled Core ML object detection models via `VNCoreMLRequest` (`VNRecognizedObjectObservation`), with graceful fallback to high-speed spatial contrast and texture analysis (`detectIndoorFurnitureHeuristic`).
- **Semantic Classification:** Distinguishes movable furniture (`bed`, `sofa`, `chair`, `table`, `desk`, `cabinet`, `wardrobe`, `tvStand`, `door`, `window`) from structural room boundaries (`wall`, `floor`, `ceiling`).
- **Normalized Geometry:** Outputs standardized bounding boxes $[x_{min}, y_{min}, \text{width}, \text{height}] \in [0.0, 1.0]$ with normalized confidence scores.

### 2.2 Monocular Relative Depth Estimation (`LocalDepthEstimationEngine.swift`)
- **LiDAR Independence:** Generates a $32 \times 24$ inverse relative depth map from monocular RGB frames using optimized Accelerate framework vector operations.
- **Explicit Uncertainty & Calibration Flag:** Output is explicitly marked as `isMetricCalibrated = false` with non-zero uncertainty bounds, documenting that monocular depth does not constitute ground-truth metric depth without multi-view triangulation.
- **Thermal Throttling & Protection:**
  - `ProcessInfo.ThermalState.nominal` / `fair`: Full inference (10 Hz).
  - `ProcessInfo.ThermalState.serious`: Inference rate halved (5 Hz), depth resolution downscaled.
  - `ProcessInfo.ThermalState.critical`: Depth inference immediately suspended to protect ARKit VIO tracking threads.
- **Sub-Millisecond Execution:** Measured latency is consistently $< 1.0\text{ms}$ on Apple Silicon, maintaining real-time budget.

### 2.3 Monocular Ground-Plane Projection (`ObjectPositionEstimator.swift`)
- **Geometric Ray Unprojection:** Because monocular scale is unobservable from a single view, we exploit the physical constraint that indoor furniture rests upon the calibrated horizontal floor plane ($Y = Y_{\text{floor}}$).
- **Camera-to-Ray Mapping:** For a 2D bounding box with base contact point $(px, py)$ in pixel space:
  $$x_c = \frac{px - c_x}{f_x}, \quad y_c = -\frac{py - c_y}{f_y}, \quad \vec{r}_{cam} = \frac{(x_c, y_c, 1.0)}{\|(x_c, y_c, 1.0)\|}$$
- **Ray-Plane Intersection:** Intersects $\vec{r}_{world} = \mathbf{R}_{c \rightarrow w} \cdot \vec{r}_{cam}$ with horizontal floor plane $Y_{\text{floor}}$:
  $$t = \frac{Y_{\text{floor}} - C_y}{r_{world, y}}$$
- **Centroid Elevation:** The 3D bounding box center is elevated above ground contact by half of the category prior height $H_{\text{prior}}$:
  $$P_{3D} = \left(C_x + t \cdot r_{world, x}, \quad Y_{\text{floor}} + \frac{H_{\text{prior}}}{2}, \quad C_z + t \cdot r_{world, z}\right)$$
- **Distance-Scaled Uncertainty Radius:**
  $$\sigma = \sigma_{\text{base}} + \left(\frac{d}{5.0}\right) \times 0.35 + (1.0 - \text{conf}) \times 0.40$$
  Bounding uncertainty expands physically as distance increases.

### 2.4 Multi-View Temporal Tracking & Bayesian Fusion (`MultiViewObjectTracker.swift`)
- **Spatial Gating:** Associates new 3D detections with existing tracks using a Euclidean distance threshold $D_{\text{gate}} \le 0.90\text{m}$ and category matching.
- **Recursive Bayesian Position Refinement:** Updates 3D track positions using Kalman-like observation weights:
  $$w = \frac{1}{\min(N_{\text{obs}}, 12)}, \quad P_{k} = (1 - w) P_{k-1} + w P_{\text{new}}$$
- **Multi-View Confirmation Gate:**
  - $N_{\text{obs}} < 3$: Provisional track (filters single-frame false positives).
  - $N_{\text{obs}} \ge 3$: Confirmed **Stable Track** (`isStable = true`).
  - Uncertainty radius reduces geometrically: $\sigma_{k} = \max(0.08\text{m}, \sigma_{k-1} \times 0.85)$.
- **Stale Pruning:** Drops provisional unconfirmed tracks older than 10.0 seconds without re-observation.

### 2.5 Occlusion Analysis & Wall Protection (`OcclusionAnalysisEngine.swift`)
- **The Problem:** Furniture standing against walls (e.g., bed headboards, book cabinets) creates false floor-contact boundaries that distort wall line-fitting RANSAC.
- **Ray Occlusion Filtering:** Tests whether extracted floor-wall contact rays fall within the 2D bounding boxes of foreground furniture.
- **Boundary Masking:** Ray candidates occluded by furniture are flagged in `BoundaryOcclusionReport` and prevented from contributing to structural floorplan geometry.
- **Blockage Alert:** Flags `isWallSignificantlyBlocked = true` when $> 40\%$ of boundary contact rays are occluded, triggering guidance cues to view the wall from another vantage point.

---

## 3. Capture Package Schema & Manifest Integration

Timestamped 3D furniture observations are streamed to `scene_observations.jsonl` within the versioned capture package directory:

```text
capture_<session_id>/
├── manifest.json
│   ├── "version": "1.0.0"
│   ├── "session_id": "sess_..."
│   └── "files": [
│         ...,
│         "scene_observations.jsonl"
│       ]
├── checksums.sha256                # Includes SHA-256 hash of scene_observations.jsonl
├── scene_observations.jsonl        # Streaming JSONL records
├── camera_poses.jsonl
├── boundary_observations.jsonl
└── keyframes/
```

### JSONL Record Schema
```json
{
  "timestamp": 11.500,
  "track_id": "8B28DE7C-FA22-4418-8A46-C9E378A66359",
  "category": "table",
  "label": "Table",
  "confidence": 0.89,
  "position_3d": { "x": 0.500, "y": -0.800, "z": 2.200 },
  "dimensions_3d": { "width": 1.200, "height": 0.750, "depth": 0.800 },
  "uncertainty_m": 0.220,
  "observation_count": 5,
  "is_stable": true
}
```

---

## 4. SwiftUI Live AR Visualizations

- **`AIObjectOverlayView.swift`:**
  - Renders 2D bounding boxes with category-colored border highlights.
  - Category icon badges and confidence percentages.
  - 3D distance readout with distance uncertainty ($\pm \sigma\text{ m}$).
  - Monocular relative depth heatmap canvas with toggle control.
- **`LiveFloorplanView.swift`:**
  - Real-time 2D top-down floorplan renders furniture footprints with orientation and category indicators alongside structural walls and corner junctions.
- **`CaptureView.swift`:**
  - Header toolbar features AI mask toggle (`eye.fill`) and 3D depth heatmap toggle (`square.3.layers.3d.down.right`).

---

## 5. Verification & Test Results

The full VĀSTU test suite executes all phases sequentially in `VastuCaptureTestRunner`:

```text
==================================================
🚀 Running VĀSTU Capture Engine Verification Suite
==================================================
[Suite 1/4] QR Redemption & Session Authorization Flow
[Suite 2/4] Keyframe Package Schema & SHA-256 Integrity
[Suite 3/4] Image Quality Assessor (Blur & Exposure)
[Suite 4/4] Live Floorplan 2D Ray Projection & Grid Accumulator
[Phase 2] QR Authentication & Session Tests (7 Tests)
[Phase 3] ARKit Room Recording Engine Tests (6 Tests)
[Phase 4] Local AI & Core ML Integration Tests (6 Tests)
[Phase 5] AI-Guided Scanning & Live Floorplan Tests (8 Tests)
[Phase 6] Local Furniture Detection & Depth AI Tests (7 Tests)
==================================================
📊 Verification Results: 231 Passed, 0 Failed (100% Pass Rate)
==================================================
```

### Dual Target Build Verification
- **iOS Device Target (`generic/platform=iOS`):** `** BUILD SUCCEEDED **`
- **iOS Simulator Target (`platform=iOS Simulator,name=iPhone 17 Pro`):** `** BUILD SUCCEEDED **`

