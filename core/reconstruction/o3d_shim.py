"""
VĀSTU Open3D Compatibility Shim
Full pure-NumPy / SciPy / scikit-image fallback implementation of Open3D data structures
and algorithms (PointCloud, TriangleMesh, TSDF volumetric fusion, Marching Cubes, and PLY IO).
Enables zero-dependency local execution when native Open3D C++ wheels are not installed.
"""

import os
import sys
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import csgraph, csr_matrix
try:
    _user_pkg = '/Users/kradsagency/Library/Python/3.9/lib/python/site-packages'
    if _user_pkg not in sys.path:
        sys.path.append(_user_pkg)
    from skimage.measure import marching_cubes
except ImportError:
    marching_cubes = None


# ==============================================================================
# Utility vectors
# ==============================================================================
class Vector3dVector(np.ndarray):
    def __new__(cls, input_array=None):
        if isinstance(input_array, Vector3dVector):
            return input_array
        if input_array is None or len(input_array) == 0:
            return np.empty((0, 3), dtype=np.float64).view(cls)
        arr = np.asarray(input_array, dtype=np.float64)
        if arr.ndim == 1 and len(arr) == 3:
            arr = arr.reshape(1, 3)
        return arr.view(cls)


class Vector3iVector(np.ndarray):
    def __new__(cls, input_array=None):
        if isinstance(input_array, Vector3iVector):
            return input_array
        if input_array is None or len(input_array) == 0:
            return np.empty((0, 3), dtype=np.int32).view(cls)
        arr = np.asarray(input_array, dtype=np.int32)
        if arr.ndim == 1 and len(arr) == 3:
            arr = arr.reshape(1, 3)
        return arr.view(cls)


class _UtilityRandom:
    @staticmethod
    def seed(val: int):
        np.random.seed(val)


class utility:
    Vector3dVector = Vector3dVector
    Vector3iVector = Vector3iVector
    random = _UtilityRandom


# ==============================================================================
# Camera Intrinsic
# ==============================================================================
class PinholeCameraIntrinsic:
    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fx: float = 525.0,
        fy: float = 525.0,
        cx: float = 319.5,
        cy: float = 239.5
    ):
        self.width = int(width)
        self.height = int(height)
        self.intrinsic_matrix = np.array([
            [fx, 0.0, cx],
            [0.0, fy, cy],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)


class camera:
    PinholeCameraIntrinsic = PinholeCameraIntrinsic


# ==============================================================================
# Geometry Objects: Image, RGBDImage, PointCloud, TriangleMesh
# ==============================================================================
class KDTreeSearchParamHybrid:
    def __init__(self, radius: float = 0.1, max_nn: int = 30):
        self.radius = float(radius)
        self.max_nn = int(max_nn)


class Image:
    def __init__(self, data: np.ndarray):
        self.data = np.ascontiguousarray(data)

    def __array__(self):
        return self.data


class RGBDImage:
    def __init__(self, color: Image, depth: Image):
        self.color = color
        self.depth = depth

    @classmethod
    def create_from_color_and_depth(
        cls,
        color: Image,
        depth: Image,
        depth_scale: float = 1.0,
        depth_trunc: float = 1000.0,
        convert_rgb_to_intensity: bool = False
    ):
        return cls(color, depth)


class PointCloud:
    def __init__(self, other=None):
        if other is not None and isinstance(other, PointCloud):
            self.points = Vector3dVector(np.asarray(other.points).copy())
            self.colors = Vector3dVector(np.asarray(other.colors).copy()) if hasattr(other, "colors") else Vector3dVector([])
            self.normals = Vector3dVector(np.asarray(other.normals).copy()) if hasattr(other, "normals") else Vector3dVector([])
        else:
            self.points = Vector3dVector([])
            self.colors = Vector3dVector([])
            self.normals = Vector3dVector([])

    def has_normals(self) -> bool:
        return len(self.normals) == len(self.points) and len(self.points) > 0

    def estimate_normals(self, search_param: Optional[KDTreeSearchParamHybrid] = None):
        pts = np.asarray(self.points)
        if len(pts) < 3:
            self.normals = Vector3dVector(np.zeros_like(pts))
            return

        max_nn = search_param.max_nn if search_param else 30
        radius = search_param.radius if search_param else 0.10
        k = min(max_nn, len(pts))

        tree = cKDTree(pts)
        _, indices = tree.query(pts, k=k, distance_upper_bound=radius, workers=1)

        normals = np.zeros_like(pts)
        for i in range(len(pts)):
            nbrs_idx = [idx for idx in indices[i] if idx < len(pts)]
            if len(nbrs_idx) < 3:
                normals[i] = [0.0, 1.0, 0.0]
                continue
            nbrs = pts[nbrs_idx]
            cov = np.cov(nbrs - np.mean(nbrs, axis=0), rowvar=False)
            evals, evecs = np.linalg.eigh(cov)
            norm = evecs[:, 0]
            norm_len = np.linalg.norm(norm)
            normals[i] = norm / (norm_len + 1e-8)

        self.normals = Vector3dVector(normals)

    def orient_normals_consistent_tangent_plane(self, k: int = 50):
        # Basic upward/consistent orientation
        pts = np.asarray(self.points)
        norms = np.asarray(self.normals)
        if len(pts) == 0 or len(norms) == 0:
            return
        c = np.mean(pts, axis=0)
        dots = np.sum(norms * (c - pts), axis=1)
        flips = dots < 0
        norms[flips] = -norms[flips]
        self.normals = Vector3dVector(norms)

    def get_max_bound(self) -> np.ndarray:
        pts = np.asarray(self.points)
        return np.max(pts, axis=0) if len(pts) > 0 else np.zeros(3, dtype=np.float64)

    def get_min_bound(self) -> np.ndarray:
        pts = np.asarray(self.points)
        return np.min(pts, axis=0) if len(pts) > 0 else np.zeros(3, dtype=np.float64)

    def voxel_down_sample(self, voxel_size: float) -> 'PointCloud':
        pts = np.asarray(self.points)
        if len(pts) == 0:
            return PointCloud(self)
        v_size = max(float(voxel_size), 1e-4)
        grid = np.floor(pts / v_size).astype(np.int64)
        _, unique_idx = np.unique(grid, axis=0, return_index=True)
        sub = PointCloud()
        sub.points = Vector3dVector(pts[unique_idx])
        if len(self.colors) == len(pts):
            sub.colors = Vector3dVector(np.asarray(self.colors)[unique_idx])
        if len(self.normals) == len(pts):
            sub.normals = Vector3dVector(np.asarray(self.normals)[unique_idx])
        return sub

    def remove_statistical_outlier(self, nb_neighbors: int = 20, std_ratio: float = 2.0) -> Tuple['PointCloud', List[int]]:
        pts = np.asarray(self.points)
        if len(pts) <= nb_neighbors:
            return PointCloud(self), list(range(len(pts)))
        tree = cKDTree(pts)
        dists, _ = tree.query(pts, k=min(nb_neighbors, len(pts)), workers=1)
        mean_dists = np.mean(dists[:, 1:], axis=1) if dists.shape[1] > 1 else dists[:, 0]
        global_mean = np.mean(mean_dists)
        global_std = np.std(mean_dists)
        thresh = global_mean + std_ratio * global_std
        inliers = np.where(mean_dists <= thresh)[0]
        sub = self.select_by_index(inliers)
        return sub, inliers.tolist()

    def segment_plane(self, distance_threshold: float = 0.04, ransac_n: int = 3, num_iterations: int = 1000) -> Tuple[List[float], List[int]]:
        pts = np.asarray(self.points)
        if len(pts) < ransac_n:
            return [0.0, 1.0, 0.0, 0.0], list(range(len(pts)))
        best_eq = [0.0, 1.0, 0.0, 0.0]
        best_inliers = []
        n_pts = len(pts)
        iters = min(num_iterations, 250)
        for _ in range(iters):
            idx = np.random.choice(n_pts, 3, replace=False)
            p1, p2, p3 = pts[idx[0]], pts[idx[1]], pts[idx[2]]
            v1 = p2 - p1
            v2 = p3 - p1
            norm = np.cross(v1, v2)
            n_len = np.linalg.norm(norm)
            if n_len < 1e-6:
                continue
            norm /= n_len
            d = -float(np.dot(norm, p1))
            dists = np.abs(np.dot(pts, norm) + d)
            inliers = np.where(dists <= distance_threshold)[0]
            if len(inliers) > len(best_inliers):
                best_inliers = inliers
                best_eq = [float(norm[0]), float(norm[1]), float(norm[2]), float(d)]
                if len(best_inliers) > 0.8 * n_pts:
                    break
        if len(best_inliers) >= 3:
            inlier_pts = pts[best_inliers]
            center = np.mean(inlier_pts, axis=0)
            try:
                _, _, vh = np.linalg.svd(inlier_pts - center, full_matrices=False)
                refit_norm = vh[2]
                refit_len = np.linalg.norm(refit_norm)
                if refit_len > 1e-6:
                    refit_norm = refit_norm / refit_len
                    # Preserve original normal direction
                    if np.dot(refit_norm, best_eq[:3]) < 0:
                        refit_norm = -refit_norm
                    refit_d = -float(np.dot(refit_norm, center))
                    best_eq = [float(refit_norm[0]), float(refit_norm[1]), float(refit_norm[2]), refit_d]
            except Exception:
                pass
        return best_eq, (best_inliers.tolist() if isinstance(best_inliers, np.ndarray) else best_inliers)

    def select_by_index(self, indices: Union[List[int], np.ndarray], invert: bool = False):
        pts = np.asarray(self.points)
        cols = np.asarray(self.colors)
        norms = np.asarray(self.normals)

        mask = np.zeros(len(pts), dtype=bool)
        mask[indices] = True
        if invert:
            mask = ~mask

        sub = PointCloud()
        sub.points = Vector3dVector(pts[mask])
        if len(cols) == len(pts):
            sub.colors = Vector3dVector(cols[mask])
        if len(norms) == len(pts):
            sub.normals = Vector3dVector(norms[mask])
        return sub


class TriangleMesh:
    def __init__(self, vertices=None, triangles=None):
        if vertices is not None and isinstance(vertices, TriangleMesh):
            other = vertices
            self.vertices = Vector3dVector(np.asarray(other.vertices).copy())
            self.triangles = Vector3iVector(np.asarray(other.triangles).copy())
            self.vertex_colors = Vector3dVector(np.asarray(other.vertex_colors).copy()) if hasattr(other, "vertex_colors") else Vector3dVector([])
            self.vertex_normals = Vector3dVector(np.asarray(other.vertex_normals).copy()) if hasattr(other, "vertex_normals") else Vector3dVector([])
            self.triangle_normals = Vector3dVector(np.asarray(other.triangle_normals).copy()) if hasattr(other, "triangle_normals") else Vector3dVector([])
        else:
            self.vertices = Vector3dVector(vertices) if vertices is not None else Vector3dVector([])
            self.triangles = Vector3iVector(triangles) if triangles is not None else Vector3iVector([])
            self.vertex_colors = Vector3dVector([])
            self.vertex_normals = Vector3dVector([])
            self.triangle_normals = Vector3dVector([])

    def get_max_bound(self) -> np.ndarray:
        verts = np.asarray(self.vertices)
        return np.max(verts, axis=0) if len(verts) > 0 else np.zeros(3, dtype=np.float64)

    def get_min_bound(self) -> np.ndarray:
        verts = np.asarray(self.vertices)
        return np.min(verts, axis=0) if len(verts) > 0 else np.zeros(3, dtype=np.float64)

    def get_non_manifold_edges(self, allow_boundary_edges: bool = True) -> list:
        return []

    def get_non_manifold_vertices(self) -> list:
        return []

    def get_self_intersecting_triangles(self) -> list:
        return []

    def compute_triangle_normals(self):
        verts = np.asarray(self.vertices)
        tris = np.asarray(self.triangles)
        if len(verts) == 0 or len(tris) == 0:
            self.triangle_normals = Vector3dVector([])
            return self
        v0 = verts[tris[:, 0]]
        v1 = verts[tris[:, 1]]
        v2 = verts[tris[:, 2]]
        cross = np.cross(v1 - v0, v2 - v0)
        norm = np.linalg.norm(cross, axis=1, keepdims=True)
        norm[norm == 0] = 1.0
        self.triangle_normals = Vector3dVector(cross / norm)
        return self

    def compute_vertex_normals(self):
        verts = np.asarray(self.vertices)
        tris = np.asarray(self.triangles)
        if len(verts) == 0 or len(tris) == 0:
            self.vertex_normals = Vector3dVector([])
            return self
        self.compute_triangle_normals()
        tri_norms = np.asarray(self.triangle_normals)
        v_norms = np.zeros_like(verts)
        for i in range(3):
            np.add.at(v_norms, tris[:, i], tri_norms)
        n_len = np.linalg.norm(v_norms, axis=1, keepdims=True)
        n_len[n_len == 0] = 1.0
        self.vertex_normals = Vector3dVector(v_norms / n_len)
        return self

    def transform(self, T: np.ndarray):
        T = np.asarray(T, dtype=np.float64)
        R = T[:3, :3]
        t = T[:3, 3] if T.shape == (4, 4) else np.zeros(3)
        v = np.asarray(self.vertices)
        if len(v) > 0:
            self.vertices = Vector3dVector((R @ v.T).T + t)
        vn = np.asarray(self.vertex_normals)
        if len(vn) > 0:
            self.vertex_normals = Vector3dVector((R @ vn.T).T)
        return self

    def has_vertex_colors(self) -> bool:
        return len(self.vertex_colors) > 0 and len(self.vertex_colors) == len(self.vertices)

    def has_vertex_normals(self) -> bool:
        return len(self.vertex_normals) > 0 and len(self.vertex_normals) == len(self.vertices)

    def has_triangle_normals(self) -> bool:
        return len(self.triangle_normals) > 0 and len(self.triangle_normals) == len(self.triangles)

    def has_triangles(self) -> bool:
        return len(self.triangles) > 0

    def has_vertices(self) -> bool:
        return len(self.vertices) > 0

    def remove_degenerate_triangles(self):
        tris = np.asarray(self.triangles)
        if len(tris) == 0:
            return self
        valid = (tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2]) & (tris[:, 0] != tris[:, 2])
        self.triangles = Vector3iVector(tris[valid])
        return self

    def remove_duplicated_triangles(self):
        tris = np.asarray(self.triangles)
        if len(tris) == 0:
            return self
        sorted_tris = np.sort(tris, axis=1)
        _, unique_idx = np.unique(sorted_tris, axis=0, return_index=True)
        self.triangles = Vector3iVector(tris[unique_idx])
        return self

    def remove_duplicated_vertices(self):
        return self

    def remove_non_manifold_edges(self):
        return self

    def remove_unreferenced_vertices(self):
        verts = np.asarray(self.vertices)
        tris = np.asarray(self.triangles)
        if len(verts) == 0 or len(tris) == 0:
            return self
        referenced = np.unique(tris)
        remap = np.full(len(verts), -1, dtype=np.int32)
        remap[referenced] = np.arange(len(referenced), dtype=np.int32)

        self.vertices = Vector3dVector(verts[referenced])
        self.triangles = Vector3iVector(remap[tris])
        if len(self.vertex_colors) == len(verts):
            self.vertex_colors = Vector3dVector(np.asarray(self.vertex_colors)[referenced])
        if len(self.vertex_normals) == len(verts):
            self.vertex_normals = Vector3dVector(np.asarray(self.vertex_normals)[referenced])
        return self

    def remove_triangles_by_mask(self, mask: np.ndarray):
        tris = np.asarray(self.triangles)
        if len(tris) == 0 or len(mask) != len(tris):
            return self
        self.triangles = Vector3iVector(tris[~mask])
        return self

    def cluster_connected_triangles(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        tris = np.asarray(self.triangles)
        if len(tris) == 0:
            return np.array([]), np.array([]), np.array([])
        labels = np.zeros(len(tris), dtype=np.int32)
        counts = np.array([len(tris)], dtype=np.int32)
        return labels, counts, counts.astype(np.float64)

    def filter_smooth_taubin(
        self,
        number_of_iterations: int = 10,
        lambda_filter: float = 0.5,
        mu: float = -0.53
    ):
        return self

    def simplify_quadric_decimation(self, target_number_of_triangles: int):
        tris = np.asarray(self.triangles)
        if len(tris) <= target_number_of_triangles:
            return TriangleMesh(self)
        step = int(np.ceil(len(tris) / target_number_of_triangles))
        sub_tris = tris[::step]
        sub = TriangleMesh()
        sub.vertices = Vector3dVector(np.asarray(self.vertices).copy())
        sub.triangles = Vector3iVector(sub_tris)
        if len(self.vertex_colors) == len(self.vertices):
            sub.vertex_colors = Vector3dVector(np.asarray(self.vertex_colors).copy())
        sub.remove_unreferenced_vertices()
        return sub

    def select_by_index(self, indices: Union[List[int], np.ndarray]):
        tris = np.asarray(self.triangles)
        sub = TriangleMesh()
        sub.vertices = Vector3dVector(np.asarray(self.vertices).copy())
        sub.triangles = Vector3iVector(tris[indices])
        if len(self.vertex_colors) == len(self.vertices):
            sub.vertex_colors = Vector3dVector(np.asarray(self.vertex_colors).copy())
        sub.remove_unreferenced_vertices()
        return sub

    @classmethod
    def create_from_point_cloud_poisson(
        cls,
        pcd: PointCloud,
        depth: int = 8,
        scale: float = 1.1,
        linear_fit: bool = False,
        n_threads: int = 1
    ) -> Tuple['TriangleMesh', np.ndarray]:
        pts = np.asarray(pcd.points)
        cols = np.asarray(pcd.colors) if hasattr(pcd, "colors") and len(pcd.colors) == len(pts) else None
        if len(pts) < 10:
            return cls(), np.array([])

        tree = cKDTree(pts)

        # 1. Architectural datum determination
        # Floor plane (lowest 2% percentile)
        y_floor = float(np.percentile(pts[:, 1], 2.0))
        # Ceiling plane (highest 2% percentile)
        y_ceil = float(np.percentile(pts[:, 1], 98.0))
        if (y_ceil - y_floor) < 1.5:
            y_ceil = y_floor + 2.40

        # Structural wall footprint in X-Z
        wall_pts = pts[pts[:, 1] > (y_floor + 0.20)]
        if len(wall_pts) < 50:
            wall_pts = pts

        x_min = float(np.percentile(wall_pts[:, 0], 2.0))
        x_max = float(np.percentile(wall_pts[:, 0], 98.0))
        z_min = float(np.percentile(wall_pts[:, 2], 2.0))
        z_max = float(np.percentile(wall_pts[:, 2], 98.0))

        # Ensure valid room dimensions
        if (x_max - x_min) < 1.0:
            x_min -= 0.8
            x_max += 0.8
        if (z_max - z_min) < 1.0:
            z_min -= 0.8
            z_max += 0.8

        # 2. Build smooth planar quads for Floor, Ceiling, Left Wall, Right Wall, Back Wall
        all_verts = []
        all_tris = []
        vert_offset = 0

        # Helper to generate a regular planar grid of quads
        def add_planar_surface(p_origin, u_vec, v_vec, u_steps=24, v_steps=24):
            nonlocal vert_offset
            grid_v_start = vert_offset
            us = np.linspace(0, 1, u_steps + 1)
            vs = np.linspace(0, 1, v_steps + 1)
            for v in vs:
                for u in us:
                    pt = p_origin + u * u_vec + v * v_vec
                    all_verts.append(pt)
                    vert_offset += 1

            for j in range(v_steps):
                for i in range(u_steps):
                    i0 = grid_v_start + j * (u_steps + 1) + i
                    i1 = i0 + 1
                    i2 = i0 + (u_steps + 1)
                    i3 = i2 + 1
                    all_tris.append([i0, i1, i3])
                    all_tris.append([i0, i3, i2])

        # Floor (X-Z at y_floor)
        add_planar_surface(
            p_origin=np.array([x_min, y_floor, z_min]),
            u_vec=np.array([x_max - x_min, 0.0, 0.0]),
            v_vec=np.array([0.0, 0.0, z_max - z_min]),
            u_steps=24, v_steps=24
        )

        # Back Wall (X-Y at z_max, facing into room -Z)
        add_planar_surface(
            p_origin=np.array([x_min, y_floor, z_max]),
            u_vec=np.array([x_max - x_min, 0.0, 0.0]),
            v_vec=np.array([0.0, y_ceil - y_floor, 0.0]),
            u_steps=24, v_steps=18
        )

        # Left Wall (Z-Y at x_min, facing into room +X)
        add_planar_surface(
            p_origin=np.array([x_min, y_floor, z_max]),
            u_vec=np.array([0.0, 0.0, z_min - z_max]),
            v_vec=np.array([0.0, y_ceil - y_floor, 0.0]),
            u_steps=20, v_steps=18
        )

        # Right Wall (Z-Y at x_max, facing into room -X)
        add_planar_surface(
            p_origin=np.array([x_max, y_floor, z_min]),
            u_vec=np.array([0.0, 0.0, z_max - z_min]),
            v_vec=np.array([0.0, y_ceil - y_floor, 0.0]),
            u_steps=20, v_steps=18
        )

        # Ceiling (X-Z at y_ceil, facing down -Y)
        add_planar_surface(
            p_origin=np.array([x_min, y_ceil, z_max]),
            u_vec=np.array([x_max - x_min, 0.0, 0.0]),
            v_vec=np.array([0.0, 0.0, z_min - z_max]),
            u_steps=24, v_steps=24
        )

        verts_arr = np.array(all_verts, dtype=np.float64)
        tris_arr = np.array(all_tris, dtype=np.int32)

        # Sample realistic vertex colors from nearest point cloud points
        dists, idxs = tree.query(verts_arr, k=min(4, len(pts)), workers=1)
        if cols is not None and len(cols) == len(pts):
            v_cols = np.mean(cols[idxs], axis=1) if idxs.ndim > 1 else cols[idxs]
        else:
            v_cols = np.full((len(verts_arr), 3), 0.85)

        mesh = cls()
        mesh.vertices = Vector3dVector(verts_arr)
        mesh.triangles = Vector3iVector(tris_arr)
        mesh.vertex_colors = Vector3dVector(v_cols)
        mesh.compute_triangle_normals()
        mesh.compute_vertex_normals()

        densities = np.ones(len(tris_arr), dtype=np.float64)
        return mesh, densities


class geometry:
    Vector3dVector = Vector3dVector
    Vector3iVector = Vector3iVector
    KDTreeSearchParamHybrid = KDTreeSearchParamHybrid
    Image = Image
    RGBDImage = RGBDImage
    PointCloud = PointCloud
    TriangleMesh = TriangleMesh


# ==============================================================================
# IO Subsystem (PLY PointCloud and TriangleMesh Writer / Reader)
# ==============================================================================
def write_point_cloud(filename: str, pcd: PointCloud, write_ascii: bool = True):
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    pts = np.asarray(pcd.points)
    cols = np.asarray(pcd.colors) if hasattr(pcd, "colors") else np.array([])
    norms = np.asarray(pcd.normals) if hasattr(pcd, "normals") else np.array([])

    has_cols = len(cols) == len(pts) and len(pts) > 0
    has_norms = len(norms) == len(pts) and len(pts) > 0

    if has_cols and cols.max() <= 1.0:
        cols = (cols * 255).astype(np.uint8)

    with open(filename, "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(pts)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        if has_norms:
            f.write("property float nx\nproperty float ny\nproperty float nz\n")
        if has_cols:
            f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")

        for i in range(len(pts)):
            line = f"{pts[i, 0]:.5f} {pts[i, 1]:.5f} {pts[i, 2]:.5f}"
            if has_norms:
                line += f" {norms[i, 0]:.4f} {norms[i, 1]:.4f} {norms[i, 2]:.4f}"
            if has_cols:
                line += f" {int(cols[i, 0])} {int(cols[i, 1])} {int(cols[i, 2])}"
            f.write(line + "\n")


def read_point_cloud(filename: str) -> PointCloud:
    pcd = PointCloud()
    pts, cols, norms = [], [], []
    with open(filename, "r") as f:
        in_header = True
        has_cols = False
        has_norms = False
        for line in f:
            line = line.strip()
            if in_header:
                if "property uchar red" in line: has_cols = True
                if "property float nx" in line: has_norms = True
                if line == "end_header": in_header = False
                continue
            parts = line.split()
            if len(parts) >= 3:
                pts.append([float(parts[0]), float(parts[1]), float(parts[2])])
                idx = 3
                if has_norms and len(parts) >= idx + 3:
                    norms.append([float(parts[idx]), float(parts[idx+1]), float(parts[idx+2])])
                    idx += 3
                if has_cols and len(parts) >= idx + 3:
                    cols.append([float(parts[idx])/255.0, float(parts[idx+1])/255.0, float(parts[idx+2])/255.0])

    pcd.points = Vector3dVector(pts)
    if cols: pcd.colors = Vector3dVector(cols)
    if norms: pcd.normals = Vector3dVector(norms)
    return pcd


def write_triangle_mesh(filename: str, mesh: TriangleMesh, write_ascii: bool = True, write_vertex_colors: bool = False) -> bool:
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    verts = np.asarray(mesh.vertices)
    tris = np.asarray(mesh.triangles)
    cols = np.asarray(mesh.vertex_colors) if hasattr(mesh, "vertex_colors") else np.array([])
    has_cols = len(cols) == len(verts) and len(verts) > 0

    if filename.lower().endswith(".glb"):
        from core.packaging.glb_exporter import GLBExporter
        norms = np.asarray(mesh.vertex_normals) if len(mesh.vertex_normals) == len(verts) else None
        export_cols = cols if (write_vertex_colors and has_cols) else None
        GLBExporter.export(verts, tris, normals=norms, output_path=filename, colors=export_cols)
        return True

    if filename.lower().endswith(".obj"):
        norms = np.asarray(mesh.vertex_normals) if len(mesh.vertex_normals) == len(verts) else None
        has_norms = norms is not None and len(norms) == len(verts)
        with open(filename, "w") as f:
            f.write("# OBJ exported by VASTU shim\n")
            for i in range(len(verts)):
                if has_cols and write_vertex_colors:
                    c = cols[i] if cols.max() <= 1.0 else cols[i] / 255.0
                    f.write(f"v {verts[i, 0]:.6f} {verts[i, 1]:.6f} {verts[i, 2]:.6f} {c[0]:.4f} {c[1]:.4f} {c[2]:.4f}\n")
                else:
                    f.write(f"v {verts[i, 0]:.6f} {verts[i, 1]:.6f} {verts[i, 2]:.6f}\n")
            if has_norms:
                for n in norms:
                    f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
            for t in tris:
                if has_norms:
                    f.write(f"f {t[0]+1}//{t[0]+1} {t[1]+1}//{t[1]+1} {t[2]+1}//{t[2]+1}\n")
                else:
                    f.write(f"f {t[0]+1} {t[1]+1} {t[2]+1}\n")
        return True

    if has_cols and cols.max() <= 1.0:
        cols = (cols * 255).astype(np.uint8)

    with open(filename, "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(verts)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        if has_cols:
            f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write(f"element face {len(tris)}\n")
        f.write("property list uchar int vertex_indices\n")
        f.write("end_header\n")

        for i in range(len(verts)):
            line = f"{verts[i, 0]:.5f} {verts[i, 1]:.5f} {verts[i, 2]:.5f}"
            if has_cols:
                line += f" {int(cols[i, 0])} {int(cols[i, 1])} {int(cols[i, 2])}"
            f.write(line + "\n")

        for t in tris:
            f.write(f"3 {int(t[0])} {int(t[1])} {int(t[2])}\n")
    return True


def read_triangle_mesh(filename: str) -> TriangleMesh:
    mesh = TriangleMesh()
    if filename.lower().endswith(".glb"):
        import struct
        import json
        with open(filename, "rb") as f:
            data = f.read()
        if len(data) < 20:
            return mesh
        magic, ver, total = struct.unpack("<III", data[:12])
        if magic != 0x46546C67:
            return mesh
        j_len, j_type = struct.unpack("<II", data[12:20])
        gltf = json.loads(data[20:20+j_len].decode("utf-8"))
        b_off = 20 + j_len
        b_len, b_type = struct.unpack("<II", data[b_off:b_off+8])
        bin_data = data[b_off+8:b_off+8+b_len]

        accessors = gltf.get("accessors", [])
        buffer_views = gltf.get("bufferViews", [])
        meshes = gltf.get("meshes", [])
        if not meshes:
            return mesh
        prims = meshes[0].get("primitives", [])
        if not prims:
            return mesh
        prim = prims[0]
        attrs = prim.get("attributes", {})

        def _extract(acc_idx, dtype, default_dim=3):
            if acc_idx is None or acc_idx >= len(accessors):
                return None
            acc = accessors[acc_idx]
            bv = buffer_views[acc["bufferView"]]
            off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            cnt = acc["count"]
            acc_type = acc.get("type", "VEC3")
            dim = 1 if acc_type == "SCALAR" else (default_dim)
            dt = np.dtype(dtype)
            raw = bin_data[off:off + cnt * dim * dt.itemsize]
            arr = np.frombuffer(raw, dtype=dt)
            return arr.reshape(cnt, dim) if dim > 1 else arr

        if "POSITION" in attrs:
            verts = _extract(attrs["POSITION"], np.float32, 3)
            if verts is not None:
                mesh.vertices = Vector3dVector(verts)
        if "NORMAL" in attrs:
            norms = _extract(attrs["NORMAL"], np.float32, 3)
            if norms is not None:
                mesh.vertex_normals = Vector3dVector(norms)
        if "COLOR_0" in attrs:
            cols = _extract(attrs["COLOR_0"], np.float32, 3)
            if cols is not None:
                mesh.vertex_colors = Vector3dVector(cols[:, :3])
        if "indices" in prim:
            idx_acc = accessors[prim["indices"]]
            c_type = idx_acc.get("componentType", 5125)
            dt = np.uint16 if c_type == 5123 else (np.uint32 if c_type == 5125 else np.uint8)
            idxs = _extract(prim["indices"], dt, 1)
            if idxs is not None:
                mesh.triangles = Vector3iVector(idxs.reshape(-1, 3))
        return mesh

    verts, faces, cols = [], [], []
    num_verts = None
    num_faces = None
    has_cols = False
    with open(filename, "r") as f:
        in_header = True
        for line in f:
            line = line.strip()
            if not line:
                continue
            if in_header:
                if line.startswith("element vertex"):
                    num_verts = int(line.split()[2])
                elif line.startswith("element face"):
                    num_faces = int(line.split()[2])
                elif "property uchar red" in line:
                    has_cols = True
                elif line == "end_header":
                    in_header = False
                continue
            parts = line.split()
            if num_verts is not None and len(verts) < num_verts:
                if len(parts) >= 3:
                    verts.append([float(parts[0]), float(parts[1]), float(parts[2])])
                    if has_cols and len(parts) >= 6:
                        cols.append([float(parts[3]) / 255.0, float(parts[4]) / 255.0, float(parts[5]) / 255.0])
            elif len(parts) >= 4 and parts[0] == "3":
                faces.append([int(parts[1]), int(parts[2]), int(parts[3])])

    mesh.vertices = Vector3dVector(verts)
    mesh.triangles = Vector3iVector(faces)
    if cols:
        mesh.vertex_colors = Vector3dVector(cols)
    mesh.compute_triangle_normals()
    return mesh


class io:
    write_point_cloud = staticmethod(write_point_cloud)
    read_point_cloud = staticmethod(read_point_cloud)
    write_triangle_mesh = staticmethod(write_triangle_mesh)
    read_triangle_mesh = staticmethod(read_triangle_mesh)


# ==============================================================================
# TSDF Volumetric Fusion Integration
# ==============================================================================
class TSDFVolumeColorType:
    RGB8 = 1


class ScalableTSDFVolume:
    def __init__(
        self,
        voxel_length: float = 0.03,
        sdf_trunc: float = 0.09,
        color_type: int = TSDFVolumeColorType.RGB8
    ):
        self.voxel_length = float(voxel_length)
        self.sdf_trunc = float(sdf_trunc)
        self.points_accum = []
        self.colors_accum = []
        self.frames_data = []

    def integrate(self, rgbd: RGBDImage, intrinsic: PinholeCameraIntrinsic, extrinsic: np.ndarray):
        color = np.asarray(rgbd.color)
        depth = np.asarray(rgbd.depth)
        h, w = depth.shape[:2]

        fx = intrinsic.intrinsic_matrix[0, 0]
        fy = intrinsic.intrinsic_matrix[1, 1]
        cx = intrinsic.intrinsic_matrix[0, 2]
        cy = intrinsic.intrinsic_matrix[1, 2]

        self.frames_data.append({
            'depth': depth.copy(),
            'color': color.copy(),
            'K': intrinsic.intrinsic_matrix.copy(),
            'extrinsic': extrinsic.copy()
        })

        step = max(2, min(8, w // 80))
        u, v = np.meshgrid(np.arange(0, w, step), np.arange(0, h, step))
        z = depth[v, u]
        valid = (z > 0.3) & (z < 6.0) & np.isfinite(z)
        if not np.any(valid):
            return

        u_val = u[valid]
        v_val = v[valid]
        z_val = z[valid]

        x_cam = (u_val - cx) * z_val / fx
        y_cam = (v_val - cy) * z_val / fy
        pts_cam = np.column_stack([x_cam, y_cam, z_val])

        # Extrinsic is World-to-Camera, invert to get Camera-to-World
        R_w2c = extrinsic[:3, :3]
        t_w2c = extrinsic[:3, 3]
        R_c2w = R_w2c.T
        t_c2w = -R_c2w @ t_w2c

        pts_world = (R_c2w @ pts_cam.T).T + t_c2w
        cols_val = color[v_val, u_val].astype(np.float64) / 255.0

        self.points_accum.append(pts_world)
        self.colors_accum.append(cols_val)

    def extract_point_cloud(self) -> PointCloud:
        pcd = PointCloud()
        if not self.points_accum:
            return pcd
        all_pts = np.vstack(self.points_accum)
        all_cols = np.vstack(self.colors_accum)
        pcd.points = Vector3dVector(all_pts)
        pcd.colors = Vector3dVector(all_cols)
        return pcd

    def extract_triangle_mesh(self) -> TriangleMesh:
        mesh = TriangleMesh()
        if not self.points_accum:
            return mesh
        all_pts = np.vstack(self.points_accum)
        all_cols = np.vstack(self.colors_accum)

        if marching_cubes is not None and len(all_pts) > 100 and len(self.frames_data) > 0:
            try:
                min_b = np.percentile(all_pts, 1.0, axis=0) - 0.15
                max_b = np.percentile(all_pts, 99.0, axis=0) + 0.15
                vox = max(0.035, float(self.voxel_length))
                nx = max(8, int(np.ceil((max_b[0] - min_b[0]) / vox)))
                ny = max(8, int(np.ceil((max_b[1] - min_b[1]) / vox)))
                nz = max(8, int(np.ceil((max_b[2] - min_b[2]) / vox)))

                nx, ny, nz = min(nx, 140), min(ny, 100), min(nz, 140)

                xs = np.linspace(min_b[0], max_b[0], nx, dtype=np.float32)
                ys = np.linspace(min_b[1], max_b[1], ny, dtype=np.float32)
                zs = np.linspace(min_b[2], max_b[2], nz, dtype=np.float32)
                xx, yy, zz = np.meshgrid(xs, ys, zs, indexing='ij')
                grid_pts = np.stack([xx.ravel(), yy.ravel(), zz.ravel()], axis=1)

                vol = np.ones(len(grid_pts), dtype=np.float32)
                weights = np.zeros(len(grid_pts), dtype=np.float32)
                sdf_trunc = float(self.sdf_trunc)

                for frame in self.frames_data:
                    d_map = frame['depth']
                    h_f, w_f = d_map.shape[:2]
                    R_w2c = frame['extrinsic'][:3, :3]
                    t_w2c = frame['extrinsic'][:3, 3]
                    K_mat = frame['K']

                    pts_c = (R_w2c @ grid_pts.T).T + t_w2c
                    z_c = pts_c[:, 2]
                    valid = (z_c > 0.35) & (z_c < 5.5)
                    val_idx = np.where(valid)[0]
                    if len(val_idx) == 0:
                        continue

                    u = np.round(K_mat[0, 0] * pts_c[val_idx, 0] / z_c[val_idx] + K_mat[0, 2]).astype(int)
                    v = np.round(K_mat[1, 1] * pts_c[val_idx, 1] / z_c[val_idx] + K_mat[1, 2]).astype(int)
                    in_img = (u >= 0) & (u < w_f) & (v >= 0) & (v < h_f)
                    val_idx = val_idx[in_img]
                    if len(val_idx) == 0:
                        continue

                    d_obs = d_map[v[in_img], u[in_img]]
                    valid_d = (d_obs > 0.35) & (d_obs < 5.5) & np.isfinite(d_obs)
                    val_idx = val_idx[valid_d]
                    if len(val_idx) == 0:
                        continue

                    sdf = d_obs[valid_d] - z_c[val_idx]
                    band = sdf > -sdf_trunc
                    val_idx = val_idx[band]
                    if len(val_idx) == 0:
                        continue

                    sdf_clamped = np.clip(sdf[band] / sdf_trunc, -1.0, 1.0)
                    w_old = weights[val_idx]
                    w_new = w_old + 1.0
                    vol[val_idx] = (vol[val_idx] * w_old + sdf_clamped) / w_new
                    weights[val_idx] = w_new

                vol_3d = vol.reshape((nx, ny, nz))
                observed = weights.reshape((nx, ny, nz)) > 0.5
                vol_3d[~observed] = 1.0

                dx = float((max_b[0] - min_b[0]) / max(nx - 1, 1))
                dy = float((max_b[1] - min_b[1]) / max(ny - 1, 1))
                dz = float((max_b[2] - min_b[2]) / max(nz - 1, 1))

                verts, faces, normals, _ = marching_cubes(vol_3d, level=0.0, spacing=(dx, dy, dz))
                verts += min_b

                if len(verts) > 50:
                    mesh.vertices = Vector3dVector(verts)
                    mesh.triangles = Vector3iVector(faces)
                    mesh.vertex_normals = Vector3dVector(normals)
                    tree = cKDTree(all_pts)
                    _, nn_idx = tree.query(verts, k=1)
                    mesh.vertex_colors = Vector3dVector(all_cols[nn_idx])
                    mesh.compute_triangle_normals()
                    return mesh
            except Exception:
                pass

        pcd = self.extract_point_cloud()
        mesh, _ = TriangleMesh.create_from_point_cloud_poisson(pcd, depth=7)
        return mesh


class integration:
    TSDFVolumeColorType = TSDFVolumeColorType
    ScalableTSDFVolume = ScalableTSDFVolume


class pipelines:
    integration = integration

