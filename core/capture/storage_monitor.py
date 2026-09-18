"""
VĀSTU Mobile Capture: Storage Monitor & Safety Guard
Monitors available disk space and triggers graceful degradation before storage exhaustion.
"""

import os
import shutil
from typing import Callable, Optional

class StorageMonitor:
    WARNING_THRESHOLD_MB = 500
    CRITICAL_THRESHOLD_MB = 200

    def __init__(
        self,
        watch_path: str,
        on_warning: Optional[Callable[[float], None]] = None,
        on_critical: Optional[Callable[[float], None]] = None,
        mock_free_bytes: Optional[int] = None
    ):
        self.watch_path = watch_path
        self.on_warning = on_warning
        self.on_critical = on_critical
        self._mock_free_bytes = mock_free_bytes

    def get_free_space_mb(self) -> float:
        if self._mock_free_bytes is not None:
            return self._mock_free_bytes / (1024 * 1024)

        try:
            total, used, free = shutil.disk_usage(self.watch_path)
            return free / (1024 * 1024)
        except Exception:
            return 10000.0  # Fallback assumption

    def check(self) -> str:
        """
        Evaluates storage safety. Returns "OK", "WARNING", or "CRITICAL".
        """
        free_mb = self.get_free_space_mb()
        if free_mb < self.CRITICAL_THRESHOLD_MB:
            if self.on_critical:
                self.on_critical(free_mb)
            return "CRITICAL"
        elif free_mb < self.WARNING_THRESHOLD_MB:
            if self.on_warning:
                self.on_warning(free_mb)
            return "WARNING"
        return "OK"

    def set_mock_free_mb(self, free_mb: float):
        self._mock_free_bytes = int(free_mb * 1024 * 1024)
