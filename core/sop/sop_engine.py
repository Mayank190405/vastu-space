"""
VĀSTU Capture SOP Engine: Event-Driven Orchestrator
Coordinates the 11 procedural stages, 8 live quality signals, 3D voxel coverage grid,
and prioritized TTS instruction generation with an 85% gated completion rule.
Fulfills Acceptance Criterion:
A user can complete the capture procedure using the application without relying on a separate written SOP.
"""

from typing import List, Dict, Any, Optional, Tuple
import time

from core.sop.stages import SOPStage, SOPStageDefinition, SOP_STAGES_SEQUENCE
from core.sop.signals import QualitySignalType, LiveTelemetrySnapshot, QualitySignalEvaluator, QualitySignalEvaluation
from core.sop.tts_engine import TTSPriority, TTSPrompt, TTSCoordinator
from core.sop.voxel_grid import VoxelCoverageGrid
from core.sop.floorplan_parser import FloorplanSOPParser


class CaptureSOPEngine:
    def __init__(
        self,
        tts_coordinator: Optional[TTSCoordinator] = None,
        stages: Optional[List[SOPStageDefinition]] = None,
        voxel_grid: Optional[VoxelCoverageGrid] = None,
        capture_sop: Optional[Dict[str, Any]] = None
    ):
        self.stages = stages or SOP_STAGES_SEQUENCE
        self.tts = tts_coordinator or TTSCoordinator()
        self.voxel_grid = voxel_grid
        self.capture_sop = capture_sop

        if self.capture_sop and not self.voxel_grid:
            self._init_voxel_grid_from_sop(self.capture_sop)

        self._current_stage_index = 0
        self._stage_start_time = time.time()
        self._accumulated_metrics: Dict[str, float] = {}
        self._has_guided_current_stage = False

        self.is_completed = False
        self.history: List[Dict[str, Any]] = []

    def _init_voxel_grid_from_sop(self, sop: Dict[str, Any]):
        mt = sop.get("metric_targets", {})
        dims = mt.get("room_dimensions_m", {})
        w = dims.get("width", 5.0)
        l = dims.get("length", 6.0)
        h = dims.get("height", 2.8)
        self.voxel_grid = VoxelCoverageGrid(width_m=w, length_m=l, height_m=h)

    def load_floorplan(
        self,
        drawing_data: Optional[Dict[str, Any]] = None,
        canvas_width: float = 1200.0,
        canvas_height: float = 800.0,
        scale_ratio: float = 1.0,
        floor_name: str = "Main Floor",
        area_sqft: float = 400.0,
        height_ft: float = 10.0
    ):
        """
        Parses floorplan blueprint into on-device SOP and configures the 3D voxel grid.
        """
        sop = FloorplanSOPParser.parse(
            drawing_data=drawing_data,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            scale_ratio=scale_ratio,
            floor_name=floor_name,
            area_sqft=area_sqft,
            height_ft=height_ft
        )
        self.capture_sop = sop
        self._init_voxel_grid_from_sop(sop)

    def update_camera_pose(
        self,
        position: Tuple[float, float, float],
        look_direction: Tuple[float, float, float],
        fov_deg: float = 65.0
    ):
        """
        Feeds live AR camera tracking into the 3D voxel occupancy grid.
        """
        if self.voxel_grid:
            self.voxel_grid.update_pose(position, look_direction, fov_deg=fov_deg)
            # Sync coverage into accumulated metrics
            self._accumulated_metrics["floor_surface_observed_fraction"] = self.voxel_grid.floor_coverage_fraction
            self._accumulated_metrics["wall_surface_observed_fraction"] = self.voxel_grid.avg_wall_coverage_fraction
            self._accumulated_metrics["overall_spatial_completeness"] = self.voxel_grid.overall_coverage_fraction

    def can_complete(self) -> Tuple[bool, List[str]]:
        """
        Checks 85% gated completion rule.
        """
        if not self.voxel_grid:
            # If no voxel grid is configured, fallback to metric accumulator
            overall = self._accumulated_metrics.get("overall_spatial_completeness", 0.0)
            if overall >= 0.85:
                return True, []
            return False, [f"Overall spatial completeness is {int(overall*100)}% (required: >= 85%)."]

        return self.voxel_grid.is_gated_complete(min_overall=0.85, min_floor=0.80, min_wall=0.70)

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
        1. Evaluates 8 live quality signals.
        2. Evaluates stage progression criteria.
        3. Enforces 85% completion gate at final stage.
        4. Emits prioritized TTS prompts.
        """
        now = current_time_sec if current_time_sec is not None else time.time()
        emitted_this_tick: List[TTSPrompt] = []

        if metrics_update:
            for k, v in metrics_update.items():
                self._accumulated_metrics[k] = self._accumulated_metrics.get(k, 0.0) + v

        # Sync telemetry coverage into metrics if available
        if telemetry.coverage_fraction is not None:
            self._accumulated_metrics["overall_spatial_completeness"] = telemetry.coverage_fraction
        if telemetry.floor_coverage_fraction is not None:
            self._accumulated_metrics["floor_surface_observed_fraction"] = telemetry.floor_coverage_fraction

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
            elif self.current_stage.stage == SOPStage.COMPLETION_VERIFICATION:
                # Fulfill 85% completion gate
                is_gated, defects = self.can_complete()
                if not is_gated:
                    stage_done = False
                    defect_msg = defects[0] if defects else "Capture incomplete."
                    gate_prompt = TTSPrompt(
                        text=f"Capture incomplete. {defect_msg}",
                        priority=TTSPriority.WARNING,
                        category="GATE_INCOMPLETE",
                        trigger_condition="GATE_CHECK_FAILED"
                    )
                    if self.tts.emit(gate_prompt, now):
                        emitted_this_tick.append(gate_prompt)
                else:
                    stage_done = (current_metric_val >= threshold)
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
