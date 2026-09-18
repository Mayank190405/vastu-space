"""
VĀSTU Capture SOP Engine: Prioritized TTS Instruction Engine
Manages speech generation, priority queuing, and strict anti-repetition cooldowns.
TTS Priority:
CRITICAL -> WARNING -> GUIDANCE -> CONFIRMATION
"""

from enum import IntEnum
import time
from typing import Dict, Optional, List
from pydantic import BaseModel, Field

class TTSPriority(IntEnum):
    # Lower integer = higher priority
    CRITICAL = 1
    WARNING = 2
    GUIDANCE = 3
    CONFIRMATION = 4


class TTSPrompt(BaseModel):
    text: str
    priority: TTSPriority
    category: str
    trigger_condition: str
    timestamp_ns: int = Field(default_factory=time.time_ns)


class TTSCoordinator:
    """
    Coordinates speech playback with priority preemption, anti-repetition gating,
    and pacing silence intervals.
    """

    DEFAULT_COOLDOWN_SEC = 6.0
    MINIMUM_SILENCE_SEC = 2.5

    def __init__(
        self,
        cooldown_sec: float = DEFAULT_COOLDOWN_SEC,
        min_silence_sec: float = MINIMUM_SILENCE_SEC
    ):
        self.cooldown_sec = cooldown_sec
        self.min_silence_sec = min_silence_sec

        # Timestamp of last spoken prompt per category/key
        self._last_spoken_time: Dict[str, float] = {}
        # Timestamp of when any speech was last emitted
        self._last_any_spoken_time: float = 0.0

        # Queue of emitted spoken prompts for audit/verification
        self.emitted_prompts: List[TTSPrompt] = []

    def can_speak(self, prompt: TTSPrompt, current_time_sec: Optional[float] = None) -> bool:
        now = current_time_sec if current_time_sec is not None else time.time()

        # CRITICAL priority can preempt silence intervals
        if prompt.priority == TTSPriority.CRITICAL:
            last_for_cat = self._last_spoken_time.get(prompt.category, 0.0)
            return (now - last_for_cat) >= (self.cooldown_sec / 2.0)

        # Anti-repetition cooldown for identical category / text
        last_for_cat = self._last_spoken_time.get(prompt.category, 0.0)
        if (now - last_for_cat) < self.cooldown_sec:
            return False

        # Pacing silence: ensure minimum gap between consecutive utterances
        if (now - self._last_any_spoken_time) < self.min_silence_sec:
            return False

        return True

    def emit(self, prompt: TTSPrompt, current_time_sec: Optional[float] = None) -> bool:
        """
        Attempts to emit a prompt through TTS.
        Returns True if emitted, False if suppressed by cooldown or pacing.
        """
        now = current_time_sec if current_time_sec is not None else time.time()
        if not self.can_speak(prompt, now):
            return False

        self._last_spoken_time[prompt.category] = now
        self._last_any_spoken_time = now
        self.emitted_prompts.append(prompt)
        return True

    def reset_cooldown(self, category: Optional[str] = None):
        if category:
            self._last_spoken_time.pop(category, None)
        else:
            self._last_spoken_time.clear()
            self._last_any_spoken_time = 0.0
