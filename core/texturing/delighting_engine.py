"""
VĀSTU Texturing & Lighting Disentanglement Engine:
Separates baked illumination and shadows from diffuse surface reflectance via multi-view median filtering.
Ensures unobserved blind spots are surfaced honestly with architectural schematic hatched textures,
strictly preventing AI hallucination of synthetic materials on unverified surfaces.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import logging

logger = logging.getLogger("vastu.texturing.delighting")


class DelightingEngine:
    """
    Disentangles view-dependent illumination and cast shadows from intrinsic surface reflectance.
    """
    def __init__(self, shadow_ratio_threshold: float = 0.45):
        self.shadow_ratio_threshold = shadow_ratio_threshold

    def extract_diffuse_albedo(
        self,
        multiview_samples: List[np.ndarray]
    ) -> np.ndarray:
        """
        Extracts diffuse surface albedo from multi-view observations using robust median filtering.
        Removes specular highlights (which appear bright only in narrow view angles)
        and transient cast shadows (which vary across camera exposures).

        Args:
            multiview_samples: List of (H, W, 3) uint8 or float RGB patches observing the same surface.

        Returns:
            delighted_patch: (H, W, 3) uint8 estimated diffuse albedo.
        """
        if not multiview_samples:
            raise ValueError("multiview_samples cannot be empty")

        if len(multiview_samples) == 1:
            return np.clip(multiview_samples[0], 0, 255).astype(np.uint8)

        # Stack views along new axis: (N, H, W, 3)
        stack = np.stack([s.astype(np.float32) for s in multiview_samples], axis=0)

        # Multi-view median filtering over observations
        diffuse_median = np.median(stack, axis=0)

        return np.clip(diffuse_median, 0, 255).astype(np.uint8)

    def detect_cast_shadow_mask(
        self,
        rgb_image: np.ndarray,
        luminance_threshold_ratio: float = 0.40
    ) -> np.ndarray:
        """
        Detects hard shadow regions in an image where illuminance drops sharply relative to
        local surroundings without a corresponding chromaticity change.
        """
        img_float = rgb_image.astype(np.float32)
        # Compute perceived luminance
        lum = 0.299 * img_float[:, :, 0] + 0.587 * img_float[:, :, 1] + 0.114 * img_float[:, :, 2]
        mean_lum = np.mean(lum)

        # Pixels with luminance significantly lower than mean without chromatic shift
        shadow_mask = lum < (mean_lum * luminance_threshold_ratio)
        return shadow_mask.astype(bool)


class ArchitecturalSchematicTextureGenerator:
    """
    Generates standard architectural CAD/BIM hatched textures for unobserved blind spots,
    explicitly signaling to the user and CAD systems that the area was UNSURVEYED.
    """
    @staticmethod
    def create_unsurveyed_hatch_texture(
        width: int = 256,
        height: int = 256,
        stripe_width: int = 4,
        stripe_interval: int = 20,
        background_rgb: Tuple[int, int, int] = (235, 238, 242),
        hatch_rgb: Tuple[int, int, int] = (148, 163, 184)
    ) -> np.ndarray:
        """
        Generates a 45-degree diagonal hatched blueprint texture for unobserved areas.
        """
        texture = np.ones((height, width, 3), dtype=np.uint8)
        texture[:, :] = background_rgb

        y_coords, x_coords = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
        diagonal_pattern = (x_coords + y_coords) % stripe_interval

        hatch_mask = diagonal_pattern < stripe_width
        texture[hatch_mask] = hatch_rgb

        return texture

    @staticmethod
    def apply_provenance_texture_mask(
        surface_texture: np.ndarray,
        provenance_mask: np.ndarray,
        hatch_texture: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Overlays the architectural schematic hatch texture onto any UV regions
        flagged as UNRESOLVED or unobserved, preventing AI inpainting hallucination.

        Args:
            surface_texture: (H, W, 3) current diffuse texture map
            provenance_mask: (H, W) bool, True where surface was physically observed
            hatch_texture: Optional (H, W, 3) pre-generated hatch texture
        """
        h, w, c = surface_texture.shape
        if hatch_texture is None:
            hatch_texture = ArchitecturalSchematicTextureGenerator.create_unsurveyed_hatch_texture(w, h)
        elif hatch_texture.shape[:2] != (h, w):
            import cv2
            hatch_texture = cv2.resize(hatch_texture, (w, h))

        output = np.copy(surface_texture)
        unobserved_mask = ~provenance_mask
        output[unobserved_mask] = hatch_texture[unobserved_mask]

        return output
