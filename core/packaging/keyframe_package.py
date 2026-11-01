"""Transactional V1 writer, alongside the existing video archive implementation."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import tempfile

from core.schemas.capture_package_v1 import CaptureManifestV1, CameraIntrinsicsRecord, CameraPoseRecord, TrackingStateEvent
from core.validation.package_validator import safe_path, sha256, validate_package


def write_package(destination, manifest: CaptureManifestV1, calibrations: list[CameraIntrinsicsRecord],
                  poses: list[CameraPoseRecord], frames: dict[str, Path],
                  events: list[TrackingStateEvent] | None = None, metadata: dict | None = None) -> Path:
    """Never overwrite a capture. Publish only after the complete package validates."""
    destination = Path(destination).absolute()
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite capture: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.capture-writing-', dir=destination.parent))
    try:
        for folder in ('frames', 'tracking', 'calibration'):
            (temporary / folder).mkdir()
        (temporary / 'manifest.json').write_text(manifest.model_copy(update={'checksums': {}}).model_dump_json(indent=2))
        (temporary / 'session_metadata.json').write_text(json.dumps({
            **(metadata or {}), 'timestamp_domain': manifest.timestamp_domain,
        }, allow_nan=False, indent=2))
        (temporary / 'calibration/camera_intrinsics.json').write_text(json.dumps(
            [c.model_dump(mode='json') for c in calibrations], allow_nan=False, indent=2))
        for name, records in (('camera_poses', poses), ('tracking_events', events or [])):
            (temporary / f'tracking/{name}.jsonl').write_text(''.join(r.model_dump_json() + '\n' for r in records))
        for name, source in frames.items():
            if '/' in name or '\\' in name:
                raise ValueError(f"Unsafe frame_id: {name}")
            shutil.copyfile(source, safe_path(temporary, 'frames/' + name))
        files = sorted(p for p in temporary.rglob('*') if p.is_file())
        (temporary / 'checksums.sha256').write_text(''.join(
            f'{sha256(p)}  {p.relative_to(temporary).as_posix()}\n' for p in files))
        validate_package(temporary)
        if destination.exists():
            raise FileExistsError(f"Refusing to overwrite capture: {destination}")
        temporary.rename(destination)
    except Exception:
        shutil.rmtree(temporary)
        raise
    return destination
