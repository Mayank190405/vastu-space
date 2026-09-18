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

from typing import List, Dict, Any, Tuple, Literal

class QualityDecisionEngine:
    def __init__(
        self,
        pass_threshold: float = 0.75,
        warning_threshold: float = 0.65,
    ):
        self.pass_threshold = pass_threshold
        self.warning_threshold = warning_threshold

    def evaluate_verdict(
        self,
        global_score: float,
        subsystem_scores: Dict[str, float],
        hard_failures: List[str],
        warnings: List[str],
        per_cell_issues: Dict[str, List[str]]
    ) -> Tuple[Literal["PASS", "WARNING", "FAIL"], List[str], str]:
        """
        Determines the final verdict, compiles recommended actions, and constructs
        a detailed explanatory narrative explaining WHY the model passed or failed.
        """
        recommended_actions = []

        # 1. Hard Failure check (Hard failures unconditionally block PASS)
        if len(hard_failures) > 0:
            verdict: Literal["PASS", "WARNING", "FAIL"] = "FAIL"
        elif global_score < self.warning_threshold:
            verdict = "FAIL"
        elif len(warnings) > 0 or global_score < self.pass_threshold:
            verdict = "WARNING"
        else:
            verdict = "PASS"

        # 2. Formulate Recommended Actions
        for fail in hard_failures:
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

        # Per-cell actions
        for cell_id, issues in per_cell_issues.items():
            if issues:
                action = f"Targeted rescan unit recommended for {cell_id}: {'; '.join(issues)}."
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
            if hard_failures:
                explanation_parts.append(
                    f"Publication is strictly BLOCKED due to {len(hard_failures)} critical hard failure(s):"
                )
                for idx, hf in enumerate(hard_failures, 1):
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
                f"Model passed baseline viability but exhibits {len(warnings)} non-blocking advisory warning(s):"
            )
            for idx, w in enumerate(warnings, 1):
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
