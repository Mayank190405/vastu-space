"""
VĀSTU Mobile Capture: Unified Capture Session
Orchestrates RGB video recording, IMU logging, ring buffering, storage safety, and recovery.
"""

import os
import time
import uuid
from typing import Dict, Any, Optional, List
from core.capture.lifecycle import CaptureLifecycleManager, CaptureState
from core.capture.telemetry import (
    FrameTelemetryRecord,
    IMUSampleRecord,
    MobileDeviceMetadata,
    DeviceOrientation,
    ExposureMetadata,
)
from core.capture.buffer import CaptureRingBuffer
from core.capture.journal import CaptureSessionJournal
from core.capture.storage_monitor import StorageMonitor
from core.capture.recovery import CaptureRecoveryManager
from storage.naming import CaptureArtifactNaming

class MobileCaptureSession:
    def __init__(
        self,
        session_dir: str,
        project_id: Optional[uuid.UUID] = None,
        capture_id: Optional[uuid.UUID] = None,
        device_meta: Optional[MobileDeviceMetadata] = None,
        fps: float = 30.0
    ):
        self.session_dir = session_dir
        self.project_id = project_id or uuid.uuid4()
        self.capture_id = capture_id or uuid.uuid4()
        self.device_meta = device_meta or MobileDeviceMetadata()
        self.fps = fps

        self.lifecycle = CaptureLifecycleManager()
        self.buffer = CaptureRingBuffer(max_frames=500, max_imu_samples=5000)
        self.journal = CaptureSessionJournal(session_dir)

        self.storage_monitor = StorageMonitor(
            watch_path=session_dir,
            on_warning=self._handle_storage_warning,
            on_critical=self._handle_storage_critical
        )

        self._active_segment_index = 0
        self._current_frame_index = 0
        self._start_monotonic_ns: Optional[int] = None

        self.storage_warnings_count = 0
        self.storage_critical_count = 0

    def initialize(self):
        self.lifecycle.transition_to(CaptureState.CONFIGURING)
        os.makedirs(self.session_dir, exist_ok=True)
        self.journal.log_event("SESSION_START", {
            "capture_id": str(self.capture_id),
            "project_id": str(self.project_id),
            "manufacturer": self.device_meta.manufacturer,
            "model": self.device_meta.model,
            "os_name": self.device_meta.os_name,
            "fps": self.fps
        })
        self.lifecycle.transition_to(CaptureState.READY)

    def start_recording(self):
        self.lifecycle.transition_to(CaptureState.RECORDING)
        self._start_monotonic_ns = time.time_ns()
        self.journal.log_event("SEGMENT_START", {
            "segment_index": self._active_segment_index,
            "start_time_ns": self._start_monotonic_ns
        })

    def record_frame(
        self,
        sensor_timestamp_ns: Optional[int] = None,
        orientation: Optional[DeviceOrientation] = None,
        exposure: Optional[ExposureMetadata] = None
    ) -> bool:
        if self.lifecycle.current_state != CaptureState.RECORDING:
            return False

        # Storage safety check
        status = self.storage_monitor.check()
        if status == "CRITICAL":
            self.interrupt(reason="LOW_STORAGE_CRITICAL")
            return False

        now_ns = time.time_ns()
        nominal_sec = self._current_frame_index * (1.0 / self.fps)
        elapsed_sec = (now_ns - self._start_monotonic_ns) / 1e9 if self._start_monotonic_ns else 0.0
        rel_sec = max(nominal_sec, elapsed_sec)
        frame_timestamp_ns = (self._start_monotonic_ns + int(rel_sec * 1e9)) if self._start_monotonic_ns else now_ns

        rec = FrameTelemetryRecord(
            monotonic_timestamp_ns=frame_timestamp_ns,
            relative_timestamp_sec=rel_sec,
            frame_index=self._current_frame_index,
            sensor_timestamp_ns=sensor_timestamp_ns or frame_timestamp_ns,
            device_orientation=orientation or DeviceOrientation(),
            exposure_metadata=exposure or ExposureMetadata(),
            capture_state=self.lifecycle.current_state,
            segment_index=self._active_segment_index
        )

        pushed = self.buffer.push_frame(rec)
        if pushed:
            self._current_frame_index += 1

        # Checkpoint every 30 frames
        if self._current_frame_index > 0 and self._current_frame_index % 30 == 0:
            self.journal.log_event("TELEMETRY_CHECKPOINT", {
                "last_frame_index": self._current_frame_index - 1,
                "segment_index": self._active_segment_index,
                "buffered_frames": self.buffer.pending_frames_count
            })

        return pushed

    def record_imu(
        self,
        accel: List[float],
        gyro: List[float],
        sensor_timestamp_ns: Optional[int] = None
    ) -> bool:
        if self.lifecycle.current_state != CaptureState.RECORDING:
            return False

        now_ns = time.time_ns()
        rec = IMUSampleRecord(
            timestamp_ns=now_ns,
            sensor_timestamp_ns=sensor_timestamp_ns or now_ns,
            accel_mps2=accel,
            gyro_radps=gyro
        )
        return self.buffer.push_imu(rec)

    def interrupt(self, reason: str = "SYSTEM_INTERRUPTION"):
        """
        Handles sudden interruption: gracefully flushes pending buffers and marks segment end.
        """
        if self.lifecycle.current_state in (CaptureState.RECORDING, CaptureState.PAUSED):
            self.lifecycle.transition_to(CaptureState.INTERRUPTED)
            self._flush_and_close_segment(reason)

    def resume(self):
        """
        Resumes an interrupted session with continuous frame indexing.
        """
        if self.lifecycle.current_state in (CaptureState.INTERRUPTED, CaptureState.PAUSED):
            self.lifecycle.transition_to(CaptureState.RESUMING)
            params = CaptureRecoveryManager.get_resume_parameters(self.session_dir)
            self._active_segment_index = params["next_segment_index"]
            self._current_frame_index = params["start_frame_index"]
            self._start_monotonic_ns = time.time_ns()
            self.lifecycle.transition_to(CaptureState.RECORDING)
            self.journal.log_event("SEGMENT_START", {
                "segment_index": self._active_segment_index,
                "start_time_ns": self._start_monotonic_ns,
                "resumed": True
            })

    def finalize(self):
        """
        Finalizes session and builds uncorrupted manifest.
        """
        if self.lifecycle.current_state in (CaptureState.RECORDING, CaptureState.PAUSED, CaptureState.INTERRUPTED):
            self.lifecycle.transition_to(CaptureState.FINALIZING)
            self._flush_and_close_segment("FINALIZED")
            manifest, report = CaptureRecoveryManager.finalize_recovered_session(
                self.session_dir,
                fps=self.fps
            )
            self.lifecycle.transition_to(CaptureState.COMPLETED)
            return manifest, report

    def _flush_and_close_segment(self, reason: str):
        frames, imus = self.buffer.flush_all()
        # Append telemetry records to disk
        ts_path = os.path.join(self.session_dir, CaptureArtifactNaming.TIMESTAMPS_FILENAME)
        existing_records = []
        if os.path.exists(ts_path):
            import json
            with open(ts_path, "r") as f:
                try:
                    existing_records = json.load(f)
                except Exception:
                    existing_records = []

        for f in frames:
            existing_records.append(f.model_dump())

        with open(ts_path, "w") as f:
            import json
            json.dump(existing_records, f, indent=2)

        self.journal.log_event("SEGMENT_END", {
            "segment_index": self._active_segment_index,
            "frames_written": len(frames),
            "reason": reason
        })

    def _handle_storage_warning(self, free_mb: float):
        self.storage_warnings_count += 1
        self.journal.log_event("STORAGE_WARNING", {"free_mb": free_mb})

    def _handle_storage_critical(self, free_mb: float):
        self.storage_critical_count += 1
        self.journal.log_event("STORAGE_CRITICAL", {"free_mb": free_mb})
