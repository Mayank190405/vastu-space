"""Geometry-based capture diagnostics. Distances retain input units until scale is proven."""
from dataclasses import dataclass, asdict
from itertools import combinations
from pathlib import Path
import csv
import html
import json
import cv2
import numpy as np


@dataclass
class ParallaxConfig:
    max_keyframes: int = 16
    min_baseline_m: float = 0.10  # advisory heuristic, not an acceptance condition
    min_overlap: float = 0.20
    min_correspondences: int = 30
    min_angle_deg: float = 1.5
    min_baseline_depth_ratio: float = 0.02
    max_relative_depth_uncertainty: float = 0.25
    min_sharpness: float = 8.0
    max_reprojection_px: float = 2.0


def camera_pose(pose):
    """Return camera-to-world orientation and center; never treat w2c t as center."""
    convention = pose.get('convention', 'world_to_camera')
    R = np.asarray(pose['R'], dtype=float).reshape(3, 3)
    t = np.asarray(pose['t'], dtype=float).reshape(3)
    if not np.isfinite(R).all() or not np.isfinite(t).all():
        raise ValueError('Nonfinite pose')
    if not np.allclose(R.T @ R, np.eye(3), atol=1e-4) or not np.isclose(np.linalg.det(R), 1, atol=1e-4):
        raise ValueError('Pose rotation must be a proper orthonormal matrix')
    if convention == 'world_to_camera':
        return R.T, -R.T @ t
    if convention == 'camera_to_world':
        return R, t
    raise ValueError('Explicit world_to_camera or camera_to_world convention required')


def metric_scale_report(evidence=None):
    e = evidence or {}
    supported = e.get('source') in {'ARKIT', 'CALIBRATED_VIO', 'LIDAR', 'MEASURED_REFERENCE'}
    factor = e.get('meters_per_unit')
    valid = (supported and e.get('validated') is True and bool(e.get('reference'))
             and e.get('tracking_valid') is True and isinstance(factor, (int, float))
             and np.isfinite(factor) and factor > 0
             and isinstance(e.get('relative_uncertainty'), (int, float))
             and 0 <= e['relative_uncertainty'] <= 0.1)
    return {'status': 'METRIC_ESTABLISHED' if valid else 'SCALE_UNOBSERVABLE',
            'source': e.get('source', 'MONOCULAR_UNSCALED'), 'evidence': e,
            'meters_per_unit': float(factor) if valid else None,
            'reason': 'Validated independent metric reference' if valid else
            'No validated independent metric reference; neural depth and essential-matrix translation do not establish metric scale.'}


def measure_pair(i, j, pose1, pose2, xy1, xy2, K, feature_counts,
                 sharpness=(float('inf'), float('inf')), config=None, scale=None):
    cfg = config or ParallaxConfig()
    Q1, C1 = camera_pose(pose1)
    Q2, C2 = camera_pose(pose2)
    baseline = float(np.linalg.norm(C2 - C1))
    rotation = float(np.degrees(np.arccos(np.clip((np.trace(Q1.T @ Q2)-1)/2, -1, 1))))
    x1, x2 = np.asarray(xy1).reshape(-1, 2), np.asarray(xy2).reshape(-1, 2)
    if len(x1) != len(x2):
        raise ValueError('Correspondence count mismatch')
    invK = np.linalg.inv(K)
    b1 = (invK @ np.c_[x1, np.ones(len(x1))].T).T
    b2 = (invK @ np.c_[x2, np.ones(len(x2))].T).T
    r1 = b1 @ Q1.T
    r2 = b2 @ Q2.T
    r1 /= np.maximum(np.linalg.norm(r1, axis=1, keepdims=True), 1e-12)
    r2 /= np.maximum(np.linalg.norm(r2, axis=1, keepdims=True), 1e-12)
    angles = np.degrees(np.arccos(np.clip(np.sum(r1*r2, axis=1), -1, 1)))
    valid = np.zeros(len(x1), dtype=bool)
    depth = np.array([])
    if baseline > 1e-10 and len(x1):
        P1 = K @ np.c_[Q1.T, -Q1.T @ C1]
        P2 = K @ np.c_[Q2.T, -Q2.T @ C2]
        Xh = cv2.triangulatePoints(P1, P2, x1.T.astype(float), x2.T.astype(float))
        good_w = np.abs(Xh[3]) > 1e-12
        X = (Xh[:3] / np.where(good_w, Xh[3], np.nan)).T
        z1, z2 = ((X-C1) @ Q1)[:, 2], ((X-C2) @ Q2)[:, 2]
        def error(P, xy):
            p = (P @ np.c_[X, np.ones(len(X))].T).T
            return np.linalg.norm(p[:, :2] / p[:, 2:3] - xy, axis=1)
        valid = good_w & (z1 > 0) & (z2 > 0) & (error(P1, x1) <= cfg.max_reprojection_px) & (error(P2, x2) <= cfg.max_reprojection_px)
        depth = np.linalg.norm(X[valid]-C1, axis=1)
    count = int(valid.sum())
    overlap = len(x1) / max(1, min(feature_counts))
    median_angle = float(np.median(angles[valid])) if count else 0.0
    median_depth = float(np.median(depth)) if count else None
    ratio = baseline / median_depth if median_depth else 0.0
    # First-order relative depth error: sigma_angle / sin(triangulation angle).
    # Missing pose covariance is unknown, never silently treated as zero uncertainty.
    sigmas = [p.get('rotation_sigma_deg') for p in (pose1, pose2)]
    ts = [p.get('translation_sigma') for p in (pose1, pose2)]
    known = all(v is not None and np.isfinite(v) and v >= 0 for v in sigmas + ts)
    sigma_angle = np.hypot(np.sqrt(2)/float(min(K[0, 0], K[1, 1])),
                           np.radians(np.linalg.norm(sigmas))) if known else None
    uncertainty = float(np.hypot(sigma_angle / max(np.sin(np.radians(median_angle)), 1e-12),
                                 np.linalg.norm(ts)/max(baseline, 1e-12))) if known else None
    reasons = []
    if not all(p.get('reliable', False) for p in (pose1, pose2)): reasons.append('UNRELIABLE_POSE')
    consistent_scale = all(p.get('scale_consistent', True) for p in (pose1, pose2))
    if not consistent_scale: reasons.append('INCONSISTENT_MONOCULAR_STEP_SCALE')
    if baseline <= 1e-10: reasons.append('ZERO_TRANSLATION')
    if count < cfg.min_correspondences: reasons.append('INSUFFICIENT_CORRESPONDENCES')
    if overlap < cfg.min_overlap: reasons.append('LOW_OVERLAP')
    if median_angle < cfg.min_angle_deg: reasons.append('POOR_TRIANGULATION_ANGLE')
    if ratio < cfg.min_baseline_depth_ratio: reasons.append('LOW_BASELINE_DEPTH_RATIO')
    if uncertainty is None: reasons.append('POSE_UNCERTAINTY_UNKNOWN')
    elif uncertainty > cfg.max_relative_depth_uncertainty: reasons.append('HIGH_GEOMETRIC_UNCERTAINTY')
    if min(sharpness) < cfg.min_sharpness: reasons.append('BLURRED_IMAGE')
    factor = (scale or {}).get('meters_per_unit')
    return {'frame_i': i, 'frame_j': j, 'rotation_deg': rotation,
            'translation_input_units': baseline if consistent_scale else None,
            'diagnostic_translation_arbitrary_steps': baseline if not consistent_scale else None,
            'translation_m': baseline*factor if factor and consistent_scale else None,
            'feature_overlap': min(1.0, overlap), 'matched_correspondences': len(x1),
            'valid_correspondences': count, 'median_triangulation_angle_deg': median_angle,
            'median_scene_depth_input_units': median_depth, 'baseline_to_depth_ratio': ratio,
            'estimated_relative_depth_uncertainty': uncertainty,
            'baseline_heuristic_met': baseline*factor >= cfg.min_baseline_m if factor and consistent_scale else None,
            'useful_triangulation': not reasons, 'acceptance_reason': '|'.join(reasons) or 'ACCEPTED',
            'observed_cells_i': sorted(set((np.floor(x1[valid, 0]/64).astype(int)*10000 + np.floor(x1[valid, 1]/64).astype(int)).tolist()))}


def select_keyframes(pairs, limit=16):
    """Greedy complementary pairs, rewarding previously uncovered image regions."""
    remaining = [p for p in pairs if p['useful_triangulation']]
    selected, chosen, covered = set(), [], set()
    while remaining:
        def score(p):
            cells = {(p['frame_i'], c) for c in p['observed_cells_i']}
            return len(cells-covered) + p['valid_correspondences'] * .01
        best = max(remaining, key=score)
        remaining.remove(best)
        ids = {best['frame_i'], best['frame_j']}
        if len(selected | ids) > limit: continue
        selected |= ids
        covered |= {(best['frame_i'], c) for c in best['observed_cells_i']}
        chosen.append([best['frame_i'], best['frame_j']])
    return sorted(selected), chosen


def analyze_frames(frames, poses, K, output, scale_evidence=None, config=None):
    cfg = config or ParallaxConfig()
    if len(frames) != len(poses): raise ValueError('Frame/pose count mismatch')
    scale = metric_scale_report(scale_evidence)
    detector = cv2.SIFT_create(nfeatures=1500)
    features, sharpness = [], []
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        features.append(detector.detectAndCompute(gray, None))
        sharpness.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
    pairs = []
    for i, j in combinations(range(len(frames)), 2):
        k1, d1 = features[i]; k2, d2 = features[j]
        matches = []
        if d1 is not None and d2 is not None and min(len(d1), len(d2)) >= 2:
            matcher = cv2.BFMatcher()
            forward = [m for m, n in matcher.knnMatch(d1, d2, k=2) if m.distance < .75*n.distance]
            backward = {(m.trainIdx, m.queryIdx) for m, n in matcher.knnMatch(d2, d1, k=2) if m.distance < .75*n.distance}
            matches = [m for m in forward if (m.queryIdx, m.trainIdx) in backward]
        xy1 = np.array([k1[m.queryIdx].pt for m in matches]).reshape(-1, 2)
        xy2 = np.array([k2[m.trainIdx].pt for m in matches]).reshape(-1, 2)
        pairs.append(measure_pair(i, j, poses[i], poses[j], xy1, xy2, K,
                                  (len(k1), len(k2)), (sharpness[i], sharpness[j]), cfg, scale))
    return export_analysis(pairs, poses, output, scale, cfg)


def export_analysis(pairs, poses, output, scale, config=None):
    cfg = config or ParallaxConfig()
    out = Path(output); out.mkdir(parents=True, exist_ok=True)
    selected, chosen = select_keyframes(pairs, cfg.max_keyframes)
    metric = scale['status'] == 'METRIC_ESTABLISHED'
    useful = [p for p in pairs if p['useful_triangulation']]
    overlapping = [p['translation_input_units'] for p in pairs if p['feature_overlap'] >= cfg.min_overlap and p['translation_input_units'] is not None]
    consistent_scale = all(p.get('scale_consistent', True) for p in poses)
    report = {'status': 'PASS' if useful and metric else 'NEEDS_RESCAN',
              'scale_status': scale['status'], 'parallax_gate_passed': bool(useful and metric),
              'verified_multi_view_geometry': bool(useful and metric),
              'diagnostic_reconstruction_label': 'DEGRADED',
              'baseline_statistic': 'maximum camera-center separation among overlapping pairs; not accumulated path length',
              'baseline_input_units': max(overlapping, default=0.0) if consistent_scale else None,
              'trajectory_scale_consistent': consistent_scale,
              'baseline_measurement_status': 'ESTIMATED' if consistent_scale else 'UNOBSERVABLE_NONUNIFORM_MONOCULAR_STEPS',
              'total_baseline_displacement_m': max(overlapping, default=0.0)*scale['meters_per_unit'] if metric and consistent_scale else None,
              'baseline_statistics_input_units': {'minimum': min(overlapping, default=0.0), 'median': float(np.median(overlapping)) if overlapping else 0.0, 'maximum': max(overlapping, default=0.0)} if consistent_scale else None,
              'threshold_min_baseline_m': cfg.min_baseline_m, 'threshold_role': 'advisory heuristic only',
              'configuration': asdict(cfg), 'pair_count': len(pairs), 'useful_pair_count': len(useful),
              'selected_keyframes': selected, 'selected_pairs': chosen,
              'pose_reliability': 'RELIABLE' if poses and all(p.get('reliable', False) for p in poses) else 'UNVERIFIED',
              'uncertainty_model': 'First-order angular pixel/pose error and translation covariance bound; missing covariance rejects verification.'}
    guidance = {'status': report['status'], 'scale_status': scale['status'],
                'missing_motion': ('Useful sideways translation with persistent overlap was not established.' if poses and all(p.get('reliable', False) for p in poses) else 'UNKNOWN: reliable camera poses are required to distinguish physical motion from tracking error.') if not useful else None,
                'instructions': ['Walk sideways smoothly while keeping the same textured surfaces visible.',
                                 'Capture sharp overlapping views at multiple positions and scene depths.',
                                 'Record validated ARKit/VIO poses, reliable LiDAR, or an independently measured reference.'],
                'tracking_caveat': 'Unreliable poses cannot establish whether the physical capture lacked translation.',
                'rejection_counts': {reason: sum(reason in p['acceptance_reason'].split('|') for p in pairs) for reason in sorted({r for p in pairs for r in p['acceptance_reason'].split('|') if r != 'ACCEPTED'})}}
    for name, data in [('parallax_analysis.json', report), ('metric_scale_report.json', scale), ('capture_guidance.json', guidance)]:
        (out/name).write_text(json.dumps(data, indent=2, allow_nan=False))
    fields = [k for k in pairs[0] if k != 'observed_cells_i'] if pairs else ['frame_i', 'frame_j', 'acceptance_reason']
    for name in ('camera_baselines.csv', 'keyframe_pair_quality.csv'):
        with (out/name).open('w') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); writer.writeheader(); writer.writerows(pairs)
    centers = [camera_pose(p)[1].tolist() for p in poses]
    # Self-contained orthographic trajectory plot; input units are explicitly labelled.
    points = np.asarray(centers).reshape(-1, 3)
    if len(points):
        span = max(float(np.ptp(points, axis=0).max()), 1e-6)
        plot = (points-points.min(axis=0))/span*420+40
        path = ' '.join(f'{p[0]:.3f},{500-p[2]:.3f}' for p in plot)
    else: path = ''
    (out/'camera_trajectory_visualization.html').write_text('<!doctype html><meta charset="utf-8"><title>Camera trajectory diagnostics</title><h1>Camera trajectory — X/Z projection</h1><p>'+html.escape(report['status']+' / '+scale['status'])+'</p><p>Axes: X (horizontal), Z (vertical), input pose units. For video-only input these are arbitrary per-step units with unverified scale consistency. Equal plotted axis scale. Projection can hide Y motion. This is an estimated trajectory, not ground truth.</p><svg viewBox="0 0 520 520" width="520"><polyline fill="none" stroke="#196" stroke-width="2" points="'+path+'"/></svg><details><summary>Camera centers (X,Y,Z), input units</summary><pre>'+html.escape(json.dumps(centers, indent=2))+'</pre></details>')
    return report


def estimate_monocular_trajectory(frames, K):
    """Diagnostic SfM only: unit inter-frame steps, no metric or covariance claim.

    Essential decomposition can be degenerate under rotation. These poses are
    deliberately unverified and cannot authorize a reconstruction.
    """
    detector = cv2.SIFT_create(nfeatures=1500)
    features = [detector.detectAndCompute(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), None) for f in frames]
    poses = [{'R': np.eye(3), 't': np.zeros(3), 'reliable': False, 'scale_consistent': False}]
    for i in range(1, len(frames)):
        R, t = np.asarray(poses[-1]['R']), np.asarray(poses[-1]['t'])
        k1, d1 = features[i-1]; k2, d2 = features[i]
        tracked = False
        if d1 is not None and d2 is not None and min(len(d1), len(d2)) >= 2:
            matches = [m for m, n in cv2.BFMatcher().knnMatch(d1, d2, k=2) if m.distance < .75*n.distance]
            if len(matches) >= 8:
                a = np.float64([k1[m.queryIdx].pt for m in matches]); b = np.float64([k2[m.trainIdx].pt for m in matches])
                E, mask = cv2.findEssentialMat(a, b, K, method=cv2.RANSAC, prob=.999, threshold=1.)
                if E is not None and E.shape == (3, 3):
                    n, relative_R, relative_t, _ = cv2.recoverPose(E, a, b, K, mask=mask)
                    if n >= 30:
                        R, t = relative_R @ R, relative_R @ t + relative_t.ravel()
                        tracked = True
        poses.append({'R': R, 't': t, 'reliable': False, 'scale_consistent': False,
                      'diagnostic_tracking_succeeded': tracked,
                      'scale_note': 'arbitrary unit step per recovered pair; trajectory scale and covariance unobserved'})
    return poses
