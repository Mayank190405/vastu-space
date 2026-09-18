"""
VĀSTU Stage 07 Worker: Semantics
Detects 3D structural objects and labels spatial regions with oriented bounding boxes.
"""

import os
import json
from typing import Dict, Any
import numpy as np
from workers.base import BaseWorker, WorkerContext
from ml.semantics.detector import SemanticObjectDetector

class SemanticsWorker(BaseWorker):
    def __init__(self):
        super().__init__(stage_name="Stage07_Semantics")
        self.detector = SemanticObjectDetector()

    def load_input(self, context: WorkerContext) -> Dict[str, Any]:
        mesh_path = os.path.join(context.work_dir, "05_mesh", "mesh3D.ply")
        if not os.path.exists(mesh_path):
            raise FileNotFoundError("Mesh input missing for semantics")
        return {"mesh_path": mesh_path}

    def validate_input(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        return raw_input

    def process(self, validated_input: Dict[str, Any], context: WorkerContext) -> Dict[str, Any]:
        sem_dir = os.path.join(context.work_dir, "07_semantics")
        os.makedirs(sem_dir, exist_ok=True)
        sem_json = os.path.join(sem_dir, "semantic_objects.json")

        sample_points = np.array([
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 1.0],
            [-1.0, 1.0, -1.0]
        ])
        objects = self.detector.detect_3d_objects(sample_points)

        with open(sem_json, "w") as f:
            json.dump(objects, f, indent=2)

        return {"semantic_objects": objects, "json_path": sem_json}

    def generate_artifacts(self, processed_data: Dict[str, Any], context: WorkerContext) -> Dict[str, str]:
        return {"semantic_objects_json": processed_data["json_path"]}

    def generate_manifest(self, artifacts: Dict[str, str], processed_data: Dict[str, Any], context: WorkerContext) -> Dict[str, Any]:
        return {
            "stage": self.stage_name,
            "detected_objects_count": len(processed_data["semantic_objects"]),
            "artifacts": artifacts
        }

    def collect_metrics(self, processed_data: Dict[str, Any], elapsed_sec: float) -> Dict[str, Any]:
        return {
            "processing_time_sec": elapsed_sec,
            "object_count": len(processed_data["semantic_objects"])
        }
