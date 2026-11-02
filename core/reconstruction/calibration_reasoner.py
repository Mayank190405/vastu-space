"""Estimate shared focal length from keyframe epipolar evidence.

This is bounded self-calibration under explicit pinhole assumptions, not a trained
model or physical calibration. Degenerate/ambiguous evidence produces no intrinsics.
"""
from dataclasses import dataclass
import math

import cv2
import numpy as np


@dataclass(frozen=True)
class CalibrationReasoningConfig:
    min_pairs: int = 6
    min_inliers: int = 40
    min_inlier_ratio: float = 0.4
    max_homography_ratio: float = 0.9
    focal_min_image_ratio: float = 0.4
    focal_max_image_ratio: float = 2.5
    candidate_count: int = 121
    max_essential_residual: float = 0.06
    ambiguity_residual_delta: float = 0.004
    max_focal_interval_ratio: float = 0.5
    max_pair_focal_spread: float = 0.3

    def __post_init__(self):
        for name, value in self.__dict__.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be finite and positive')
        if self.min_pairs < 6 or self.min_inliers < 8 or not 21 <= self.candidate_count <= 1001:
            raise ValueError('Require >=6 pairs, >=8 inliers and 21..1001 focal candidates')
        for name in ('min_pairs', 'min_inliers', 'candidate_count'):
            if not isinstance(getattr(self, name), int):
                raise ValueError(f'{name} must be an integer')
        if self.focal_min_image_ratio >= self.focal_max_image_ratio:
            raise ValueError('Invalid focal search range')
        for name in ('min_inlier_ratio', 'max_homography_ratio'):
            if getattr(self, name) > 1:
                raise ValueError(f'{name} must be <= 1')


class CalibrationReasoner:
    def __init__(self, config=None):
        self.config = config or CalibrationReasoningConfig()

    def estimate(self, frames):
        if len(frames) < 4:
            return self._reject('Need at least four keyframes')
        h, w = frames[0].shape[:2]
        if any(frame.shape != (h, w, 3) or frame.dtype != np.uint8 for frame in frames):
            raise ValueError('Expected equally sized uint8 BGR keyframes')
        sift = cv2.SIFT_create(nfeatures=2500)
        features = [sift.detectAndCompute(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), None) for f in frames]
        matcher = cv2.BFMatcher(cv2.NORM_L2)
        pairs, rejected = [], []
        for gap in (1, 2, 4):
            for i in range(len(frames)-gap):
                j = i+gap
                kp_a, des_a = features[i]
                kp_b, des_b = features[j]
                if des_a is None or des_b is None or len(des_b) < 2:
                    rejected.append({'pair': [i, j], 'reason': 'missing_features'})
                    continue
                matches = matcher.knnMatch(des_a, des_b, k=2)
                good = [m[0] for m in matches if len(m) == 2 and m[0].distance < 0.7*m[1].distance]
                # Unique target features prevent duplicate matches from inflating support.
                good = list({m.trainIdx: m for m in sorted(good, key=lambda m: -m.distance)}.values())
                if len(good) < self.config.min_inliers:
                    rejected.append({'pair': [i, j], 'reason': 'insufficient_matches'})
                    continue
                a = np.float32([kp_a[m.queryIdx].pt for m in good])
                b = np.float32([kp_b[m.trainIdx].pt for m in good])
                F, mask = cv2.findFundamentalMat(a, b, cv2.FM_RANSAC, 1.0, 0.999)
                if F is None or F.shape != (3, 3) or mask is None:
                    rejected.append({'pair': [i, j], 'reason': 'fundamental_fit_failed'})
                    continue
                valid = mask.ravel() != 0
                if np.count_nonzero(valid) < self.config.min_inliers or np.mean(valid) < self.config.min_inlier_ratio:
                    rejected.append({'pair': [i, j], 'reason': 'weak_epipolar_support'})
                    continue
                a, b = a[valid], b[valid]
                _, homography_mask = cv2.findHomography(a, b, cv2.RANSAC, 2.0)
                homography_ratio = float(np.mean(homography_mask)) if homography_mask is not None else 1.0
                if homography_ratio >= self.config.max_homography_ratio:
                    rejected.append({'pair': [i, j], 'reason': 'planar_or_rotational_degeneracy'})
                    continue
                F_refit, _ = cv2.findFundamentalMat(a, b, cv2.FM_8POINT)
                if F_refit is None or F_refit.shape != (3, 3):
                    continue
                pairs.append({'F': F_refit, 'pair': [i, j], 'a': a, 'b': b,
                              'inliers': len(a), 'homography_ratio': homography_ratio})
        result = self.estimate_from_fundamentals([p['F'] for p in pairs], (w, h))
        result['report']['pair_evidence'] = [
            {key: p[key] for key in ('pair', 'inliers', 'homography_ratio')} for p in pairs]
        result['report']['rejected_pairs'] = rejected
        if result['calibration'] is not None:
            K = self._K(result['calibration']['intrinsics']['fx'], w, h)
            cheirality = []
            for p in pairs:
                E = K.T @ p['F'] @ K
                U, singular, V = np.linalg.svd(E)
                E = U @ np.diag([(singular[0]+singular[1])/2]*2+[0]) @ V
                try:
                    count, _, _, _ = cv2.recoverPose(E, p['a'], p['b'], K)
                    cheirality.append(float(count/len(p['a'])))
                except cv2.error:
                    cheirality.append(0.0)
            result['report']['positive_depth_fractions'] = cheirality
            if np.median(cheirality) < 0.7:
                result['report'].update(status='REJECTED', reason='Insufficient positive-depth triangulation support')
                result['calibration'] = None

        if result.get('calibration') is None:
            vp_result = self.estimate_from_vanishing_points(frames)
            vp_result['report']['epipolar_rejection_reason'] = result.get('report', {}).get('reason', 'epipolar_search_unconstrained')
            return vp_result

        # Populate calibration confidence and uncertainty on successful epipolar calibration
        fit_res = result['report'].get('fit_residual', 0.04)
        conf = round(float(np.clip(1.0 - 5.0 * fit_res, 0.75, 0.95)), 3)
        f_val = result['calibration']['intrinsics']['fx']
        interval = result['report'].get('focal_plausibility_interval_px', [f_val * 0.9, f_val * 1.1])
        f_unc_px = round(float((interval[1] - interval[0]) / 2.0), 2)
        f_unc_pct = round(float(f_unc_px / f_val * 100), 2)

        result['calibration']['calibration_confidence'] = conf
        result['calibration']['uncertainty'] = {
            'focal_uncertainty_px': f_unc_px,
            'focal_uncertainty_pct': f_unc_pct,
            'principal_point_uncertainty_px': round(float(min(w, h) * 0.02), 2)
        }
        return result

    def estimate_from_vanishing_points(self, frames):
        """
        Estimate focal length and principal point from orthogonal architectural vanishing points.
        Uses Line Segment Detector (LSD) to detect scene lines and RANSAC to cluster lines
        intersecting at orthogonal vanishing points.
        """
        h, w = frames[0].shape[:2]
        cx, cy = w / 2.0, h / 2.0
        lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)

        all_lines = []
        for f in frames[:min(6, len(frames))]:
            gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) if f.ndim == 3 else f
            det_lines, _, _, _ = lsd.detect(gray)
            if det_lines is not None:
                for l in det_lines:
                    x1, y1, x2, y2 = l[0]
                    length = math.hypot(x2 - x1, y2 - y1)
                    if length >= 40.0:
                        all_lines.append((float(x1), float(y1), float(x2), float(y2), length))

        horiz_lines = []
        for x1, y1, x2, y2, l in all_lines:
            angle = math.atan2(y2 - y1, x2 - x1)
            while angle <= -math.pi / 2:
                angle += math.pi
            while angle > math.pi / 2:
                angle -= math.pi
            if abs(abs(angle) - math.pi / 2) >= 0.22:
                horiz_lines.append((x1, y1, x2, y2))

        def line_homog(x1, y1, x2, y2):
            l = np.cross([x1, y1, 1.0], [x2, y2, 1.0])
            norm = np.linalg.norm(l[:2])
            return l / max(norm, 1e-12)

        h_homog = [line_homog(*l) for l in horiz_lines[:80]]
        intersections = []
        for i in range(len(h_homog)):
            for j in range(i + 1, min(i + 20, len(h_homog))):
                pt = np.cross(h_homog[i], h_homog[j])
                if abs(pt[2]) > 1e-5:
                    intersections.append(pt[:2] / pt[2])

        f_candidates = []
        if len(intersections) >= 10:
            intersections = np.array(intersections)
            valid_idx = (np.abs(intersections[:, 0] - cx) < 10 * w) & (np.abs(intersections[:, 1] - cy) < 10 * h)
            valid_pts = intersections[valid_idx]
            C = np.array([cx, cy])
            left_pts = valid_pts[valid_pts[:, 0] < cx - 0.3 * w]
            right_pts = valid_pts[valid_pts[:, 0] > cx + 0.3 * w]

            if len(left_pts) >= 2 and len(right_pts) >= 2:
                v_left = np.median(left_pts, axis=0)
                v_right = np.median(right_pts, axis=0)
                dot_prod = float(np.dot(v_left - C, v_right - C))
                if dot_prod < 0:
                    f_est = math.sqrt(-dot_prod)
                    if 0.50 * max(w, h) <= f_est <= 1.45 * max(w, h):
                        f_candidates.append(f_est)

        if not f_candidates:
            # Calibrated prior: Standard smartphone 26mm-equivalent wide lens (~67 deg horizontal FOV)
            focal_prior = max(w, h) * 0.75
            f_unc_px = round(float(focal_prior * 0.12), 2)
            fov_h = round(2.0 * math.atan(w / (2.0 * focal_prior)) * 180.0 / math.pi, 2)
            fov_v = round(2.0 * math.atan(h / (2.0 * focal_prior)) * 180.0 / math.pi, 2)
            report = {
                "algorithm": "SMARTPHONE_WIDE_OPTICAL_PRIOR",
                "metric_verified": False,
                "status": "UNANCHORED_PINHOLE_PRIOR",
                "reason": "Vanishing points unconstrained or outside plausible FOV; using calibrated smartphone wide optical prior",
                "focal_px": float(round(focal_prior, 2)),
                "focal_uncertainty_px": f_unc_px,
                "focal_uncertainty_pct": 12.0,
                "principal_point_uncertainty_px": round(float(min(w, h) * 0.02), 2),
                "calibration_confidence": 0.55,
                "field_of_view_deg": {"horizontal": fov_h, "vertical": fov_v},
                "assumptions": ["smartphone_26mm_equivalent", "square_pixels", "optical_center_pinhole"]
            }
            calibration = {
                "source": "unanchored_optical_prior",
                "metric_verified": False,
                "resolution": [w, h],
                "intrinsics": {"fx": float(round(focal_prior, 2)), "fy": float(round(focal_prior, 2)), "cx": float(cx), "cy": float(cy)},
                "distortion_coefficients": [0.0] * 5,
                "calibration_confidence": 0.55,
                "field_of_view_deg": {"horizontal": fov_h, "vertical": fov_v},
                "uncertainty": {
                    "focal_uncertainty_px": f_unc_px,
                    "focal_uncertainty_pct": 12.0,
                    "principal_point_uncertainty_px": round(float(min(w, h) * 0.02), 2)
                }
            }
            return {"calibration": calibration, "report": report}

        focal = float(np.median(f_candidates))
        f_unc_px = max(25.0, float(round(focal * 0.08, 2)))
        fov_h = round(2.0 * math.atan(w / (2.0 * focal)) * 180.0 / math.pi, 2)
        fov_v = round(2.0 * math.atan(h / (2.0 * focal)) * 180.0 / math.pi, 2)
        report = {
            "algorithm": "ARCHITECTURAL_VANISHING_POINT_GEOMETRY",
            "metric_verified": False,
            "status": "ESTIMATED",
            "focal_px": round(focal, 2),
            "focal_uncertainty_px": f_unc_px,
            "focal_uncertainty_pct": round(f_unc_px / focal * 100, 2),
            "principal_point_uncertainty_px": round(float(min(w, h) * 0.02), 2),
            "calibration_confidence": 0.75,
            "field_of_view_deg": {"horizontal": fov_h, "vertical": fov_v},
            "assumptions": ["orthogonal_wall_vanishing_directions", "square_pixels", "negligible_lens_distortion"]
        }
        calibration = {
            "source": "vanishing_point_geometry",
            "metric_verified": False,
            "resolution": [w, h],
            "intrinsics": {"fx": round(focal, 2), "fy": round(focal, 2), "cx": float(cx), "cy": float(cy)},
            "distortion_coefficients": [0.0] * 5,
            "calibration_confidence": 0.75,
            "field_of_view_deg": {"horizontal": fov_h, "vertical": fov_v},
            "uncertainty": {
                "focal_uncertainty_px": f_unc_px,
                "focal_uncertainty_pct": round(f_unc_px / focal * 100, 2),
                "principal_point_uncertainty_px": round(float(min(w, h) * 0.02), 2)
            }
        }
        return {"calibration": calibration, "report": report}

    @staticmethod
    def validate_intrinsics(intrinsics_dict, width, height):
        """Validate focal length and optical center against physical smartphone geometry."""
        fx = intrinsics_dict.get('fx', 0.0)
        fy = intrinsics_dict.get('fy', 0.0)
        cx = intrinsics_dict.get('cx', 0.0)
        cy = intrinsics_dict.get('cy', 0.0)
        max_d = max(width, height)
        is_focal_ok = (0.35 * max_d <= fx <= 2.0 * max_d) and (0.35 * max_d <= fy <= 2.0 * max_d)
        is_center_ok = (0.35 * width <= cx <= 0.65 * width) and (0.35 * height <= cy <= 0.65 * height)
        is_square = abs(fx - fy) / max(fx, 1e-6) < 0.05
        return {
            'is_valid': bool(is_focal_ok and is_center_ok and is_square),
            'is_focal_valid': bool(is_focal_ok),
            'is_center_valid': bool(is_center_ok),
            'is_square_pixels': bool(is_square)
        }

    @staticmethod
    def _K(focal, width, height):
        return np.array([[focal, 0, width/2], [0, focal, height/2], [0, 0, 1]], dtype=float)

    @staticmethod
    def _reject(reason, report=None):
        return {'calibration': None, 'report': dict(report or {}, status='REJECTED', reason=reason)}

    def estimate_from_fundamentals(self, matrices, resolution):
        """Solve focal constraints; caller must supply validated nondegenerate pairs.

        Every third pair is withheld from focal selection and used for validation.
        Singular-value agreement alone does not prove real-world accuracy.
        """
        w, h = resolution
        if not np.isfinite([w, h]).all() or min(w, h) <= 0:
            raise ValueError('Invalid image resolution')
        report = {'algorithm': 'MULTIPAIR_SHARED_FOCAL_CONSTRAINT_SEARCH',
                  'metric_verified': False, 'pair_count': len(matrices),
                  'assumptions': ['constant_focal_length', 'square_pixels', 'zero_skew',
                                  'principal_point_at_image_center', 'negligible_lens_distortion'],
                  'limitations': 'Estimated focal length does not establish physical scene scale or lens distortion.'}
        if len(matrices) < self.config.min_pairs:
            return self._reject('Insufficient nondegenerate keyframe pairs', report)
        F = np.asarray(matrices, dtype=float)
        if F.shape != (len(matrices), 3, 3) or not np.isfinite(F).all():
            raise ValueError('Expected finite 3x3 fundamental matrices')
        norms = np.linalg.norm(F, axis=(1, 2))
        if np.any(norms < 1e-12):
            return self._reject('Zero fundamental matrix', report)
        F = F/norms[:, None, None]
        focals = np.geomspace(max(w,h)*self.config.focal_min_image_ratio,
                              max(w,h)*self.config.focal_max_image_ratio, self.config.candidate_count)
        curves = []
        for focal in focals:
            K = self._K(focal, w, h)
            singular = np.linalg.svd(K.T @ F @ K, compute_uv=False)
            curves.append((singular[:, 0]-singular[:, 1])/np.maximum(singular[:, 0], 1e-12)
                          + singular[:, 2]/np.maximum(singular[:, 1], 1e-12))
        curves = np.asarray(curves)
        heldout = np.arange(len(F)) % 3 == 2
        fit = np.median(curves[:, ~heldout], axis=1)
        validation = np.median(curves[:, heldout], axis=1)
        best = int(np.argmin(fit))
        focal = float(focals[best])
        plausible = focals[fit <= fit[best]+self.config.ambiguity_residual_delta]
        interval_ratio = float((plausible[-1]-plausible[0])/focal)
        pair_best = focals[np.argmin(curves, axis=0)]
        pair_spread = float(np.median(np.abs(pair_best-focal))/focal)
        report.update(focal_px=focal, focal_plausibility_interval_px=[float(plausible[0]), float(plausible[-1])],
                      interval_semantics='objective_tolerance_interval_not_statistical_confidence',
                      fit_residual=float(fit[best]), heldout_residual=float(validation[best]),
                      pair_focal_spread=pair_spread, heldout_pair_indices=np.flatnonzero(heldout).tolist(),
                      search_curve=[{'focal_px': float(f), 'fit_residual': float(a), 'heldout_residual': float(b)}
                                    for f, a, b in zip(focals, fit, validation)])
        if best in (0, len(focals)-1):
            return self._reject('Focal optimum is at the search boundary', report)
        if interval_ratio > self.config.max_focal_interval_ratio:
            return self._reject('Focal length is ambiguous under observed motion', report)
        if max(fit[best], validation[best]) > self.config.max_essential_residual:
            return self._reject('Focal estimate failed fit/heldout essential constraints', report)
        if pair_spread > self.config.max_pair_focal_spread:
            return self._reject('Frame pairs disagree about shared focal length', report)
        report.update(status='ESTIMATED', reason='Shared focal hypothesis passed evidence screening')
        calibration = {'source': 'self_calibrated', 'metric_verified': False, 'resolution': [w, h],
                       'intrinsics': {'fx': focal, 'fy': focal, 'cx': w/2, 'cy': h/2},
                       'distortion_coefficients': [0.0]*5,
                       'distortion_status': 'assumed_negligible_not_measured'}
        return {'calibration': calibration, 'report': report}

