"""Explicit ARKit/OpenGL C2W → legacy OpenCV W2C boundary.

Does not estimate or refine supplied VIO poses; reprojection quality is unmeasured.
The canonical depth workers use a single K, so varying calibration is rejected
until those consumers accept per-frame calibration.
"""
from pathlib import Path
import json
import shutil
import tempfile

import numpy as np

from core.coordinates.conventions import CameraPose
from core.validation.package_validator import validate_package


def adapt_capture(directory) -> dict:
    capture = validate_package(directory)
    if len(capture.poses) < 2:
        raise ValueError('INPUT_INVALID: reconstruction requires at least two frames')
    first_calibration = capture.calibrations[capture.poses[0].intrinsics_id]
    signature = lambda c: (c.fx, c.fy, c.cx, c.cy, c.image_width, c.image_height)
    if any(signature(capture.calibrations[p.intrinsics_id]) != signature(first_calibration) for p in capture.poses):
        raise ValueError('INPUT_INVALID: legacy workers require constant calibration; per-frame K is not yet supported')
    keyframes, poses = [], []
    for index, record in enumerate(capture.poses):
        if record.tracking_state.value != 'NORMAL':
            raise ValueError(f'TRACKING_FAILURE: {record.frame_id}: recover tracking or select normal keyframes')
        pose = CameraPose.from_4x4(record.T_world_camera, capture.manifest.camera_convention).to_opencv()
        R, t = pose.world_to_camera_transform()
        keyframes.append({
            'frame_index': index, 'frame_id': record.frame_id,
            'timestamp_ns': record.timestamp_ns, 'is_keyframe': True,
            'file_path': str(capture.root / 'frames' / record.frame_id),
        })
        poses.append({
            'frame_index': index, 'timestamp_ns': record.timestamp_ns,
            'R': R.tolist(), 't': t.tolist(),
            'rotation_matrix': R.tolist(), 'translation_vector_m': t.tolist(),
            'camera_center_m': pose.t.tolist(),
            'quaternion_xyzw': CameraPose(R, np.zeros(3)).quaternion.tolist(),
            'tracking_source': 'DEVICE_VIO', 'reprojection_error': None,
        })
    c = first_calibration
    return {
        'schema_version': '1.0.0', 'session_id': capture.manifest.session_id,
        'camera_convention': 'OPENCV_RDF', 'pose_direction': 'world_to_camera',
        'world_convention': 'RIGHT_HANDED_Y_UP', 'units': 'meters',
        'intrinsics': [c.fx, c.fy, c.cx, c.cy], 'keyframes': keyframes,
        'poses': poses, 'pose_refinement': 'NOT PERFORMED', 'reprojection_rms_px': None,
    }


def prepare_worker_input(directory, work_dir) -> dict:
    """Materialize the layout the existing depth/mesh workers expect, without overwrites."""
    payload = adapt_capture(directory)
    work_dir = Path(work_dir).absolute()
    if work_dir.exists():
        raise FileExistsError(f'Refusing to overwrite reconstruction workspace: {work_dir}')
    work_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.ingest-', dir=work_dir.parent))
    try:
        (temporary / '01_keyframes').mkdir()
        (temporary / '02_sfm').mkdir()
        for frame in payload['keyframes']:
            target_name = f"frame_{frame['frame_index']:05d}.jpg"
            # Re-encode rather than renaming PNG bytes to a JPEG extension.
            import cv2
            image = cv2.imread(frame['file_path'], cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
            if not cv2.imwrite(str(temporary / '01_keyframes' / target_name), image):
                raise ValueError(f"Could not prepare frame {frame['frame_id']}")
            frame['file_path'] = str(work_dir / '01_keyframes' / target_name)
        (temporary / '01_keyframes/frame_metadata.json').write_text(json.dumps(payload['keyframes'], indent=2))
        (temporary / '02_sfm/camera_poses.json').write_text(json.dumps(payload, allow_nan=False, indent=2))
        if work_dir.exists():
            raise FileExistsError(f'Refusing to overwrite reconstruction workspace: {work_dir}')
        temporary.rename(work_dir)
    except Exception:
        shutil.rmtree(temporary)
        raise
    return payload
