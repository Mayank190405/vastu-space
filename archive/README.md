# VĀSTU Architecture Archive

This directory stores early research, phase-verification, and prototype scripts that have been superseded by the canonical modular architecture.

## Contents of `legacy_scripts/`:

1. **`build_diorama_twin.py`**: Early experimental script for rendering diorama-style floor cutouts. Superseded by `workers/stages/stage05_meshing.py`.
2. **`reconstruct_measured_space.py`**: Prototype for bounding-box constrained geometric reconstruction. Superseded by `geometry/planes.py` and `workers/stages/stage06_texturing.py`.
3. **`solve_pose_scale_rgbd.py`**: Standalone RGB-D camera scale solver. Incorporated into `workers/stages/stage02_sfm.py`.
4. **`run_first_scan.py`**: Prototype scan runner script. Superseded by `workers/pipeline.py`.
5. **`test1_two_view.py` through `test6_reprojection_validation.py`**: Step-by-step verification scripts used during initial pipeline algorithm research. Superseded by unified test suite in `tests/`.
6. **`test_tsdf_reconstruction.py`**: Experimental TSDF voxel grid integration test.
7. **`inspect_clouds_and_floor.py`**: Ad-hoc cloud inspection tool.

All active production algorithms live under `workers/stages/`, `geometry/`, `ml/`, and `navigation/`.
