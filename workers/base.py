"""
VĀSTU Standardized Worker Interface
Defines the canonical 8-stage worker execution lifecycle:
INPUT -> VALIDATION -> PROCESSING -> OUTPUT ARTIFACT -> OUTPUT MANIFEST -> METRICS -> LOGGING -> ERROR STATE
"""

from abc import ABC, abstractmethod
import time
import logging
import uuid
import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict
from core.domain.enums import WorkerStatus
from storage.base import StorageAdapter
from storage import get_storage_adapter

class WorkerContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    job_id: uuid.UUID
    project_id: uuid.UUID
    work_dir: str
    storage_adapter: Optional[Any] = None
    params: Dict[str, Any] = {}

class WorkerResult(BaseModel):
    status: WorkerStatus
    stage_name: str
    artifacts: Dict[str, str] = {}
    manifest: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}
    error_message: Optional[str] = None
    execution_time_sec: float = 0.0

class BaseWorker(ABC):
    def __init__(self, stage_name: str):
        self.stage_name = stage_name
        self.logger = logging.getLogger(f"VastuWorker.{stage_name}")

    def execute(self, context: WorkerContext) -> WorkerResult:
        """
        Standardized Canonical Worker Lifecycle:
        1. INPUT Loading
        2. VALIDATION of Inputs
        3. Core Algorithmic PROCESSING
        4. OUTPUT ARTIFACT verification
        5. OUTPUT MANIFEST generation
        6. METRICS collection
        7. LOGGING
        8. ERROR STATE management
        """
        self.logger.info(f"[{self.stage_name}] 1. Loading inputs for Job: {context.job_id}")
        start_time = time.perf_counter()
        os.makedirs(context.work_dir, exist_ok=True)

        try:
            # 1. INPUT
            raw_input = self.load_input(context)

            # 2. VALIDATION
            self.logger.info(f"[{self.stage_name}] 2. Validating input contracts")
            validated_input = self.validate_input(raw_input)

            # 3. PROCESSING
            self.logger.info(f"[{self.stage_name}] 3. Executing core processing algorithm")
            processed_data = self.process(validated_input, context)

            # 4. OUTPUT ARTIFACT
            self.logger.info(f"[{self.stage_name}] 4. Generating and verifying output artifacts")
            artifacts = self.generate_artifacts(processed_data, context)

            # 5. OUTPUT MANIFEST
            self.logger.info(f"[{self.stage_name}] 5. Constructing output manifest")
            manifest = self.generate_manifest(artifacts, processed_data, context)

            # 6. METRICS
            elapsed_sec = time.perf_counter() - start_time
            metrics = self.collect_metrics(processed_data, elapsed_sec)

            # 7. LOGGING
            self.logger.info(f"[{self.stage_name}] 7. Completed successfully in {elapsed_sec:.2f}s. Artifacts: {list(artifacts.keys())}")

            return WorkerResult(
                status=WorkerStatus.SUCCESS,
                stage_name=self.stage_name,
                artifacts=artifacts,
                manifest=manifest,
                metrics=metrics,
                execution_time_sec=round(elapsed_sec, 3)
            )

        except Exception as e:
            # 8. ERROR STATE
            elapsed_sec = time.perf_counter() - start_time
            self.logger.exception(f"[{self.stage_name}] 8. Stage failure encountered: {str(e)}")
            return WorkerResult(
                status=WorkerStatus.FAILED,
                stage_name=self.stage_name,
                error_message=str(e),
                execution_time_sec=round(elapsed_sec, 3)
            )

    @abstractmethod
    def load_input(self, context: WorkerContext) -> Any:
        """Loads required files, previous stage manifests, or configurations."""
        pass

    @abstractmethod
    def validate_input(self, raw_input: Any) -> Any:
        """Enforces schema and value contracts on the loaded input."""
        pass

    @abstractmethod
    def process(self, validated_input: Any, context: WorkerContext) -> Any:
        """Executes the specific mathematical / computer vision processing."""
        pass

    @abstractmethod
    def generate_artifacts(self, processed_data: Any, context: WorkerContext) -> Dict[str, str]:
        """Saves output files to work_dir and returns mapping of artifact_name -> path."""
        pass

    @abstractmethod
    def generate_manifest(self, artifacts: Dict[str, str], processed_data: Any, context: WorkerContext) -> Dict[str, Any]:
        """Produces formal stage output manifest describing artifact metadata."""
        pass

    @abstractmethod
    def collect_metrics(self, processed_data: Any, elapsed_sec: float) -> Dict[str, Any]:
        """Collects numerical stage performance, memory, and geometric metrics."""
        pass
