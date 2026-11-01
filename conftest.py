"""
Pytest root configuration for VĀSTU test suite.
Guarantees safe initialization of OpenMP and Open3D on macOS ARM64 / Linux environments.
"""

import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    import open3d as o3d
except ImportError:
    pass
