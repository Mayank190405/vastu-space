"""
Contract 13: Model Version Schema
Version: 2.0.0
Producer: Backend Model Service (PromoteModel, RescanIntegrator)
Consumer: Client Web Viewer, Mobile Apps, Export Pipeline, Quality Engine
"""

import uuid
from typing import Dict, Any, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from core.schemas.metric_transform import MetricTransformSchema

class ModelArtifactKeys(BaseModel):
    lod0_glb_s3_key: str
    lod1_glb_s3_key: Optional[str] = None
    lod2_glb_s3_key: Optional[str] = None
    splat_ply_s3_key: Optional[str] = None
    navmesh_json_s3_key: Optional[str] = None

class ModelVersion(BaseModel):
    model_version_id: str
    model_id: str
    project_id: uuid.UUID
    version: str
    semver: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    parent_version: Optional[str] = None
    parent_version_id: Optional[str] = None
    changed_cells: List[str] = Field(default_factory=list)
    pipeline_version: str = "2.0.0"
    algorithm_versions: Dict[str, str] = Field(default_factory=dict)
    quality_report: Optional[Dict[str, Any]] = None
    quality_report_id: Optional[uuid.UUID] = None
    artifacts: ModelArtifactKeys
    metric_transform: Optional[MetricTransformSchema] = None
    creation_timestamp: str
    created_at: str
    is_active_production: bool = False
    is_immutable: bool = True
    change_type: Literal["INITIAL_RECONSTRUCTION", "INCREMENTAL_RESCAN_PATCH", "MANUAL_EDIT", "ROLLBACK"] = "INITIAL_RECONSTRUCTION"
    summary_of_changes: str = "Initial model release"

    @model_validator(mode="before")
    @classmethod
    def reconcile_legacy_and_new_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. Project ID / Model ID
            if "model_id" not in data and "project_id" in data:
                data["model_id"] = str(data["project_id"])
            elif "project_id" not in data and "model_id" in data:
                try:
                    data["project_id"] = uuid.UUID(str(data["model_id"]))
                except ValueError:
                    data["project_id"] = uuid.uuid5(uuid.NAMESPACE_DNS, str(data["model_id"]))
            elif "model_id" not in data and "project_id" not in data:
                gen_uuid = uuid.uuid4()
                data["project_id"] = gen_uuid
                data["model_id"] = str(gen_uuid)

            # 2. Version / Semver
            if "version" not in data and "semver" in data:
                data["version"] = data["semver"]
            elif "semver" not in data and "version" in data:
                v_str = str(data["version"]).lstrip("v")
                parts = v_str.split(".")
                if len(parts) == 1:
                    v_str = f"{parts[0]}.0.0"
                elif len(parts) == 2:
                    v_str = f"{parts[0]}.{parts[1]}.0"
                data["semver"] = v_str
                data["version"] = data.get("version", v_str)
            elif "version" not in data and "semver" not in data:
                data["version"] = "1.0.0"
                data["semver"] = "1.0.0"

            # 3. Parent version
            if "parent_version" not in data and "parent_version_id" in data:
                data["parent_version"] = data["parent_version_id"]
            elif "parent_version_id" not in data and "parent_version" in data:
                data["parent_version_id"] = data["parent_version"]

            # 4. Timestamp
            if "creation_timestamp" not in data and "created_at" in data:
                data["creation_timestamp"] = data["created_at"]
            elif "created_at" not in data and "creation_timestamp" in data:
                data["created_at"] = data["creation_timestamp"]
            elif "creation_timestamp" not in data and "created_at" not in data:
                from datetime import datetime, timezone
                now_str = datetime.now(timezone.utc).isoformat()
                data["creation_timestamp"] = now_str
                data["created_at"] = now_str

            # 5. Quality report
            if "quality_report_id" in data and data["quality_report_id"] and "quality_report" not in data:
                data["quality_report"] = {"quality_report_id": str(data["quality_report_id"])}

        return data
