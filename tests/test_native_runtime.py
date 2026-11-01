import unittest
from types import SimpleNamespace
from unittest.mock import patch
from core.reconstruction.native_runtime import load_open3d


class NativeRuntimeTests(unittest.TestCase):
    def test_native_backend_preserved(self):
        native = SimpleNamespace(__name__="open3d", __version__="0.18.0")
        with patch("importlib.import_module", return_value=native):
            self.assertIs(load_open3d(), native)

    def test_missing_backend_fails_closed(self):
        with patch("importlib.import_module", side_effect=ImportError("missing")):
            with self.assertRaisesRegex(RuntimeError, "NATIVE_OPEN3D_REQUIRED"):
                load_open3d()

    def test_injected_shim_rejected(self):
        shim = SimpleNamespace(__name__="core.reconstruction.o3d_shim")
        with patch("importlib.import_module", return_value=shim):
            with self.assertRaisesRegex(RuntimeError, "NATIVE_OPEN3D_REQUIRED"):
                load_open3d()

    def test_diagnostic_opt_in(self):
        shim = object()
        with patch("importlib.import_module", side_effect=[ImportError("missing"), shim]):
            self.assertIs(load_open3d(allow_diagnostic=True), shim)
