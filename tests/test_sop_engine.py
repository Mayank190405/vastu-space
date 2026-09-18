import time
import pytest

from core.sop.stages import SOPStage, SOP_STAGES_SEQUENCE
from core.sop.signals import (
    QualitySignalType,
    LiveTelemetrySnapshot,
    QualitySignalEvaluator,
)
from core.sop.tts_engine import TTSPriority, TTSPrompt, TTSCoordinator
from core.sop.sop_engine import CaptureSOPEngine


def test_sop_11_stages_sequence():
    assert len(SOP_STAGES_SEQUENCE) == 11
    expected_order = [
        SOPStage.ROOM_ENTRY,
        SOPStage.PERIMETER_COVERAGE,
        SOPStage.WALL_COVERAGE,
        SOPStage.CORNERS,
        SOPStage.DOORWAY,
        SOPStage.WINDOWS,
        SOPStage.FLOOR,
        SOPStage.CEILING,
        SOPStage.CENTER_TRAVERSAL,
        SOPStage.RETURN_LOOP_CLOSURE,
        SOPStage.COMPLETION_VERIFICATION,
    ]
    actual_order = [s.stage for s in SOP_STAGES_SEQUENCE]
    assert actual_order == expected_order


def test_7_live_quality_signals_thresholds():
    # 1. Healthy nominal telemetry: 0 signals triggered
    nominal = LiveTelemetrySnapshot()
    evals = QualitySignalEvaluator.evaluate(nominal)
    assert len(evals) == 0

    # 2. Excessive Motion (linear velocity 1.1 m/s > 0.80 m/s)
    fast_telemetry = LiveTelemetrySnapshot(linear_velocity_mps=1.1)
    evals = QualitySignalEvaluator.evaluate(fast_telemetry)
    assert any(e.signal_type == QualitySignalType.EXCESSIVE_MOTION for e in evals)

    # 3. Blur (Laplacian variance 65 < 100)
    blurry_telemetry = LiveTelemetrySnapshot(blur_laplacian_variance=65.0)
    evals = QualitySignalEvaluator.evaluate(blurry_telemetry)
    assert any(e.signal_type == QualitySignalType.BLUR for e in evals)

    # 4. Insufficient Overlap (rotation delta 18 deg > 15 deg)
    low_overlap = LiveTelemetrySnapshot(inter_frame_rotation_deg=18.0)
    evals = QualitySignalEvaluator.evaluate(low_overlap)
    assert any(e.signal_type == QualitySignalType.INSUFFICIENT_OVERLAP for e in evals)

    # 5. Poor Lighting (dark: 15 lux < 30 lux)
    dark_telemetry = LiveTelemetrySnapshot(ambient_lux=15.0)
    evals = QualitySignalEvaluator.evaluate(dark_telemetry)
    assert any(e.signal_type == QualitySignalType.POOR_LIGHTING for e in evals)

    # 6. Low Feature Density (55 keypoints < 80)
    textureless = LiveTelemetrySnapshot(tracked_feature_count=55)
    evals = QualitySignalEvaluator.evaluate(textureless)
    assert any(e.signal_type == QualitySignalType.LOW_FEATURE_DENSITY for e in evals)

    # 7. Inadequate Coverage (unobserved fraction 0.45 > 0.30)
    sparse_coverage = LiveTelemetrySnapshot(unobserved_area_fraction=0.45)
    evals = QualitySignalEvaluator.evaluate(sparse_coverage)
    assert any(e.signal_type == QualitySignalType.INADEQUATE_COVERAGE for e in evals)

    # 8. Tracking Degradation (inliers 18 < 30)
    degraded_tracking = LiveTelemetrySnapshot(tracking_inlier_count=18, is_tracking_lost=True)
    evals = QualitySignalEvaluator.evaluate(degraded_tracking)
    assert any(e.signal_type == QualitySignalType.TRACKING_DEGRADATION and e.severity == "CRITICAL" for e in evals)


def test_tts_priority_ordering():
    assert TTSPriority.CRITICAL < TTSPriority.WARNING
    assert TTSPriority.WARNING < TTSPriority.GUIDANCE
    assert TTSPriority.GUIDANCE < TTSPriority.CONFIRMATION


def test_anti_repetition_cooldown():
    coordinator = TTSCoordinator(cooldown_sec=6.0, min_silence_sec=2.5)

    prompt1 = TTSPrompt(
        text="Slow down. Move camera steadily.",
        priority=TTSPriority.WARNING,
        category="MOTION_WARNING",
        trigger_condition="VELOCITY_1.2"
    )

    t0 = 100.0
    # First emit: succeeds
    assert coordinator.emit(prompt1, current_time_sec=t0) is True

    # Immediate repetition at t0 + 2.0s (within 6.0s cooldown): must be suppressed!
    assert coordinator.can_speak(prompt1, current_time_sec=t0 + 2.0) is False
    assert coordinator.emit(prompt1, current_time_sec=t0 + 2.0) is False

    # After cooldown expires at t0 + 6.5s: succeeds
    assert coordinator.can_speak(prompt1, current_time_sec=t0 + 6.5) is True
    assert coordinator.emit(prompt1, current_time_sec=t0 + 6.5) is True


def test_pacing_silence_gap():
    coordinator = TTSCoordinator(cooldown_sec=6.0, min_silence_sec=2.5)

    prompt_a = TTSPrompt(
        text="Instruction A",
        priority=TTSPriority.GUIDANCE,
        category="CAT_A",
        trigger_condition="COND_A"
    )
    prompt_b = TTSPrompt(
        text="Instruction B",
        priority=TTSPriority.GUIDANCE,
        category="CAT_B",
        trigger_condition="COND_B"
    )

    t0 = 100.0
    assert coordinator.emit(prompt_a, current_time_sec=t0) is True

    # Different category at t0 + 1.0s (less than 2.5s pacing silence): must be suppressed!
    assert coordinator.can_speak(prompt_b, current_time_sec=t0 + 1.0) is False
    assert coordinator.emit(prompt_b, current_time_sec=t0 + 1.0) is False

    # After pacing silence at t0 + 2.6s: allowed!
    assert coordinator.can_speak(prompt_b, current_time_sec=t0 + 2.6) is True
    assert coordinator.emit(prompt_b, current_time_sec=t0 + 2.6) is True


def test_critical_priority_preemption():
    coordinator = TTSCoordinator(cooldown_sec=6.0, min_silence_sec=2.5)

    normal_prompt = TTSPrompt(
        text="Normal guidance prompt",
        priority=TTSPriority.GUIDANCE,
        category="GUIDANCE_CAT",
        trigger_condition="NORMAL"
    )
    critical_prompt = TTSPrompt(
        text="Emergency tracking lost!",
        priority=TTSPriority.CRITICAL,
        category="CRITICAL_TRACKING",
        trigger_condition="TRACKING_LOST"
    )

    t0 = 100.0
    coordinator.emit(normal_prompt, current_time_sec=t0)

    # 0.5s later: normal prompt would be blocked by 2.5s silence gap,
    # but CRITICAL prompt is permitted immediately!
    assert coordinator.can_speak(critical_prompt, current_time_sec=t0 + 0.5) is True
    assert coordinator.emit(critical_prompt, current_time_sec=t0 + 0.5) is True


def test_end_to_end_sop_walkthrough():
    """
    Fulfills Acceptance Criterion:
    A user can complete the capture procedure using the application without relying on a separate written SOP.
    """
    engine = CaptureSOPEngine()
    t = 1000.0

    # Start session: Stage 1 (Room Entry)
    initial_prompt = engine.start_session(current_time_sec=t)
    assert initial_prompt is not None
    assert engine.current_stage.stage == SOPStage.ROOM_ENTRY
    assert "Stand at the main doorway" in initial_prompt.text

    # Complete all 11 stages by fulfilling each stage's measurable target metric
    target_metric_values = {
        "baseline_frames_accumulated": 50.0,
        "perimeter_path_length_m": 9.0,
        "wall_surface_observed_fraction": 0.85,
        "corners_captured_count": 4.0,
        "doorway_frames_captured": 35.0,
        "windows_frames_captured": 35.0,
        "floor_surface_observed_fraction": 0.80,
        "ceiling_surface_observed_fraction": 0.75,
        "center_cross_distance_m": 3.5,
        "distance_to_origin_m": 0.35,  # Within 0.50m threshold
        "overall_spatial_completeness": 0.90
    }

    nominal_telemetry = LiveTelemetrySnapshot()

    # Step through stages
    for stage_def in list(SOP_STAGES_SEQUENCE):
        t += 3.0
        metric_key = stage_def.target_metric_key
        metric_val = target_metric_values[metric_key]

        prompts = engine.update(
            telemetry=nominal_telemetry,
            metrics_update={metric_key: metric_val},
            current_time_sec=t
        )
        assert len(prompts) > 0
        # Check that confirmation or guidance was spoken
        assert any(p.priority in (TTSPriority.CONFIRMATION, TTSPriority.GUIDANCE) for p in prompts)

    # Verify session completed successfully
    assert engine.is_completed is True
    assert engine.progress_fraction == 1.0
    assert len(engine.tts.emitted_prompts) >= 11
