"""
Architectural Structure Extractor: Extracts crisp, sharp dominant planes,
classifies them into floor/wall/ceiling/other, computes boundaries & confidences,
resolves plane intersections with selective 90-degree priors while preserving non-orthogonal geometry,
and builds an independent architectural plane graph.
"""

from typing import Optional, Dict, Any, List, Tuple
import numpy as np

from geometry.normals import estimate_point_normals
from geometry.planes import fit_plane_ransac
from core.structure.classifier import PlaneClassifier, PlaneType
from core.structure.confidence import PlaneConfidenceEstimator
from core.structure.boundaries import PlaneBoundaryExtractor
from core.structure.intersections import PlaneIntersectionResolver
from core.structure.graph import ArchitecturalPlaneGraph

class ArchitecturalStructureExtractor:
    def __init__(
        self,
        up_vector: Optional[np.ndarray] = None,
        distance_threshold: float = 0.03,
        min_inliers_per_plane: int = 40,
        max_planes: int = 20,
        normal_alignment_threshold: float = 0.70,
        orthogonal_tolerance_deg: float = 3.5,
        min_angle_confidence: float = 0.50
    ):
        self.up_vector = up_vector if up_vector is not None else np.array([0.0, 0.0, 1.0])
        self.distance_threshold = distance_threshold
        self.min_inliers_per_plane = min_inliers_per_plane
        self.max_planes = max_planes
        self.normal_alignment_threshold = normal_alignment_threshold

        self.classifier = PlaneClassifier(up_vector=self.up_vector)
        self.confidence_estimator = PlaneConfidenceEstimator(min_inliers_expected=min_inliers_per_plane)
        self.boundary_extractor = PlaneBoundaryExtractor()
        self.intersection_resolver = PlaneIntersectionResolver(
            orthogonal_tolerance_deg=orthogonal_tolerance_deg,
            min_angle_confidence=min_angle_confidence
        )

    def extract_structure(
        self,
        points: np.ndarray,
        normals: Optional[np.ndarray] = None,
        point_confidences: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ArchitecturalPlaneGraph:
        """
        Executes end-to-end architectural structure extraction from dense spatial evidence.
        """
        if len(points) == 0:
            return ArchitecturalPlaneGraph(metadata=metadata)

        points = np.asarray(points, dtype=np.float64)

        # 1. Estimate normals if not provided
        if normals is None or len(normals) != len(points):
            normals = estimate_point_normals(points, k_neighbors=20)
        else:
            normals = np.asarray(normals, dtype=np.float64)

        # 2. Detect dominant planes via iterative normal-consistent RANSAC
        extracted_planes = self._detect_dominant_planes(points, normals)

        # 3. Batch classify planes into FLOOR, WALL, CEILING, OTHER
        plane_inputs = [(p["plane_equation"][:3], p["centroid"]) for p in extracted_planes]
        classifications = self.classifier.classify_planes(plane_inputs)

        # 4 & 5. Compute confidences and boundaries
        for i, p in enumerate(extracted_planes):
            p["plane_type"] = classifications[i]
            inlier_pts = points[p["inlier_indices"]]
            inlier_normals = normals[p["inlier_indices"]]

            # Confidence
            conf = self.confidence_estimator.compute_confidence(
                inlier_pts,
                p["plane_equation"],
                point_normals=inlier_normals
            )
            p["confidence"] = conf

            # RMSE
            norm_len = np.linalg.norm(p["plane_equation"][:3]) + 1e-9
            dists = np.abs(np.dot(inlier_pts, p["plane_equation"][:3] / norm_len) + p["plane_equation"][3] / norm_len)
            p["rmse_m"] = float(np.sqrt(np.mean(dists ** 2)))

            # Boundaries
            corners_3d, boundary_poly_3d, area_m2 = self.boundary_extractor.extract_boundaries(
                inlier_pts,
                p["plane_equation"]
            )
            p["corners_3d"] = corners_3d
            p["boundary_polygon_3d"] = boundary_poly_3d
            p["surface_area_m2"] = area_m2

        # 7. Initialize Architectural Plane Graph
        graph = ArchitecturalPlaneGraph(metadata=metadata)
        for p in extracted_planes:
            graph.add_plane(
                plane_id=p["plane_id"],
                plane_type=p["plane_type"],
                plane_equation=p["plane_equation"].tolist(),
                normal=p["plane_equation"][:3].tolist(),
                inlier_count=len(p["inlier_indices"]),
                surface_area_m2=p["surface_area_m2"],
                confidence=p["confidence"],
                rmse_m=p["rmse_m"],
                corners_3d=p["corners_3d"],
                boundary_polygon_3d=p["boundary_polygon_3d"]
            )

        # 6. Detect plane intersections & apply selective architectural priors
        num_planes = len(extracted_planes)
        for i in range(num_planes):
            for j in range(i + 1, num_planes):
                p1 = extracted_planes[i]
                p2 = extracted_planes[j]

                pts1 = points[p1["inlier_indices"]]
                pts2 = points[p2["inlier_indices"]]

                edge_info = self.intersection_resolver.resolve_intersection(
                    plane_id_1=p1["plane_id"],
                    plane_id_2=p2["plane_id"],
                    plane_type_1=p1["plane_type"],
                    plane_type_2=p2["plane_type"],
                    plane_eq_1=p1["plane_equation"],
                    plane_eq_2=p2["plane_equation"],
                    pts_1=pts1,
                    pts_2=pts2,
                    conf_1=p1["confidence"],
                    conf_2=p2["confidence"]
                )

                if edge_info is not None:
                    graph.add_intersection_edge(
                        edge_id=edge_info["edge_id"],
                        source_plane_id=edge_info["source_plane_id"],
                        target_plane_id=edge_info["target_plane_id"],
                        raw_angle_deg=edge_info["raw_angle_deg"],
                        adjusted_angle_deg=edge_info["adjusted_angle_deg"],
                        angle_confidence=edge_info["angle_confidence"],
                        is_orthogonal_prior_applied=edge_info["is_orthogonal_prior_applied"],
                        intersection_line_start=edge_info["intersection_line_start"],
                        intersection_line_end=edge_info["intersection_line_end"],
                        junction_type=edge_info["junction_type"]
                    )

        return graph

    def _detect_dominant_planes(
        self,
        points: np.ndarray,
        normals: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Iteratively extracts dominant planes from point cloud.
        """
        remaining_indices = np.arange(len(points))
        planes = []
        plane_count = 0

        while len(remaining_indices) >= self.min_inliers_per_plane and plane_count < self.max_planes:
            subset_pts = points[remaining_indices]
            plane_model, inliers_local = fit_plane_ransac(
                subset_pts,
                distance_threshold=self.distance_threshold,
                num_iterations=400
            )

            if len(inliers_local) < self.min_inliers_per_plane:
                break

            # Filter inliers by normal consistency
            inlier_pts_global_idx = remaining_indices[inliers_local]
            inlier_normals = normals[inlier_pts_global_idx]
            normal = plane_model[:3] / (np.linalg.norm(plane_model[:3]) + 1e-9)

            dot_prods = np.abs(np.dot(inlier_normals, normal))
            consistent_mask = dot_prods >= self.normal_alignment_threshold

            if np.count_nonzero(consistent_mask) < self.min_inliers_per_plane:
                # Remove these points to avoid infinite loops on noisy clusters
                mask = np.ones(len(remaining_indices), dtype=bool)
                mask[inliers_local] = False
                remaining_indices = remaining_indices[mask]
                continue

            valid_inlier_indices = inlier_pts_global_idx[consistent_mask]

            # Re-refine plane equation using PCA on verified inliers
            refined_pts = points[valid_inlier_indices]
            centroid = np.mean(refined_pts, axis=0)
            cov = np.cov((refined_pts - centroid).T)
            eigvals, eigvecs = np.linalg.eigh(cov)
            refined_normal = eigvecs[:, 0]
            if np.dot(refined_normal, normal) < 0:
                refined_normal = -refined_normal
            refined_d = -float(np.dot(refined_normal, centroid))
            refined_plane = np.array([refined_normal[0], refined_normal[1], refined_normal[2], refined_d])

            plane_id = f"plane_{plane_count:03d}"
            planes.append({
                "plane_id": plane_id,
                "plane_equation": refined_plane,
                "inlier_indices": valid_inlier_indices,
                "centroid": centroid
            })

            # Remove extracted inliers from remaining set
            inlier_set = set(valid_inlier_indices)
            remaining_indices = np.array([idx for idx in remaining_indices if idx not in inlier_set])
            plane_count += 1

        return planes
