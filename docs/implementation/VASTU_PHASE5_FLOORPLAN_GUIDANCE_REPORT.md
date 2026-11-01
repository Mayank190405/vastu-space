# VĀSTU Mobile App — Phase 5: AI-Guided Scanning & Live Floorplan Engineering Report

**Document Version:** 1.0.0  
**Phase Status:** Complete & Verified  
**Author:** VĀSTU Core Mobile Architecture Team  
**Verification:** 168 Unit & Integration Tests Passed (0 Failed) • Xcode Device & Simulator Build Succeeded  

---

## 1. Executive Summary

Phase 5 transitions the VĀSTU Capture native iOS application from a passive keyframe and pose logger into an **intelligent spatial guidance and live mapping system**. Operating completely on-device without cloud AI dependencies or LiDAR sensors, Phase 5 fuses ARKit visual-inertial odometry (VIO) with Phase 4 local Core ML semantic segmentation to construct a provisional 2D floorplan, track perimeter and angular coverage, detect degenerated camera motions (such as pure rotation), and provide real-time scanning instructions.

```text
ARKit Camera (60 Hz) + VIO Tracking
                 ↓
Phase 4 Local AI Segmentation (5-10 Hz Throttled)
                 ↓
Floor Plane Validation & Raycasting (FloorAnchorEstimator)
                 ↓
World-Space 2D Boundary Accumulator (WallBoundaryMapper)
                 ↓
Sequential RANSAC Wall Segment Fitting & Non-Orthogonal Preservation
                 ↓
Corner Intersection & Angle Detection (CornerDetectionEngine)
                 ↓
Parallax TRR & Rotation-Only Monitoring (ParallaxAnalyzer)
                 ↓
16-Sector Angular & Perimeter Coverage (RoomCoverageTracker)
                 ↓
Real-Time Cued Guidance State Machine (ScanGuidanceEngine)
                 ↓
Pre-Finish Quality Audit & Warning Gate (CaptureQualityEvaluator)
```

---

## 2. Core Mathematical & Algorithmic Modules

### 2.1 Floor Plane Estimation & Raycasting (`FloorAnchorEstimator.swift`)
- **Coordinate System:** Standard right-handed, metric $+Y$-up coordinate convention matching ARKit world space.
- **Ray-Plane Intersection:** Given camera position $\vec{C} = (C_x, C_y, C_z)$ and camera-space unit ray $\vec{r}_{cam}$, the world-space direction is obtained via camera rotation matrix:
  $$\vec{R}_{world} = \mathbf{R}_{c \rightarrow w} \cdot \vec{r}_{cam}$$
  For floor plane height $Y_{floor}$, with downward ray component $R_y < -0.05$:
  $$t = \frac{Y_{floor} - C_y}{R_y}$$
  Valid intersections require $0.25\text{m} \le t \le 7.50\text{m}$.
  World hit coordinates:
  $$P_x = C_x + t \cdot R_x, \quad P_z = C_z + t \cdot R_z$$
- **Confidence Attenuation:** Ray confidence decays linearly with distance $t$ to account for angular unprojection spread at long range:
  $$\text{conf}_{hit} = \text{conf}_{ray} \times \max\left(0.20, 1.0 - 0.6 \cdot \frac{t}{t_{max}}\right)$$

### 2.2 Spatial Binning & Sequential RANSAC Wall Fitting (`WallBoundaryMapper.swift`)
- **Grid Binning:** Discretizes the $(X, Z)$ ground plane into $6\text{cm} \times 6\text{cm}$ bins. Repeated observations accumulate hits, weighted spatial means, and confidence scores.
- **Sequential RANSAC Line Extraction:**
  Rather than naive Euclidean clustering (which merges adjacent walls meeting at corners into single V-shaped clusters), sequential RANSAC extracts linear wall segments iteratively:
  1. Identifies line candidates with inlier distance $\le 8\text{cm}$.
  2. Extracts wall segment using covariance eigen-decomposition on inlier points.
  3. Strips inliers from candidate pool and repeats.
- **Arbitrary Geometry Preservation:** Walls are not forced to $90^\circ$ right angles. Irregular architectures (e.g. $45^\circ$ bay windows, $120^\circ$ alcoves) are preserved.

### 2.3 Corner Intersection & Direct Observation (`CornerDetectionEngine.swift`)
- Computes intersection $P_{corner} = (x, z)$ of line equations:
  $$A_1 x + B_1 z = C_1, \quad A_2 x + B_2 z = C_2$$
  $$\det = A_1 B_2 - A_2 B_1$$
- Enforces endpoint proximity: $P_{corner}$ must lie within $0.65\text{m}$ of endpoints of both segments.
- Computes corner angle: $\theta = \arccos(|\vec{d}_1 \cdot \vec{d}_2|) \times \frac{180}{\pi}$.
- Verifies direct observation against local point cloud ($< 0.30\text{m}$).

### 2.4 Parallax & Pure Rotation Detection (`ParallaxAnalyzer.swift`)
- Pure rotation (spinning in place) produces zero baseline translation, causing visual feature tracking to degrade and photogrammetry bundle adjustment to fail.
- **Translation-to-Rotation Ratio (TRR):**
  $$\text{TRR} = \frac{\Delta \text{translation (m)}}{\Delta \text{rotation (rad)} + 10^{-4}}$$
  Over a rolling 2.0-second window, if rotation $> 0.45\text{ rad}$ ($\approx 25^\circ$) while translation $< 0.10\text{m}$, `isRotationOnly` is asserted, prompting the operator to step sideways.
- **Sufficient Parallax Gate:** Requires translation baseline $\ge 0.80\text{m}$, total path $\ge 1.20\text{m}$, and non-degenerate trajectory bounding area.

### 2.5 Multi-Dimensional Coverage Tracking (`RoomCoverageTracker.swift`)
- **Angular Coverage:** 16 radial sectors ($22.5^\circ$ each) around the room centroid track directional view diversity.
- **Perimeter Coverage:** Evaluates accumulated wall length against estimated room perimeter bounding box.

### 2.6 Scan Guidance & Pre-Finish Gate (`ScanGuidanceEngine.swift` & `CaptureQualityEvaluator.swift`)
- **Guidance State Machine Hierarchy:**
  1. *Tracking Loss / Safety (Alert):* Excessive motion, relocalizing, blank walls.
  2. *Visual Quality (Warning):* Motion blur, severe underexposure/glare.
  3. *Parallax Failure (Warning):* Pure rotation detected $\rightarrow$ `STEP_SIDEWAYS`.
  4. *Initial Baseline (Info):* Establishing initial $0.80\text{m}$ baseline.
  5. *Unscanned Corners (Info):* Prompting corner anchor capture.
  6. *Missing Wall Sectors (Info):* Directing to opposite wall.
  7. *Loop Closure (Info):* Return to starting doorway.
  8. *Completion (Success):* Full coverage and parallax verified.
- **Pre-Finish Warning Modal:** Warns operator if capture finalization is attempted prematurely.

---

## 3. Capture Package Integration

Timestamped boundary points are streamed during keyframe acquisition and saved to:
```text
capture_<session_id>/
├── manifest.json                  # Includes boundary_observations.jsonl entry
├── calibration.json               # ARKit camera intrinsics
├── camera_poses.jsonl             # 6-DoF poses with matching frame IDs
├── tracking_events.jsonl          # Session lifecycle and tracking state changes
├── boundary_observations.jsonl    # [Phase 5] Timestamped floor-wall contact points
├── frames/
│   ├── frame_000001.jpg
│   └── ...
└── checksums.sha256               # Verifies boundary_observations.jsonl integrity
```

---

## 4. Verification Results

### 4.1 Automated Test Suite Summary (`168 Passed, 0 Failed`)
- **Phase 1 (UI & Coordinator):** 16 assertions passed.
- **Phase 2 (QR Authentication & Anti-Replay):** 38 assertions passed.
- **Phase 3 (ARKit Zero-LiDAR Recording):** 37 assertions passed.
- **Phase 4 (Local Core ML Segmentation & Throttling):** 33 assertions passed.
- **Phase 5 (Live Floorplan, RANSAC, Parallax, Guidance):** 44 assertions passed:
  - `FloorAnchorEstimator`: Height calibration, accurate downward raycast, rejection of ceiling/out-of-range rays.
  - `WallBoundaryMapper`: Inlier extraction, non-orthogonal angle preservation ($45^\circ$, $120^\circ$).
  - `CornerDetectionEngine`: Exact $90^\circ$ corner detection, endpoint proximity gating.
  - `RoomCoverageTracker`: 16-sector radial sweep, perimeter tracking, missing sector listing.
  - `ParallaxAnalyzer`: Pure rotation detection, TRR thresholding, baseline displacement tracking.
  - `ScanGuidanceEngine`: Priority hierarchy from tracking alerts down to completion cues.
  - `CaptureQualityEvaluator`: Multi-factor audit ($0-100\%$) and pre-finish warning generation.
  - `End-to-End Simulation`: Multi-frame perimeter traversal loop with active guidance.

### 4.2 Xcode Compilation Verification
- **Physical Device Target (`generic/platform=iOS`):** `** BUILD SUCCEEDED **`
- **Simulator Target (`platform=iOS Simulator,name=iPhone 17 Pro`):** `** BUILD SUCCEEDED **`

---

## 5. Known Limitations & Mitigations

| Limitation | Impact | Mitigation Implemented |
|---|---|---|
| **Moving foreground obstacles** (e.g. pets, walking people) | Transient spurious boundary points | Minimum hit threshold in spatial grid cells ($N \ge 2$) and RANSAC line fitting reject transient points. |
| **Featureless glossy/mirrored surfaces** | ARKit tracking degradation | Tracking status monitor alerts operator and pauses keyframe logging during relocalization. |
| **Irregular room non-right angles** | Forced orthogonal assumption would distort geometry | Sequential RANSAC fits arbitrary linear angles without forcing right angles. |
| **Thermal throttling during prolonged capture** | Dropped UI frame rate | Inference scheduler throttles AI from 10 Hz down to 5 Hz under thermal pressure while preserving ARKit tracking. |

---

## 6. Readiness for Phase 6

Phase 5 is verified and production-ready. The codebase is prepared for:
**Phase 6 — Local Furniture Detection, Optional Monocular Depth AI, and Advanced Scene Understanding.**

