"""
VĀSTU Mobile Capture: Local Ring Buffer
Thread-safe circular in-memory buffer that decouples camera/sensor callbacks from disk writes.
Enforces the strict requirement: The capture engine must NEVER silently lose frames or sensor data.
"""

from collections import deque
import threading
import time
from typing import List, Optional, Tuple, Dict, Any
from core.capture.telemetry import FrameTelemetryRecord, IMUSampleRecord

class CaptureRingBuffer:
    def __init__(self, max_frames: int = 300, max_imu_samples: int = 3000):
        self._max_frames = max_frames
        self._max_imu = max_imu_samples

        self._frame_deque = deque()
        self._imu_deque = deque()

        self._lock = threading.Lock()

        # Audit & Loss Tracking (Explicit loss reporting, NEVER silent)
        self.dropped_frame_count: int = 0
        self.dropped_imu_count: int = 0
        self.drop_events: List[Dict[str, Any]] = []

    def push_frame(self, frame: FrameTelemetryRecord) -> bool:
        """
        Appends a frame record. If buffer is saturated, explicitly records drop event.
        """
        with self._lock:
            if len(self._frame_deque) >= self._max_frames:
                # Buffer saturated: cannot drop silently!
                self.dropped_frame_count += 1
                ev = {
                    "type": "FRAME_DROP",
                    "frame_index": frame.frame_index,
                    "timestamp_ns": frame.timestamp_ns,
                    "reason": "BUFFER_SATURATION_IO_BACKPRESSURE",
                    "queue_length": len(self._frame_deque)
                }
                self.drop_events.append(ev)
                return False

            self._frame_deque.append(frame)
            return True

    def push_imu(self, imu: IMUSampleRecord) -> bool:
        """
        Appends an IMU record. If buffer is saturated, explicitly records drop event.
        """
        with self._lock:
            if len(self._imu_deque) >= self._max_imu:
                self.dropped_imu_count += 1
                ev = {
                    "type": "IMU_DROP",
                    "timestamp_ns": imu.timestamp_ns,
                    "reason": "BUFFER_SATURATION_IO_BACKPRESSURE",
                    "queue_length": len(self._imu_deque)
                }
                self.drop_events.append(ev)
                return False

            self._imu_deque.append(imu)
            return True

    def pop_batch(self, max_batch: int = 50) -> Tuple[List[FrameTelemetryRecord], List[IMUSampleRecord]]:
        """
        Pulls a batch of pending records for disk spooling.
        """
        frames: List[FrameTelemetryRecord] = []
        imus: List[IMUSampleRecord] = []

        with self._lock:
            while self._frame_deque and len(frames) < max_batch:
                frames.append(self._frame_deque.popleft())
            while self._imu_deque and len(imus) < (max_batch * 10):
                imus.append(self._imu_deque.popleft())

        return frames, imus

    def flush_all(self) -> Tuple[List[FrameTelemetryRecord], List[IMUSampleRecord]]:
        """
        Empties and returns all remaining items in the buffer.
        """
        with self._lock:
            frames = list(self._frame_deque)
            imus = list(self._imu_deque)
            self._frame_deque.clear()
            self._imu_deque.clear()
        return frames, imus

    @property
    def pending_frames_count(self) -> int:
        with self._lock:
            return len(self._frame_deque)

    @property
    def pending_imu_count(self) -> int:
        with self._lock:
            return len(self._imu_deque)
