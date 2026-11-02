import unittest
import numpy as np
from core.reconstruction.alignment import (
    output_transform, transform_points, aligned_camera, verified_depth_inputs, trajectory_parallax,
)


class AlignmentTests(unittest.TestCase):
    def test_geometry_texture_and_camera_share_coordinates(self):
        angle = .31
        level = np.array([[1,0,0],[0,np.cos(angle),-np.sin(angle)],[0,np.sin(angle),np.cos(angle)]])
        upright = np.diag([-1.,-1.,1.])
        A, b = output_transform(upright, -1.2, level, .24)
        pose = {'R': np.eye(3), 't': np.array([[.1],[.2],[.3]])}
        pts = np.array([[.4,.5,3.],[-.2,.7,2.]])
        q = transform_points(pts,A,b)
        cam = aligned_camera(pose,A,b)
        np.testing.assert_allclose((cam['R'] @ q.T + cam['t']).T,
                                   (pose['R'] @ pts.T + pose['t']).T,atol=1e-12)
        original_center = (-pose['R'].T @ pose['t']).ravel()
        np.testing.assert_allclose(cam['C'],transform_points(original_center[None],A,b)[0])

    def test_no_leveling_transform(self):
        A,b=output_transform(np.eye(3),2.)
        np.testing.assert_allclose(transform_points([[1,3,4]],A,b),[[1,1,4]])

    def test_sparse_or_empty_evidence_never_keeps_prior_depth(self):
        depth=np.full((5,5),2.)
        for count in (0,1,5):
            mask=np.zeros((5,5),bool); mask.flat[:count]=True
            out,valid=verified_depth_inputs([depth],[np.ones_like(mask)],[depth*1.1],[mask])
            self.assertEqual(np.count_nonzero(valid[0]),count)
            self.assertTrue(np.all(out[0][~mask]==0))

    def test_nonfinite_and_originally_disabled_pixels_stay_disabled(self):
        d=np.array([[np.nan,-1],[2,3.]])
        out,valid=verified_depth_inputs([d],[np.array([[1,1],[0,1]],bool)],[d],[np.ones((2,2),bool)])
        np.testing.assert_array_equal(out[0],[[0,0],[0,3]])
        self.assertEqual(valid[0].sum(),1)

    def test_parallax_uses_separation_not_jitter_or_rotation(self):
        def pose(x): return {'R':np.eye(3),'t':np.array([[x],[0.],[0.]])}
        self.assertFalse(trajectory_parallax([pose(x) for x in [0,.01,0,.01]*20],5.)[1])
        self.assertFalse(trajectory_parallax([pose(0),pose(.5)],.2)[1])
        baseline,passed=trajectory_parallax([pose(0),pose(.2)],2.)
        self.assertFalse(passed)  # Separation alone has no metric/triangulation evidence.
        self.assertAlmostEqual(baseline,.2)

class PhotometricTests(unittest.TestCase):
    def test_large_errors_do_not_wrap_and_black_pixels_count(self):
        from core.reconstruction.alignment import photometric_rmse
        black = np.zeros((10,10,3),np.uint8)
        white = np.full_like(black,255)
        mask = np.ones((10,10),bool)
        self.assertEqual(photometric_rmse(white,black,mask),255.)
        self.assertEqual(photometric_rmse(black,black,mask),0.)

    def test_no_observations_is_not_a_perfect_score(self):
        from core.reconstruction.alignment import photometric_rmse
        img = np.zeros((10,10,3),np.uint8)
        self.assertIsNone(photometric_rmse(img,img,np.zeros((10,10),bool)))

class QualityGateTests(unittest.TestCase):
    def gate(self, **overrides):
        from scripts.generate_video_twin import VastuDigitalTwinPipeline
        from types import SimpleNamespace
        p = VastuDigitalTwinPipeline.__new__(VastuDigitalTwinPipeline)
        p.recovery = SimpleNamespace(history=[{'stage':'STAGE_01b','result':'ADAPTED'}])
        mesh = dict(triangle_count=20000,validation_verdict='PASS',largest_component_ratio=.99,
                    reconstruction_backend=dict(fusion_engine='TSDF_SCALABLE_VOLUME',
                        meshing_method='TSDF_MARCHING_CUBES_TOPOLOGY_PRESERVING',integrated_frames=10))
        args = dict(capture_report={'usable_frame_pct':100},
                    trajectory_metrics=[{'confidence':.9}],
                    depth_stats={'frame_statistics':[{'confidence_ratio':.9}]},
                    reg_metrics={'consensus_support_ratio':.9},
                    pcd_metrics={'total_points':50000,'dimensions_m':{'width_x':3}},
                    mesh_val=mesh,tex_val={'surface_coverage_pct':90},
                    reproj_report={'mean_pixel_rmse':10},
                    parallax_report={'parallax_gate_passed':True,'parallax_score':1.})
        args.update(overrides)
        return p._stage_22_quality_gate(**args)

    def test_recovery_note_does_not_override_failed_parallax(self):
        r=self.gate(parallax_report={'parallax_gate_passed':False,'parallax_score':.2})
        self.assertFalse(r['category_gates']['PARALLAX'])
        self.assertEqual(r['final_verdict'],'FAIL')

    def test_missing_backend_is_not_verified_by_triangle_count(self):
        r=self.gate(mesh_val={'triangle_count':20000,'validation_verdict':'PASS'})
        self.assertFalse(r['backend_verification']['verified'])

    def test_topology_rejection_is_not_hidden_by_high_triangle_count(self):
        r=self.gate(mesh_val={'triangle_count':200000,'validation_verdict':'FAIL'})
        self.assertFalse(r['category_gates']['MESH'])

    def test_no_reprojection_evidence_is_rejected(self):
        r=self.gate(reproj_report={'mean_pixel_rmse':None})
        self.assertFalse(r['category_gates']['REPROJECTION'])

    def test_observed_support_replaces_constant_coverage_score(self):
        r=self.gate(reg_metrics={'consensus_support_ratio':.6})
        self.assertEqual(r['category_scores']['COVERAGE'],.6)
        self.assertFalse(r['category_gates']['COVERAGE'])
