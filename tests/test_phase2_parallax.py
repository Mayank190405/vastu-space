import json
import tempfile
import unittest
import cv2
import numpy as np
from core.reconstruction.parallax import (camera_pose, measure_pair, metric_scale_report,
    export_analysis, select_keyframes, ParallaxConfig)


class ParallaxTests(unittest.TestCase):
    def setUp(self):
        self.K = np.array([[600.,0,320],[0,600,240],[0,0,1]])
        rng = np.random.default_rng(12)
        self.X = np.c_[rng.uniform(-.7,.7,120), rng.uniform(-.5,.5,120), rng.uniform(1.5,2.5,120)]
        self.evidence = dict(source='ARKIT', validated=True, tracking_valid=True,
                             reference='synthetic controlled metric trajectory', meters_per_unit=1., relative_uncertainty=.01)
        self.scale = metric_scale_report(self.evidence)

    def pose(self, center, angle=0, convention='world_to_camera'):
        R = cv2.Rodrigues(np.array([0.,angle,0.]))[0]
        return dict(R=R, t=-R@np.array(center), reliable=True,
                    rotation_sigma_deg=.01, translation_sigma=.0001, convention=convention)

    def project(self, pose, X=None):
        Q,C=camera_pose(pose)
        p=(self.K @ (Q.T @ ((self.X if X is None else X)-C).T)).T
        return p[:,:2]/p[:,2:3]

    def pair(self, baseline, depth_factor=1, counts=(120,120), angle=0, scale=None):
        a,b=self.pose([0,0,0]),self.pose([baseline,0,0],angle)
        X=self.X*depth_factor
        return measure_pair(0,1,a,b,self.project(a,X),self.project(b,X),self.K,counts,scale=scale or self.scale)

    def test_pure_rotation(self):
        a,b=self.pose([0,0,0]),self.pose([0,0,0],.4)
        p=measure_pair(0,1,a,b,self.project(a),self.project(b),self.K,(120,120),scale=self.scale)
        self.assertAlmostEqual(p['translation_m'],0)
        self.assertAlmostEqual(p['rotation_deg'],np.degrees(.4))
        self.assertFalse(p['useful_triangulation'])

    def test_five_cm_close_scene_can_pass_without_lowering_heuristic(self):
        p=self.pair(.05,depth_factor=.5)
        self.assertAlmostEqual(p['translation_m'],.05)
        self.assertFalse(p['baseline_heuristic_met'])
        self.assertTrue(p['useful_triangulation'])

    def test_twenty_cm(self):
        p=self.pair(.2)
        self.assertAlmostEqual(p['translation_m'],.2)
        self.assertTrue(p['useful_triangulation'])

    def test_transform_inversion(self):
        p=self.pose([1,2,3],.7)
        Q,C=camera_pose(p)
        np.testing.assert_allclose(C,[1,2,3],atol=1e-12)
        self.assertFalse(np.allclose(p['t'],C))
        np.testing.assert_allclose(camera_pose(dict(R=Q,t=C,convention='camera_to_world'))[1],C)
        # Rotation around a fixed off-origin center must have zero baseline.
        q=self.pose([1,2,3],-.3)
        np.testing.assert_allclose(camera_pose(q)[1],C,atol=1e-12)
        with self.assertRaises(ValueError): camera_pose(dict(R=np.eye(3)*2,t=[0,0,0]))

    def test_unscaled_sfm_cannot_pass_metric_gate(self):
        scale=metric_scale_report({'source':'MONOCULAR_SFM','meters_per_unit':1})
        self.assertEqual(scale['status'],'SCALE_UNOBSERVABLE')
        p=self.pair(.2,scale=scale)
        self.assertIsNone(p['translation_m'])
        with tempfile.TemporaryDirectory() as d:
            r=export_analysis([p],[self.pose([0,0,0]),self.pose([.2,0,0])],d,scale)
            self.assertEqual(r['status'],'NEEDS_RESCAN')
            self.assertFalse(r['parallax_gate_passed'])
            self.assertIsNone(r['total_baseline_displacement_m'])

    def test_valid_metric_arkit_gate_and_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            r=export_analysis([self.pair(.2)],[self.pose([0,0,0]),self.pose([.2,0,0])],d,self.scale)
            self.assertTrue(r['parallax_gate_passed'])
            from pathlib import Path
            self.assertEqual(len(list(Path(d).iterdir())),6)
            self.assertEqual(json.loads(Path(d,'metric_scale_report.json').read_text())['status'],'METRIC_ESTABLISHED')

    def test_low_overlap(self):
        p=self.pair(.2,counts=(1000,1000))
        self.assertIn('LOW_OVERLAP',p['acceptance_reason'])
        self.assertFalse(p['useful_triangulation'])

    def test_distant_scene_poor_triangulation(self):
        p=self.pair(.2,depth_factor=100)
        self.assertTrue(p['baseline_heuristic_met'])
        self.assertIn('POOR_TRIANGULATION_ANGLE',p['acceptance_reason'])
        self.assertFalse(p['useful_triangulation'])

    def test_unknown_or_high_uncertainty_and_blur_reject(self):
        a,b=self.pose([0,0,0]),self.pose([.2,0,0])
        del b['rotation_sigma_deg']
        p=measure_pair(0,1,a,b,self.project(a),self.project(b),self.K,(120,120))
        self.assertIn('POSE_UNCERTAINTY_UNKNOWN',p['acceptance_reason'])
        b['rotation_sigma_deg']=10
        p=measure_pair(0,1,a,b,self.project(a),self.project(b),self.K,(120,120),sharpness=(1,100))
        self.assertIn('HIGH_GEOMETRIC_UNCERTAINTY',p['acceptance_reason'])
        self.assertIn('BLURRED_IMAGE',p['acceptance_reason'])

    def test_units_conversion_and_scale_provenance(self):
        evidence=dict(self.evidence,meters_per_unit=.001)
        p=self.pair(200,depth_factor=1000,scale=metric_scale_report(evidence))
        self.assertAlmostEqual(p['translation_m'],.2)
        self.assertTrue(p['useful_triangulation'])
        for change in ({'reference':''},{'tracking_valid':False},{'relative_uncertainty':.5},{'source':'NEURAL_DEPTH'}):
            self.assertEqual(metric_scale_report(dict(self.evidence,**change))['status'],'SCALE_UNOBSERVABLE')

    def test_nonadjacent_complementary_pair_selection(self):
        bad=self.pair(0)
        good=self.pair(.2); good['frame_j']=3
        other=dict(good,frame_i=2,frame_j=4)
        selected,pairs=select_keyframes([bad,good,other])
        self.assertEqual(selected,[0,2,3,4])
        self.assertIn([0,3],pairs)

    def test_nonuniform_monocular_steps_do_not_report_a_baseline(self):
        a,b=self.pose([0,0,0]),self.pose([.2,0,0])
        a['scale_consistent']=b['scale_consistent']=False
        p=measure_pair(0,1,a,b,self.project(a),self.project(b),self.K,(120,120),scale=self.scale)
        self.assertIsNone(p['translation_input_units'])
        self.assertIsNone(p['translation_m'])
        self.assertFalse(p['useful_triangulation'])

    def test_rotation_and_translation_are_independent(self):
        p=self.pair(.2,angle=.4)
        self.assertAlmostEqual(p['translation_m'],.2)
        self.assertAlmostEqual(p['rotation_deg'],np.degrees(.4))
        self.assertTrue(p['useful_triangulation'])
        self.assertFalse(self.pair(.05)['useful_triangulation'])

if __name__=='__main__': unittest.main()
