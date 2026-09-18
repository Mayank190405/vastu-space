"""
Test Suite: Metric Coordinate Alignment & Canonical World System
Verifies:
1. 5-tier evidence priority order (LiDAR -> Physical -> Floorplan -> Object -> Manual).
2. Canonical world coordinate alignment (gravity alignment +Z up, floor leveling at Z=0, yaw alignment).
3. Explicit transformation Sim(3) point mapping (forward and inverse).
4. Prevention of silent scaling (explicit transform stored).
5. Acceptance Criterion: Every published model has an explicit metric transform and its scale source is recorded.
"""

import pytest
import numpy as np
import uuid

from core.schemas.metric_transform import MetricTransformSchema, MetricScaleSource
from core.schemas.model_version import ModelVersion, ModelArtifactKeys
from core.alignment.transform import MetricTransform
from core.alignment.priorities import (
    LiDAREvidence,
    PhysicalMeasurementEvidence,
    FloorplanDimensionEvidence,
    KnownObjectEvidence,
    ManualCorrectionEvidence
)
from core.alignment.estimator import MetricCoordinateAligner
from core.alignment.publisher import ModelPublisher

def test_5_tier_evidence_priority_order():
    """Verifies that evidence is evaluated in strict descending priority order."""
    aligner = MetricCoordinateAligner()

    ev_lidar = LiDAREvidence(scale_factor=1.002, confidence=0.99)
    ev_phys = PhysicalMeasurementEvidence(
        measured_distance_m=5.00,
        point_a_3d=np.array([0, 0, 0]),
        point_b_3d=np.array([2.5, 0, 0]), # scale = 2.0
        confidence=0.92
    )
    ev_floor = FloorplanDimensionEvidence(
        reference_distance_m=6.00,
        feature_a_3d=np.array([0, 0, 0]),
        feature_b_3d=np.array([2.0, 0, 0]), # scale = 3.0
        drawing_reference_id="DWG-01",
        confidence=0.85
    )
    ev_obj = KnownObjectEvidence(
        object_class="door",
        observed_dimension_m=0.50,
        standard_dimension_m=0.90, # scale = 1.8
        confidence=0.75
    )
    ev_man = ManualCorrectionEvidence(
        manual_scale_factor=1.50,
        operator_id="eng_01",
        reason="Field adjustment",
        confidence=0.60
    )

    # 1. LiDAR present alongside all others -> LiDAR MUST win (Priority 1)
    s1, src1, conf1, _ = aligner.resolve_scale(
        lidar_evidence=ev_lidar,
        physical_evidence=ev_phys,
        floorplan_evidence=ev_floor,
        object_evidence=ev_obj,
        manual_evidence=ev_man
    )
    assert src1 == MetricScaleSource.METRIC_LIDAR_AR
    assert s1 == 1.002

    # 2. No LiDAR, but Physical present -> Physical MUST win (Priority 2)
    s2, src2, conf2, _ = aligner.resolve_scale(
        lidar_evidence=None,
        physical_evidence=ev_phys,
        floorplan_evidence=ev_floor,
        object_evidence=ev_obj,
        manual_evidence=ev_man
    )
    assert src2 == MetricScaleSource.MEASURED_PHYSICAL_DIMENSIONS
    assert s2 == 2.0

    # 3. No LiDAR or Physical, Floorplan present -> Floorplan MUST win (Priority 3)
    s3, src3, conf3, _ = aligner.resolve_scale(
        lidar_evidence=None,
        physical_evidence=None,
        floorplan_evidence=ev_floor,
        object_evidence=ev_obj,
        manual_evidence=ev_man
    )
    assert src3 == MetricScaleSource.KNOWN_FLOORPLAN_DIMENSIONS
    assert s3 == 3.0

    # 4. Only Known Object and Manual present -> Known Object MUST win (Priority 4)
    s4, src4, conf4, _ = aligner.resolve_scale(
        lidar_evidence=None,
        physical_evidence=None,
        floorplan_evidence=None,
        object_evidence=ev_obj,
        manual_evidence=ev_man
    )
    assert src4 == MetricScaleSource.RELIABLE_KNOWN_OBJECT_DIMENSIONS
    assert pytest.approx(s4, 0.01) == 1.8

    # 5. Only Manual present -> Manual wins (Priority 5)
    s5, src5, conf5, _ = aligner.resolve_scale(
        lidar_evidence=None,
        physical_evidence=None,
        floorplan_evidence=None,
        object_evidence=None,
        manual_evidence=ev_man
    )
    assert src5 == MetricScaleSource.MANUAL_CORRECTION
    assert s5 == 1.50

def test_canonical_world_alignment_gravity_and_floor():
    """Verifies that model is rotated so gravity points in -Z (+Z UP) and floor sits at Z = 0."""
    aligner = MetricCoordinateAligner()

    # Synthetic room tilted: Floor normal is in +Y direction instead of +Z (camera frame tilted by 90 deg)
    floor_normal = np.array([0.0, 1.0, 0.0])
    floor_point = np.array([0.0, 2.0, 0.0]) # Floor at y = 2.0
    pts = np.array([
        [0.0, 2.0, 0.0],
        [2.0, 2.0, 0.0],
        [0.0, 4.8, 0.0], # ceiling 2.8m above floor
    ])

    transform = aligner.compute_alignment_transform(
        points=pts,
        floor_normal=floor_normal,
        floor_point=floor_point,
        lidar_evidence=LiDAREvidence(scale_factor=1.0)
    )

    # Apply transform to points
    pts_world = transform.apply(pts)

    # Floor points must now have Z == 0.0
    assert pytest.approx(pts_world[0][2], 0.001) == 0.0
    assert pytest.approx(pts_world[1][2], 0.001) == 0.0
    # Ceiling point must now have Z == 2.8
    assert pytest.approx(pts_world[2][2], 0.001) == 2.8

def test_explicit_transformation_point_mapping_and_inversion():
    """Verifies forward and inverse point transformation accuracy."""
    R = np.array([
        [0.0, -1.0, 0.0],
        [1.0,  0.0, 0.0],
        [0.0,  0.0, 1.0]
    ]) # 90 deg rotation around Z
    t = np.array([10.0, 20.0, 5.0])
    s = 2.5

    transform = MetricTransform(
        scale=s,
        rotation_matrix=R,
        translation=t,
        scale_source=MetricScaleSource.METRIC_LIDAR_AR,
        scale_confidence=0.98
    )

    pts = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 2.0, 3.0],
        [5.0, 5.0, 5.0]
    ])

    world_pts = transform.apply(pts)
    recovered_pts = transform.apply_inverse(world_pts)

    assert np.allclose(pts, recovered_pts, atol=1e-5)

    # Check schema conversion
    schema = transform.to_schema()
    assert isinstance(schema, MetricTransformSchema)
    assert schema.scale == 2.5
    assert len(schema.matrix_4x4) == 4
    assert len(schema.rotation_quaternion) == 4

def test_acceptance_criterion_published_model_must_have_explicit_metric_transform():
    """
    Acceptance Criterion:
    Every published model has an explicit metric transform and its scale source is recorded.
    """
    publisher = ModelPublisher(require_metric=True)

    artifacts = ModelArtifactKeys(
        lod0_glb_s3_key="projects/p1/models/lod0.glb",
        splat_ply_s3_key="projects/p1/models/splat.ply"
    )

    valid_transform = MetricTransformSchema(
        scale=1.042,
        translation=[1.2, -0.5, 0.0],
        rotation_matrix=[[1,0,0],[0,1,0],[0,0,1]],
        rotation_quaternion=[0,0,0,1],
        matrix_4x4=[[1.042,0,0,1.2],[0,1.042,0,-0.5],[0,0,1.042,0.0],[0,0,0,1]],
        scale_source=MetricScaleSource.METRIC_LIDAR_AR,
        scale_confidence=0.98,
        canonical_frame="RIGHT_HANDED_Z_UP",
        floor_elevation_m=0.0
    )

    # 1. Publishing succeeds when explicit metric transform is provided
    published = publisher.publish_model(
        project_id=uuid.uuid4(),
        semver="1.0.0",
        artifacts=artifacts,
        metric_transform=valid_transform
    )
    assert isinstance(published, ModelVersion)
    assert published.metric_transform is not None
    assert published.metric_transform.scale == 1.042
    assert published.metric_transform.scale_source == MetricScaleSource.METRIC_LIDAR_AR

    # 2. Publishing fails when metric transform is missing
    with pytest.raises(ValueError, match="Missing explicit metric transform"):
        publisher.publish_model(
            project_id=uuid.uuid4(),
            semver="1.0.0",
            artifacts=artifacts,
            metric_transform=None
        )

    # 3. Publishing fails when scale_source is UNSCALED
    unscaled_transform = valid_transform.model_copy()
    unscaled_transform.scale_source = MetricScaleSource.UNSCALED
    with pytest.raises(ValueError, match="invalid or unscaled"):
        publisher.publish_model(
            project_id=uuid.uuid4(),
            semver="1.0.0",
            artifacts=artifacts,
            metric_transform=unscaled_transform
        )
