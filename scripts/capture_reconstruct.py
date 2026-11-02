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
    VastuDigitalTwinPipeline(video, str(root)).run()
    gate = json.loads((root / 'quality_gate.json').read_text())
    if gate.get('final_verdict') != 'PASS' or not gate.get('backend_verification', {}).get('verified'):
        raise RuntimeError('RECONSTRUCTION_QUALITY_FAILED: measured quality gates did not pass; viewer withheld')
    for name in ('index.html', 'textured_mesh.obj', 'textured_mesh.mtl', 'texture_atlas.png'):
        if not (root / name).is_file() or (root / name).stat().st_size == 0:
            raise RuntimeError(f'ARTIFACT_MISSING: {name}')


if __name__ == '__main__':
    try:
        main(*sys.argv[1:3])
    except ReconstructionSafetyError:
        traceback.print_exc()
        sys.exit(42)  # Deterministic evidence failure; retry needs changed input/settings.
