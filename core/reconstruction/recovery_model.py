"""Export supported geometry after a strict pipeline rejection.

Diagnostic geometry retains holes and unverified scale. No architectural box,
closed floor, repeated camera pose or invented unseen surface is substituted.
"""
import json
from pathlib import Path
import cv2
import numpy as np
from core.reconstruction.depth_reasoner import KeyframeDepthReasoner
from core.reconstruction.safety import ReconstructionSafetyError


def export_recovery_model(frames, depths, confidences, poses, K, output_dir, context=None):
    try:
        import open3d as o3d
    except ImportError:
        import core.reconstruction.o3d_shim as o3d
    from core.dense.tsdf_fusion import TSDFFusionEngine
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise ReconstructionSafetyError('Recovery output must be a fresh directory')
    output.mkdir(parents=True, exist_ok=True)
    indices = [i for i, p in enumerate(poses) if p is not None]
    if len(indices) < 3:
        raise ReconstructionSafetyError('Need at least three tracked keyframes to export multi-view geometry')
    fs, ds, cs, ps = ([items[i] for i in indices] for items in (frames, depths, confidences, poses))
    result = KeyframeDepthReasoner().refine(fs, ds, cs, ps, K)
    (output/'depth_reasoning.json').write_text(json.dumps(result['report'], indent=2))
    volume = TSDFFusionEngine(voxel_length_m=.02, sdf_trunc_m=.06, depth_max_m=20., depth_model='DEPTH_ANYTHING_V2_METRIC')
    integrated = []
    for local, original in enumerate(indices):
        valid = result['reasons'][local] == 0
        np.savez_compressed(output/f'evidence_{original:02d}.npz', depth=result['depths'][local],
                            reasons=result['reasons'][local], support=result['support'][local])
        if np.count_nonzero(valid) < 100:
            continue
        ok = volume.integrate_frame(cv2.cvtColor(fs[local], cv2.COLOR_BGR2RGB),
                                    result['depths'][local], ps[local]['R'], ps[local]['t'], K, valid)
        if ok:
            integrated.append(original)
    mesh = volume.extract_mesh(snap_architectural_planes=False)
    if mesh is None or len(mesh.triangles) < 100:
        raise ReconstructionSafetyError('Insufficient supported surface area to export a recovery mesh')
    # Preserve independently supported geometry as its own auditable asset.
    mesh.transform(np.diag([1., -1., -1., 1.]))
    mesh.compute_vertex_normals()
    if not o3d.io.write_triangle_mesh(str(output/'supported_model.glb'), mesh, write_vertex_colors=True):
        raise RuntimeError('Failed to write supported surface mesh')
    normalize_glb_buffer(output/'supported_model.glb')
    supported_counts = {'vertices': len(mesh.vertices), 'triangles': len(mesh.triangles)}
    # A separate preview uses the original neural predictions. These are observed
    # image surfaces with inferred depth, NOT multi-view verified measurements.
    inferred = TSDFFusionEngine(voxel_length_m=.02, sdf_trunc_m=.06, depth_max_m=20., depth_model='DEPTH_ANYTHING_V2_METRIC')
    for frame, depth, confidence, pose in zip(fs, ds, cs, ps):
        inferred.integrate_frame(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), depth, pose['R'], pose['t'], K, confidence)
    preview = inferred.extract_mesh(snap_architectural_planes=False)
    if preview is not None and len(preview.triangles) >= 100:
        mesh = preview
        if len(mesh.triangles) > 100000:
            mesh = mesh.simplify_quadric_decimation(100000)
    else:
        # Already upright; undo once before the common transform below.
        mesh.transform(np.diag([1., -1., -1., 1.]))
    # OpenCV camera coordinates to glTF upright convention; no floor or dimensions assumed.
    mesh.transform(np.diag([1., -1., -1., 1.]))
    mesh.remove_duplicated_triangles().remove_degenerate_triangles().remove_unreferenced_vertices()
    mesh.compute_vertex_normals()
    from core.reconstruction.geometry_reasoner import GeometryReasoner
    mesh, geometry_report = GeometryReasoner().refine(mesh)
    (output/'geometry_reasoning.json').write_text(json.dumps(geometry_report, indent=2))
    for name in ('model.glb', 'mesh.ply', 'mesh.obj'):
        if not o3d.io.write_triangle_mesh(str(output/name), mesh, write_vertex_colors=True):
            raise RuntimeError(f'Failed to write {name}')
    normalize_glb_buffer(output/"model.glb")
    import copy
    geometry = copy.deepcopy(mesh)
    geometry.vertex_colors = o3d.utility.Vector3dVector()
    if not o3d.io.write_triangle_mesh(str(output/'geometry.glb'), geometry):
        raise RuntimeError('Failed to export geometry review mesh')
    normalize_glb_buffer(output/'geometry.glb')
    # Read back exported geometry to verify it is real and nonempty.
    check = o3d.io.read_triangle_mesh(str(output/'model.glb'))
    if len(check.triangles) == 0 or not np.isfinite(np.asarray(check.vertices)).all():
        raise RuntimeError('Exported GLB failed geometry readback')
    report = {'status': 'DIAGNOSTIC_MODEL_GENERATED', 'accepted_metric_model': False,
              'scale_verified': False, 'coverage_complete': False,
              'model_depth_source': 'neural_inference_not_independently_verified',
              'supported_model': supported_counts,
              'geometry_reasoning': geometry_report,
              'vertices': len(mesh.vertices), 'triangles': len(mesh.triangles),
              'tracked_frame_ids': indices, 'integrated_frame_ids': integrated,
              'depth_reasoning_coverage_passed': result['report']['status'] == 'PASS',
              'limitations': ['Estimated calibration and neural depth scale',
                             'Primary preview contains inferred depth; supported_model.glb contains only multi-view supported surfaces',
                             'Coverage and dimensions have not been validated'], 'context': context or {}}
    (output/'model_report.json').write_text(json.dumps(report, indent=2))
    (output/'index.html').write_text(VIEWER)
    return report


def normalize_glb_buffer(path):
    import base64
    import struct
    path = Path(path)
    data = path.read_bytes()
    magic, version, total = struct.unpack('<III', data[:12])
    if magic != 0x46546C67 or version != 2 or total != len(data):
        raise RuntimeError('Invalid GLB header')
    length, kind = struct.unpack('<II', data[12:20])
    if kind != 0x4E4F534A:
        raise RuntimeError('Missing GLB JSON chunk')
    document = json.loads(data[20:20+length])
    buffers = document.get('buffers', [])
    if len(buffers) != 1 or not buffers[0].get('uri', '').startswith('data:'):
        return
    binary = base64.b64decode(buffers[0].pop('uri').split(',', 1)[1], validate=True)
    if len(binary) != buffers[0]['byteLength']:
        raise RuntimeError('GLB buffer size mismatch')
    text = json.dumps(document, separators=(',', ':')).encode()
    text += b' '*((-len(text)) % 4)
    binary += b'\0'*((-len(binary)) % 4)
    total = 12+8+len(text)+8+len(binary)
    path.write_bytes(struct.pack('<III', 0x46546C67, 2, total)+struct.pack('<II', len(text), 0x4E4F534A)
                     +text+struct.pack('<II', len(binary), 0x004E4942)+binary)


VIEWER = '''<!doctype html><html><head><meta charset="utf-8"><title>Geometry-first reconstruction</title>
<style>body{margin:0;background:#10151d;font:14px system-ui;color:#eee}header{position:fixed;top:0;padding:16px;background:#10151ddd;z-index:2}#status{color:#eac079}canvas{display:block}a{color:#7ecbff}</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script></head>
<body><header><b>Geometry-first reconstruction</b><div>Estimated shape · scale unverified · drag to orbit, scroll to zoom</div>
<div id="status">Loading mesh…</div><button id="geometry">Geometry</button> <button id="wireframe">Wireframe</button> <button id="predicted">Appearance</button> <button id="supported">Supported evidence only</button> <a href="geometry.glb" download>Download geometry</a> · <a href="model.glb" download>Appearance GLB</a> · <a href="model_report.json">Evidence report</a></header>
<script type="module">
import * as THREE from 'three';import {OrbitControls} from 'three/addons/controls/OrbitControls.js';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(Math.min(devicePixelRatio,2));document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color('#10151d');const camera=new THREE.PerspectiveCamera(55,innerWidth/innerHeight,.01,1000);const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
scene.add(new THREE.HemisphereLight(0xffffff,0x666666,2));const light=new THREE.DirectionalLight(0xffffff,1);light.position.set(2,4,3);scene.add(light);
let currentModel=null;let wireframe=false;
function loadModel(file,label){
 document.getElementById('status').textContent='Loading '+label+'…';
 new GLTFLoader().load(file,g=>{if(currentModel)scene.remove(currentModel);currentModel=g.scene;scene.add(g.scene);g.scene.traverse(o=>{if(o.isMesh){o.material.side=THREE.DoubleSide;o.material=file==='geometry.glb'?new THREE.MeshStandardMaterial({color:0xbcc9d8,roughness:.8,metalness:0,side:THREE.DoubleSide,wireframe}):new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.DoubleSide,wireframe});}});const box=new THREE.Box3().setFromObject(g.scene);const center=box.getCenter(new THREE.Vector3());const span=box.getSize(new THREE.Vector3()).length();controls.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(span*.35,span*.2,span*.75));camera.far=Math.max(span*20,100);camera.updateProjectionMatrix();document.getElementById('status').textContent=label+' — scale and completeness unverified';},undefined,e=>{document.getElementById('status').textContent='Mesh could not load. Open this viewer through a local HTTP server.';console.error(e);});
}
document.getElementById('predicted').onclick=()=>loadModel('model.glb','Neural depth surface');
document.getElementById('supported').onclick=()=>loadModel('supported_model.glb','Multi-view supported surface');
document.getElementById('geometry').onclick=()=>loadModel('geometry.glb','Geometry-first review');
document.getElementById('wireframe').onclick=()=>{wireframe=!wireframe;if(currentModel)currentModel.traverse(o=>{if(o.isMesh)o.material.wireframe=wireframe;});};
loadModel('geometry.glb','Geometry-first review');
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});function animate(){requestAnimationFrame(animate);controls.update();renderer.render(scene,camera);}animate();
</script></body></html>'''

