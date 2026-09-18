"""
VĀSTU Reconstruction Pipeline Runner
Executes stages sequentially under the canonical BaseWorker lifecycle.
"""

import os
import uuid
import time
import logging
from typing import Dict, Any, List
from workers.base import WorkerContext, WorkerResult
from core.domain.enums import WorkerStatus
from workers.stages import (
    PreprocessingWorker,
    SfMWorker,
    DepthWorker,
    PointCloudWorker,
    MeshingWorker,
    TexturingWorker,
    SemanticsWorker,
    NavMeshWorker,
    QualityWorker
)

logger = logging.getLogger("VastuPipelineRunner")

class PipelineRunner:
    def __init__(self):
        self.stages = [
            PreprocessingWorker(),
            SfMWorker(),
            DepthWorker(),
            PointCloudWorker(),
            MeshingWorker(),
            TexturingWorker(),
            SemanticsWorker(),
            NavMeshWorker(),
            QualityWorker()
        ]

    def run(self, video_path: str, work_dir: str, job_id: uuid.UUID = None, project_id: uuid.UUID = None) -> Dict[str, Any]:
        """
        Executes all canonical stages sequentially.
        Halts immediately on any stage failure.
        """
        j_id = job_id or uuid.uuid4()
        p_id = project_id or uuid.uuid4()
        context = WorkerContext(
            job_id=j_id,
            project_id=p_id,
            work_dir=work_dir,
            params={"video_path": video_path}
        )

        pipeline_start = time.perf_counter()
        results: Dict[str, WorkerResult] = {}

        for stage in self.stages:
            logger.info(f"===> Executing Pipeline Stage: {stage.stage_name}")
            res = stage.execute(context)
            results[stage.stage_name] = res

            if res.status != WorkerStatus.SUCCESS:
                logger.error(f"Pipeline terminated prematurely at {stage.stage_name}: {res.error_message}")
                return {
                    "status": "FAILED",
                    "failed_stage": stage.stage_name,
                    "error": res.error_message,
                    "total_duration_sec": round(time.perf_counter() - pipeline_start, 2),
                    "stage_results": {k: v.model_dump() for k, v in results.items()}
                }

        total_time = round(time.perf_counter() - pipeline_start, 2)
        logger.info(f"🎉 Pipeline completed all {len(self.stages)} stages successfully in {total_time}s")
        return {
            "status": "SUCCESS",
            "job_id": str(j_id),
            "project_id": str(p_id),
            "total_duration_sec": total_time,
            "stage_results": {k: v.model_dump() for k, v in results.items()}
        }
