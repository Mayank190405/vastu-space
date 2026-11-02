# Phase 2: baseline, parallax, and metric scale

## Findings

The former Stage 01b estimate was not a metric baseline. It multiplied image flow by an assumed 2.2 m scene depth and a 0.05 factor, imposed a 0.002 m minimum per adjacent pair, and summed those values. Pure rotation, noise, and additional selected frames could all inflate the result. Neither the historical approximately 0.032 m result nor its stationary-pivot diagnosis is established by that computation.

The later `trajectory_parallax` implementation correctly used `C = -R.T @ t` for world-to-camera poses, but maximized separation across arbitrary pairs without checking overlap. Its trajectory used neural-depth-anchored PnP, which does not independently validate metric scale. A homography residual is also not proof of translation: planar scenes, mismatches, calibration errors, and rotation can affect it.

## Implemented behavior

`core/reconstruction/parallax.py` handles both explicit camera-to-world and world-to-camera poses and validates rotations. It reports rotation independently from camera-center displacement. Every candidate pair, including non-adjacent pairs, is matched using reciprocal SIFT ratio matches. Positive depth in both views and reprojection error filter triangulations. The diagnostics retain matched and valid correspondence counts separately, with feature overlap defined as reciprocal matches divided by the smaller detected-feature count.

Triangulation angles use corresponding rays transformed to the same world frame, removing camera rotation. A first-order uncertainty estimate combines pixel angular error, rotation uncertainty, and translation uncertainty. Missing uncertainty or unreliable poses reject verification. This is an approximate error model, not calibrated posterior covariance or proof that tracking is accurate. Calibration accuracy must be independently established for a verified use of the pose-bundle interface.

Keyframes are selected from accepted geometric pairs, greedily rewarding complementary image regions and correspondences. Sharpness, overlap, correspondence count, triangulation angle, baseline/depth ratio, and pose uncertainty are mandatory criteria. Several complementary pairs can contribute. Initial video samples are candidates only, rather than time-selected verified keyframes.

The retained 0.10 m threshold is configurable and advisory. A controlled 5 cm baseline passes for a close scene and fails at a greater depth; a controlled 20 cm baseline fails for a distant scene. The threshold was not reduced.

Metric scale requires a supported independent source (ARKit, calibrated VIO, reliable LiDAR, or a measured reference), validated tracking, an evidence reference, a positive conversion factor, and declared scale uncertainty at most 10%. These are input evidence requirements, not an automatic certification of an arbitrary uploaded assertion. No such evidence accompanies the original video. Predicted monocular depth is not accepted as an independent reference.

Essential-matrix unit translations are used only for diagnostic visualization. Their successive scales are not mutually observable; the code marks this explicitly and withholds both a metric baseline and a consistent input-unit baseline. It cannot infer physical camera motion from these poses. A pose bundle can provide externally validated poses and uncertainty for the standalone analyzer; the video reconstruction entrypoint has no independent metric input and therefore rejects video-only verification.

The production video path saves diagnostics and a `NEEDS_RESCAN` summary before depth inference, fusion, mesh generation, or publication. No synthetic walls or furniture are generated. Diagnostic trajectories are unverified and labelled `DEGRADED`. The older scalar-only baseline helper cannot authorize reconstruction. Preflight consumes the geometry decision and scale status. Rejected depth evidence no longer becomes a monocular-prior recovery, failed final gates reject publication, and distorted inputs must be undistorted before pinhole geometry.

## Reproduction

From the repository root, using the existing worker environment:

```sh
backend/workers/venv/bin/python -m pytest tests/test_phase2_parallax.py tests/test_reconstruction_alignment.py tests/test_preflight_and_supervisor.py tests/test_coordinate_conventions.py tests/test_capture_package_schema.py tests/test_capture_package_validator.py tests/test_reconstruction_safety.py -q
backend/workers/venv/bin/python scripts/analyze_capture_parallax.py --video IMG_3966.MOV --output phase2_diagnostics/IMG_3966 --samples 24
backend/workers/venv/bin/python scripts/reconstruct.py --video IMG_3966.MOV --output phase2_diagnostics/pipeline_IMG_3966
backend/workers/venv/bin/python scripts/analyze_capture_parallax.py --video IMG_4964.MOV --output phase2_diagnostics/IMG_4964 --samples 16
```

The production command is expected to exit 1 for `NEEDS_RESCAN`. The standalone diagnostic command completes successfully even when capture acceptance fails. Its JSON report, rather than exit success, defines acceptance. Unreadable sampled frames are recorded; pose-bound frames cannot be silently skipped.

The original capture is identified by `baseline_manifest.json` as `IMG_3966.MOV`. The additional `IMG_4964.MOV` analysis covers the older output with a 0.0313 m proxy result. Video hashes, decoded source-frame indices, calibration provenance, and diagnostic poses are preserved with standalone outputs. Existing reconstruction directories were not overwritten.

## Validation and limits

The final selected regression suite passed: **67 tests in 3.53 seconds**. The production reprocess evaluated 946 pairs (0 accepted); the standalone original-video analysis evaluated 276 pairs (0 accepted). The supplemental IMG_4964 analysis evaluated 105 pairs (0 accepted), with sampled frame 2095 unreadable and recorded in provenance. It covers all eight requested scenarios plus scale-unit conversion, unknown/high uncertainty, sharpness rejection, complementary non-adjacent pairs, independent rotation/translation, nonuniform monocular steps, and safety/coordinate/capture-package regressions. Exact results and execution logs are preserved under `phase2_diagnostics`.

The original capture is rejected with `NEEDS_RESCAN` and `SCALE_UNOBSERVABLE`. This validates the rejection behavior, not a physical 3.2 cm baseline or a claim of pure rotation. A trustworthy metric trajectory or independently measured reference is still needed to validate actual motion and scale. Recapture should use smooth sideways motion, sharp overlapping views of the same surfaces, and validated ARKit/VIO, reliable LiDAR, or another measured reference.

Phase 3 has not started. Synthetic geometry and selected Phase 1 regression checks passing do not establish full Phase 1/2 capture acceptance. The real capture remains unvalidated for verified metric reconstruction.
