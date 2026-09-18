"""
VĀSTU Capture SOP Engine: Event-Driven Orchestrator
Coordinates the 11 procedural stages, 7 live quality signals, and prioritized TTS instruction generation.
Fulfills Acceptance Criterion:
A user can complete the capture procedure using the application without relying on a separate written SOP.
"""

from typing import List, Dict, Any, Optional
import time

from core.sop.stages import SOPStage, SOPStageDefinition, SOP_STAGES_SEQUENCE
from core.sop.signals import QualitySignalType, LiveTelemetrySnapshot, QualitySignalEvaluator, QualitySignalEvaluation
from core.sop.tts_engine import TTSPriority, TTSPrompt, TTSCoordinator

class CaptureSOPEngine:
    def __init__(
        self,
        tts_coordinator: Optional[TTSCoordinator] = None,
        stages: Optional[List[SOPStageDefinition]] = None
    ):
        self.stages = stages or SOP_STAGES_SEQUENCE
        self.tts = tts_coordinator or TTSCoordinator()

        self._current_stage_index = 0
        self._stage_start_time = time.time()
        self._accumulated_metrics: Dict[str, float] = {}
        self._has_guided_current_stage = False

        self.is_completed = False
        self.history: List[Dict[str, Any]] = []

    @property
    def current_stage(self) -> SOPStageDefinition:
        return self.stages[self._current_stage_index]

    @property
    def current_stage_number(self) -> int:
        return self._current_stage_index + 1

    @property
    def total_stages(self) -> int:
        return len(self.stages)

    @property
    def progress_fraction(self) -> float:
        if self.is_completed:
            return 1.0
        return self._current_stage_index / float(self.total_stages)

    def start_session(self, current_time_sec: Optional[float] = None) -> Optional[TTSPrompt]:
        """
        Begins SOP guidance with initial Room Entry instructions.
        """
        now = current_time_sec if current_time_sec is not None else time.time()
        self._stage_start_time = now
        self._current_stage_index = 0
        self.is_completed = False

        prompt = TTSPrompt(
            text=self.current_stage.guidance_instruction,
            priority=TTSPriority.GUIDANCE,
            category=f"GUIDANCE_{self.current_stage.stage.value}",
            trigger_condition=f"ENTER_STAGE_{self.current_stage.stage.value}"
        )
        self._has_guided_current_stage = True
        self.tts.emit(prompt, now)
        return prompt

    def update(
        self,
        telemetry: LiveTelemetrySnapshot,
        metrics_update: Optional[Dict[str, float]] = None,
        current_time_sec: Optional[float] = None
    ) -> List[TTSPrompt]:
        """
        Main tick:
        1. Evaluates 7 live quality signals.
        2. Evaluates stage progression criteria.
        3. Emits prioritized TTS prompts.
        """
        now = current_time_sec if current_time_sec is not None else time.time()
        emitted_this_tick: List[TTSPrompt] = []

        if metrics_update:
            for k, v in metrics_update.items():
                self._accumulated_metrics[k] = self._accumulated_metrics.get(k, 0.0) + v

        # -------------------------------------------------------------------
        # 1. Evaluate Live Quality Signals
        # -------------------------------------------------------------------
        evaluations = QualitySignalEvaluator.evaluate(telemetry)
        for ev in evaluations:
            # Determine TTS priority
            priority = TTSPriority.CRITICAL if ev.severity == "CRITICAL" else (
                TTSPriority.WARNING if ev.severity == "WARNING" else TTSPriority.GUIDANCE
            )
            prompt = TTSPrompt(
                text=ev.instruction,
                priority=priority,
                category=f"SIGNAL_{ev.signal_type.value}",
                trigger_condition=f"{ev.signal_type.value}: {ev.measured_value} (threshold {ev.threshold_value})"
            )
            if self.tts.emit(prompt, now):
                emitted_this_tick.append(prompt)

        # -------------------------------------------------------------------
        # 2. Check Stage Completion Criteria
        # -------------------------------------------------------------------
        if not self.is_completed:
            target_key = self.current_stage.target_metric_key
            current_metric_val = self._accumulated_metrics.get(target_key, 0.0)
            threshold = self.current_stage.target_metric_threshold

            # In Return / Loop Closure, criterion is distance <= threshold
            stage_done = False
            if self.current_stage.stage == SOPStage.RETURN_LOOP_CLOSURE:
                # Target is being close to origin (distance_to_origin_m <= 0.50)
                dist = self._accumulated_metrics.get("distance_to_origin_m", 10.0)
                stage_done = (dist <= threshold)
            else:
                stage_done = (current_metric_val >= threshold)

            if stage_done:
                # 1. Confirm current stage completion
                confirm_prompt = TTSPrompt(
                    text=self.current_stage.completion_instruction,
                    priority=TTSPriority.CONFIRMATION,
                    category=f"CONFIRMATION_{self.current_stage.stage.value}",
                    trigger_condition=f"CRITERIA_MET_{target_key}={current_metric_val:.2f}>={threshold:.2f}"
                )
                self.tts.reset_cooldown(f"CONFIRMATION_{self.current_stage.stage.value}")
                if self.tts.emit(confirm_prompt, now):
                    emitted_this_tick.append(confirm_prompt)

                # 2. Advance to next stage or complete
                if self._current_stage_index < self.total_stages - 1:
                    self._current_stage_index += 1
                    self._stage_start_time = now
                    self._has_guided_current_stage = False

                    # Emit guidance for new stage
                    next_guide = TTSPrompt(
                        text=self.current_stage.guidance_instruction,
                        priority=TTSPriority.GUIDANCE,
                        category=f"GUIDANCE_{self.current_stage.stage.value}",
                        trigger_condition=f"ENTER_STAGE_{self.current_stage.stage.value}"
                    )
                    self.tts.reset_cooldown(f"GUIDANCE_{self.current_stage.stage.value}")
                    # Allow brief spacing for guidance
                    if self.tts.emit(next_guide, now + 0.5):
                        emitted_this_tick.append(next_guide)
                else:
                    self.is_completed = True

        return emitted_this_tick
