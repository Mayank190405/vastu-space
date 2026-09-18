import os
import tempfile
import time
import pytest

from core.capture.lifecycle import (
    CaptureState,
    CaptureLifecycleManager,
    IllegalStateTransitionError,
)
from core.capture.telemetry import (
    FrameTelemetryRecord,
    IMUSampleRecord,
    DeviceOrientation,
    ExposureMetadata,
    MobileDeviceMetadata,
)
from core.capture.buffer import CaptureRingBuffer
from core.capture.journal import CaptureSessionJournal
from core.capture.storage_monitor import StorageMonitor
from core.capture.session import MobileCaptureSession
from core.capture.recovery import CaptureRecoveryManager
from core.capture.queue import UploadQueueManager
from core.validation.capture_validator import CaptureValidator


def test_lifecycle_state_transitions():
    mgr = CaptureLifecycleManager()
    assert mgr.current_state == CaptureState.INITIALIZED

    assert mgr.transition_to(CaptureState.CONFIGURING) == CaptureState.CONFIGURING
    assert mgr.transition_to(CaptureState.READY) == CaptureState.READY
    assert mgr.transition_to(CaptureState.RECORDING) == CaptureState.RECORDING
    assert mgr.transition_to(CaptureState.PAUSED) == CaptureState.PAUSED
    assert mgr.transition_to(CaptureState.RESUMING) == CaptureState.RESUMING
    assert mgr.transition_to(CaptureState.RECORDING) == CaptureState.RECORDING
    assert mgr.transition_to(CaptureState.FINALIZING) == CaptureState.FINALIZING
    assert mgr.transition_to(CaptureState.COMPLETED) == CaptureState.COMPLETED

    # Test illegal transition raises error
    with pytest.raises(IllegalStateTransitionError):
        mgr.transition_to(CaptureState.RECORDING)


def test_frame_telemetry_all_required_fields():
    rec = FrameTelemetryRecord(
        timestamp_ns=1_700_000_000_000_000_000,
        timestamp_sec=1.5,
        frame_index=45,
        sensor_timestamp_ns=1_700_000_000_000_005_000,
        device_orientation=DeviceOrientation(
            roll_rad=0.01,
            pitch_rad=0.02,
            yaw_rad=0.03,
            quaternion=[0.0, 0.0, 0.0, 1.0]
        ),
        exposure_metadata=ExposureMetadata(
            exposure_duration_sec=0.0166,
            iso=125.0,
            f_number=1.8,
            lens_position=0.6
        ),
        capture_state=CaptureState.RECORDING,
        segment_index=1
    )

    data = rec.model_dump()
    assert "timestamp_ns" in data
    assert "frame_index" in data
    assert "sensor_timestamp_ns" in data
    assert "device_orientation" in data
    assert "exposure_metadata" in data
    assert "capture_state" in data
    assert data["frame_index"] == 45
    assert data["device_orientation"]["quaternion"] == [0.0, 0.0, 0.0, 1.0]


def test_ring_buffer_never_silent_loss():
    buffer = CaptureRingBuffer(max_frames=5, max_imu_samples=10)

    # Push 5 frames - should all succeed
    for i in range(5):
        f = FrameTelemetryRecord(
            timestamp_ns=i * 1000,
            timestamp_sec=i * 0.033,
            frame_index=i,
            sensor_timestamp_ns=i * 1000
        )
        assert buffer.push_frame(f) is True

    assert buffer.pending_frames_count == 5
    assert buffer.dropped_frame_count == 0

    # 6th frame must exceed capacity and explicitly record drop event
    f_extra = FrameTelemetryRecord(
        timestamp_ns=5000,
        timestamp_sec=5 * 0.033,
        frame_index=5,
        sensor_timestamp_ns=5000
    )
    assert buffer.push_frame(f_extra) is False
    assert buffer.dropped_frame_count == 1
    assert len(buffer.drop_events) == 1
    assert buffer.drop_events[0]["reason"] == "BUFFER_SATURATION_IO_BACKPRESSURE"


def test_storage_monitoring_thresholds():
    with tempfile.TemporaryDirectory() as temp_dir:
        warnings = []
        criticals = []

        monitor = StorageMonitor(
            watch_path=temp_dir,
            on_warning=lambda free_mb: warnings.append(free_mb),
            on_critical=lambda free_mb: criticals.append(free_mb)
        )

        # 1. Healthy storage (10 GB)
        monitor.set_mock_free_mb(10240.0)
        assert monitor.check() == "OK"
        assert len(warnings) == 0

        # 2. Warning storage (450 MB < 500 MB)
        monitor.set_mock_free_mb(450.0)
        assert monitor.check() == "WARNING"
        assert len(warnings) == 1

        # 3. Critical storage (150 MB < 200 MB)
        monitor.set_mock_free_mb(150.0)
        assert monitor.check() == "CRITICAL"
        assert len(criticals) == 1


def test_capture_interruption_and_resumption_recovery():
    """
    Fulfills Acceptance Criterion:
    A capture session can be interrupted and resumed without corrupting the dataset.
    """
    with tempfile.TemporaryDirectory() as session_dir:
        session = MobileCaptureSession(session_dir=session_dir, fps=30.0)
        session.initialize()
        session.start_recording()

        # Record initial 30 frames (Segment 0)
        for i in range(30):
            session.record_frame()
            session.record_imu(accel=[0.0, 9.81, 0.0], gyro=[0.0, 0.0, 0.0])

        assert session.lifecycle.current_state == CaptureState.RECORDING

        # Abrupt system interruption occurs (e.g. Phone call, low battery, or backgrounding)
        session.interrupt(reason="INCOMING_PHONE_CALL")
        assert session.lifecycle.current_state == CaptureState.INTERRUPTED

        # Verify session state from disk journal
        analysis = CaptureRecoveryManager.analyze_session(session_dir)
        assert analysis["is_interrupted"] is True
        assert analysis["can_resume"] is True
        assert analysis["last_frame_index"] == 29

        # User returns and resumes recording
        session.resume()
        assert session.lifecycle.current_state == CaptureState.RECORDING

        # Record 30 additional frames (Segment 1, continuous frame indices 30 to 59)
        for i in range(30):
            session.record_frame()
            session.record_imu(accel=[0.0, 9.81, 0.0], gyro=[0.0, 0.0, 0.0])

        # Finalize the resumed session
        manifest, report = session.finalize()
        assert session.lifecycle.current_state == CaptureState.COMPLETED

        # Dataset verification: MUST BE VALID AND UNCORRUPTED
        assert manifest is not None
        assert manifest.files.video.frame_count >= 60
        assert report.is_valid is True
        assert len(report.errors) == 0
        assert "video_checksum_verified" in report.checks_passed
        assert "frame_timestamps_strictly_monotonic" in report.checks_passed


def test_upload_queue_preparation():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a sample 12MB file (should split into three 5MB parts: 5MB + 5MB + 2MB)
        file_path = os.path.join(temp_dir, "raw_video.mov")
        file_size = 12 * 1024 * 1024
        with open(file_path, "wb") as f:
            f.write(b"V" * file_size)

        item = UploadQueueManager.prepare_file_chunks(
            file_path=file_path,
            capture_id="cap-123",
            project_id="proj-456",
            chunk_size=5 * 1024 * 1024
        )

        assert item.total_size_bytes == file_size
        assert item.total_chunks == 3
        assert item.chunks[0].length_bytes == 5 * 1024 * 1024
        assert item.chunks[1].length_bytes == 5 * 1024 * 1024
        assert item.chunks[2].length_bytes == 2 * 1024 * 1024
        assert all(len(c.sha256) == 64 for c in item.chunks)
