"""Geometry-first structural priors with bounded edits and explicit provenance.

Large supported planes may regularize nearby vertices. Only tiny planar boundary
loops may be filled. No room box, Manhattan layout or unseen object is invented.
"""
from dataclasses import dataclass, asdict
import numpy as np


@dataclass(frozen=True)
class GeometryReasoningConfig:
    max_planes: int = 6
    plane_distance_m: float = .025
    max_snap_m: float = .04
    min_plane_points: int = 200
    min_plane_extent_m: float = .7
    min_normal_alignment: float = .9
    smoothing_iterations: int = 3
    max_smoothing_m: float = .015
    max_hole_diameter_m: float = .10
    max_hole_perimeter_m: float = .35
    max_holes: int = 300

    def __post_init__(self):
        import math
        for key, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{key} must be finite and positive')
        for key in ('max_planes', 'min_plane_points', 'smoothing_iterations', 'max_holes'):
            if not isinstance(getattr(self, key), int):
                raise ValueError(f'{key} must be an integer')
        if self.min_normal_alignment > 1 or self.min_plane_points < 3:
            raise ValueError('Invalid plane support criteria')


class GeometryReasoner:
    def __init__(self, config=None):
        self.config = config or GeometryReasoningConfig()

    def refine(self, source):
        try:
            import open3d as o3d
        except ImportError:
            import core.reconstruction.o3d_shim as o3d
        import copy
        cfg = self.config
        mesh = copy.deepcopy(source)
        mesh.remove_degenerate_triangles().remove_duplicated_triangles().remove_unreferenced_vertices()
        mesh.compute_vertex_normals()
        original = np.asarray(mesh.vertices).copy()
        faces = np.asarray(mesh.triangles).copy()
        if len(faces) == 0 or not np.isfinite(original).all():
            raise ValueError('Need finite, nonempty geometry')
        normals = np.asarray(mesh.vertex_normals).copy()
        vertices = original.copy()
        boundary, loops = self._boundaries(faces)
        protected = np.zeros(len(vertices), bool)
        protected[boundary] = True
        labels = np.full(len(vertices), -1, dtype=np.int16)
        remaining = np.arange(len(vertices))
        planes = []
        try:
            o3d.utility.random.seed(19)
        except Exception:
            np.random.seed(19)
        for _ in range(cfg.max_planes):
            if len(remaining) < cfg.min_plane_points:
                break
            cloud = o3d.geometry.PointCloud()
            cloud.points = o3d.utility.Vector3dVector(original[remaining])
            equation, local = cloud.segment_plane(distance_threshold=cfg.plane_distance_m,
                                                 ransac_n=3, num_iterations=500)
            if len(local) < cfg.min_plane_points:
                break
            support = remaining[np.asarray(local)]
            remaining = np.setdiff1d(remaining, support, assume_unique=True)
            n = np.asarray(equation[:3], dtype=float)
            n /= np.linalg.norm(n)
            center = np.median(original[support], axis=0)
            _, _, basis = np.linalg.svd(original[support]-center, full_matrices=False)
            projected = (original[support]-center) @ basis[:2].T
            extent = np.ptp(projected, axis=0)
            if np.min(extent) < cfg.min_plane_extent_m:
                continue
            distance = vertices @ n+equation[3]
            aligned = np.abs(normals @ n) >= cfg.min_normal_alignment
            snap = (np.abs(distance) <= cfg.max_snap_m) & aligned & ~protected & (labels == -1)
            if np.count_nonzero(snap) < cfg.min_plane_points:
                continue
            vertices[snap] -= distance[snap, None]*n
            labels[snap] = len(planes)
            planes.append({'normal': n.tolist(), 'offset': float(equation[3]),
                           'support_vertices': len(support), 'snapped_vertices': int(snap.sum()),
                           'extent_m': extent.tolist(), 'semantics': 'large_observed_plane_not_semantically_classified'})
        mesh.vertices = o3d.utility.Vector3dVector(vertices)
        smoothed = mesh.filter_smooth_taubin(number_of_iterations=cfg.smoothing_iterations)
        candidate = np.asarray(smoothed.vertices)
        delta = candidate-vertices
        lengths = np.linalg.norm(delta, axis=1)
        factor = np.minimum(1, cfg.max_smoothing_m/np.maximum(lengths, 1e-12))
        movable = (labels == -1) & ~protected
        vertices[movable] += delta[movable]*factor[movable, None]
        displacement = np.linalg.norm(vertices-original, axis=1)
        # Tiny boundary completion has its own provenance. Large gaps remain open.
        added_faces, added_vertices, added_colors = [], [], []
        colors = np.asarray(mesh.vertex_colors).copy()
        filled = []
        triangle_points = vertices[faces]
        triangle_centers = triangle_points.mean(axis=1)
        for loop in loops:
            if len(filled) >= cfg.max_holes or not 3 <= len(loop) <= 24:
                continue
            points = vertices[loop]
            diameter = float(np.max(np.linalg.norm(points[:, None]-points[None], axis=2)))
            perimeter = float(np.linalg.norm(points-np.roll(points, 1, axis=0), axis=1).sum())
            if diameter > cfg.max_hole_diameter_m or perimeter > cfg.max_hole_perimeter_m:
                continue
            center = points.mean(axis=0)
            _, _, basis = np.linalg.svd(points-center, full_matrices=False)
            if np.max(np.abs((points-center) @ basis[-1])) > .005:
                continue
            # Only convex loops: avoid filling across concavities or silhouettes.
            xy = (points-center) @ basis[:2].T
            cross = np.cross(np.roll(xy,-1,axis=0)-xy, np.roll(xy,-2,axis=0)-np.roll(xy,-1,axis=0))
            if not (np.all(cross >= -1e-8) or np.all(cross <= 1e-8)):
                continue
            nearby = np.linalg.norm(triangle_centers-center, axis=1) <= max(diameter*2, .02)
            triangles = triangle_points[nearby]
            if len(triangles):
                xy_triangles = (triangles-center) @ basis[:2].T
                a, b, c = xy_triangles[:, 0], xy_triangles[:, 1], xy_triangles[:, 2]
                def cross2(x, y):
                    return x[:, 0]*y[:, 1]-x[:, 1]*y[:, 0]
                denom = cross2(b-a, c-a)
                usable = np.abs(denom) > 1e-12
                beta = np.divide(cross2(-a, c-a), denom, out=np.full(len(a), -1.), where=usable)
                gamma = np.divide(cross2(b-a, -a), denom, out=np.full(len(a), -1.), where=usable)
                coplanar = np.max(np.abs((triangles-center) @ basis[-1]), axis=1) < .005
                if np.any(usable & coplanar & (beta >= 0) & (gamma >= 0) & (beta+gamma <= 1)):
                    continue  # Exterior silhouettes already cover their center; do not cap them.
            index = len(vertices)+len(added_vertices)
            added_vertices.append(center)
            if len(colors) == len(vertices):
                added_colors.append(colors[loop].mean(axis=0))
            positive = np.dot(np.cross(points[1]-points[0], center-points[0]), normals[loop].mean(axis=0)) >= 0
            for j, a in enumerate(loop):
                b = loop[(j+1) % len(loop)]
                added_faces.append([a, b, index] if positive else [b, a, index])
            filled.append({'boundary_vertices': loop, 'diameter_m': diameter, 'perimeter_m': perimeter})
        if added_vertices:
            vertices = np.vstack([vertices, added_vertices])
            faces = np.vstack([faces, added_faces])
            if len(colors) == len(original):
                mesh.vertex_colors = o3d.utility.Vector3dVector(np.vstack([colors, added_colors]))
        mesh.vertices = o3d.utility.Vector3dVector(vertices)
        mesh.triangles = o3d.utility.Vector3iVector(faces)
        mesh.compute_vertex_normals()
        report = {'algorithm': 'BOUNDED_PLANE_REGULARIZATION_AND_SMALL_GAP_COMPLETION',
                  'config': asdict(cfg), 'planes': planes, 'filled_holes': filled,
                  'original_vertices': len(original), 'original_triangles': len(source.triangles),
                  'output_vertices': len(vertices), 'output_triangles': len(faces),
                  'max_existing_vertex_displacement_m': float(displacement.max()),
                  'boundary_loops_preserved': len(loops)-len(filled),
                  'new_inferred_vertices': len(added_vertices), 'new_inferred_triangles': len(added_faces),
                  'scale_verified': False, 'complete_room_recovered': False,
                  'limitations': ['Structural planes are geometric hypotheses, not semantic wall labels',
                                 'Small filled gaps are inferred; large openings remain unchanged',
                                 'No global camera bundle adjustment or semantic object completion in this stage']}
        return mesh, report

    @staticmethod
    def _boundaries(faces):
        directed = np.vstack([faces[:, [0,1]], faces[:, [1,2]], faces[:, [2,0]]])
        edges, counts = np.unique(np.sort(directed, axis=1), axis=0, return_counts=True)
        boundary = edges[counts == 1]
        adjacency = {}
        for a, b in boundary:
            adjacency.setdefault(int(a), []).append(int(b))
            adjacency.setdefault(int(b), []).append(int(a))
        visited, loops = set(), []
        for start in adjacency:
            if start in visited or len(adjacency[start]) != 2:
                continue
            path, previous, current = [], None, start
            while current not in visited and len(adjacency[current]) == 2:
                visited.add(current)
                path.append(current)
                options = adjacency[current]
                following = options[0] if options[0] != previous else options[1]
                previous, current = current, following
            if current == start:
                loops.append(path)
        return np.unique(boundary), loops

