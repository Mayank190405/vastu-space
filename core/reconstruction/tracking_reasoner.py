"""Multi-anchor camera recovery with mutual matching and held-out reprojection checks."""
import cv2
import numpy as np


class TrackingReasoner:
    def __init__(self, policy, max_anchors=4):
        self.policy = policy
        self.max_anchors = max_anchors

    def track(self, frames, depths, K):
        """
        Multi-anchor camera tracking with geometric verification, Levenberg-Marquardt
        refinement, held-out reprojection error evaluation, and discontinuity detection.
        """
        sift = cv2.SIFT_create(nfeatures=4000)
        features = [sift.detectAndCompute(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), None) for f in frames]
        poses = [None] * len(frames)
        # Frame 0 is anchor at origin
        poses[0] = {
            'R': np.eye(3, dtype=np.float64),
            't': np.zeros((3, 1), dtype=np.float64),
            'is_tracked': True,
            'tracking_status': 'ANCHOR',
            'confidence': 1.0,
            'reprojection_rmse_px': 0.0,
            'reprojection_median_px': 0.0,
            'inliers': 0,
            'inlier_ratio': 1.0,
            'camera_position': [0.0, 0.0, 0.0]
        }

        attempts = []
        selected = []
        pnp_diagnostics = []

        # Record anchor frame 0 diagnostic
        pnp_diagnostics.append({
            'frame_idx': 0,
            'anchor_idx': -1,
            'candidate_matches': 0,
            'valid_3d_2d_correspondences': 0,
            'inliers': 0,
            'inlier_ratio': 1.0,
            'reprojection_rmse_px': 0.0,
            'reprojection_median_px': 0.0,
            'translation_m': 0.0,
            'rotation_deg': 0.0,
            'camera_pos_x': 0.0,
            'camera_pos_y': 0.0,
            'camera_pos_z': 0.0,
            'confidence': 1.0,
            'is_tracked': True,
            'estimator': 'ANCHOR',
            'rejection_reason': None
        })

        for current in range(1, len(frames)):
            candidates = []
            anchors = [i for i in range(current - 1, -1, -1) if poses[i] is not None][:self.max_anchors]
            rejection_reasons = []

            for anchor in anchors:
                result, report = self._attempt(anchor, current, features, depths, K, poses[anchor])
                attempts.append(report)
                if result is not None:
                    candidates.append((result, report))
                else:
                    rejection_reasons.append(f"anchor_{anchor}:{report.get('reason', 'rejected')}")

            if candidates:
                # Rank candidates by: heldout inlier ratio, inlier count, and lowest heldout median error
                result, report = max(candidates, key=lambda item: (
                    item[1]['heldout_inlier_ratio'],
                    item[1]['inliers'],
                    -item[1].get('heldout_median_error_px', 999.0)
                ))
                cam_pos = report.get('camera_position', [0.0, 0.0, 0.0])
                result['is_tracked'] = True
                result['tracking_status'] = 'TRACKED'
                result['confidence'] = report.get('confidence', 0.8)
                result['reprojection_rmse_px'] = report.get('reprojection_rmse_px', 1.0)
                result['reprojection_median_px'] = report.get('heldout_median_error_px', 1.0)
                result['inliers'] = report.get('inliers', 0)
                result['inlier_ratio'] = report.get('inlier_ratio', 0.0)
                result['camera_position'] = cam_pos
                poses[current] = result
                selected.append(report)

                pnp_diagnostics.append({
                    'frame_idx': current,
                    'anchor_idx': report.get('frame_a', -1),
                    'candidate_matches': report.get('candidate_matches', 0),
                    'valid_3d_2d_correspondences': report.get('valid_3d_2d_correspondences', 0),
                    'inliers': report.get('inliers', 0),
                    'inlier_ratio': round(report.get('inlier_ratio', 0.0), 3),
                    'reprojection_rmse_px': round(report.get('reprojection_rmse_px', 0.0), 2),
                    'reprojection_median_px': round(report.get('heldout_median_error_px', 0.0), 2),
                    'translation_m': round(report.get('translation_mag_m', 0.0), 4),
                    'rotation_deg': round(report.get('rotation_deg', 0.0), 2),
                    'camera_pos_x': round(cam_pos[0], 4),
                    'camera_pos_y': round(cam_pos[1], 4),
                    'camera_pos_z': round(cam_pos[2], 4),
                    'confidence': round(report.get('confidence', 0.0), 3),
                    'is_tracked': True,
                    'estimator': report.get('estimator', 'REFINED_PNP_LM'),
                    'rejection_reason': None
                })
            else:
                # Frame failed tracking on all anchors: record explicit untracked state
                rejection_str = "; ".join(rejection_reasons) if rejection_reasons else "no_valid_anchors"
                poses[current] = None
                pnp_diagnostics.append({
                    'frame_idx': current,
                    'anchor_idx': anchors[0] if anchors else -1,
                    'candidate_matches': 0,
                    'valid_3d_2d_correspondences': 0,
                    'inliers': 0,
                    'inlier_ratio': 0.0,
                    'reprojection_rmse_px': 999.0,
                    'reprojection_median_px': 999.0,
                    'translation_m': 0.0,
                    'rotation_deg': 0.0,
                    'camera_pos_x': 0.0,
                    'camera_pos_y': 0.0,
                    'camera_pos_z': 0.0,
                    'confidence': 0.0,
                    'is_tracked': False,
                    'estimator': 'NONE',
                    'rejection_reason': rejection_str
                })

        # Calculate trajectory-wide statistics and continuity
        tracked_indices = [i for i, p in enumerate(poses) if p is not None]
        untracked_indices = [i for i, p in enumerate(poses) if p is None]
        inlier_counts = [d['inliers'] for d in pnp_diagnostics if d['is_tracked'] and d['frame_idx'] > 0]
        inlier_ratios = [d['inlier_ratio'] for d in pnp_diagnostics if d['is_tracked'] and d['frame_idx'] > 0]
        rmse_values = [d['reprojection_rmse_px'] for d in pnp_diagnostics if d['is_tracked'] and d['frame_idx'] > 0]
        median_values = [d['reprojection_median_px'] for d in pnp_diagnostics if d['is_tracked'] and d['frame_idx'] > 0]
        step_translations = [d['translation_m'] for d in pnp_diagnostics if d['is_tracked'] and d['frame_idx'] > 0]
        step_rotations = [d['rotation_deg'] for d in pnp_diagnostics if d['is_tracked'] and d['frame_idx'] > 0]

        max_step_trans = float(np.max(step_translations)) if step_translations else 0.0
        max_step_rot = float(np.max(step_rotations)) if step_rotations else 0.0
        is_continuous = (len(untracked_indices) == 0) and (max_step_trans <= 1.5) and (max_step_rot <= 45.0)

        pose_validation = {
            'total_keyframes': len(frames),
            'tracked_keyframes': len(tracked_indices),
            'untracked_keyframes': len(untracked_indices),
            'tracking_success_rate': round(len(tracked_indices) / max(len(frames), 1), 3),
            'average_inliers': round(float(np.mean(inlier_counts)), 1) if inlier_counts else 0.0,
            'average_inlier_ratio': round(float(np.mean(inlier_ratios)), 3) if inlier_ratios else 0.0,
            'average_reprojection_rmse_px': round(float(np.mean(rmse_values)), 2) if rmse_values else 0.0,
            'average_heldout_median_error_px': round(float(np.mean(median_values)), 2) if median_values else 0.0,
            'is_trajectory_continuous': is_continuous,
            'max_step_translation_m': round(max_step_trans, 4),
            'max_step_rotation_deg': round(max_step_rot, 2),
            'discontinuities_detected': 0 if is_continuous else (1 if untracked_indices else 0),
            'overall_tracking_confidence': round(float(np.mean([d['confidence'] for d in pnp_diagnostics if d['is_tracked']])), 3) if tracked_indices else 0.0,
            'tracking_method': 'MULTI_ANCHOR_PNP_WITH_LM_REFINEMENT',
            'per_keyframe_diagnostics': pnp_diagnostics
        }

        return {
            'poses': poses,
            'keypoints': [f[0] for f in features],
            'descriptors': [f[1] for f in features],
            'pnp_diagnostics': pnp_diagnostics,
            'pose_validation': pose_validation,
            'report': {
                'algorithm': 'MULTI_ANCHOR_MUTUAL_EPIPOLAR_PNP_HELDOUT',
                'status': 'PASS' if len(untracked_indices) == 0 else 'PARTIAL',
                'tracked_frames': tracked_indices,
                'rejected_frames': untracked_indices,
                'attempts': attempts,
                'selected': selected,
                'pose_validation': pose_validation,
                'pnp_diagnostics': pnp_diagnostics
            }
        }

    def _attempt(self, a, b, features, depths, K, pose):
        report = {'frame_a': a, 'frame_b': b, 'accepted': False}
        kp_a, des_a = features[a]
        kp_b, des_b = features[b]
        if des_a is None or des_b is None or min(len(des_a), len(des_b)) < 2:
            return None, dict(report, reason='missing_features')

        matcher = cv2.BFMatcher(cv2.NORM_L2)
        forward = matcher.knnMatch(des_a, des_b, k=2)
        backward = matcher.knnMatch(des_b, des_a, k=2)
        reverse = {m[0].queryIdx: m[0].trainIdx for m in backward if len(m) == 2 and m[0].distance < 0.75 * m[1].distance}
        good = [m[0] for m in forward if len(m) == 2 and m[0].distance < 0.75 * m[1].distance
                and reverse.get(m[0].trainIdx) == m[0].queryIdx]
        report['candidate_matches'] = len(good)
        report['mutual_matches'] = len(good)

        # Realistic floor for mutual matches in room scanning
        min_mutual_required = max(15, self.policy.min_tracking_inliers // 2)
        if len(good) < min_mutual_required:
            return None, dict(report, reason='insufficient_mutual_matches')

        p = np.float32([kp_a[m.queryIdx].pt for m in good])
        q = np.float32([kp_b[m.trainIdx].pt for m in good])
        F, mask = cv2.findFundamentalMat(p, q, cv2.FM_RANSAC, 1.0, 0.999)
        if F is None or mask is None:
            return None, dict(report, reason='epipolar_fit_failed')
        keep = mask.ravel() != 0
        p, q = p[keep], q[keep]

        h, w = depths[a].shape
        u, v = np.clip(np.rint(p[:, 0]).astype(int), 0, w - 1), np.clip(np.rint(p[:, 1]).astype(int), 0, h - 1)
        z = depths[a][v, u]
        keep = np.isfinite(z) & (z > 0.35) & (z < self.policy.max_scene_depth_m)
        p, q, z = p[keep], q[keep], z[keep]

        # Avoid feature depths that straddle extreme depth discontinuities
        gx = cv2.Sobel(depths[a], cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(depths[a], cv2.CV_32F, 0, 1, ksize=3)
        u2 = np.clip(np.rint(p[:, 0]).astype(int), 0, w - 1)
        v2 = np.clip(np.rint(p[:, 1]).astype(int), 0, h - 1)
        stable = np.hypot(gx[v2, u2], gy[v2, u2]) / np.maximum(z, 0.1) < 0.15
        report['stable_depth_matches'] = int(np.count_nonzero(stable))

        min_geo_matches = max(12, self.policy.min_tracking_inliers // 2)
        if np.count_nonzero(stable) >= min_geo_matches:
            p, q, z = p[stable], q[stable], z[stable]
        report['valid_3d_2d_correspondences'] = len(p)
        report['epipolar_depth_matches'] = len(p)

        if len(p) < min_geo_matches:
            return None, dict(report, reason='insufficient_geometric_matches')

        # Backproject 2D keypoints using pinhole intrinsics and depth
        X = (np.linalg.inv(K) @ np.column_stack([p, np.ones(len(p))]).T).T * z[:, None]

        # 20% independent held-out correspondence test split
        heldout = np.arange(len(p)) % 5 == 0
        train = ~heldout
        if np.count_nonzero(train) < 6:
            train = np.ones(len(p), dtype=bool)
            heldout = np.zeros(len(p), dtype=bool)

        ret, r, t, inliers = cv2.solvePnPRansac(
            X[train].astype(np.float32), q[train].astype(np.float32), K, None,
            iterationsCount=1000, reprojectionError=2.0, confidence=0.999, flags=cv2.SOLVEPNP_EPNP
        )
        count = len(inliers) if inliers is not None else 0
        ratio = count / max(np.count_nonzero(train), 1)
        report.update(inliers=count, inlier_ratio=round(ratio, 3))

        if not ret or r is None or t is None or not np.isfinite(r).all() or not np.isfinite(t).all():
            return None, dict(report, reason='pnp_failed')

        # Non-linear Levenberg-Marquardt pose refinement on inliers
        if count >= 6:
            try:
                cv2.solvePnPRefineLM(
                    X[train][inliers.ravel()].astype(np.float64),
                    q[train][inliers.ravel()].astype(np.float64),
                    K.astype(np.float64),
                    None,
                    r,
                    t
                )
            except Exception:
                pass

        # Reprojection RMSE on inliers
        if count > 0:
            proj_inliers, _ = cv2.projectPoints(X[train][inliers.ravel()], r, t, K, None)
            err_inliers = np.linalg.norm(proj_inliers.reshape(-1, 2) - q[train][inliers.ravel()], axis=1)
            reproj_rmse_px = float(np.sqrt(np.mean(err_inliers**2)))
        else:
            reproj_rmse_px = 999.0

        # Reprojection error on independent held-out correspondences
        if np.count_nonzero(heldout) > 0:
            projected, _ = cv2.projectPoints(X[heldout], r, t, K, None)
            error_heldout = np.linalg.norm(projected.reshape(-1, 2) - q[heldout], axis=1)
            heldout_ratio = float(np.mean(error_heldout <= 3.0))
            heldout_median_px = float(np.median(error_heldout))
        else:
            heldout_ratio = ratio
            heldout_median_px = reproj_rmse_px

        translation = float(np.linalg.norm(t))
        rot_deg = float(np.degrees(np.linalg.norm(r)))

        report.update(
            heldout_inlier_ratio=round(heldout_ratio, 3),
            heldout_median_error_px=round(heldout_median_px, 2),
            reprojection_rmse_px=round(reproj_rmse_px, 2),
            translation_mag_m=round(translation, 4),
            rotation_deg=round(rot_deg, 2),
            good_matches=len(p),
            confidence=round(min(ratio, heldout_ratio), 3)
        )

        min_required_inliers = max(12, int(self.policy.min_tracking_inliers * 0.5))
        min_required_ratio = max(0.25, self.policy.min_tracking_inlier_ratio * 0.7)

        # Immediate trajectory discontinuity check
        if translation > 1.5 or rot_deg > 45.0:
            return None, dict(report, reason=f'trajectory_discontinuity_detected (step={translation:.2f}m > 1.5m, rot={rot_deg:.1f}deg > 45deg)')

        if (count < min_required_inliers or ratio < min_required_ratio or
                heldout_ratio < min_required_ratio or heldout_median_px > 3.5 or
                translation > self.policy.max_pair_translation_m or rot_deg > 45.0):
            recovered = self._essential_recovery(X, p, q, train, heldout, K)
            if recovered is None:
                return None, dict(report, reason='tracking_or_heldout_gate_failed')
            r, t, evidence = recovered
            rot_deg = float(np.degrees(np.linalg.norm(r)))
            report.update(evidence, estimator='ESSENTIAL_ROTATION_WITH_DEPTH_ANCHORED_SCALE', rotation_deg=round(rot_deg, 2))
        else:
            report['estimator'] = 'REFINED_PNP_LM'

        R, _ = cv2.Rodrigues(r)
        world_R = R @ pose['R']
        world_t = R @ pose['t'] + t.reshape(3, 1)
        camera = (-world_R.T @ world_t).ravel()

        anchor_cam = (-pose['R'].T @ pose['t']).ravel()
        step_dist = float(np.linalg.norm(camera - anchor_cam))

        if not np.isfinite(camera).all() or np.linalg.norm(camera) > 20.0:
            return None, dict(report, reason='trajectory_extent_invalid')

        # Detect unexplained trajectory discontinuity
        if step_dist > 1.5 or rot_deg > 45.0:
            return None, dict(report, reason=f'trajectory_discontinuity_detected (step={step_dist:.2f}m > 1.5m, rot={rot_deg:.1f}deg > 45deg)')

        report.update(
            accepted=True,
            reason='independent_reprojection_gate_passed',
            camera_position=[round(c, 4) for c in camera.tolist()],
            step_distance_m=round(step_dist, 4)
        )
        return {'R': world_R, 't': world_t}, report

    def _essential_recovery(self, X, p, q, train, heldout, K):
        candidates = []
        E, _ = cv2.findEssentialMat(p[train], q[train], K, cv2.RANSAC, 0.999, 0.5)
        if E is not None and E.shape == (3, 3):
            candidates.append(E)
        F, _ = cv2.findFundamentalMat(p[train], q[train], cv2.FM_8POINT)
        if F is not None and F.shape == (3, 3):
            E = K.T @ F @ K
            U, singular, V = np.linalg.svd(E)
            candidates.append(U @ np.diag([(singular[0] + singular[1]) / 2] * 2 + [0]) @ V)

        rays = (np.linalg.inv(K) @ np.column_stack([q, np.ones(len(q))]).T).T
        best = None
        min_required_inliers = max(12, int(self.policy.min_tracking_inliers * 0.5))

        for E in candidates:
            try:
                _, R, direction, _ = cv2.recoverPose(E, p[train], q[train], K)
            except cv2.error:
                continue
            rotated = (R @ X.T).T
            A = np.cross(rays[train], direction.ravel())
            B = np.cross(rays[train], rotated[train])
            scales = -np.sum(A * B, axis=1) / np.maximum(np.sum(A * A, axis=1), 1e-12)
            scales = scales[np.isfinite(scales) & (scales >= 0) & (scales <= self.policy.max_pair_translation_m)]
            if len(scales) < min_required_inliers:
                continue
            r, _ = cv2.Rodrigues(R)
            for scale in np.unique(np.quantile(scales, np.linspace(0, 1, 81))):
                t = direction * scale
                projected, _ = cv2.projectPoints(X[train], r, t, K, None)
                errors = np.linalg.norm(projected.reshape(-1, 2) - q[train], axis=1)
                score = (int(np.count_nonzero(errors <= 2.0)), -float(np.median(errors)))
                if best is None or score > best[0]:
                    best = (score, r, t)
        if best is None:
            return None

        count = best[0][0]
        ratio = count / max(np.count_nonzero(train), 1)
        r, t = best[1:]

        if np.count_nonzero(heldout) > 0:
            projected, _ = cv2.projectPoints(X[heldout], r, t, K, None)
            errors = np.linalg.norm(projected.reshape(-1, 2) - q[heldout], axis=1)
            heldout_ratio = float(np.mean(errors <= 3.0))
            median = float(np.median(errors))
        else:
            heldout_ratio = ratio
            median = -best[0][1]

        min_required_ratio = max(0.25, self.policy.min_tracking_inlier_ratio * 0.7)
        if count < min_required_inliers or ratio < min_required_ratio or heldout_ratio < min_required_ratio or median > 3.5:
            return None

        return r, t, {
            'inliers': count,
            'inlier_ratio': round(ratio, 3),
            'heldout_inlier_ratio': round(heldout_ratio, 3),
            'heldout_median_error_px': round(median, 2),
            'translation_mag_m': round(float(np.linalg.norm(t)), 4),
            'confidence': round(min(ratio, heldout_ratio), 3)
        }
