"""V1 package boundary. No model initialization, archive extraction, or axis guessing."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import hashlib
import json
import re

import cv2

from core.schemas.capture_package_v1 import (
    CaptureManifestV1, CameraIntrinsicsRecord, CameraPoseRecord, TrackingStateEvent,
)


@dataclass
class ValidatedCapture:
    root: Path
    manifest: CaptureManifestV1
    calibrations: dict[str, CameraIntrinsicsRecord]
    poses: list[CameraPoseRecord]
    events: list[TrackingStateEvent]


def safe_path(root: Path, name: str) -> Path:
    """Accept portable relative paths only, rejecting symlinks at every level."""
    parts = PurePosixPath(name)
    if not name or '\\' in name or parts.is_absolute() or any(p in ('..', '.') for p in name.split('/')):
        raise ValueError(f"INPUT_INVALID: unsafe package path {name!r}")
    path = root
    for part in parts.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"INPUT_INVALID: symlink is not permitted: {name}")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path, model):
    result = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            raise ValueError(f"INPUT_INVALID: {path.name}:{line_number}: blank record")
        try:
            result.append(model.model_validate_json(line))
        except ValueError as exc:
            raise ValueError(f"INPUT_INVALID: {path.name}:{line_number}: {exc}") from exc
    return result


def validate_package(directory: str | Path) -> ValidatedCapture:
    root = Path(directory).absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("INPUT_INVALID: expected a package directory, not a symlink")
    required = {
        'manifest.json', 'session_metadata.json', 'calibration/camera_intrinsics.json',
        'tracking/camera_poses.jsonl', 'tracking/tracking_events.jsonl', 'checksums.sha256',
    }
    for name in sorted(required):
        if not safe_path(root, name).is_file():
            raise ValueError(f"INPUT_INVALID: missing required file {name}")
    # Inventory all files, including optional observations: no unchecked sidecars.
    files = set()
    for path in root.rglob('*'):
        name = path.relative_to(root).as_posix()
        safe_path(root, name)
        if path.is_file():
            files.add(name)
    checksums = {}
    for line in (root / 'checksums.sha256').read_text().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match:
            raise ValueError("INPUT_INVALID: checksums.sha256 requires '<sha256>  <relative path>'")
        digest, name = match.groups()
        safe_path(root, name)
        if name in checksums or name == 'checksums.sha256':
            raise ValueError(f"INPUT_INVALID: duplicate or recursive checksum: {name}")
        checksums[name] = digest
    if set(checksums) != files - {'checksums.sha256'}:
        raise ValueError("INPUT_INVALID: checksum inventory must cover every file except checksums.sha256")
    for name, digest in checksums.items():
        if sha256(safe_path(root, name)) != digest:
            raise ValueError(f"INPUT_INVALID: SHA-256 mismatch: {name}")
    manifest = CaptureManifestV1.model_validate_json((root / 'manifest.json').read_text())
    if manifest.image_orientation != 'sensor_native':
        raise ValueError("INPUT_INVALID: rotate imagery and calibration explicitly; V1 ingest requires sensor_native")
    metadata = json.loads((root / 'session_metadata.json').read_text())
    if not isinstance(metadata, dict) or metadata.get('timestamp_domain') != manifest.timestamp_domain:
        raise ValueError("INPUT_INVALID: session_metadata timestamp_domain must match manifest")
    # Manifest checksums are optional for old in-memory callers; sidecar is authoritative.
    for name, digest in manifest.checksums.items():
        if checksums.get(name) != digest or name == 'manifest.json':
            raise ValueError(f"INPUT_INVALID: manifest checksum disagrees with sidecar: {name}")
    raw = json.loads((root / 'calibration/camera_intrinsics.json').read_text())
    if not isinstance(raw, list) or not raw:
        raise ValueError("INPUT_INVALID: calibration file must be a nonempty list")
    calibrations = {}
    for item in raw:
        calibration = CameraIntrinsicsRecord.model_validate(item)
        if calibration.calibration_id in calibrations:
            raise ValueError(f"INPUT_INVALID: duplicate calibration ID {calibration.calibration_id}")
        calibrations[calibration.calibration_id] = calibration
    if manifest.calibration_id not in calibrations:
        raise ValueError("INPUT_INVALID: manifest calibration_id is missing")
    poses = read_jsonl(root / 'tracking/camera_poses.jsonl', CameraPoseRecord)
    events = read_jsonl(root / 'tracking/tracking_events.jsonl', TrackingStateEvent)
    if len(poses) != manifest.frame_count:
        raise ValueError("INPUT_INVALID: frame_count disagrees with pose record count")
    seen = set()
    previous_ts = -1
    for pose in poses:
        if pose.frame_id in seen or '/' in pose.frame_id or '\\' in pose.frame_id:
            raise ValueError(f"INPUT_INVALID: duplicate or unsafe frame_id {pose.frame_id}")
        seen.add(pose.frame_id)
        if pose.timestamp_ns <= previous_ts:
            raise ValueError(f"INPUT_INVALID: nonmonotonic timestamp at {pose.frame_id}")
        previous_ts = pose.timestamp_ns
        if not manifest.capture_start_ns <= pose.timestamp_ns <= manifest.capture_end_ns:
            raise ValueError(f"INPUT_INVALID: timestamp outside capture interval at {pose.frame_id}")
        calibration = calibrations.get(pose.intrinsics_id)
        if calibration is None:
            raise ValueError(f"INPUT_INVALID: unknown intrinsics_id at {pose.frame_id}")
        if pose.image_orientation != manifest.image_orientation:
            raise ValueError(f"INPUT_INVALID: image orientation mismatch at {pose.frame_id}")
        if (pose.image_width, pose.image_height) != (calibration.image_width, calibration.image_height):
            raise ValueError(f"INPUT_INVALID: calibration dimensions mismatch at {pose.frame_id}")
        image = cv2.imread(str(safe_path(root, 'frames/' + pose.frame_id)), cv2.IMREAD_UNCHANGED | cv2.IMREAD_IGNORE_ORIENTATION)
        if image is None or image.shape[:2] != (pose.image_height, pose.image_width):
            raise ValueError(f"INPUT_INVALID: image missing, undecodable or wrong dimensions: {pose.frame_id}")
    image_files = {name.removeprefix('frames/') for name in files if name.startswith('frames/')}
    if image_files != seen:
        raise ValueError("INPUT_INVALID: frame/pose association is not one-to-one")
    for index, event in enumerate(events):
        if not manifest.capture_start_ns <= event.timestamp_ns <= manifest.capture_end_ns:
            raise ValueError("INPUT_INVALID: tracking event outside capture interval")
        if index and (event.timestamp_ns < events[index-1].timestamp_ns or event.previous_state != events[index-1].current_state):
            raise ValueError("INPUT_INVALID: tracking events are out of order or state chain is broken")
    return ValidatedCapture(root, manifest, calibrations, poses, events)
