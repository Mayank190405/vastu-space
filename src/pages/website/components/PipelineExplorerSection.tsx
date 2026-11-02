import React, { useState } from 'react';
import {
  Zap,
  CheckCircle2,
  Cpu,
  Layers,
  Box,
  Compass,
  Database,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  FileCode,
  Sparkles,
  Clock
} from 'lucide-react';

interface StageData {
  id: number;
  code: string;
  name: string;
  worker: string;
  duration: string;
  inputs: string;
  outputs: string;
  algorithm: string;
  qualityGate: string;
  description: string;
  codeSnippet: string;
}

export const PipelineExplorerSection: React.FC = () => {
  const [selectedStage, setSelectedStage] = useState<number>(1);

  const stages: StageData[] = [
    {
      id: 1,
      code: 'STAGE_01_PREPROCESSING',
      name: 'Ingestion & Laplacian Blur Rejection',
      worker: 'Python / OpenCV / Celery',
      duration: '~45 seconds',
      inputs: 'Raw 4K 30/60fps MP4/MOV video + 6-DoF IMU telemetry (100 Hz)',
      outputs: 'Sharp Keyframe Sequence (JPEG, 3840x2160) + Frame Metadata Manifest',
      algorithm: 'Discrete 3x3 Laplacian Convolution Kernel + Variance of Laplacian Thresholding',
      qualityGate: 'Variance σ²_Laplacian ≥ 120.0 (discard motion-blurred frames)',
      description: 'Ingests chunked 5MB uploads from mobile field surveyors. Reassembles byte streams, verifies SHA-256 integrity, extracts keyframes at dynamic temporal intervals, and purges any frames with high-speed motion blur to prevent catastrophic bundle adjustment failure.',
      codeSnippet: `def audit_keyframe_sharpness(frame_bgr: np.ndarray) -> bool:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return variance >= 120.0  # Quality Gate Threshold`,
    },
    {
      id: 2,
      code: 'STAGE_02_SFM',
      name: 'Structure-from-Motion & Camera Tracking',
      worker: 'PyCOLMAP / C++ Native',
      duration: '~3.2 minutes',
      inputs: 'Validated sharp keyframes + known camera intrinsics (fx, fy, cx, cy)',
      outputs: 'Sparse 3D Point Cloud (.ply) + Calibrated Camera Poses (R_i, t_i)',
      algorithm: 'SIFT Feature Extraction + FLANN Matcher + Levenberg-Marquardt Bundle Adjustment',
      qualityGate: 'Mean Reprojection Error ϵ_reproj ≤ 1.2 pixels; ≥ 85% registered cameras',
      description: 'Extracts scale-invariant feature transform (SIFT) descriptors across adjacent keyframes. Solves epipolar constraints through five-point and eight-point algorithms, executing global bundle adjustment to establish sparse 3D geometry and exact 6-DoF camera trajectories.',
      codeSnippet: `reconstruction = pycolmap.incremental_mapping(
    database_path=db_path,
    image_path=keyframes_dir,
    output_path=sfm_dir,
    options=pycolmap.IncrementalPipelineOptions(min_num_matches=15)
)`,
    },
    {
      id: 3,
      code: 'STAGE_03_DEPTH',
      name: 'Multi-View Stereo Dense Depth Estimation',
      worker: 'OpenMVS / CUDA Accelerated',
      duration: '~4.5 minutes',
      inputs: 'Sparse 3D point cloud + Registered camera poses + Keyframes',
      outputs: 'Dense 32-bit Floating Point Depth Maps + Confidence Maps',
      algorithm: 'PatchMatch Stereo Consistency + Multi-View Depth Consensus',
      qualityGate: 'Minimum 3 overlapping view consensus per reconstructed 3D pixel',
      description: 'Estimates pixel-level photometric depth maps for every camera viewpoint using CUDA-accelerated PatchMatch stereo algorithms. Applies multi-view geometric consistency filters to eliminate specular reflections, glare, and dynamic site interferences.',
      codeSnippet: `depth_estimator = PatchMatchStereo(
    geom_consistency=True,
    min_views=3,
    depth_range=(0.3, 15.0)  # Metric indoor bounds (meters)
)
depth_maps = depth_estimator.compute(reconstruction)`,
    },
    {
      id: 4,
      code: 'STAGE_04_POINTCLOUD',
      name: 'Multi-View Consensus Fusion & Filtering',
      worker: 'Open3D / NumPy Core',
      duration: '~1.8 minutes',
      inputs: 'Dense multi-view depth maps + Confidence maps',
      outputs: 'Cleaned, Voxel-Downsampled Dense Point Cloud (.ply / .xyzrgb)',
      algorithm: 'Statistical Outlier Removal (SOR) + Voxel Grid Spatial Hashing (5mm cell)',
      qualityGate: 'Point cloud density ≥ 12,000 pts/m²; zero floating outlier clusters',
      description: 'Back-projects multi-view depth maps into a unified 3D Cartesian coordinate frame. Points supported by fewer than 3 independent camera rays are purged. A 5mm voxel spatial hash downsamples redundant points while preserving sharp geometric edges and corners.',
      codeSnippet: `pcd = open3d.geometry.PointCloud.create_from_depth_images(depth_maps)
pcd = pcd.voxel_down_sample(voxel_size=0.005)  # 5mm metric voxel
pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=25, std_ratio=1.5)`,
    },
    {
      id: 5,
      code: 'STAGE_05_MESHING',
      name: 'Screened Poisson Watertight Surface Meshing',
      worker: 'PoissonRecon / Open3D',
      duration: '~2.4 minutes',
      inputs: 'Fused dense point cloud with oriented surface normals',
      outputs: 'Watertight Triangular Mesh (.obj / .ply, ~250k - 500k polygons)',
      algorithm: 'Screened Poisson Surface Reconstruction (Octree Depth 10) + Manifold Repair',
      qualityGate: 'Zero non-manifold edges; Euler characteristic χ = 2 (watertight genus 0)',
      description: 'Solves the Screened Poisson equation ∇²χ = ∇ · V across an adaptive octree (depth 10) to generate a seamless, manifold surface representation of floors, ceilings, walls, and architectural recesses without gaping holes or irregular gaps.',
      codeSnippet: `mesh, densities = open3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
    pcd, depth=10, width=0, scale=1.1, linear_fit=True
)
mesh = repair_non_manifold_edges(mesh)`,
    },
    {
      id: 6,
      code: 'STAGE_06_TEXTURING',
      name: 'Visibility-Aware Photometric Texture Atlas',
      worker: 'OpenMVS / Pillow / C++',
      duration: '~2.8 minutes',
      inputs: 'Watertight triangular mesh + Calibrated keyframes',
      outputs: 'Optimized GLTF/GLB with 4K Texture Atlas (.png / WebP)',
      algorithm: 'Conformal UV Parameterization + Angle-of-Incidence Visibility Weighting',
      qualityGate: 'Texture coverage ≥ 98.5%; UV chart distortion ≤ 4.2%',
      description: 'Parameterizes the 3D surface into 2D UV texture charts. For every triangle facet, evaluates camera angle of incidence w = max(0, n · v) and projectiveness to select the crispest, least-distorted image source, synthesizing a high-fidelity 4K texture atlas.',
      codeSnippet: `uv_atlas = generate_conformal_uvs(mesh)
texture_atlas = bake_visibility_weighted_textures(
    mesh=mesh, uvs=uv_atlas, keyframes=keyframes, max_resolution=4096
)
export_gltf(mesh, texture_atlas, output_path="model.glb")`,
    },
    {
      id: 7,
      code: 'STAGE_07_SEMANTICS',
      name: 'Semantic 3D Spatial Parsing & Bounding Boxes',
      worker: 'Python / RANSAC / Vāstu Rules',
      duration: '~1.1 minutes',
      inputs: 'Watertight mesh + Dense point cloud',
      outputs: 'Manhattan Wall Planes + 3D Oriented Bounding Boxes (OBBs) + Room Metadata',
      algorithm: 'RANSAC Plane Fitting + Manhattan Orthogonal Regularization + Compass Alignment',
      qualityGate: 'Wall orthogonal orthogonality error ≤ 3.5°; floor normal aligned to [0,1,0]',
      description: 'Segments the scene into architectural primitives (floor, ceiling, primary walls) and extracts 3D oriented bounding boxes for physical furniture objects (tables, sofas, desks). Integrates compass heading to classify Vāstu directional zones (Ishanya, Agni, etc.).',
      codeSnippet: `planes = extract_ransac_planes(mesh, tolerance_cm=2.5)
ortho_walls = regularize_manhattan_walls(planes.vertical_walls)
obbs = detect_3d_bounding_boxes(mesh, min_volume_m3=0.15)`,
    },
    {
      id: 8,
      code: 'STAGE_08_NAVMESH',
      name: 'Obstacle-Aware 3D NavMesh & Path Extraction',
      worker: 'Navigation Engine / PostGIS',
      duration: '~45 seconds',
      inputs: 'Floor plane polygon + Furniture OBBs + Wall boundaries',
      outputs: 'Topological Navigation Graph (Nodes & Edges) + ADA Accessibility Flags',
      algorithm: 'Minkowski Sum Obstacle Dilation + Constrained Delaunay Triangulation + A*',
      qualityGate: 'All corridor passages ≥ 915mm clear width; slope ≤ 4.76° (ADA Section 405)',
      description: 'Subtracts obstacle collision bounding boxes from the walkable floor polygon with a 0.35m clearance margin. Derives a 3D topological graph stored directly in PostGIS 3.4 for real-time shortest-path traversal and live WebAR wayfinding arrows.',
      codeSnippet: `navmesh = generate_walkable_navmesh(floor_polygon, obstacles=obbs, agent_radius=0.35)
nav_graph = build_topological_graph(navmesh)
verify_ada_slopes(nav_graph, max_slope_degrees=4.76)`,
    },
    {
      id: 9,
      code: 'STAGE_09_QUALITY',
      name: 'Metric Quality Audit & PostGIS Synchronization',
      worker: 'Control Plane / Go / PostgreSQL',
      duration: '~30 seconds',
      inputs: 'Complete 3D Digital Twin Package (.glb, .dxf, NavMesh, POIs)',
      outputs: 'Automated Metric Quality Audit Report + Live Public Viewer Link',
      algorithm: 'Geometric Variance Benchmark vs Ground-Truth Tolerances + SRID:0 PostGIS Ingestion',
      qualityGate: 'Composite Quality Score ≥ 85.0 / 100; Absolute Metric Error ≤ 2.5cm / 10m',
      description: 'Executes automated statistical regression checks against metric ground truth. If quality gates pass, registers spatial POIs and navigation nodes into PostgreSQL 16 with PostGIS 3.4 SRID:0 coordinates, generates signed S3 CDN delivery URLs, and notifies the project team.',
      codeSnippet: `quality_score = compute_composite_quality_score(
    reproj_err=0.84, blur_passed=True, manifold_ok=True, metric_error_cm=1.4
)
if quality_score >= 85.0:
    postgis_sync_model(model_id, glb_url, nav_graph)
    publish_project_view(project_id)`,
    },
  ];

  const current = stages[selectedStage - 1];

  return (
    <section id="pipeline" className="py-24 bg-[#0E0C0A] relative border-t border-[#C5A059]/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-[#1A1714] border border-[#C5A059]/40 text-[#E8C982] text-xs font-mono uppercase tracking-wider">
            <Zap className="w-3.5 h-3.5 text-[#C5A059]" />
            <span>Autonomous Cloud Engine</span>
          </div>

          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold text-[#FAF7F0] tracking-tight">
            The 9-Stage{' '}
            <span className="text-[#E8C982]">Reconstruction Pipeline</span>
          </h2>

          <p className="text-[#C4B9AC] text-sm sm:text-base font-light leading-relaxed">
            From raw handheld smartphone video to watertight textured 3D digital twins and ADA navigation meshes—completely automated without manual 3D modeling or CAD tracing.
          </p>
        </div>

        {/* Pipeline Horizontal Stepper Grid */}
        <div className="mt-14 grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-2">
          {stages.map((stage) => {
            const isSelected = selectedStage === stage.id;
            return (
              <button
                key={stage.id}
                onClick={() => setSelectedStage(stage.id)}
                className={`p-3 rounded-xl border text-center transition-all flex flex-col items-center justify-between min-h-[90px] relative ${
                  isSelected
                    ? 'bg-gradient-to-b from-[#C5A059]/20 to-[#141210] border-[#C5A059] shadow-lg shadow-[#C5A059]/20 ring-1 ring-[#C5A059]'
                    : 'bg-[#141210] border-[#C5A059]/20 hover:border-[#C5A059]/50 hover:bg-[#1A1714]'
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <span
                    className={`font-mono text-xs font-bold ${
                      isSelected ? 'text-[#E8C982]' : 'text-[#6D5020]'
                    }`}
                  >
                    0{stage.id}
                  </span>
                  {isSelected && (
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  )}
                </div>
                <span
                  className={`text-[11px] font-sans font-medium line-clamp-2 leading-tight ${
                    isSelected ? 'text-white' : 'text-[#9C9183]'
                  }`}
                >
                  {stage.name.split(' ')[0]} {stage.name.split(' ')[1] || ''}
                </span>
                <span className="text-[9px] font-mono text-[#6D5020] mt-1">
                  {stage.duration}
                </span>
              </button>
            );
          })}
        </div>

        {/* Selected Stage Detail Card */}
        <div className="mt-8 rounded-2xl bg-[#141210] border border-[#C5A059]/40 p-6 sm:p-10 shadow-2xl relative overflow-hidden">
          {/* Top Stage Identification */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#C5A059]/20 pb-6">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="font-mono text-xs text-[#C5A059] font-semibold tracking-wider">
                  {current.code}
                </span>
                <span className="text-[#6D5020]">|</span>
                <span className="text-xs font-mono text-[#A6998A] flex items-center space-x-1">
                  <Clock className="w-3 h-3 text-[#C5A059]" />
                  <span>Execution Time: {current.duration}</span>
                </span>
              </div>
              <h3 className="font-serif text-2xl sm:text-3xl font-bold text-[#FAF7F0]">
                Stage 0{current.id}: {current.name}
              </h3>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3 py-1.5 rounded-lg bg-[#0E0C0A] border border-[#C5A059]/30 font-mono text-xs text-[#E8C982]">
                Worker: {current.worker}
              </span>
            </div>
          </div>

          {/* Description & Technical Breakdown */}
          <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="space-y-5">
              <p className="text-sm text-[#C4B9AC] font-light leading-relaxed">
                {current.description}
              </p>

              {/* Input / Output Spec Box */}
              <div className="p-4 rounded-xl bg-[#0E0C0A] border border-[#C5A059]/20 space-y-3 font-mono text-xs">
                <div>
                  <span className="text-[#A6998A] uppercase text-[10px] block">Input Specifications:</span>
                  <span className="text-[#E8C982]">{current.inputs}</span>
                </div>
                <div className="pt-2 border-t border-[#C5A059]/10">
                  <span className="text-[#A6998A] uppercase text-[10px] block">Output Artifacts:</span>
                  <span className="text-emerald-400 font-semibold">{current.outputs}</span>
                </div>
              </div>

              {/* Quality Gate Box */}
              <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-1.5 font-mono text-xs">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold uppercase text-[10px]">
                  <ShieldCheck className="w-4 h-4" />
                  <span>Mandatory Quality Gate Check:</span>
                </div>
                <p className="text-[#E3DDD5] font-sans text-xs">
                  {current.qualityGate}
                </p>
              </div>
            </div>

            {/* Code Snippet / Algorithm Implementation Box */}
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-[#0E0C0A] border border-[#C5A059]/20 space-y-2">
                <span className="text-[10px] font-mono uppercase tracking-wider text-[#A6998A] block">
                  Algorithmic Strategy:
                </span>
                <p className="text-xs text-[#E8C982] font-mono">
                  {current.algorithm}
                </p>
              </div>

              <div className="rounded-xl bg-[#080706] border border-[#C5A059]/30 overflow-hidden shadow-inner">
                <div className="px-4 py-2 bg-[#141210] border-b border-[#C5A059]/20 flex items-center justify-between text-[11px] font-mono text-[#A6998A]">
                  <span className="text-[#E8C982]">pipeline_stage_0{current.id}.py</span>
                  <span>PYTHON 3.10 / ASYNC</span>
                </div>
                <pre className="p-4 text-[11px] font-mono text-[#C4B9AC] overflow-x-auto leading-relaxed">
                  <code>{current.codeSnippet}</code>
                </pre>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={() => setSelectedStage((prev) => (prev > 1 ? prev - 1 : 9))}
                  className="px-3 py-1.5 rounded-lg border border-[#C5A059]/30 text-xs text-[#C4B9AC] hover:text-white hover:border-[#C5A059] transition-colors"
                >
                  ← Previous Stage
                </button>
                <button
                  onClick={() => setSelectedStage((prev) => (prev < 9 ? prev + 1 : 1))}
                  className="px-3 py-1.5 rounded-lg bg-[#C5A059]/20 hover:bg-[#C5A059]/30 border border-[#C5A059]/50 text-xs text-[#E8C982] font-semibold transition-colors flex items-center space-x-1"
                >
                  <span>Next Stage</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

