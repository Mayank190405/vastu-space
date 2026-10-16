#!/usr/bin/env python3
"""
VĀSTU WORKER — PIPELINE ORCHESTRATOR MODULE
===========================================
Entrypoint compatibility wrapper for 3D digital twin reconstruction pipeline.
"""

import os
import sys

# Ensure workers and scripts directories are on PYTHONPATH
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKERS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
SCRIPTS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "..", "scripts"))

for p in [WORKERS_DIR, SCRIPTS_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from pipeline.v3_reconstruction_engine import run_v3_digital_twin_reconstruction

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.pipeline_orchestrator <video_path> [output_dir]")
        sys.exit(1)
    video_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "reconstruction_output"
    run_v3_digital_twin_reconstruction(video_path, output_dir)

if __name__ == "__main__":
    main()
