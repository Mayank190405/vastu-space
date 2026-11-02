"""One rigid coordinate transform for geometry, texture cameras and trajectories."""
import numpy as np


def output_transform(upright, floor, leveling=None, level_floor=0.0):
    rotation = np.asarray(upright, dtype=float)
    translation = np.array([0., -float(floor), 0.])
    if leveling is not None:
        leveling = np.asarray(leveling, dtype=float)
        rotation = leveling @ rotation
        translation = leveling @ translation - np.array([0., float(level_floor), 0.])
    return rotation, translation


def transform_points(points, rotation, translation):
    return (rotation @ np.asarray(points).T).T + translation


def aligned_camera(pose, rotation, translation):
    # q=A*x+b, camera=R*x+t -> camera=(R*A.T)*q + t-(R*A.T)*b
    R = np.asarray(pose['R']) @ rotation.T
    t = np.asarray(pose['t']).reshape(3, 1) - R @ np.asarray(translation).reshape(3, 1)
    return {'R': R, 't': t, 'C': (-R.T @ t).ravel().tolist()}


def verified_depth_inputs(depths, confidences, refined, masks):
    if not (len(depths) == len(confidences) == len(refined) == len(masks)):
        raise ValueError('Depth evidence frame count mismatch')
    outputs, enabled = [], []
    for prior, confidence, candidate, mask in zip(depths, confidences, refined, masks):
        candidate = np.asarray(candidate)
        if candidate.shape != prior.shape or np.asarray(mask).shape != prior.shape:
            raise ValueError('Depth evidence shape mismatch')
        valid = (np.asarray(confidence, dtype=bool) & np.asarray(mask, dtype=bool)
                 & np.isfinite(candidate) & (candidate > 0))
        outputs.append(np.where(valid, candidate, 0).astype(np.float32))
        enabled.append(valid)
    return outputs, enabled


def trajectory_parallax(poses, residual_px, min_baseline=0.10, min_residual=1.5, pair_report=None):
    """Legacy separation diagnostic in input units. Only a geometry report can pass.

    Pixel residual and an arbitrary-scale trajectory cannot establish metric parallax.
    Use core.reconstruction.parallax for pair selection and verification.
    """
    centers = np.array([(-np.asarray(p['R']).T @ np.asarray(p['t']).reshape(3, 1)).ravel()
                        for p in poses])
    if len(centers) < 2 or not np.isfinite(centers).all() or not np.isfinite(residual_px):
        return 0.0, False
    # Maximum separation, not accumulated jitter or optical-flow-derived meters.
    baseline = float(np.max(np.linalg.norm(centers[:, None] - centers[None, :], axis=2)))
    return baseline, bool(pair_report and pair_report.get('parallax_gate_passed') is True
                          and pair_report.get('scale_status') == 'METRIC_ESTABLISHED'
                          and pair_report.get('verified_multi_view_geometry') is True)


def photometric_rmse(reference, rendered, mask, minimum_pixels=100):
    mask = np.asarray(mask, dtype=bool)
    if np.count_nonzero(mask) < minimum_pixels:
        return None
    # Convert before squaring: uint8 arithmetic wraps, hiding large errors.
    delta = reference.astype(np.float32)[mask] - rendered.astype(np.float32)[mask]
    return float(np.sqrt(np.mean(delta * delta)))
