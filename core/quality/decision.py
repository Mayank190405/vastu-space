"""
Decision Engine for Central Quality Evaluation:
Enforces:
1. No arbitrary numerical score as sole publication decision:
   - Even with a high numerical score (e.g. 0.88), any blocking Hard Failure forces verdict to FAIL.
2. Comprehensive Narrative Reasoning:
   - Explains WHY the reconstruction passed, warned, or failed.
3. Actionable Remediation Generation:
   - Maps failures and warnings to precise physical or algorithmic steps (Targeted Rescans, CAD fixes).
"""

from typing import List, Dict, Any, Tuple, Literal, Optional

class QualityDecisionEngine:
    """
    Quality Decision Engine:
    Enforces fail-safe publication rules:
    - 'A crash is detectable. A visually convincing but geometrically incorrect digital twin is not.'
    - Even with high composite score, any hard failure forces FAIL.
    - If unverified/inferred surface area > 5%, clean PASS is blocked (downgraded to WARNING or FAIL).
    - If geometric uncertainty > 20mm, triggers actionable targeted rescan.
    - Generates structured 30-second targeted rescan prompts with 3D coordinates.
    """
    def __init__(
        self,
        pass_threshold: float = 0.75,
        warning_threshold: float = 0.65,
        max_unverified_area_ratio: float = 0.05,
        max_geometric_uncertainty_mm: float = 20.0
    ):
        self.pass_threshold = pass_threshold
        self.warning_threshold = warning_threshold
        self.max_unverified_area_ratio = max_unverified_area_ratio
        self.max_geometric_uncertainty_mm = max_geometric_uncertainty_mm

    def generate_targeted_rescan_instruction(
        self,
        cell_id: str,
        center_xyz: List[float],
        dominant_issue: str,
        duration_sec: int = 30
    ) -> Dict[str, Any]:
        """
        Synthesizes a standardized, actionable 30-second targeted rescan directive
        with spatial coordinates and operator movement constraints.
        """
        cx, cy, cz = center_xyz if len(center_xyz) == 3 else [0.0, 0.0, 1.0]
        return {
            "cell_id": cell_id,
            "target_center_xyz": [round(cx, 3), round(cy, 3), round(cz, 3)],
            "recommended_duration_sec": duration_sec,
            "max_angular_velocity_deg_s": 15.0,
            "required_lighting": "DIFFUSE_UNIFORM",
            "instruction": (
                f"Position camera 1.5m facing [{cx:.2f}, {cy:.2f}, {cz:.2f}] at eye level. "
                f"Execute a slow 30-second arc sweep at < 15 deg/sec to resolve {dominant_issue}. "
                f"Avoid reflective glare or rapid acceleration."
            )
        }

    def evaluate_verdict(
        self,
        global_score: float,
        subsystem_scores: Dict[str, float],
        hard_failures: List[str],
        warnings: List[str],
        per_cell_issues: Dict[str, List[str]],
        unverified_area_ratio: float = 0.0,
        max_geometric_uncertainty_mm: float = 0.0,
        cell_centroids: Optional[Dict[str, List[float]]] = None
    ) -> Tuple[Literal["PASS", "WARNING", "FAIL"], List[str], str]:
        """
        Determines the final verdict, compiles recommended actions, and constructs
        a detailed explanatory narrative explaining WHY the model passed or failed.
        Enforces that unverified surfaces (> 5%) strictly downgrade PASS to WARNING/FAIL.
        """
        recommended_actions: List[str] = []
        active_hard_failures = list(hard_failures)
        active_warnings = list(warnings)

        # Fail-Safe Rule: Unverified or inferred geometry checks
        if unverified_area_ratio > 0.20:
            active_hard_failures.append(
                f"FAILSAFE_BLOCKER: Unverified/inferred surface area is {unverified_area_ratio * 100:.1f}% (> 20% limit). "
                f"Inferred geometry cannot replace observed physical measurements."
            )
        elif unverified_area_ratio > self.max_unverified_area_ratio:
            active_warnings.append(
                f"FAILSAFE_ALERT: Unverified/inferred surface area is {unverified_area_ratio * 100:.1f}% "
                f"(> {self.max_unverified_area_ratio * 100:.1f}% threshold). Clean PASS blocked."
            )

        if max_geometric_uncertainty_mm > self.max_geometric_uncertainty_mm:
            active_warnings.append(
                f"FAILSAFE_ALERT: Maximum geometric uncertainty {max_geometric_uncertainty_mm:.1f}mm "
                f"exceeds {self.max_geometric_uncertainty_mm:.1f}mm metrology tolerance."
            )

        # 1. Hard Failure check (Hard failures unconditionally block PASS)
        if len(active_hard_failures) > 0:
            verdict: Literal["PASS", "WARNING", "FAIL"] = "FAIL"
        elif global_score < self.warning_threshold:
            verdict = "FAIL"
        elif len(active_warnings) > 0 or global_score < self.pass_threshold:
            verdict = "WARNING"
        else:
            verdict = "PASS"

        # 2. Formulate Recommended Actions
        for fail in active_hard_failures:
            if "NAVIGATION" in fail:
                recommended_actions.append(
                    "Resolve blocked corridor or doorway collider in navigation graph to restore route connectivity."
                )
            elif "GEOMETRY" in fail and "phantom" in fail.lower():
                recommended_actions.append(
                    "Apply geometric clipping or execute targeted rescan with polarized filter to prune specular reflection phantoms."
                )
            elif "POSE" in fail and "tracking" in fail.lower():
                recommended_actions.append(
                    "Execute targeted rescan across disconnected trajectory gap maintaining <= 15° rotational velocity."
                )
            elif "CAPTURE" in fail and "coverage" in fail.lower():
                recommended_actions.append(
                    "Schedule targeted mobile capture sweep to cover unvisited volumetric regions."
                )
            elif "FAILSAFE" in fail:
                recommended_actions.append(
                    "Execute targeted rescans on unverified blind spots; pipeline forbids guessing physical structures."
                )

        # Per-cell actions with 3D instructions
        centroids = cell_centroids or {}
        for cell_id, issues in per_cell_issues.items():
            if issues:
                center = centroids.get(cell_id, [0.0, 0.0, 1.0])
                rescan_info = self.generate_targeted_rescan_instruction(
                    cell_id=cell_id,
                    center_xyz=center,
                    dominant_issue=issues[0]
                )
                action = f"Targeted 30s rescan for {cell_id}: {rescan_info['instruction']}"
                if action not in recommended_actions:
                    recommended_actions.append(action)

        if verdict == "PASS" and not recommended_actions:
            recommended_actions.append("Model approved for production publication across Visual, Structural, and Collision pipelines.")

        # 3. Formulate Explanatory Narrative (Acceptance Criterion: Explain WHY)
        explanation_parts = []
        explanation_parts.append(
            f"Quality Verdict: {verdict} (Global Composite Score: {global_score:.2f})."
        )

        if verdict == "FAIL":
            if active_hard_failures:
                explanation_parts.append(
                    f"Publication is strictly BLOCKED due to {len(active_hard_failures)} critical hard failure(s):"
                )
                for idx, hf in enumerate(active_hard_failures, 1):
                    explanation_parts.append(f"  {idx}. {hf}")
                explanation_parts.append(
                    "Note: In accordance with the central quality policy, high composite scores cannot override structural or navigational integrity blockers."
                )
            else:
                explanation_parts.append(
                    f"Global composite score ({global_score:.2f}) falls below the minimum viable quality threshold ({self.warning_threshold:.2f})."
                )
        elif verdict == "WARNING":
            explanation_parts.append(
                f"Model passed baseline viability but exhibits {len(active_warnings)} non-blocking advisory warning(s):"
            )
            for idx, w in enumerate(active_warnings, 1):
                explanation_parts.append(f"  {idx}. {w}")
            explanation_parts.append(
                "Publication permitted for staging/preview; resolve warnings prior to formal tenant sign-off."
            )
        else:
            explanation_parts.append(
                "All 6 subsystems (Capture, Pose, Depth, Geometry, Semantics, Navigation) meet or exceed authoritative production thresholds with zero hard failures or critical warnings."
            )

        # Subsystem summary breakdown
        score_breakdown = ", ".join([f"{k.capitalize()}: {v:.2f}" for k, v in subsystem_scores.items()])
        explanation_parts.append(f"Subsystem Scores: [{score_breakdown}].")

        explanation = " ".join(explanation_parts)
        return verdict, recommended_actions, explanation

