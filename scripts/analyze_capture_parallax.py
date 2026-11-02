#!/usr/bin/env python3
"""Re-decode a video and export Phase 2 diagnostics without creating geometry."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from core.reconstruction.parallax import analyze_frames, estimate_monocular_trajectory


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--video', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--samples', type=int, default=24)
    parser.add_argument('--pose-bundle', help='JSON: poses, K, frame_indices, scale_evidence. Intrinsics must match decoded/resized frames.')
    args = parser.parse_args()
    if args.samples < 2: parser.error('--samples must be at least 2')
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened(): raise ValueError('Cannot open video')
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    bundle = json.loads(Path(args.pose_bundle).read_text()) if args.pose_bundle else None
    indices = bundle['frame_indices'] if bundle else np.linspace(0, max(0, count-3), min(count, args.samples), dtype=int).tolist()
    frames, decoded_indices, failed_indices = [], [], []
    for i in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i)); ok, frame = cap.read()
        if not ok:
            if bundle: raise ValueError(f'Cannot decode pose-bound frame {i}')
            failed_indices.append(i)
            continue
        if not bundle:
            h, w = frame.shape[:2]; factor = 640/max(h, w)
            frame = cv2.resize(frame, (round(w*factor), round(h*factor)))
        frames.append(frame)
        decoded_indices.append(i)
    cap.release()
    if len(frames) < 2: raise ValueError('NEEDS_RESCAN: fewer than two decoded frames')
    h, w = frames[0].shape[:2]
    K = np.asarray(bundle['K']) if bundle else np.array([[.95*max(w,h), 0, w/2], [0, .95*max(w,h), h/2], [0, 0, 1.]])
    poses = bundle['poses'] if bundle else estimate_monocular_trajectory(frames, K)
    report = analyze_frames(frames, poses, K, args.output, bundle.get('scale_evidence') if bundle else None)
    digest = hashlib.sha256()
    with Path(args.video).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            digest.update(chunk)
    provenance = {'video_sha256': digest.hexdigest(), 'video': str(Path(args.video).resolve()), 'frame_indices': decoded_indices, 'failed_decode_indices': failed_indices, 'K': K.tolist(),
                  'calibration_source': 'provided' if bundle else 'uncalibrated focal prior',
                  'pose_source': 'provided' if bundle else 'unscaled sequential essential decomposition',
                  'warning': 'Diagnostic SfM can invent translation under rotation; no physical-motion conclusion without reliable independent poses.'}
    Path(args.output, 'processing_provenance.json').write_text(json.dumps(provenance, indent=2))
    serial = [{k: v.tolist() if isinstance(v, np.ndarray) else v for k,v in p.items()} for p in poses]
    Path(args.output, 'diagnostic_camera_poses.json').write_text(json.dumps(serial, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
