"""
VĀSTU BaseWorker Lifecycle & Interface Tests
Verifies the 8-stage execution contract:
INPUT -> VALIDATION -> PROCESSING -> OUTPUT ARTIFACT -> OUTPUT MANIFEST -> METRICS -> LOGGING -> ERROR STATE
"""

import os
import uuid
import pytest
from workers.base import BaseWorker, WorkerContext, WorkerResult
from core.domain.enums import WorkerStatus

class DummySuccessWorker(BaseWorker):
    def __init__(self):
        super().__init__(stage_name="DummySuccess")

    def load_input(self, context: WorkerContext):
        return {"val": context.params.get("input_val", 10)}

    def validate_input(self, raw_input):
        if raw_input["val"] < 0:
            raise ValueError("Input value must be non-negative")
        return raw_input

    def process(self, validated_input, context: WorkerContext):
        return {"computed": validated_input["val"] * 2}

    def generate_artifacts(self, processed_data, context: WorkerContext):
        artifact_path = os.path.join(context.work_dir, "output.txt")
        with open(artifact_path, "w") as f:
            f.write(str(processed_data["computed"]))
        return {"output_file": artifact_path}

    def generate_manifest(self, artifacts, processed_data, context: WorkerContext):
        return {"stage": self.stage_name, "computed": processed_data["computed"], "artifacts": artifacts}

    def collect_metrics(self, processed_data, elapsed_sec: float):
        return {"execution_time": elapsed_sec, "multiplier": 2}

class DummyFailingWorker(BaseWorker):
    def __init__(self):
        super().__init__(stage_name="DummyFailing")

    def load_input(self, context: WorkerContext):
        return {"val": -5}

    def validate_input(self, raw_input):
        raise ValueError("Invalid negative input in validation phase")

    def process(self, validated_input, context: WorkerContext):
        return {}

    def generate_artifacts(self, processed_data, context: WorkerContext):
        return {}

    def generate_manifest(self, artifacts, processed_data, context: WorkerContext):
        return {}

    def collect_metrics(self, processed_data, elapsed_sec: float):
        return {}

def test_worker_lifecycle_success(tmp_path):
    ctx = WorkerContext(
        job_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        work_dir=str(tmp_path),
        params={"input_val": 25}
    )
    worker = DummySuccessWorker()
    result = worker.execute(ctx)

    assert result.status == WorkerStatus.SUCCESS
    assert result.stage_name == "DummySuccess"
    assert "output_file" in result.artifacts
    assert os.path.exists(result.artifacts["output_file"])
    assert result.manifest["computed"] == 50
    assert result.metrics["multiplier"] == 2
    assert result.execution_time_sec >= 0.0

def test_worker_lifecycle_error_handling(tmp_path):
    ctx = WorkerContext(
        job_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        work_dir=str(tmp_path),
        params={}
    )
    worker = DummyFailingWorker()
    result = worker.execute(ctx)

    assert result.status == WorkerStatus.FAILED
    assert "Invalid negative input in validation phase" in result.error_message
    assert result.stage_name == "DummyFailing"
