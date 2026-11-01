"""CPU-only contract regression: independent projections and corrupt package inputs."""
import json
from pathlib import Path
import uuid

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from core.coordinates.conventions import (
    CameraPose, CameraIntrinsics, image_rotation_homography,
    quaternion_to_rotation_matrix,
)
from core.schemas.capture_package_v1 import CaptureManifestV1, CameraPoseRecord, CameraIntrinsicsRecord
from core.packaging.keyframe_package import write_package
from core.packaging.capture_adapter import adapt_capture, prepare_worker_input
from core.validation.package_validator import validate_package, sha256


@pytest.fixture
def package(tmp_path):
    source = tmp_path / 'source.jpg'
    assert cv2.imwrite(str(source), np.full((48, 64, 3), 120, np.uint8))
    calibration = CameraIntrinsicsRecord(fx=50, fy=52, cx=32, cy=24, image_width=64, image_height=48)
    poses = []
    for index in range(3):
        matrix = np.eye(4)
        matrix[:3, 3] = [index * 0.2, 1.5, 0.1]
        poses.append(CameraPoseRecord(frame_id=f'frame_{index:06d}.jpg', timestamp_ns=1000 + index * 100,
                                     T_world_camera=matrix.tolist(), image_width=64, image_height=48))
    manifest = CaptureManifestV1(session_id='synthetic', device_model='SYNTHETIC', frame_count=3,
                                 capture_start_ns=1000, capture_end_ns=1200)
    return write_package(tmp_path / 'capture_synthetic', manifest, [calibration], poses,
                         {p.frame_id: source for p in poses})


def rehash(root):
    files = sorted(p for p in root.rglob('*') if p.is_file() and p.name != 'checksums.sha256')
    (root / 'checksums.sha256').write_text(''.join(f'{sha256(p)}  {p.relative_to(root).as_posix()}\n' for p in files))


def change_pose(root, edit):
    path = root / 'tracking/camera_poses.jsonl'
    records = [json.loads(line) for line in path.read_text().splitlines()]
    edit(records)
    path.write_text(''.join(json.dumps(record) + '\n' for record in records))
    rehash(root)


def test_package_roundtrip_and_worker_layout(package, tmp_path):
    capture = validate_package(package)
    assert capture.manifest.frame_count == 3
    assert capture.poses[0].exposure_time_s is None
    output = prepare_worker_input(package, tmp_path / 'work')
    assert Path(output['keyframes'][0]['file_path']).is_file()
    assert output['reprojection_rms_px'] is None
    assert output['intrinsics'] == [50, 52, 32, 24]
    assert output['pose_direction'] == 'world_to_camera'
    np.testing.assert_allclose(output['poses'][2]['camera_center_m'], [0.4, 1.5, 0.1])
    with pytest.raises(FileExistsError):
        prepare_worker_input(package, tmp_path / 'work')


def test_actual_sfm_worker_boundary(package, tmp_path):
    from workers.stages.stage02_sfm import SfMWorker
    from workers.base import WorkerContext
    from core.domain.enums import WorkerStatus
    worker = SfMWorker()
    context = WorkerContext(job_id=uuid.uuid4(), project_id=uuid.uuid4(), work_dir=str(tmp_path / 'worker'),
                            params={'capture_package_dir': str(package)})
    result = worker.execute(context)
    assert result.status == WorkerStatus.SUCCESS, result.error_message
    payload = json.loads(Path(result.artifacts['camera_poses']).read_text())
    assert payload['pose_refinement'] == 'NOT PERFORMED'
    assert payload['poses'][1]['reprojection_error'] is None


@pytest.mark.parametrize('corruption,match', [
    ('checksum', 'SHA-256'), ('missing', 'missing required'), ('extra', 'checksum inventory'),
    ('image', 'undecodable'), ('dimensions', 'wrong dimensions'), ('timestamp', 'nonmonotonic'),
    ('association', 'duplicate'), ('calibration', 'unknown intrinsics'), ('rotation', 'orthonormal'),
    ('nonfinite', 'finite'), ('orientation', 'orientation mismatch'), ('interval', 'outside capture'),
])
def test_corrupted_packages_rejected(package, corruption, match):
    first_image = package / 'frames/frame_000000.jpg'
    if corruption == 'checksum':
        first_image.write_bytes(b'corrupt')
    elif corruption == 'missing':
        (package / 'session_metadata.json').unlink()
    elif corruption == 'extra':
        (package / 'unchecked.txt').write_text('unchecked')
    elif corruption == 'image':
        first_image.write_bytes(b'not an image'); rehash(package)
    elif corruption == 'dimensions':
        cv2.imwrite(str(first_image), np.zeros((10, 10, 3), np.uint8)); rehash(package)
    else:
        def edit(records):
            if corruption == 'timestamp': records[1]['timestamp_ns'] = records[0]['timestamp_ns']
            if corruption == 'association': records[1]['frame_id'] = records[0]['frame_id']
            if corruption == 'calibration': records[1]['intrinsics_id'] = 'missing'
            if corruption == 'rotation': records[1]['T_world_camera'][0][1] = 0.4
            if corruption == 'nonfinite': records[1]['T_world_camera'][0][3] = float('nan')
            if corruption == 'orientation': records[1]['image_orientation'] = 'portrait'
            if corruption == 'interval': records[-1]['timestamp_ns'] = 99999
        change_pose(package, edit)
    with pytest.raises(ValueError, match=match):
        validate_package(package)


def test_path_traversal_and_symlinks(package, tmp_path):
    path = package / 'checksums.sha256'
    original = path.read_text()
    path.write_text(original + '0' * 64 + '  ../outside.jpg\n')
    with pytest.raises(ValueError, match='unsafe'):
        validate_package(package)
    path.write_text(original)
    (package / 'escape').symlink_to(tmp_path)
    with pytest.raises(ValueError, match='symlink'):
        validate_package(package)


def test_unsupported_manifest_contract(package):
    path = package / 'manifest.json'
    original = json.loads(path.read_text())
    for key, value in [('schema_version', '9.0'), ('units', 'millimeters'), ('world_convention', 'RIGHT_HANDED_Z_UP'),
                       ('timestamp_domain', 'unix_epoch_ns'), ('image_orientation', 'portrait')]:
        path.write_text(json.dumps({**original, key: value})); rehash(package)
        with pytest.raises(ValueError): validate_package(package)


def test_tracking_and_variable_calibration_not_silently_accepted(package):
    change_pose(package, lambda r: r[1].update(tracking_state='LIMITED_RELOCALIZING'))
    validate_package(package)  # Capture contract retains degraded observations.
    with pytest.raises(ValueError, match='TRACKING_FAILURE'): adapt_capture(package)
    change_pose(package, lambda r: r[1].update(tracking_state='NORMAL', intrinsics_id='other'))
    path = package / 'calibration/camera_intrinsics.json'
    calibrations = json.loads(path.read_text())
    calibrations.append({**calibrations[0], 'calibration_id': 'other', 'fx': 51})
    path.write_text(json.dumps(calibrations)); rehash(package)
    with pytest.raises(ValueError, match='constant calibration'): adapt_capture(package)


def test_identity_translation_rotation_inversion():
    K = CameraIntrinsics(400, 420, 320, 240, 640, 480)
    identity = CameraPose(np.eye(3), np.zeros(3))
    uv, depth = identity.project_point([1, 1, -4], K)
    np.testing.assert_allclose(uv, [420, 135])  # Independent expected pixel: up must decrease v.
    assert depth == 4
    yaw = np.pi / 2
    R = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]])
    pose = CameraPose(R, [2, 1.5, 3])
    np.testing.assert_allclose(pose.project_point([-2, 1.5, 3], K)[0], [320, 240])
    cv_pose = pose.to_opencv()
    Rcw, tcw = cv_pose.world_to_camera_transform()
    inverse = np.eye(4); inverse[:3, :3] = Rcw; inverse[:3, 3] = tcw
    np.testing.assert_allclose(inverse @ cv_pose.T_4x4, np.eye(4), atol=1e-12)
    np.testing.assert_allclose(cv_pose.to_arkit().T_4x4, pose.T_4x4)
    np.testing.assert_allclose(CameraPose.from_quaternion_translation(pose.quaternion, pose.t).T_4x4, pose.T_4x4, atol=1e-12)


def test_synthetic_room_independent_opencv_projection(package):
    payload = adapt_capture(package)
    K = np.array([[50, 0, 32], [0, 52, 24], [0, 0, 1]], dtype=float)
    corners = np.array([[-2, 0, -4], [2, 0, -4], [2, 3, -4], [-2, 3, -4]], dtype=float)
    intrinsics = CameraIntrinsics(50, 52, 32, 24, 64, 48)
    for record, converted in zip(validate_package(package).poses, payload['poses']):
        R = np.asarray(converted['R']); t = np.asarray(converted['t'])
        pixels, _ = cv2.projectPoints(corners, cv2.Rodrigues(R)[0], t, K, None)
        original = CameraPose.from_4x4(record.T_world_camera)
        for point, expected in zip(corners, pixels.reshape(-1, 2)):
            uv, depth = original.project_point(point, intrinsics)
            assert np.linalg.norm(uv - expected) < 1e-6
            np.testing.assert_allclose(original.backproject_pixel(*uv, depth, intrinsics), point, atol=1e-10)
        assert pixels[0, 0, 0] < pixels[1, 0, 0]  # No left/right mirror.
        assert pixels[0, 0, 1] > pixels[3, 0, 1]  # Floor below ceiling in image.


@pytest.mark.parametrize('turns,expected', [(0, [10, 20, 1]), (1, [27, 10, 1]), (2, [53, 27, 1]), (3, [20, 53, 1])])
def test_image_orientation_pixel_centers(turns, expected):
    H = image_rotation_homography(64, 48, turns)
    np.testing.assert_allclose(H @ [10, 20, 1], expected)
    image = np.zeros((48, 64), np.uint8); image[20, 10] = 255
    rotated = np.rot90(image, -turns)
    assert rotated[expected[1], expected[0]] == 255


@pytest.mark.parametrize('kind', ['shear', 'nan_translation', 'bad_bottom', 'reflection', 'nan_quaternion', 'nan_intrinsics'])
def test_invalid_spatial_inputs(kind):
    with pytest.raises(ValueError):
        T = np.eye(4)
        if kind == 'shear': T[0, 1] = 0.5
        if kind == 'nan_translation': T[0, 3] = np.nan
        if kind == 'bad_bottom': T[3, 0] = 1
        if kind == 'reflection': T[0, 0] = -1
        if kind == 'nan_quaternion': quaternion_to_rotation_matrix([np.nan, 0, 0, 1]); return
        if kind == 'nan_intrinsics': CameraIntrinsics(np.nan, 1, 1, 1, 2, 2); return
        CameraPose.from_4x4(T)


def test_calibration_nonfinite_rejected():
    with pytest.raises(ValidationError):
        CameraIntrinsicsRecord(fx=np.inf, fy=50, cx=32, cy=24, image_width=64, image_height=48)
