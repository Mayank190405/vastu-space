"""Require the native geometry backend; shims are explicit diagnostics only."""
import importlib


def load_open3d(allow_diagnostic=False):
    try:
        backend = importlib.import_module("open3d")
        if "o3d_shim" in getattr(backend, "__name__", "") or not getattr(backend, "__version__", None):
            raise ImportError("Native Open3D was replaced by an unverified module")
        return backend
    except ImportError as exc:
        if allow_diagnostic:
            return importlib.import_module("core.reconstruction.o3d_shim")
        raise RuntimeError("NATIVE_OPEN3D_REQUIRED: install the pinned worker dependencies; diagnostic geometry cannot be published") from exc
