"""Offline regression tests for evidence gates; no model downloads."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from core.reconstruction.safety import ReconstructionPolicy, ReconstructionSafetyError
from ml.depth.estimator import DepthEstimator
import scripts.generate_video_twin
from scripts.generate_video_twin import VastuDigitalTwinPipeline


class ReconstructionSafetyTests(unittest.TestCase):
    def test_rejects_unsafe_policy(self):
        for settings in ({'min_view_support': 1}, {'min_view_support': 2.5},
                         {'max_depth_disagreement_m': float('nan')},
                         {'min_pair_overlap': 1.1}, {'min_tracking_inliers': True}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                ReconstructionPolicy(**settings)

    def test_tracking_rejects_failed_and_weak_poses(self):
        policy = ReconstructionPolicy()
        for args in ((False, 100, 0.9, 0.1), (True, 12, 0.9, 0.1),
                     (True, 100, 0.2, 0.1), (True, 100, 0.9, 2),
                     (True, 100, float('nan'), 0.1)):
            with self.subTest(args=args), self.assertRaises(ReconstructionSafetyError):
                policy.check_tracking(*args)
        policy.check_tracking(True, 100, 0.9, 0.1)

    def test_approximate_depth_rejected_by_default(self):
        for backend in ('PHOTOMETRIC_ANALYTICAL', 'NEURAL_METRIC_CALIBRATED'):
            with patch.object(DepthEstimator, '_initialize_model'):
                estimator = DepthEstimator()
            estimator.active_backend = backend
            with self.subTest(backend=backend), self.assertRaisesRegex(RuntimeError, 'requires a metric'):
                estimator.estimate_depth(np.zeros((20, 20, 3), dtype=np.uint8))

    def test_diagnostic_depth_requires_explicit_opt_in(self):
        with patch.object(DepthEstimator, '_initialize_model'):
            estimator = DepthEstimator(allow_approximate_depth=True)
        estimator.active_backend = 'PHOTOMETRIC_ANALYTICAL'
        depth, _ = estimator.estimate_depth(np.zeros((20, 20, 3), dtype=np.uint8))
        self.assertEqual(depth.shape, (20, 20))

    def test_invalid_model_output_rejected(self):
        with patch.object(DepthEstimator, '_initialize_model'):
            estimator = DepthEstimator()
        estimator.active_backend = 'DEPTH_ANYTHING_V2_METRIC'
        estimator.model = object()
        estimator.transform = object()
        for value in (float('nan'), float('inf'), -1):
            with patch.object(estimator, '_infer_depth_anything_v2', return_value=(
                    np.full((20, 20), value), np.ones((20, 20)))):
                with self.assertRaisesRegex(RuntimeError, 'invalid depth'):
                    estimator.estimate_depth(np.zeros((20, 20, 3), dtype=np.uint8))

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory, 'mesh.ply')
            sentinel.write_bytes(b'existing geometry')
            pipeline = VastuDigitalTwinPipeline('unused.mov', directory)
            with self.assertRaisesRegex(ReconstructionSafetyError, 'contains files'):
                pipeline.run()
            self.assertEqual(sentinel.read_bytes(), b'existing geometry')
            self.assertFalse(Path(directory, 'run_status.json').exists())

    def test_failure_persists_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            pipeline = VastuDigitalTwinPipeline('unused.mov', directory)
            with patch.object(pipeline, '_run_stages', side_effect=RuntimeError('model unavailable')):
                with self.assertRaises(RuntimeError):
                    pipeline.run()
            status = json.loads(Path(directory, 'run_status.json').read_text())
            self.assertFalse(status['accepted'])
            self.assertEqual(status['error'], 'model unavailable')

    def test_final_quality_gate_enforced(self):
        for verdict in ('PASS', 'FAIL', None):
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as directory:
                pipeline = VastuDigitalTwinPipeline('unused.mov', directory)
                with patch.object(pipeline, '_run_stages', return_value={'quality_status': verdict}):
                    if verdict == 'PASS':
                        pipeline.run()
                    else:
                        with self.assertRaises(ReconstructionSafetyError):
                            pipeline.run()
                status = json.loads(Path(directory, 'run_status.json').read_text())
                self.assertEqual(status['accepted'], verdict == 'PASS')

    def test_later_view_failure_is_not_hidden_by_first_pair(self):
        pipeline = VastuDigitalTwinPipeline.__new__(VastuDigitalTwinPipeline)
        with patch.object(pipeline, '_check_view_pair', side_effect=[
                {'gate_passed': True, 'overlap_ratio': 0.9},
                {'gate_passed': False, 'overlap_ratio': 0.1}]):
            result = pipeline._stage_07_two_view_gate([0, 1, 2], [0, 1, 2], None, [0, 1, 2])
        self.assertFalse(result['gate_passed'])
        self.assertEqual(len(result['pairs']), 2)

    def test_projection_accepts_matching_planes_rejects_wrong_depth(self):
        pipeline = VastuDigitalTwinPipeline.__new__(VastuDigitalTwinPipeline)
        pipeline.safety_policy = ReconstructionPolicy()
        frames = [np.zeros((60, 60, 3), dtype=np.uint8)] * 2
        K = np.array([[60., 0, 30], [0, 60, 30], [0, 0, 1]])
        poses = [{'R': np.eye(3), 't': np.zeros((3, 1))}] * 2
        plane = np.full((60, 60), 2.)
        self.assertTrue(pipeline._check_view_pair(frames, [plane, plane], K, poses)['gate_passed'])
        self.assertFalse(pipeline._check_view_pair(frames, [plane, plane + 0.2], K, poses)['gate_passed'])

    def test_reasoning_stage_persists_evidence_and_enforces_gate(self):
        shape = (10, 10)
        for verdict in ('PASS', 'REJECTED'):
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as directory:
                pipeline = VastuDigitalTwinPipeline('unused.mov', directory)
                reason = np.zeros(shape, dtype=np.uint8)
                reason[:2] = 2
                result = {'report': {'status': verdict},
                          'depths': [np.ones(shape)], 'confidences': [np.ones(shape)],
                          'reasons': [reason], 'support': [np.full(shape, 2)],
                          'hypothesis_step_m': [np.full(shape, 0.03)]}
                with patch('scripts.generate_video_twin.KeyframeDepthReasoner.refine', return_value=result):
                    if verdict == 'PASS':
                        _, masks, _ = pipeline._stage_depth_reasoning([None], [np.ones(shape)], [None], [None], None)
                        self.assertFalse(masks[0][:2].any())
                        self.assertTrue(masks[0][2:].all())
                    else:
                        with self.assertRaises(ReconstructionSafetyError):
                            pipeline._stage_depth_reasoning([None], [np.ones(shape)], [None], [None], None)
                saved = json.loads(Path(directory, 'depth_reasoning.json').read_text())
                self.assertEqual(saved['status'], verdict)
                with np.load(Path(directory, '05_depth/reasoning/frame_00.npz')) as evidence:
                    np.testing.assert_array_equal(evidence['rejection_reason'], reason)

    def test_missing_calibration_uses_reasoner_with_estimated_provenance(self):
        calibration = {'source': 'self_calibrated', 'metric_verified': False,
                       'resolution': [100, 100],
                       'intrinsics': {'fx': 90., 'fy': 90., 'cx': 50., 'cy': 50.}}
        with tempfile.TemporaryDirectory() as directory:
            pipeline = VastuDigitalTwinPipeline('unused.mov', directory)
            with patch('scripts.generate_video_twin.CalibrationReasoner.estimate', return_value={
                    'calibration': calibration, 'report': {'status': 'ESTIMATED'}}):
                pipeline._stage_calibration_reasoning([None]*4)
            report, _ = pipeline._stage_02_camera_calibration({'resolution': [100, 100]}, 100, 100)
            self.assertEqual(report['calibration_source'], 'self_calibrated')
            self.assertEqual(pipeline.calibration_source, 'self_calibrated')
            self.assertFalse(json.loads(Path(directory, 'estimated_camera_intrinsics.json').read_text())['metric_verified'])

    def test_ambiguous_automatic_calibration_stops_with_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            pipeline = VastuDigitalTwinPipeline('unused.mov', directory)
            with patch('scripts.generate_video_twin.CalibrationReasoner.estimate', return_value={
                    'calibration': None, 'report': {'status': 'REJECTED', 'reason': 'ambiguous focal'}}):
                with self.assertRaisesRegex(ReconstructionSafetyError, 'ambiguous focal'):
                    pipeline._stage_calibration_reasoning([None]*4)
            self.assertIsNone(pipeline.calibration)
            self.assertTrue(Path(directory, 'calibration_reasoning.json').exists())

    def test_calibration_scales_to_processing_resolution(self):
        pipeline = VastuDigitalTwinPipeline.__new__(VastuDigitalTwinPipeline)
        pipeline.calibration = {'resolution': [1000, 2000],
                                'intrinsics': {'fx': 900, 'fy': 920, 'cx': 500, 'cy': 1000}}
        report, K = pipeline._stage_02_camera_calibration({'resolution': [1000, 2000]}, 500, 1000)
        self.assertEqual(K[0, 0], 450)
        self.assertEqual(K[1, 1], 460)
        self.assertEqual(report['calibration_source'], 'provided')
        pipeline.calibration['distortion_coefficients'] = [0.1, 0, 0, 0, 0]
        with self.assertRaises(ReconstructionSafetyError):
            pipeline._stage_02_camera_calibration({'resolution': [1000, 2000]}, 500, 1000)


if __name__ == '__main__':
    unittest.main()
