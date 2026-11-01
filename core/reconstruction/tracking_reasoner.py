"""Multi-anchor camera recovery with mutual matching and held-out reprojection checks."""
import cv2
import numpy as np


class TrackingReasoner:
    def __init__(self, policy, max_anchors=4):
        self.policy = policy
        self.max_anchors = max_anchors

    def track(self, frames, depths, K):
        sift = cv2.SIFT_create(nfeatures=4000)
        features = [sift.detectAndCompute(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), None) for f in frames]
        poses = [None]*len(frames)
        poses[0] = {'R': np.eye(3), 't': np.zeros((3, 1))}
        attempts, selected = [], []
        for current in range(1, len(frames)):
            candidates = []
            anchors = [i for i in range(current-1, -1, -1) if poses[i] is not None][:self.max_anchors]
            for anchor in anchors:
                result, report = self._attempt(anchor, current, features, depths, K, poses[anchor])
                attempts.append(report)
                if result is not None:
                    candidates.append((result, report))
            if candidates:
                result, report = max(candidates, key=lambda item: (
                    item[1]['heldout_inlier_ratio'], item[1]['inliers']))
                poses[current] = result
                selected.append(report)
        return {'poses': poses, 'keypoints': [f[0] for f in features],
                'descriptors': [f[1] for f in features],
                'report': {'algorithm': 'MULTI_ANCHOR_MUTUAL_EPIPOLAR_PNP_HELDOUT',
                           'status': 'PASS' if all(p is not None for p in poses) else 'PARTIAL',
                           'tracked_frames': [i for i, p in enumerate(poses) if p is not None],
                           'rejected_frames': [i for i, p in enumerate(poses) if p is None],
                           'attempts': attempts, 'selected': selected}}

    def _attempt(self, a, b, features, depths, K, pose):
        report = {'frame_a': a, 'frame_b': b, 'accepted': False}
        kp_a, des_a = features[a]
        kp_b, des_b = features[b]
        if des_a is None or des_b is None or min(len(des_a), len(des_b)) < 2:
            return None, dict(report, reason='missing_features')
        matcher = cv2.BFMatcher(cv2.NORM_L2)
        forward = matcher.knnMatch(des_a, des_b, k=2)
        backward = matcher.knnMatch(des_b, des_a, k=2)
        reverse = {m[0].queryIdx: m[0].trainIdx for m in backward if len(m) == 2 and m[0].distance < .72*m[1].distance}
        good = [m[0] for m in forward if len(m) == 2 and m[0].distance < .72*m[1].distance
                and reverse.get(m[0].trainIdx) == m[0].queryIdx]
        report['mutual_matches'] = len(good)
        if len(good) < self.policy.min_tracking_inliers+12:
            return None, dict(report, reason='insufficient_mutual_matches')
        p = np.float32([kp_a[m.queryIdx].pt for m in good])
        q = np.float32([kp_b[m.trainIdx].pt for m in good])
        F, mask = cv2.findFundamentalMat(p, q, cv2.FM_RANSAC, 1.0, .999)
        if F is None or mask is None:
            return None, dict(report, reason='epipolar_fit_failed')
        keep = mask.ravel() != 0
        p, q = p[keep], q[keep]
        h, w = depths[a].shape
        u, v = np.clip(np.rint(p[:, 0]).astype(int), 0, w-1), np.clip(np.rint(p[:, 1]).astype(int), 0, h-1)
        z = depths[a][v, u]
        keep = np.isfinite(z) & (z > .35) & (z < self.policy.max_scene_depth_m)
        p, q, z = p[keep], q[keep], z[keep]
        # Avoid feature depths that straddle a depth discontinuity. This mask is
        # selected from source depth alone, before fitting or testing a pose.
        gx = cv2.Sobel(depths[a], cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(depths[a], cv2.CV_32F, 0, 1, ksize=3)
        u2 = np.clip(np.rint(p[:, 0]).astype(int), 0, w-1)
        v2 = np.clip(np.rint(p[:, 1]).astype(int), 0, h-1)
        stable = np.hypot(gx[v2, u2], gy[v2, u2])/np.maximum(z, .1) < .12
        report['stable_depth_matches'] = int(np.count_nonzero(stable))
        if np.count_nonzero(stable) >= self.policy.min_tracking_inliers+12:
            p, q, z = p[stable], q[stable], z[stable]
        report['epipolar_depth_matches'] = len(p)
        if len(p) < self.policy.min_tracking_inliers+12:
            return None, dict(report, reason='insufficient_geometric_matches')
        X = (np.linalg.inv(K) @ np.column_stack([p, np.ones(len(p))]).T).T*z[:, None]
        heldout = np.arange(len(p)) % 5 == 0
        train = ~heldout
        ret, r, t, inliers = cv2.solvePnPRansac(
            X[train].astype(np.float32), q[train], K, None, iterationsCount=500,
            reprojectionError=2., confidence=.999, flags=cv2.SOLVEPNP_EPNP)
        count = len(inliers) if inliers is not None else 0
        ratio = count/max(np.count_nonzero(train), 1)
        report.update(inliers=count, inlier_ratio=ratio)
        if not ret or r is None or t is None or not np.isfinite(r).all() or not np.isfinite(t).all():
            return None, dict(report, reason='pnp_failed')
        if count >= 6:
            cv2.solvePnPRefineLM(X[train][inliers.ravel()], q[train][inliers.ravel()], K, None, r, t)
        projected, _ = cv2.projectPoints(X[heldout], r, t, K, None)
        error = np.linalg.norm(projected.reshape(-1, 2)-q[heldout], axis=1)
        heldout_ratio = float(np.mean(error <= 3.))
        translation = float(np.linalg.norm(t))
        report.update(heldout_inlier_ratio=heldout_ratio, heldout_median_error_px=float(np.median(error)),
                      translation_mag_m=translation, good_matches=len(p), confidence=min(ratio, heldout_ratio))
        if (count < self.policy.min_tracking_inliers or ratio < self.policy.min_tracking_inlier_ratio
                or heldout_ratio < self.policy.min_tracking_inlier_ratio or np.median(error) > 3
                or translation > self.policy.max_pair_translation_m):
            recovered = self._essential_recovery(X, p, q, train, heldout, K)
            if recovered is None:
                return None, dict(report, reason='tracking_or_heldout_gate_failed')
            r, t, evidence = recovered
            report.update(evidence, estimator='ESSENTIAL_ROTATION_WITH_DEPTH_ANCHORED_SCALE')
        else:
            report['estimator'] = 'REFINED_PNP'

        R, _ = cv2.Rodrigues(r)
        world_R = R @ pose['R']
        world_t = R @ pose['t']+t.reshape(3, 1)
        camera = (-world_R.T @ world_t).ravel()
        if not np.isfinite(camera).all() or np.linalg.norm(camera) > 20:
            return None, dict(report, reason='trajectory_extent_invalid')
        report.update(accepted=True, reason='independent_reprojection_gate_passed', camera_position=camera.tolist())
        return {'R': world_R, 't': world_t}, report

    def _essential_recovery(self, X, p, q, train, heldout, K):
        candidates = []
        E, _ = cv2.findEssentialMat(p[train], q[train], K, cv2.RANSAC, .999, .5)
        if E is not None and E.shape == (3, 3):
            candidates.append(E)
        F, _ = cv2.findFundamentalMat(p[train], q[train], cv2.FM_8POINT)
        if F is not None and F.shape == (3, 3):
            E = K.T @ F @ K
            U, singular, V = np.linalg.svd(E)
            candidates.append(U @ np.diag([(singular[0]+singular[1])/2]*2+[0]) @ V)
        rays = (np.linalg.inv(K) @ np.column_stack([q, np.ones(len(q))]).T).T
        best = None
        for E in candidates:
            try:
                _, R, direction, _ = cv2.recoverPose(E, p[train], q[train], K)
            except cv2.error:
                continue
            rotated = (R @ X.T).T
            A = np.cross(rays[train], direction.ravel())
            B = np.cross(rays[train], rotated[train])
            scales = -np.sum(A*B, axis=1)/np.maximum(np.sum(A*A, axis=1), 1e-12)
            scales = scales[np.isfinite(scales) & (scales >= 0) & (scales <= self.policy.max_pair_translation_m)]
            if len(scales) < self.policy.min_tracking_inliers:
                continue
            r, _ = cv2.Rodrigues(R)
            for scale in np.unique(np.quantile(scales, np.linspace(0, 1, 81))):
                t = direction*scale
                projected, _ = cv2.projectPoints(X[train], r, t, K, None)
                errors = np.linalg.norm(projected.reshape(-1, 2)-q[train], axis=1)
                score = (int(np.count_nonzero(errors <= 2)), -float(np.median(errors)))
                if best is None or score > best[0]:
                    best = (score, r, t)
        if best is None:
            return None
        count = best[0][0]
        ratio = count/max(np.count_nonzero(train), 1)
        r, t = best[1:]
        projected, _ = cv2.projectPoints(X[heldout], r, t, K, None)
        errors = np.linalg.norm(projected.reshape(-1, 2)-q[heldout], axis=1)
        heldout_ratio = float(np.mean(errors <= 3))
        median = float(np.median(errors))
        if count < self.policy.min_tracking_inliers or ratio < self.policy.min_tracking_inlier_ratio or heldout_ratio < self.policy.min_tracking_inlier_ratio or median > 3:
            return None
        return r, t, {'inliers': count, 'inlier_ratio': ratio, 'heldout_inlier_ratio': heldout_ratio,
                      'heldout_median_error_px': median, 'translation_mag_m': float(np.linalg.norm(t)),
                      'confidence': min(ratio, heldout_ratio)}

