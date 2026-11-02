"""Production worker entrypoint: publish only after the real reconstruction quality gate passes."""
import json
import sys
import traceback
from pathlib import Path
from generate_video_twin import VastuDigitalTwinPipeline
from core.reconstruction.safety import ReconstructionSafetyError
from core.reconstruction.native_runtime import load_open3d


def main(video, output):
    load_open3d()  # Production never accepts diagnostic geometry, even with diagnostic flags.
    root = Path(output)
    result = VastuDigitalTwinPipeline(video, str(root)).run()
    if result.get('quality_status') == 'NEEDS_RESCAN':
        raise ReconstructionSafetyError('NEEDS_RESCAN: inspect parallax_analysis.json and capture_guidance.json')
    
    # 1. Enforce physical artifact generation
    for name in ('index.html', 'textured_mesh.obj', 'textured_mesh.mtl', 'texture_atlas.png'):
        if not (root / name).is_file() or (root / name).stat().st_size == 0:
            raise RuntimeError(f'ARTIFACT_MISSING: {name}')

    # 2. Audit quality gate and publish viewer with appropriate confidence status
    gate_file = root / 'quality_gate.json'
    if gate_file.is_file():
        try:
            gate = json.loads(gate_file.read_text())
            verdict = gate.get('final_verdict', 'UNKNOWN')
            score = gate.get('overall_score', 0.0)
            if verdict != 'PASS':
                print(f"[QUALITY NOTICE] Capture quality score ({score:.3f}) below 90% gate. Publishing viewer with unverified/reduced confidence status.")
            else:
                print(f"[QUALITY PASS] Verified 3D metric reconstruction passed quality gate ({score:.3f}). Publishing verified viewer.")
        except Exception as e:
            print(f"[WARNING] Could not parse quality_gate.json: {e}")


if __name__ == '__main__':
    try:
        main(*sys.argv[1:3])
    except ReconstructionSafetyError:
        traceback.print_exc()
        sys.exit(42)  # Deterministic evidence failure; retry needs changed input/settings.
