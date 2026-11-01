# VĀSTU v3.0 — FINAL MASTER ARCHITECTURE & IMPLEMENTATION PLAN

Version: 3.0  
Status: Engineering implementation baseline  
Date: October 2026  

ZERO-LIDAR CAPTURE · METRIC ARCHITECTURAL GEOMETRY · PHOTOREALISTIC 3DGS · COLLISION-AWARE FREE ROAMING

============================================================
1. PRODUCT VISION
============================================================

VĀSTU is an end-to-end spatial computing platform that converts smartphone RGB imagery and visual-inertial tracking into three synchronized representations of indoor environments.

A. ARCHITECTURAL DIGITAL TWIN
- Metric walls, floors, ceilings, corners, doors, windows, columns, and recesses.
- Confidence-aware topology and geometric regularization.
- Measurable dimensions and architectural floor plans.

B. PHOTOREALISTIC DIGITAL TWIN
- 3D Gaussian Splatting trained from calibrated imagery.
- View-dependent visual appearance and furniture detail.
- Compressed SPZ assets for web delivery.
- Explicit identification of poorly observed viewpoints.

C. NAVIGABLE DIGITAL TWIN
- Walkable floor regions.
- Physical wall and furniture collisions.
- Desktop WASD/mouse and mobile touch navigation.
- Mini-map, optional route planning, and architectural overlays.

The three representations share one metric coordinate system but remain independent assets.

PRIMARY PRINCIPLES
1. No LiDAR dependency in the reconstruction pipeline.
2. Supported ARKit-compatible iPhones first; ARCore later.
3. Capture quality and camera-pose reliability come before reconstruction complexity.
4. Learned depth and normals are uncertain priors, not physical ground truth.
5. Multiview geometry and validated metric anchors establish consistency.
6. Architectural regularization must preserve genuine nonorthogonal structures.
7. Quality gates determine whether results are accepted, retried, or recaptured.
8. Every uncertain dependency requires a time-boxed validation spike.
9. Every performance and accuracy claim requires benchmark evidence.
10. Geometry, appearance, and navigation may fail or recover independently.

NON-GOALS FOR V1
- Universal support for every smartphone.
- Guaranteed perfect geometry.
- Guaranteed reconstruction of completely occluded surfaces.
- Physically accurate mirror and glass rendering.
- Guaranteed 15 MB files or 60 FPS on arbitrary hardware.
- Complete BIM authoring or multi-floor building reconstruction.

============================================================
2. SYSTEM ARCHITECTURE
============================================================

IOS CAPTURE APPLICATION
  |
  |-- ARKit visual-inertial tracking
  |-- RGB image recording
  |-- Intrinsics and pose logging
  |-- Tracking confidence monitoring
  |-- Floor anchoring
  |-- Boundary observations
  |-- Keyframe quality selection
  |-- Coverage mini-map
  |-- Guided infill and targeted recapture
  |
  v
CAPTURE PACKAGE
  |
  |-- Versioned manifest
  |-- Calibrated keyframes
  |-- Camera-to-world poses
  |-- Tracking events
  |-- Floor and semantic observations
  |-- Integrity checksums
  |
  v
INGESTION AND VALIDATION
  |
  |-- File integrity
  |-- Coordinate normalization
  |-- Timestamp validation
  |-- Calibration validation
  |-- Pose continuity
  |-- Coverage assessment
  |
  v
POSE REFINEMENT
  |
  |-- Feature extraction
  |-- LightGlue matching
  |-- Geometric outlier rejection
  |-- Multiview triangulation
  |-- Bundle adjustment with metric priors
  |-- Loop closure and drift analysis
  |
  +-----------------------------+
  |                             |
  v                             v
GEOMETRY PIPELINE          APPEARANCE PIPELINE
  |                             |
  |-- Multiview stereo          |-- Image preparation
  |-- Metric depth priors       |-- Pose registration
  |-- Normal estimation         |-- 3DGS initialization
  |-- Semantic masking          |-- gsplat optimization
  |-- Confidence fusion         |-- Held-out evaluation
  |-- Structural planes         |-- Artifact cleanup
  |-- Topology recovery         |-- Quantization
  |-- Architectural mesh        |-- SPZ export
  |                             |
  v                             |
NAVIGATION PIPELINE             |
  |                             |
  |-- Collision geometry        |
  |-- Furniture obstacles       |
  |-- Walkable surfaces         |
  |-- Navmesh generation        |
  |                             |
  +--------------+--------------+
                 |
                 v
ASSET MANIFEST + QUALITY GATES
                 |
                 v
WEB VIEWER
  |
  |-- Three.js scene
  |-- Gaussian splat renderer
  |-- Architectural overlays
  |-- Collision controller
  |-- Desktop and mobile input
  |-- Mini-map and optional A* routing
  |-- Adaptive performance
  |-- Mesh-only fallback

============================================================
3. PHASE 0 — VALIDATION SPIKES
============================================================

Duration: Weeks 1–3.

S1: ARKIT METRIC SCALE AND DRIFT

Dataset:
- Five measured rooms.
- Empty, furnished, L-shaped, low-texture, and bright-window scenes.
- Two non-LiDAR iPhones.
- Three capture runs per room and device.

Ground truth:
- Laser distance meter for wall lengths and diagonals.
- Independently measured ceiling height.
- Digital level where necessary.

Measurements:
- Scale ratio.
- Loop-closure translation and rotation error.
- Trajectory consistency.
- Tracking interruptions.
- Run-to-run variation.

Provisional pass target:
- Scale error <= 2%.
- Loop gap <= 5 cm over a 15–20 m perimeter.

These thresholds are spike decision criteria, not product guarantees.

Fallback:
- Require a known-length reference, user-measured wall, or calibrated marker.
- Reassess dimensional accuracy gates after scale correction.

S2: GAUSSIAN SPLAT RENDERER

Evaluate at least three renderer candidates, including Spark and PlayCanvas where compatible.

Devices:
- Reference laptop.
- Supported iPhone.
- Mid-range Android browser.

Measure:
- Actual SPZ compatibility.
- Conversion requirements.
- Initial load latency.
- p95 frame time.
- Peak memory.
- Visual fidelity.
- Maintenance and license status.

Pass:
- At least one renderer supports an adaptive mobile profile near or above 30 FPS on defined reference devices.

Fallback:
- Mesh-only mobile rendering.
- Gaussian splats on supported desktop hardware.

S3: DEPTH, NORMALS, AND LICENSING

Benchmark:
- Depth Anything V2 Small.
- UniDepth.
- Metric3D v2.
- MoGe.
- DSINE or an alternative normal estimator.

Verify exact checkpoint licenses, dependencies, and commercial deployment rights.

Evaluate:
- Depth accuracy after shared metric alignment.
- Multiview consistency.
- Blank-wall performance.
- Reflective-surface failure modes.
- Runtime and GPU memory.
- Normal agreement.

Fallback:
- Multiview stereo as the primary measurement source.
- Monocular depth as a low-confidence prior.

S4: ON-DEVICE SEGMENTATION

Evaluate a Core ML floor/wall segmentation model on at least 200 labeled room frames.

Measure:
- Floor-wall boundary accuracy.
- Inference latency.
- Energy consumption.
- Memory.
- Five-minute thermal stability.

Provisional pass:
- Useful boundary inference at >= 5 Hz without unacceptable thermal degradation.

Fallback:
- ARKit floor plane plus user-confirmed floor anchor.
- Ship semantic boundary inference in v1.1.

S5: COORDINATE CONVENTIONS

Define:
- World: right-handed, Y-up, meters.
- Internal pose: T_world_camera.
- ARKit camera: local -Z forward.
- OpenCV camera: +Z forward, +X right, +Y down.
- Explicit conversion at import/export boundaries.

For a camera-frame conversion, the Y/Z axis flip can be represented by diag(1,-1,-1), but full transform composition and image orientation must be tested.

Required:
- Synthetic projection/reprojection tests.
- Quaternion and matrix conversion tests.
- Image orientation and intrinsics tests.
- Real-scene validation.
- No mirrored or inverted output.

Provisional synthetic reprojection tolerance: < 1 pixel.

This spike is mandatory and has no bypass.

S6: EXISTING PIPELINE BASELINE

Run the existing reconstruction pipeline on all five reference rooms.

Record:
- Dimensional error.
- Wall flatness.
- Corner-angle error.
- Coverage.
- Reconstruction runtime.
- Failure rate.
- Visual artifacts.

Deliverable:
Six written spike decisions and one reproducible reference dataset.

============================================================
4. IOS CAPTURE APPLICATION
============================================================

Application: VastuCapture

The app launches directly into the capture interface.

STATE MACHINE

IDLE
  -> DEVICE_CHECK
  -> SESSION_CALIBRATION
  -> FLOOR_ANCHOR
  -> PERIMETER_OBSERVATION
  -> GUIDED_INFILL
  -> COVERAGE_VALIDATION
  -> FINALIZE
  -> UPLOAD

Additional states:
- TRACKING_RECOVERY
- TARGETED_RESCAN
- CAPTURE_FAILED
- UPLOAD_RETRY

4.1 DEVICE CHECK

Validate:
- ARWorldTrackingConfiguration support.
- Camera permission.
- Available storage.
- Camera calibration.
- Device thermal state.
- Adequate initial lighting.
- Tracking initialization.

Never assume all RGB + IMU smartphones support equivalent VIO.

4.2 FLOOR ANCHOR

Use:
- ARKit horizontal plane detection.
- Floor classification where available.
- User-confirmed floor point when needed.

Gravity determines floor orientation, not absolute elevation.

Validate floor elevation against later boundary observations.

Start with a configurable disagreement threshold near 10 cm, then tune experimentally.

4.3 PERIMETER RECONNAISSANCE

The original mandatory 30-second scan is replaced by quality-driven observation.

Procedure:
1. Establish a stable tracking origin.
2. Guide the operator along accessible room boundaries.
3. Observe floor-wall boundaries.
4. Detect candidate boundary pixels.
5. Back-project rays using calibrated camera intrinsics.
6. Intersect rays with a validated floor plane.
7. Reject nearly parallel rays and low-confidence observations.
8. Accumulate top-down boundary evidence.
9. Identify observed corners, recesses, and alcoves.
10. Mark unobserved regions as unknown.

The live blueprint is provisional until backend validation.

4.4 GUIDED INFILL

Capture:
- Every accessible wall.
- Floor-wall junctions.
- Ceiling-wall junctions.
- Doors and windows.
- Structural corners.
- Furniture from multiple accessible viewpoints.

Coverage confidence combines:
- Visible area.
- Viewing-angle diversity.
- Translational parallax.
- Tracking quality.
- Image sharpness.
- Exposure.
- Semantic confidence.

Do not equate high frame overlap with reconstruction completeness.

4.5 KEYFRAME SELECTION

Accept candidate keyframes based on:
- New visual coverage.
- Translation.
- Rotation.
- Sharpness.
- Exposure quality.
- Feature distribution.
- Tracking confidence.

Pure rotation can add useful appearance observations but does not create triangulation baseline.

Do not reject low-texture walls automatically.

Use classical blur metrics and clipping analysis before introducing a dedicated learned blur network.

Thresholds should be calibrated per device and session.

4.6 CAPTURE CONTROL

Where supported:
- Configure stable exposure.
- Configure white balance.
- Configure focus.

Record actual capture parameters.

Do not assume all ARKit camera streams permit independent AVFoundation manual controls.

If controls are unavailable, preserve metadata and compensate during reconstruction.

4.7 CAPTURE COMPLETION

Provisional coverage targets:
- >= 90% observable structural wall coverage.
- Explicit floor and ceiling coverage assessments.
- Sufficient multiview baseline for important surfaces.

Allow documented exceptions for occluded or inaccessible surfaces.

Do not manufacture missing geometry to satisfy a coverage percentage.

4.8 FIELD ACCEPTANCE

Run at least 20 field sessions across two supported devices.

Initial target:
- >= 90% complete without manual recovery.

Record recapture frequency, operator time, tracking failures, and battery consumption.

============================================================
5. CAPTURE PACKAGE AND DATA CONTRACT
============================================================

capture_<session_id>/
  manifest.json
  session_metadata.json
  calibration/
    camera_intrinsics.json
    lens_metadata.json
  tracking/
    camera_poses.jsonl
    tracking_events.jsonl
    anchors.json
  frames/
    frame_000001.jpg
    ...
  observations/
    floor_boundaries.jsonl
    semantic_masks/
    coverage.json
  checksums.sha256

Use selected high-quality keyframes as the primary reconstruction input.

An optional lower-resolution video track may preserve capture continuity.

Manifest fields:
- schema_version
- session_id
- device_model
- OS_version
- camera_convention
- world_convention
- image_orientation
- units
- calibration_identifier
- frame_count
- capture_start/end
- integrity checksums

Per-frame fields:
- frame_id
- monotonic timestamp
- T_world_camera
- intrinsics identifier
- image dimensions
- image orientation
- tracking state
- exposure time
- ISO
- white balance metadata
- focus/lens metadata where available
- rolling shutter metadata where available

Schema rules:
- Required versus optional fields must be explicit.
- Unavailable hardware metadata must not invalidate otherwise usable sessions.
- Reject invalid required data.
- Validate monotonic timestamps.
- Validate rotation orthonormality.
- Version schema migrations.
- Maintain stable frame identifiers.

============================================================
6. CAMERA POSE REFINEMENT
============================================================

Inputs:
- ARKit VIO poses.
- Camera intrinsics.
- RGB keyframes.
- Optional metric reference.

Pipeline:
1. Extract local image features.
2. Match frames with LightGlue or a validated equivalent.
3. Reject geometrically inconsistent correspondences.
4. Triangulate sparse landmarks.
5. Build multiview tracks.
6. Run bundle adjustment with VIO pose priors.
7. Detect loop closure.
8. Validate metric scale.
9. Measure refinement divergence.
10. Export final poses and quality report.

Do not perform unconstrained similarity alignment that silently destroys metric scale.

When optimizing scale, constrain it using validated physical measurements or VIO priors.

Output:
pose_quality.json

Metrics:
- Reprojection RMS.
- Feature inlier ratio.
- Loop-closure residual.
- Translation drift.
- Rotation drift.
- Scale correction.
- Tracking confidence.

Provisional targets:
- Reprojection RMS around or below 1 pixel on reference scenes.
- Investigate unexpected scale changes above approximately 2%.

A low reprojection error alone does not establish metric accuracy.

============================================================
7. DEPTH AND SURFACE NORMAL RECONSTRUCTION
============================================================

7.1 PRIMARY GEOMETRIC EVIDENCE

Use multiview stereo and triangulation where sufficient image texture and baseline exist.

7.2 LEARNED DEPTH PRIOR

Use a commercially permitted metric depth model selected through S3.

Monocular depth contributes:
- Blank-wall priors.
- Dense initialization.
- Low-texture support.
- Additional confidence estimates.

Do not treat monocular metric output as calibrated ground truth.

7.3 SCALE AND SHIFT ALIGNMENT

Fit depth calibration using shared multiview landmarks and metric anchors.

Avoid unconstrained independent per-frame scale/shift corrections.

Preferred strategy:
- Shared metric coordinate system.
- Robust global or temporally regularized calibration.
- Per-frame residual diagnostics.
- Cross-view consistency penalties.
- Rejection of inconsistent predictions.

For inverse-depth predictors, calibrate in the appropriate inverse-depth domain rather than assuming a metric-depth affine transform.

Sparse alignment residuals provide useful evidence but are not a complete uncertainty estimate.

7.4 NORMAL CONSISTENCY

For camera intrinsics K and depth D:

P(u,v) = D(u,v) K^-1 [u,v,1]^T

Geometric normals derive from:

n_D = normalize(dP/du × dP/dv)

Compare n_D with predicted normals after transforming both into the same coordinate frame.

Normal disagreement becomes a confidence penalty.

Do not hard-force all surfaces to match learned normal predictions.

7.5 MULTIVIEW FUSION

Use confidence-weighted point fusion or TSDF.

Preserve:
- Observation count.
- Depth uncertainty.
- View consistency.
- Semantic confidence.
- Pose confidence.
- Visibility.

Thresholds should depend on depth and uncertainty.

Do not use a universal 3 cm fusion cutoff.

============================================================
8. SEMANTICS, FURNITURE, AND REFLECTIONS
============================================================

8.1 STRUCTURAL CLASSES

- Wall
- Floor
- Ceiling
- Door
- Window
- Column
- Structural recess

8.2 NONSTRUCTURAL CLASSES

- Bed
- Chair
- Table
- Cabinet
- Other movable furniture
- Person
- Pet
- Temporary clutter

8.3 FURNITURE PIPELINE

2D open-vocabulary detection
  -> Instance segmentation
  -> Depth-based lifting
  -> Multiview association
  -> 3D clustering
  -> Oriented bounding box fitting

Use furniture masks to reduce structural plane contamination.

Keep conservative furniture collision geometry independent from the architectural mesh.

8.4 MIRRORS AND GLASS

Detect reflective/transparent surfaces using semantic evidence and multiview inconsistency.

Prevent unreliable reflected geometry from entering:
- Architectural plane fitting.
- Depth fusion.
- Physical collision geometry.

For 3DGS, evaluate masking, specialized treatment, or visual fallback.

Do not automatically remove all mirrors from visual training if that destroys useful appearance; use measured quality to choose the treatment.

8.5 DYNAMIC OBJECTS

Mask people, pets, and moving objects during geometry fusion and 3DGS training where possible.

Test that dynamic-object artifacts do not become collision obstacles.

============================================================
9. ARCHITECTURAL GEOMETRY ENGINE
============================================================

9.1 FLOOR AND CEILING

Estimate candidate horizontal surfaces using:
- Gravity.
- Height distributions.
- Semantic labels.
- Multiview observations.

Validate floor and ceiling independently.

9.2 WALL EXTRACTION

1. Isolate structural points.
2. Project relevant points into the floor coordinate plane.
3. Detect candidate wall directions and 2D line segments.
4. Fit robust 3D wall planes.
5. Evaluate inlier ratios and residuals.
6. Identify dominant orientation groups.
7. Apply conditional geometric regularization.

9.3 PLANE EQUATION

For each plane:

n_i · X + d_i = 0

Use weighted point-to-plane residuals, semantic support, and normal agreement.

9.4 MANHATTAN / ATLANTA REGULARIZATION

Manhattan:
- Use when the evidence supports orthogonal wall directions.

Atlanta:
- Use for multiple dominant horizontal orientations.

Free-angle:
- Preserve irregular walls, bay windows, and other legitimate geometry.

Never force all corners to 90 degrees.

9.5 VERTEX SNAPPING

Snap only when:
- Plane confidence is sufficient.
- Residual RMS is acceptable.
- Semantic evidence supports the surface.
- Projection distance is within a validated tolerance.

At corners:
- Use intersections of accepted adjoining planes.
- Preserve topological continuity.
- Avoid snapping to only one of the two planes.

9.6 OPENINGS AND TOPOLOGY

Recover:
- Wall extents.
- Floor-wall intersections.
- Ceiling-wall intersections.
- Concave and convex corners.
- Doors.
- Windows.
- Columns.
- Recesses.
- Irregular footprints.

Do not interpret every unobserved region as an opening.

Mark ambiguous or occluded regions as uncertain.

9.7 OUTPUTS

geometry/
  architecture.glb
  collision.glb
  floorplan.geojson
  architectural_planes.json
  semantic_objects.json
  navmesh.bin
  geometry_quality.json

Per-wall quality:
- RMS residual.
- Surface coverage.
- Plane confidence.
- Orientation confidence.
- Dimensional uncertainty.

============================================================
10. PHOTOREALISTIC 3D GAUSSIAN SPLATTING
============================================================

Framework:
- gsplat or another benchmark-validated implementation.

Inputs:
- Validated keyframes.
- Refined camera poses.
- Sparse SfM points.
- Optional depth-supported initialization.
- Exposure metadata.
- Dynamic-object masks.

Training:
1. Prepare training and validation views.
2. Initialize Gaussian primitives.
3. Train baseline model.
4. Apply controlled densification.
5. Evaluate held-out views.
6. Extend training if metrics improve.
7. Prune low-value Gaussians.
8. Detect isolated floaters.
9. Quantize and export.
10. Verify browser compatibility.

ITERATION STRATEGY

Start around 15k iterations.
Extend toward 30k when convergence and validation metrics justify it.

Do not hardcode 30k as a universal quality requirement.

VALIDATION

Measure:
- PSNR.
- SSIM.
- LPIPS.
- Visual quality from held-out viewpoints.
- Floater frequency.
- Structural appearance stability.
- Asset size.
- Rendering speed.

Split validation by spatial coverage, not simply by every eighth frame, because adjacent video frames can be nearly identical.

EXPORT

appearance/
  scene_desktop.spz
  scene_mobile.spz
  appearance_quality.json
  training_manifest.json

Desktop:
- Higher splat count and visual detail.

Mobile:
- Lower splat count, reduced SH complexity, adaptive rendering.

Initial typical-room size target:
15–50 MB, to be confirmed by benchmarks.

No guarantee of exact size or appearance from unobserved viewpoints.

============================================================
11. NAVIGATION AND COLLISION
============================================================

Separate:
- Appearance splats.
- Architectural mesh.
- Collision mesh.
- Navigation mesh.

11.1 COLLISION

Use:
- Capsule or swept-sphere character collision.
- BVH-accelerated mesh queries where appropriate.
- Furniture OBBs or simplified colliders.
- Fixed-timestep movement.
- Collision sliding.
- Conservative doorway clearance.

Do not use Gaussian splats as physical collision surfaces.

11.2 NAVMESH

Generate walkable regions using a validated navmesh toolchain such as Recast.

Use the navmesh for:
- Valid walking regions.
- A* route planning.
- Reachability tests.

Collision and navmesh are complementary, not interchangeable.

11.3 DESKTOP CONTROLS

W — Forward
A — Left
S — Backward
D — Right
Mouse — Look
Shift — Sprint
Mini-map — Top-down view

Walking is constrained to valid surfaces while camera orientation remains freely controllable.

11.4 MOBILE CONTROLS

Left virtual joystick:
- Movement.

Right touch region:
- Camera look.

Additional controls:
- Mini-map toggle.
- Reset orientation.
- Walk speed settings.

11.5 CAMERA HEIGHT

Default approximately 1.65 m, configurable and clamped for clearance.

Do not derive a person's eye height solely from ceiling height.

11.6 COLLISION TESTS

Automate:
- Walking into walls.
- Sprinting into corners.
- Sliding along walls.
- Approaching furniture.
- Traversing valid doors.
- Rejecting narrow openings.
- Preventing out-of-bounds movement.

============================================================
12. WEB VIEWER
============================================================

Stack:
- React / Next.js.
- Three.js.
- Validated 3DGS renderer.
- Collision and navmesh libraries.
- Asset manifest loader.

Viewer components:
- Spatial3DViewer
- GaussianScene
- ArchitecturalOverlay
- FirstPersonController
- CollisionController
- MobileControls
- MiniMap
- AssetQualityIndicator

PERFORMANCE PROFILES

Desktop High:
- 60 FPS target on reference hardware.

Desktop Balanced:
- Adaptive resolution and splat budget.

Mobile:
- 30 FPS target on supported hardware.

Fallback:
- Architectural GLB visualization without splats.

Measure:
- p50/p95 frame time.
- Loading latency.
- GPU memory.
- Peak RAM.
- Splat decode time.
- Asset download size.
- Browser compatibility.

============================================================
13. BACKEND ORCHESTRATION
============================================================

Job states:

UPLOADED
  -> VALIDATING
  -> POSE_REFINEMENT
  -> GEOMETRY / APPEARANCE
  -> NAVIGATION
  -> PACKAGING
  -> QUALITY_CHECK
  -> READY

Independent branches execute concurrently after shared pose dependencies complete.

Requirements:
- Durable queue.
- GPU workers.
- Idempotency keys.
- Per-stage checkpoints.
- Model and configuration versioning.
- Retry policies.
- Structured logs.
- Artifact checksums.
- Reproducible manifests.

Failure categories:
- INPUT_INVALID
- TRACKING_FAILURE
- RETRYABLE
- MODEL_FAILURE
- RESOURCE_EXHAUSTED
- QUALITY_GATE_FAILED

Do not repeat expensive successful stages when only a downstream asset fails.

============================================================
14. REPOSITORY STRUCTURE
============================================================

vastu/
  apps/
    ios-capture/
      VastuCapture/
        App/
        Camera/
          ARSessionManager.swift
          FrameRecorder.swift
          CameraCalibration.swift
        Capture/
          CaptureStateMachine.swift
          FloorAnchorEstimator.swift
          BoundaryObservationEngine.swift
          KeyframeSelector.swift
          CoverageTracker.swift
        ML/
          ImageQualityEvaluator.swift
          SemanticInferenceEngine.swift
        UI/
          CaptureView.swift
          MiniMapHUD.swift
          CaptureGuidanceView.swift
        Export/
          CapturePackageWriter.swift

    web/
      src/
        app/
        components/viewer/
          Spatial3DViewer.tsx
          GaussianScene.tsx
          ArchitecturalOverlay.tsx
          FirstPersonController.ts
          CollisionController.ts
          MobileControls.tsx
          MiniMap.tsx
        lib/spatial/
          coordinates.ts
          assets.ts
          navigation.ts

  services/
    api/
      routes/
      schemas/
      storage/

    reconstruction/
      ingest/
      calibration/
      poses/
        matching.py
        bundle_adjustment.py
        pose_validation.py
      depth/
        estimator.py
        normals.py
        fusion.py
      semantics/
        segmentation.py
        object_fusion.py
      geometry/
        planes.py
        topology.py
        regularization.py
        mesh_export.py
      splatting/
        train.py
        evaluate.py
        export_spz.py
      navigation/
        collision.py
        navmesh.py
      pipeline.py

  packages/
    capture-schema/
    spatial-schema/
    asset-manifest/

  benchmarks/
    capture/
    geometry/
    appearance/
    viewer/

  tests/
  infra/
  docs/

This is a target structure, not an instruction to delete or blindly replace existing working modules.

============================================================
15. BENCHMARK AND ACCEPTANCE PLAN
============================================================

Reference dataset:
- Five rooms in Phase 0.
- Expand to 15–20 rooms before production release.

Ground truth:
- Laser-measured wall dimensions.
- Room diagonals.
- Ceiling height.
- Verified corner angles.
- Structural landmarks.

PROVISIONAL PRODUCT TARGETS

Metric dimensions:
<= 3 cm or 1%, whichever is larger, on validated reference rooms.

Planar wall residual:
<= 1.5 cm RMS on verified planar surfaces.

Manhattan corner angle:
<= 1 degree where orthogonality is independently verified.

Observable structural coverage:
>= 90%.

Desktop rendering:
p95 frame time <= 16.7 ms on reference hardware.

Mobile rendering:
p95 frame time <= 33.3 ms on supported hardware.

Collision:
No penetration beyond numerical tolerance in automated tests.

Processing reliability:
>= 95% successful processing of valid benchmark captures.

These are targets, not current performance claims.

Report accuracy separately for:
- Empty rooms.
- Furnished rooms.
- Low-texture rooms.
- Irregular rooms.
- Reflective rooms.
- Low-light rooms.

Every reconstruction-changing pull request should run representative regression tests.

Full GPU benchmarks may run in scheduled CI rather than on every PR when cost is excessive.

============================================================
16. PRIVACY, SECURITY, AND LICENSING
============================================================

Capture images can reveal private rooms, screens, documents, and personal belongings.

Requirements:
- Encrypted upload.
- Encryption at rest.
- Authenticated API access.
- Signed short-lived asset URLs.
- Configurable retention.
- Tested deletion.
- Restricted access to intermediate artifacts.
- Auditable sharing permissions.
- Privacy filtering for shared/exported assets.

Provide optional or policy-driven face, screen, and document redaction.

Retain unredacted originals only where explicitly authorized and necessary for reconstruction.

Maintain a license inventory for:
- Model weights.
- Datasets.
- Training frameworks.
- Segmentation models.
- Renderer libraries.
- Navigation libraries.

Block commercial deployment when required licenses remain unresolved.

============================================================
17. IMPLEMENTATION ROADMAP
============================================================

PHASE 0 — WEEKS 1–3
Validation spikes S1–S6.
Freeze schemas and coordinates.
Create reference dataset.
Establish existing pipeline baseline.

Exit:
Written decisions and reproducible measurements.

PHASE 1 — WEEKS 4–10
Capture application reliability.
Pose/frame synchronization.
Floor anchor.
Guided capture.
Keyframe gating.
Coverage HUD.
Field testing.

Exit:
>= 90% field-session completion target.

PHASE 2 — WEEKS 8–17
Pose refinement.
Depth and normal priors.
Multiview fusion.
Semantic segmentation.
Architectural topology.
Geometry validation.

Exit:
Reference rooms satisfy agreed accuracy gates.

PHASE 3 — WEEKS 14–21
3DGS training.
Held-out evaluation.
Pruning.
SPZ export.
Desktop/mobile asset tiers.

Exit:
Visual quality and reference-device loading tests pass.

PHASE 4 — WEEKS 18–24
Viewer integration.
Collision geometry.
Navmesh.
WASD controls.
Mobile controls.
Mini-map.
Adaptive rendering.

Exit:
Collision tests and reference-device FPS targets pass.

PHASE 5 — WEEKS 24–32
Reliability hardening.
Security and privacy.
Worker recovery.
Monitoring.
Compatibility tests.
Expanded benchmarks.
Release candidate.

Exit:
Production quality gates pass.

PLANNING RANGE:
Approximately 26–36 weeks for a small team, depending on staffing, parallelism, hardware, and existing code maturity.

============================================================
18. RISK REGISTER
============================================================

R1. VIO scale drift
Impact: High
Mitigation: S1, metric anchors, scale validation.

R2. Model commercial licensing
Impact: High
Mitigation: S3, checkpoint license inventory, alternative models.

R3. On-device thermal throttling
Impact: Medium
Mitigation: S4, asynchronous inference, staged ML deployment.

R4. Mobile splat rendering performance
Impact: High
Mitigation: S2, adaptive rendering, mesh fallback.

R5. Low-texture walls
Impact: High
Mitigation: Guided capture, MVS confidence, monocular priors, plane regularization.

R6. Mirrors and glass
Impact: Medium
Mitigation: Semantic detection, multiview inconsistency checks, selective exclusion.

R7. Pose/coordinate conversion errors
Impact: Critical
Mitigation: S5, synthetic and real reprojection tests.

R8. Overaggressive architectural snapping
Impact: High
Mitigation: Confidence thresholds, free-angle models, ground-truth validation.

R9. Incorrect collision geometry
Impact: High
Mitigation: Separate collision assets, conservative obstacles, automated tests.

R10. Processing cost and timeline growth
Impact: High
Mitigation: Checkpoints, caching, profiling, staged delivery, explicit phase gates.

============================================================
19. FIRST IMPLEMENTATION SPRINT
============================================================

SPRINT 1 — FOUNDATION

Task 1:
Define coordinate conventions and schema version 1.

Task 2:
Implement ARKit frame, camera pose, and intrinsics logging.

Task 3:
Add monotonic timestamps and tracking-state events.

Task 4:
Implement capture package writer and validator.

Task 5:
Build synthetic camera transform/reprojection tests.

Task 6:
Capture three measured rooms for initial smoke testing.

Task 7:
Run the current reconstruction pipeline on those captures.

Task 8:
Record baseline dimensional accuracy, tracking failures, processing time, and artifacts.

Definition of done:
- A valid capture package can be exported.
- Camera poses and images are correctly synchronized.
- Coordinate conversion passes tests.
- Existing backend accepts or can deterministically convert the package.
- Baseline reconstruction metrics are recorded.
- No unverified metric accuracy claim is made.

============================================================
20. RELEASE STRATEGY
============================================================

MILESTONE A — CAPTURE ALPHA
Reliable RGB + VIO capture and export.

MILESTONE B — GEOMETRY ALPHA
Measured room geometry with confidence reporting.

MILESTONE C — VISUAL ALPHA
Registered Gaussian splat appearance.

MILESTONE D — WALKTHROUGH BETA
Collision-aware desktop and mobile viewer.

MILESTONE E — PRODUCTION CANDIDATE
Security, reliability, compatibility, and benchmark acceptance.

Each milestone must be independently demonstrable.

============================================================
21. FINAL ENGINEERING DECISION
============================================================

VĀSTU is not one reconstruction model.

It is a validated spatial pipeline composed of:

1. Reliable visual-inertial capture.
2. Metric pose and depth reconstruction.
3. Confidence-aware architectural geometry.
4. Independent photorealistic 3DGS appearance.
5. Explicit physical navigation assets.
6. Quality-controlled web delivery.

Prioritize accurate measurements over visually perfect but false geometry.

Prioritize reliable capture over adding more neural models.

Prioritize independently testable components over one monolithic pipeline.

Prioritize demonstrated browser performance over fixed splat-count claims.

The first engineering investment is Phase 0 and Sprint 1.

END OF VĀSTU v3.0 MASTER PLAN.
