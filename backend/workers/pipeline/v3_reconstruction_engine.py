#!/usr/bin/env python3
"""
VĀSTU WORKER — STANDARDIZED V3 RECONSTRUCTION ENGINE MODULE
===========================================================
Modular worker pipeline wrapper for Celery/Asynq background task workers.
"""

import os
import sys

SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from generate_video_twin import VastuDigitalTwinPipeline

def run_v3_digital_twin_reconstruction(video_path: str, output_dir: str) -> dict:
    """Standardized entrypoint for backend asynchronous processing workers."""
    pipeline = VastuDigitalTwinPipeline(video_path, output_dir)
    return pipeline.run()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 v3_reconstruction_engine.py <video_path> [output_dir]")
        sys.exit(1)
    v_path = sys.argv[1]
    o_dir = sys.argv[2] if len(sys.argv) > 2 else "digital_twin_output"
    run_v3_digital_twin_reconstruction(v_path, o_dir)
