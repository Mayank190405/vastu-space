"""
VĀSTU Mobile Capture: Session Lifecycle State Machine
Defines the authoritative lifecycle states and allowed state transitions.
"""

from enum import Enum
from typing import Set

class CaptureState(str, Enum):
    INITIALIZED = "INITIALIZED"
    CONFIGURING = "CONFIGURING"
    READY = "READY"
    RECORDING = "RECORDING"
    PAUSED = "PAUSED"
    INTERRUPTED = "INTERRUPTED"
    RESUMING = "RESUMING"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CaptureLifecycleManager:
    """
    Guarantees deterministic, valid lifecycle state transitions.
    """

    ALLOWED_TRANSITIONS = {
        CaptureState.INITIALIZED: {CaptureState.CONFIGURING, CaptureState.FAILED},
        CaptureState.CONFIGURING: {CaptureState.READY, CaptureState.FAILED},
        CaptureState.READY: {CaptureState.RECORDING, CaptureState.FINALIZING, CaptureState.FAILED},
        CaptureState.RECORDING: {CaptureState.PAUSED, CaptureState.INTERRUPTED, CaptureState.FINALIZING, CaptureState.FAILED},
        CaptureState.PAUSED: {CaptureState.RESUMING, CaptureState.FINALIZING, CaptureState.FAILED},
        CaptureState.INTERRUPTED: {CaptureState.RESUMING, CaptureState.FINALIZING, CaptureState.FAILED},
        CaptureState.RESUMING: {CaptureState.RECORDING, CaptureState.FAILED},
        CaptureState.FINALIZING: {CaptureState.COMPLETED, CaptureState.FAILED},
        CaptureState.COMPLETED: set(),
        CaptureState.FAILED: set(),
    }

    def __init__(self):
        self._current_state = CaptureState.INITIALIZED

    @property
    def current_state(self) -> CaptureState:
        return self._current_state

    def can_transition_to(self, target_state: CaptureState) -> bool:
        return target_state in self.ALLOWED_TRANSITIONS.get(self._current_state, set())

    def transition_to(self, target_state: CaptureState) -> CaptureState:
        if not self.can_transition_to(target_state):
            raise IllegalStateTransitionError(
                f"Illegal capture lifecycle transition: cannot move from {self._current_state} to {target_state}"
            )
        self._current_state = target_state
        return self._current_state


class IllegalStateTransitionError(Exception):
    pass
