"""
Unit Tests for DelightingEngine and ArchitecturalSchematicTextureGenerator
Verifies:
1. Multi-view median filtering separates specular glares and transient shadows.
2. Unobserved areas receive the CAD/BIM architectural schematic hatched texture.
3. Provenance texture masking preserves real observed pixels while marking unobserved ones.
"""

import pytest
import numpy as np

from core.texturing.delighting_engine import DelightingEngine, ArchitecturalSchematicTextureGenerator


def test_delighting_median_filter():
    engine = DelightingEngine()

    # Base true albedo is 120 (neutral gray)
    base_patch = np.full((16, 16, 3), 120, dtype=np.uint8)

    # View 1: Normal observation
    v1 = base_patch.copy()

    # View 2: Has a specular glare artifact (value 255 at center)
    v2 = base_patch.copy()
    v2[6:10, 6:10] = 255

    # View 3: Has a cast shadow artifact (value 40 at corner)
    v3 = base_patch.copy()
    v3[0:4, 0:4] = 40

    delighted = engine.extract_diffuse_albedo([v1, v2, v3])

    # Median filtering must recover 120 across all pixels
    assert delighted[7, 7, 0] == 120
    assert delighted[2, 2, 0] == 120
    assert np.all(delighted == 120)


def test_schematic_hatch_texture():
    hatch = ArchitecturalSchematicTextureGenerator.create_unsurveyed_hatch_texture(
        width=64, height=64, stripe_width=2, stripe_interval=8
    )
    assert hatch.shape == (64, 64, 3)
    # Background and hatch colors must both be present
    unique_colors = np.unique(hatch.reshape(-1, 3), axis=0)
    assert len(unique_colors) == 2


def test_provenance_texture_masking():
    # 32x32 texture
    observed_texture = np.full((32, 32, 3), 200, dtype=np.uint8)
    # Left half observed, right half unobserved
    provenance_mask = np.zeros((32, 32), dtype=bool)
    provenance_mask[:, :16] = True

    result = ArchitecturalSchematicTextureGenerator.apply_provenance_texture_mask(
        surface_texture=observed_texture,
        provenance_mask=provenance_mask
    )

    # Left half must remain 200
    assert np.all(result[:, :16] == 200)
    # Right half must have hatch pattern applied
    assert not np.all(result[:, 16:] == 200)
