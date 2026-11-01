"""Evidence-based local plane-sweep depth refinement.

Neural depth supplies bounded hypotheses, not ground truth. Independent translated
views must support a hypothesis photometrically and geometrically. Unknown pixels
stay unknown; confidence is an evidence score, not a calibrated probability.
Poses use X_camera = R @ X_world + t. All images share calibrated intrinsics.
"""
from dataclasses import asdict, dataclass
import math
import logging

import cv2
import numpy as np


@dataclass(frozen=True)
class DepthReasoningConfig:
    hypothesis_count: int = 13
    relative_search_radius: float = 0.15
    max_neighbors: int = 4
    min_supporting_neighbors: int = 2
    min_baseline_m: float = 0.03
    min_ray_angle_deg: float = 1.0
    depth_tolerance_m: float = 0.05
    relative_depth_tolerance: float = 0.02
    patch_size: int = 5
    min_texture_std: float = 0.015
    max_photometric_error: float = 0.06
    min_uniqueness_margin: float = 0.002
    min_accepted_fraction: float = 0.05

    def __post_init__(self):
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be finite and positive')
        for name in ('hypothesis_count', 'max_neighbors', 'min_supporting_neighbors', 'patch_size'):
            if not isinstance(getattr(self, name), int):
                raise ValueError(f'{name} must be an integer')
        if not 5 <= self.hypothesis_count <= 65 or self.hypothesis_count % 2 != 1:
            raise ValueError('hypothesis_count must be odd and between 5 and 65')
        if self.patch_size < 3 or self.patch_size % 2 != 1:
            raise ValueError('patch_size must be odd and at least 3')
        if self.min_supporting_neighbors < 2 or not self.min_supporting_neighbors <= self.max_neighbors <= 32:
            raise ValueError('Require 2 to 32 independent neighboring views')
        if self.relative_search_radius >= 1 or self.min_accepted_fraction > 1 or self.min_ray_angle_deg >= 90:
            raise ValueError('Invalid search radius, accepted fraction, or ray angle')


class KeyframeDepthReasoner:
    REASONS = {0: 'accepted', 1: 'invalid_or_low_confidence_prior', 2: 'insufficient_texture',
               3: 'insufficient_independent_baseline', 4: 'insufficient_depth_consensus',
               5: 'photometric_mismatch', 6: 'ambiguous_depth_hypotheses', 7: 'search_boundary_reached'}

    def __init__(self, config=None):
        self.config = config or DepthReasoningConfig()

    def refine(self, frames, depths, confidences, poses, K):
        """Return refined depths, evidence confidence, rejection masks and audit report.

        Rejected depth is zero. Inputs are never mutated. No iterative self-voting:
        all hypotheses are checked against the original, frozen neighboring priors.
        """
        n = len(frames)
        if n < 3 or not (len(depths) == len(confidences) == len(poses) == n):
            raise ValueError('Need at least three matching frames, depths, confidences and poses')
        K = np.asarray(K, dtype=np.float64)
        if K.shape != (3, 3) or not np.isfinite(K).all() or K[0, 0] <= 0 or K[1, 1] <= 0 or not np.allclose(K[2], [0, 0, 1]):
            raise ValueError('Invalid calibrated intrinsics')
        shape = depths[0].shape
        if len(shape) != 2 or min(shape) < self.config.patch_size:
            raise ValueError('Depth maps must be 2D and larger than the patch')
        rotations, translations, centers, grays, textures, valid_masks = [], [], [], [], [], []
        for frame, depth, confidence, pose in zip(frames, depths, confidences, poses):
            if frame.shape != (*shape, 3) or frame.dtype != np.uint8 or depth.shape != shape or confidence.shape != shape:
                raise ValueError('Expected equal-sized uint8 BGR images, depths and confidence maps')
            R = np.asarray(pose['R'], dtype=np.float64)
            t = np.asarray(pose['t'], dtype=np.float64).reshape(3)
            if (R.shape != (3, 3) or not np.isfinite(R).all() or not np.isfinite(t).all()
                    or not np.allclose(R.T @ R, np.eye(3), atol=1e-5) or not np.isclose(np.linalg.det(R), 1, atol=1e-5)):
                raise ValueError('Camera poses must be finite rigid world-to-camera transforms')
            rotations.append(R)
            translations.append(t)
            centers.append(-R.T @ t)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
            mean = self._box(gray)
            textures.append(np.sqrt(np.maximum(self._box(gray * gray) - mean * mean, 0)))
            grays.append(gray - mean)  # Local mean removal tolerates moderate exposure changes.
            valid_masks.append(np.isfinite(depth) & (depth > 0) & np.isfinite(confidence) & (confidence > 0.25))
        h, w = shape
        v, u = np.indices(shape, dtype=np.float32)
        rays = (np.linalg.inv(K) @ np.stack([u.ravel(), v.ravel(), np.ones(h*w)])).reshape(3, h, w)
        result_depths, result_confidences, reason_maps, support_maps, uncertainty_maps, frame_reports = [], [], [], [], [], []
        for i in range(n):
            logging.getLogger(__name__).info("Depth evidence reasoning: keyframe %d/%d", i+1, n)
            neighbors = []
            # Prefer nearby frames; duplicate camera centers never count as independent evidence.
            for j in sorted(range(n), key=lambda j: abs(j-i)):
                if j == i or np.linalg.norm(centers[i]-centers[j]) < self.config.min_baseline_m:
                    continue
                if any(np.linalg.norm(centers[j]-centers[k]) < self.config.min_baseline_m for k in neighbors):
                    continue
                neighbors.append(j)
                if len(neighbors) == self.config.max_neighbors:
                    break
            reason = np.full(shape, 4, dtype=np.uint8)
            reason[~valid_masks[i]] = 1
            textured = textures[i] >= self.config.min_texture_std
            reason[valid_masks[i] & ~textured] = 2
            eligible = valid_masks[i] & textured
            if len(neighbors) < self.config.min_supporting_neighbors:
                reason[eligible] = 3
                refined = np.zeros(shape, dtype=np.float32)
                confidence = np.zeros(shape, dtype=np.float32)
                support = np.zeros(shape, dtype=np.uint8)
                uncertainty = np.zeros(shape, dtype=np.float32)
            else:
                refined, confidence, support, uncertainty, reason = self._refine_frame(
                    i, neighbors, depths, grays, valid_masks, rotations, translations,
                    K, rays, eligible, reason)
            result_depths.append(refined)
            result_confidences.append(confidence)
            reason_maps.append(reason)
            support_maps.append(support)
            uncertainty_maps.append(uncertainty)
            accepted = reason == 0
            frame_reports.append({'frame_id': i, 'neighbor_frame_ids': neighbors,
                                  'accepted_fraction': float(np.mean(accepted)),
                                  'reason_counts': {name: int(np.count_nonzero(reason == code))
                                                    for code, name in self.REASONS.items()},
                                  'median_depth_change_m': float(np.median(np.abs(refined[accepted]-depths[i][accepted]))) if accepted.any() else None})
        fraction = float(np.mean([r['accepted_fraction'] for r in frame_reports]))
        passed = all(r['accepted_fraction'] >= self.config.min_accepted_fraction for r in frame_reports)
        return {'depths': result_depths, 'confidences': result_confidences, 'reasons': reason_maps,
                'support': support_maps, 'hypothesis_step_m': uncertainty_maps,
                'report': {'algorithm': 'BOUNDED_MULTIVIEW_PLANE_SWEEP', 'status': 'PASS' if passed else 'REJECTED',
                           'accepted_fraction': fraction, 'config': asdict(self.config), 'frames': frame_reports,
                           'scale_source': 'input_depth_and_pose_priors_not_independent_metric_measurement',
                           'confidence_semantics': 'evidence_score_not_probability',
                           'uncertainty_semantics': 'hypothesis_step_not_physical_error_bound'}}

    def _box(self, data):
        size = self.config.patch_size
        return cv2.boxFilter(data, -1, (size, size), borderType=cv2.BORDER_REFLECT101)

    def _refine_frame(self, i, neighbors, depths, grays, masks, rotations, translations, K, rays, eligible, reason):
        cfg = self.config
        shape = depths[i].shape
        h, w = shape
        factors = np.linspace(1-cfg.relative_search_radius, 1+cfg.relative_search_radius, cfg.hypothesis_count)
        costs = np.full((len(factors), h, w), np.inf, dtype=np.float32)
        counts = np.zeros(costs.shape, dtype=np.uint8)
        safe_prior = np.where(masks[i], depths[i], 0).astype(np.float32)
        transforms = []
        for j in neighbors:
            R = rotations[j] @ rotations[i].T
            t = translations[j] - R @ translations[i]
            center_j = -R.T @ t  # Neighbor center in the reference camera coordinates.
            transforms.append((j, R, t, center_j))
        for k, factor in enumerate(factors):
            d = safe_prior * factor
            X = rays * d
            total = np.zeros(shape, dtype=np.float32)
            count = np.zeros(shape, dtype=np.uint8)
            for j, R, t, center_j in transforms:
                Xn = (R @ X.reshape(3, -1) + t[:, None]).reshape(3, h, w)
                zn = Xn[2]
                with np.errstate(divide='ignore', invalid='ignore'):
                    projected = K @ Xn.reshape(3, -1)
                    mx = (projected[0]/projected[2]).reshape(shape).astype(np.float32)
                    my = (projected[1]/projected[2]).reshape(shape).astype(np.float32)
                mx = np.nan_to_num(mx, nan=-100, posinf=-100, neginf=-100)
                my = np.nan_to_num(my, nan=-100, posinf=-100, neginf=-100)
                radius = cfg.patch_size // 2 + 1
                inside = (zn > 0) & (mx >= radius) & (mx < w-radius) & (my >= radius) & (my < h-radius)
                observed = cv2.remap(np.where(masks[j], depths[j], 0).astype(np.float32), mx, my, cv2.INTER_NEAREST)
                neighbor_valid = cv2.remap(masks[j].astype(np.uint8), mx, my, cv2.INTER_NEAREST) > 0
                # Points behind a nearer observed surface are occluded, not evidence.
                tolerance = cfg.depth_tolerance_m + cfg.relative_depth_tolerance * np.maximum(zn, 0)
                geometric = neighbor_valid & (np.abs(zn-observed) <= tolerance)
                ray_j = X - center_j[:, None, None]
                cosine = np.sum(X*ray_j, axis=0) / np.maximum(np.linalg.norm(X, axis=0)*np.linalg.norm(ray_j, axis=0), 1e-12)
                triangulatable = cosine <= np.cos(np.deg2rad(cfg.min_ray_angle_deg))
                warped = cv2.remap(grays[j], mx, my, cv2.INTER_LINEAR)
                photo = self._box(np.abs(grays[i]-warped))
                valid = eligible & inside & geometric & triangulatable
                total += np.where(valid, photo, 0)
                count += valid.astype(np.uint8)
            counts[k] = count
            good = count >= cfg.min_supporting_neighbors
            costs[k, good] = total[good] / count[good]
        best_index = np.argmin(costs, axis=0)
        best = np.take_along_axis(costs, best_index[None], axis=0)[0]
        support = np.take_along_axis(counts, best_index[None], axis=0)[0]
        # Competing solutions must be separated by >= two hypothesis steps.
        competitors = costs.copy()
        for k in range(len(factors)):
            competitors[k][np.abs(best_index-k) <= 1] = np.inf
        second = np.min(competitors, axis=0)
        with np.errstate(invalid='ignore'):
            margin = second-best
        consensus = eligible & np.isfinite(best)
        photo_ok = consensus & (best <= cfg.max_photometric_error)
        # An isolated valid candidate is NOT enough to establish uniqueness.
        unique = np.isfinite(second) & (margin >= cfg.min_uniqueness_margin)
        boundary = (best_index == 0) | (best_index == len(factors)-1)
        accepted = photo_ok & unique & ~boundary
        reason[consensus] = 5
        reason[photo_ok] = 6
        reason[photo_ok & unique & boundary] = 7
        reason[accepted] = 0
        refined = np.where(accepted, safe_prior*factors[best_index], 0).astype(np.float32)
        confidence = np.where(accepted, np.clip(1-best/cfg.max_photometric_error, 0, 1), 0).astype(np.float32)
        step = np.where(accepted, safe_prior*(factors[1]-factors[0]), 0).astype(np.float32)
        support[~accepted] = 0
        return refined, confidence, support, step, reason

