"""
Model Publishing Service:
Enforces publishing criteria: Every published model must have an explicit metric transform
and its scale source recorded, preventing unscaled or undocumented geometry from being published.
"""

from typing import Dict, Any, Optional
import uuid

from core.schemas.model_version import ModelVersion, ModelArtifactKeys
from core.schemas.metric_transform import MetricTransformSchema, MetricScaleSource
from core.alignment.transform import MetricTransform

class ModelPublisher:
    def __init__(self, require_metric: bool = True):
        self.require_metric = require_metric

    def publish_model(
        self,
        project_id: uuid.UUID,
        semver: str,
        artifacts: ModelArtifactKeys,
        metric_transform: Optional[MetricTransformSchema] = None,
        summary_of_changes: str = "Published model version",
        change_type: str = "INITIAL_RECONSTRUCTION",
        quality_report_id: Optional[uuid.UUID] = None,
        parent_version_id: Optional[str] = None
    ) -> ModelVersion:
        """
        Validates and publishes a ModelVersion.
        Enforces Acceptance Criterion:
        Every published model has an explicit metric transform and its scale source is recorded.
        """
        # Enforcement Gate: Must have an explicit metric transform
        if metric_transform is None:
            raise ValueError(
                "Model publication rejected: Missing explicit metric transform. "
                "Every published model must have an explicit metric transform."
            )

        # Enforcement Gate: Scale source must be recorded and valid
        if not metric_transform.scale_source or metric_transform.scale_source == MetricScaleSource.UNSCALED:
            if self.require_metric:
                raise ValueError(
                    f"Model publication rejected: Scale source '{metric_transform.scale_source}' is invalid or unscaled. "
                    "Every published model must have its scale source recorded."
                )

        if metric_transform.scale <= 0.0:
            raise ValueError(f"Model publication rejected: Invalid scale factor {metric_transform.scale} <= 0")

        model_version_id = f"mod_{uuid.uuid4().hex[:10]}"
        return ModelVersion(
            model_version_id=model_version_id,
            project_id=project_id,
            parent_version_id=parent_version_id,
            semver=semver,
            is_active_production=True,
            change_type=change_type,
            summary_of_changes=summary_of_changes,
            quality_report_id=quality_report_id,
            artifacts=artifacts,
            metric_transform=metric_transform,
            created_at="2026-09-06T17:15:00Z"
        )
