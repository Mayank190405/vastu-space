#!/usr/bin/env python3
"""
VĀSTU / Namma Space — Official Reconstruction CLI
==================================================
Converts smartphone video captures into metric 3D digital twins
without manual CAD or Blender intervention.

Usage:
  python scripts/reconstruct.py --video /path/to/capture.mp4 --output /path/to/output
  python scripts/reconstruct.py --demo
"""

import os
import sys
import argparse
import logging

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from generate_video_twin import VastuDigitalTwinPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("vastu.reconstruct")

def parse_args():
    parser = argparse.ArgumentParser(
        description="VĀSTU Automated 3D Spatial Reconstruction Pipeline"
    )
    parser.add_argument(
        "--video", "-v",
        type=str,
        required=True,
        help="Path to input smartphone capture video (MP4/MOV)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=os.path.join(ROOT_DIR, "digital_twin_output"),
        help="Target directory for 3D outputs (mesh.ply, textured_mesh.obj, splats)"
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Copy generated assets directly to public web viewer models/ directory"
    )
    return parser.parse_args()

def main():
    args = parse_args()
    
    video_path = args.video
    if not os.path.exists(video_path):
        logger.error(f"Capture video file not found: {video_path}")
        sys.exit(1)
            
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("=" * 65)
    logger.info("  VĀSTU / NAMMA SPACE — 3D SPATIAL RECONSTRUCTION")
    logger.info(f"  Input Capture : {video_path}")
    logger.info(f"  Output Folder : {output_dir}")
    logger.info("=" * 65)
    
    pipeline = VastuDigitalTwinPipeline(video_path, output_dir)
    success = pipeline.run()
    
    if success:
        logger.info("Reconstruction completed successfully!")
        
        if args.deploy:
            public_models = os.path.join(ROOT_DIR, "public", "models")
            os.makedirs(public_models, exist_ok=True)
            import shutil
            for fname in ["textured_mesh.obj", "textured_mesh.mtl", "texture_atlas.jpg", "texture_atlas.png", "mesh.ply", "dense_pointcloud_clean.ply", "digital_twin_summary.json", "camera_trajectory.json", "supervisor_diagnostics.json", "index.html"]:
                src = os.path.join(output_dir, fname)
                if not os.path.exists(src):
                    src = os.path.join(output_dir, "17_texture" if "texture" in fname or "obj" in fname or "mtl" in fname else ("14_mesh" if ("mesh.ply" in fname or "supervisor" in fname) else ("10_dense_pointcloud" if "pointcloud" in fname else ("04_camera_poses" if "trajectory" in fname else ("20_viewer" if "index.html" in fname else "")))), fname)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(public_models, fname))
                    logger.info(f"Deployed asset -> {public_models}/{fname}")
    else:
        logger.error("Pipeline encountered quality gate errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()
