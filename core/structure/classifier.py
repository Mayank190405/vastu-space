"""
Architectural Plane Classifier: Categorizes fitted 3D planes into FLOOR, WALL, CEILING, and OTHER.
"""

from typing import List, Literal, Tuple, Optional
import numpy as np

PlaneType = Literal["WALL", "FLOOR", "CEILING", "OTHER"]

class PlaneClassifier:
    def __init__(
        self,
        up_vector: Optional[np.ndarray] = None,
        horizontal_tolerance_deg: float = 15.0,
        vertical_tolerance_deg: float = 15.0
    ):
        """
        Initializes the classifier.
        Args:
            up_vector: Global gravity/vertical up direction. Defaults to [0, 0, 1] if None.
            horizontal_tolerance_deg: Maximum angle deviation from up-vector to be considered horizontal.
            vertical_tolerance_deg: Maximum angle deviation from 90 degrees relative to up-vector to be considered vertical.
        """
        if up_vector is None:
            self.up_vector = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        else:
            norm = np.linalg.norm(up_vector)
            self.up_vector = (np.array(up_vector, dtype=np.float64) / norm) if norm > 1e-6 else np.array([0.0, 0.0, 1.0])
        
        self.cos_horizontal_thresh = np.cos(np.radians(horizontal_tolerance_deg))
        self.sin_vertical_thresh = np.sin(np.radians(vertical_tolerance_deg))

    def classify_single_plane(
        self,
        normal: np.ndarray,
        centroid: np.ndarray,
        scene_elevation_range: Optional[Tuple[float, float]] = None
    ) -> PlaneType:
        """
        Classifies a single plane based on its normal and centroid elevation along the up-vector.
        """
        norm = np.linalg.norm(normal)
        if norm < 1e-6:
            return "OTHER"
        unit_normal = normal / norm

        # Dot product with up-vector: cos(theta)
        dot_up = float(np.dot(unit_normal, self.up_vector))
        abs_dot = abs(dot_up)

        elevation = float(np.dot(centroid, self.up_vector))

        # Check if nearly horizontal (normal parallel or anti-parallel to up vector)
        if abs_dot >= self.cos_horizontal_thresh:
            if scene_elevation_range is not None:
                min_elev, max_elev = scene_elevation_range
                mid_elev = (min_elev + max_elev) / 2.0
                return "FLOOR" if elevation <= mid_elev else "CEILING"
            else:
                # If normal points directly upward, likely floor; if downward, ceiling
                return "FLOOR" if dot_up > 0 else "CEILING"

        # Check if nearly vertical (normal perpendicular to up vector)
        if abs_dot <= self.sin_vertical_thresh:
            return "WALL"

        # Slanted surfaces (sloped roofs, ramps, decorative angled geometry)
        return "OTHER"

    def classify_planes(
        self,
        planes: List[Tuple[np.ndarray, np.ndarray]]
    ) -> List[PlaneType]:
        """
        Batch classifies a list of (plane_model, centroid_3d) or (normal_3d, centroid_3d).
        Performs contextual elevation comparison for floors vs ceilings.
        """
        if not planes:
            return []

        elevations = [float(np.dot(centroid, self.up_vector)) for _, centroid in planes]
        min_elev = min(elevations)
        max_elev = max(elevations)
        elev_range = (min_elev, max_elev)

        results: List[PlaneType] = []
        for plane_item, centroid in planes:
            normal = plane_item[:3]
            ptype = self.classify_single_plane(normal, centroid, scene_elevation_range=elev_range)
            results.append(ptype)

        return results
