"""Offline regression checks for the production metric-model loading contract."""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from ml.depth.estimator import DepthEstimator


class MetricDepthCacheTests(unittest.TestCase):
    def test_missing_production_cache_never_falls_back(self):
        processor = SimpleNamespace(from_pretrained=Mock(side_effect=OSError('missing weights')))
        model = SimpleNamespace(from_pretrained=Mock())
        transformers = SimpleNamespace(AutoImageProcessor=processor, AutoModelForDepthEstimation=model)
        with patch.dict(os.environ, {'VASTU_METRIC_DEPTH_MODEL_PATH': '/opt/cached-model'}), \
                patch.dict(sys.modules, {'transformers': transformers}), \
                patch('ml.depth.estimator.HAS_TORCH', True):
            with self.assertRaisesRegex(RuntimeError, 'METRIC_DEPTH_MODEL_UNAVAILABLE'):
                DepthEstimator(device='cpu')
        processor.from_pretrained.assert_called_once_with('/opt/cached-model', local_files_only=True)
        model.from_pretrained.assert_not_called()

    def test_relative_model_is_not_accepted_as_metric(self):
        processor = SimpleNamespace(from_pretrained=Mock(return_value=object()))
        loaded = SimpleNamespace(config=SimpleNamespace(depth_estimation_type='relative'))
        model = SimpleNamespace(from_pretrained=Mock(return_value=loaded))
        with patch.dict(os.environ, {'VASTU_METRIC_DEPTH_MODEL_PATH': '/opt/cached-model'}), \
                patch.dict(sys.modules, {'transformers': SimpleNamespace(AutoImageProcessor=processor, AutoModelForDepthEstimation=model)}), \
                patch('ml.depth.estimator.HAS_TORCH', True):
            with self.assertRaisesRegex(RuntimeError, 'METRIC_DEPTH_MODEL_UNAVAILABLE'):
                DepthEstimator(device='cpu')
        model.from_pretrained.assert_called_once_with('/opt/cached-model', local_files_only=True, use_safetensors=True)


if __name__ == '__main__':
    unittest.main()
