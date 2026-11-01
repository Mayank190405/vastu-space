import React, { useState } from 'react';
import {
  Cpu,
  Layers,
  Compass,
  Box,
  Database,
  ArrowRight,
  CheckCircle2,
  FileCode,
  Shield,
  Zap,
  Activity,
  Maximize2
} from 'lucide-react';

export const ApproachDeepDiveSection: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    'sfm' | 'poisson' | 'manhattan' | 'navmesh' | 'postgis'
  >('sfm');

  const tabs = [
    {
      id: 'sfm',
      title: '1. Multi-View SfM & Blur Filter',
      short: 'SfM & Pose Estimation',
      icon: Cpu,
    },
    {
      id: 'poisson',
      title: '2. Watertight Poisson Meshing',
      short: 'Poisson Surface & UV',
      icon: Layers,
    },
    {
      id: 'manhattan',
      title: '3. Manhattan-World CAD Vectorizer',
      short: 'Manhattan 2D/3D CAD',
      icon: Box,
    },
    {
      id: 'navmesh',
      title: '4. ADA-Compliant 3D A* NavMesh',
      short: 'Obstacle A* Routing',
      icon: Compass,
    },
    {
      id: 'postgis',
      title: '5. PostGIS 3.4 Spatial Database',
      short: 'PostGIS SRID:0 Engine',
      icon: Database,
    },
  ];

  return (
    <section id="approach" className="py-24 bg-[#141210] relative border-t border-[#C5A059]/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-[#1A1714] border border-[#C5A059]/40 text-[#E8C982] text-xs font-mono uppercase tracking-wider">
            <Cpu className="w-3.5 h-3.5 text-[#C5A059]" />
            <span>Mathematical Foundations & Pure Algorithms</span>
          </div>

          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold text-[#FAF7F0] tracking-tight">
            The Scientific &{' '}
            <span className="text-[#E8C982]">Geometric Approach</span>
          </h2>

          <p className="text-[#C4B9AC] text-sm sm:text-base font-light leading-relaxed">
            VĀSTU operates on deterministic geometric principles, multi-view epipolar geometry, and algebraic spatial constraints. Explore each module of our computational engine below.
          </p>
        </div>

        {/* Tab Selection Navigation Bar */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-2 p-1.5 rounded-2xl bg-[#0E0C0A] border border-[#C5A059]/30 max-w-4xl mx-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-[#C5A059] to-[#9A7B3E] text-black shadow-lg shadow-[#C5A059]/20'
                    : 'text-[#C4B9AC] hover:text-[#E8C982] hover:bg-[#1A1714]'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-black' : 'text-[#C5A059]'}`} />
                <span>{tab.short}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Content Display */}
        <div className="mt-8 rounded-2xl bg-[#0E0C0A] border border-[#C5A059]/30 p-6 sm:p-10 shadow-2xl">
          {/* TAB 1: STRUCTURE-FROM-MOTION */}
          {activeTab === 'sfm' && (
            <div className="space-y-8 animate-in fade-in duration-300">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#C5A059]/20 pb-6">
                <div>
                  <span className="text-xs font-mono uppercase tracking-widest text-[#C5A059]">
                    STAGE 01 & 02 · CAMERA POSE ESTIMATION
                  </span>
                  <h3 className="text-2xl sm:text-3xl font-serif font-bold text-[#FAF7F0] mt-1">
                    Multi-View Geometry & Laplacian Blur Rejection
                  </h3>
                </div>
                <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
                  <span className="px-3 py-1 rounded bg-[#1A1714] border border-[#C5A059]/30 text-[#E8C982]">
                    PyCOLMAP / SIFT
                  </span>
                  <span className="px-3 py-1 rounded bg-emerald-950/40 border border-emerald-500/30 text-emerald-400">
                    Reproj Err ≤ 1.2 px
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="space-y-4 text-sm text-[#C4B9AC] leading-relaxed font-light">
                  <p>
                    Casual handheld smartphone video inevitably suffers from variable pan speeds and motion blur. VĀSTU applies an edge-based <strong>Laplacian convolution filter</strong> across every raw frame:
                  </p>

                  <div className="p-4 rounded-xl bg-[#141210] border border-[#C5A059]/30 font-mono text-xs text-[#E8C982] space-y-2">
                    <div className="text-[10px] text-[#A6998A] uppercase">Laplacian Blur Variance Formulation:</div>
                    <div>
                      ∇²I = (∂²I / ∂x²) + (∂²I / ∂y²)
                    </div>
                    <div>
                      σ²_Laplacian = (1/N) ∑ (∇²I(x,y) - μ_∇²I)² ≥ 120.0
                    </div>
                  </div>

                  <p>
                    Frames scoring below <strong>120.0</strong> are discarded before feature matching. The remaining keyframes are ingested into <strong>PyCOLMAP</strong>, where Scale-Invariant Feature Transform (SIFT) descriptors and nearest-neighbor ratio tests extract sparse feature correspondences.
                  </p>

                  <p>
                    Non-linear <strong>Levenberg-Marquardt bundle adjustment</strong> refines camera positions R_i, t_i and 3D world landmarks X_j by minimizing the sum of reprojection errors across all observed cameras.
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/30 space-y-3">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-[#E8C982] font-semibold">
                      Mathematical Principles Enforced:
                    </h4>
                    <ul className="space-y-2 text-xs text-[#C4B9AC]">
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>Epipolar Geometry:</strong> Essential matrix E = [t]_× R connects calibrated camera rays x'^T E x = 0.</span>
                      </li>
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>Corner Anchor Sweeps:</strong> 1.5s stationary dwell at room corners locks metric scale using known visual-inertial distance priors.</span>
                      </li>
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>Robust Outlier Rejection:</strong> RANSAC geometric consensus purges false matches with 99.9% statistical confidence.</span>
                      </li>
                    </ul>
                  </div>

                  <div className="p-4 rounded-xl bg-[#1A1714] border border-[#C5A059]/20 font-mono text-[11px] text-[#9C9183] space-y-1">
                    <div className="text-[#C5A059] font-bold"># Python Worker Verification Logic</div>
                    <div>var_laplacian = cv2.Laplacian(frame_gray, cv2.CV_64F).var()</div>
                    <div>if var_laplacian &lt; 120.0:</div>
                    <div className="pl-4 text-red-400">return QualityGateResult(passed=False, reason="BLUR_EXCEEDED")</div>
                    <div className="text-emerald-400">return QualityGateResult(passed=True, score=var_laplacian)</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: POISSON MESHING */}
          {activeTab === 'poisson' && (
            <div className="space-y-8 animate-in fade-in duration-300">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#C5A059]/20 pb-6">
                <div>
                  <span className="text-xs font-mono uppercase tracking-widest text-[#C5A059]">
                    STAGE 05 & 06 · SURFACE RECONSTRUCTION & UV TEXTURE
                  </span>
                  <h3 className="text-2xl sm:text-3xl font-serif font-bold text-[#FAF7F0] mt-1">
                    Screened Poisson Watertight Meshing & Atlas Synthesis
                  </h3>
                </div>
                <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
                  <span className="px-3 py-1 rounded bg-[#1A1714] border border-[#C5A059]/30 text-[#E8C982]">
                    Screened Poisson Octree 10
                  </span>
                  <span className="px-3 py-1 rounded bg-emerald-950/40 border border-emerald-500/30 text-emerald-400">
                    0 Non-Manifold Edges
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="space-y-4 text-sm text-[#C4B9AC] leading-relaxed font-light">
                  <p>
                    Point clouds alone cannot represent solid walls, floors, or cast architectural shadows. VĀSTU synthesizes a continuous watertight triangle mesh using <strong>Screened Poisson Surface Reconstruction</strong>:
                  </p>

                  <div className="p-4 rounded-xl bg-[#141210] border border-[#C5A059]/30 font-mono text-xs text-[#E8C982] space-y-2">
                    <div className="text-[10px] text-[#A6998A] uppercase">Poisson Indicator Equation:</div>
                    <div>
                      ∇²χ = ∇ · V
                    </div>
                    <div className="text-[11px] text-[#C4B9AC]">
                      where χ(x,y,z) is the 3D indicator function (1 inside solid, 0 outside) and V is the normal vector field.
                    </div>
                  </div>

                  <p>
                    Surface normals are estimated via Principal Component Analysis (PCA) over k-nearest spatial neighbors. An adaptive octree depth of 10 balances sub-centimeter architectural edge fidelity with rapid cloud execution.
                  </p>

                  <p>
                    <strong>Visibility-Weighted Texture Atlas Synthesis:</strong> Instead of simple projection, each triangle facet computes camera visibility angle w = max(0, n · v). The sharpest, most perpendicular camera view bakes the RGB texture, preventing blurry seam artifacts.
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/30 space-y-3">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-[#E8C982] font-semibold">
                      Watertight Topology Guarantees:
                    </h4>
                    <ul className="space-y-2 text-xs text-[#C4B9AC]">
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>Zero Non-Manifold Edges:</strong> Every edge in the mesh is shared by exactly two adjacent faces.</span>
                      </li>
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>Laplacian Smoothing:</strong> Eliminates high-frequency surface noise while preserving sharp 90° architectural corners.</span>
                      </li>
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>Direct WebGL Export:</strong> Generates Draco-compressed `.glb` assets loadable under 2.5s on desktop or mobile.</span>
                      </li>
                    </ul>
                  </div>

                  <div className="p-4 rounded-xl bg-[#1A1714] border border-[#C5A059]/20 font-mono text-[11px] text-[#9C9183] space-y-1">
                    <div className="text-[#C5A059] font-bold"># Screened Poisson Shell Invocator</div>
                    <div>mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(</div>
                    <div className="pl-4">pcd, depth=10, width=0, scale=1.1, linear_fit=True</div>
                    <div>)[0]</div>
                    <div className="text-emerald-400">assert mesh.is_edge_manifold() and mesh.is_vertex_manifold()</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: MANHATTAN-WORLD CAD */}
          {activeTab === 'manhattan' && (
            <div className="space-y-8 animate-in fade-in duration-300">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#C5A059]/20 pb-6">
                <div>
                  <span className="text-xs font-mono uppercase tracking-widest text-[#C5A059]">
                    STAGE 07 · PLANAR EXTRACTION & CAD VECTORIZATION
                  </span>
                  <h3 className="text-2xl sm:text-3xl font-serif font-bold text-[#FAF7F0] mt-1">
                    Manhattan-World Alignment & 2D Vector CAD Studio
                  </h3>
                </div>
                <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
                  <span className="px-3 py-1 rounded bg-[#1A1714] border border-[#C5A059]/30 text-[#E8C982]">
                    RANSAC Plane Fitting
                  </span>
                  <span className="px-3 py-1 rounded bg-blue-950/40 border border-blue-500/30 text-blue-400">
                    DXF / SVG / JSON Output
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="space-y-4 text-sm text-[#C4B9AC] leading-relaxed font-light">
                  <p>
                    Interior architecture consists largely of mutually orthogonal planes (floors, ceilings, walls). VĀSTU harnesses the <strong>Manhattan-World assumption</strong> to extract clean CAD vectors without manual tracing:
                  </p>

                  <div className="p-4 rounded-xl bg-[#141210] border border-[#C5A059]/30 font-mono text-xs text-[#E8C982] space-y-2">
                    <div className="text-[10px] text-[#A6998A] uppercase">RANSAC 3D Planar Regularization:</div>
                    <div>
                      a·x + b·y + c·z + d = 0, where ||[a,b,c]|| = 1
                    </div>
                    <div className="text-[11px] text-[#C4B9AC]">
                      Normals are snapped to orthogonal basis vectors: {'{'} [1,0,0], [0,1,0], [0,0,1] {'}'} within ±5° tolerance.
                    </div>
                  </div>

                  <p>
                    Floor polygons are isolated via height histogram clustering. Wall planes are projected downward onto the horizontal datum plane to produce 2D line segments. Door and window openings are identified by raycasting bounding gaps in vertical wall surfaces.
                  </p>

                  <p>
                    The extracted geometry is immediately exportable to <strong>AutoCAD DXF (R14/2000)</strong>, scalable vector graphics (SVG), and PostGIS structural schemas for turnkey construction use.
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/30 space-y-3">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-[#E8C982] font-semibold">
                      CAD Studio Features:
                    </h4>
                    <ul className="space-y-2 text-xs text-[#C4B9AC]">
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>Configurable Wall Thickness:</strong> Parametric adjustment between 100mm (drywall) and 230mm (structural brickwork).</span>
                      </li>
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>Magnetic Endpoint Snapping:</strong> Automatic vertex welding prevents unclosed room boundaries.</span>
                      </li>
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>Room Area & Perimeter Readout:</strong> Instant carpet area calculations in both Metric (m²) and Imperial (sq.ft.).</span>
                      </li>
                    </ul>
                  </div>

                  <div className="p-4 rounded-xl bg-[#1A1714] border border-[#C5A059]/20 font-mono text-[11px] text-[#9C9183] space-y-1">
                    <div className="text-[#C5A059] font-bold"># RANSAC Planar Extraction Snippet</div>
                    <div>plane_model, inliers = pcd.segment_plane(</div>
                    <div className="pl-4">distance_threshold=0.025, ransac_n=3, num_iterations=1000</div>
                    <div>)</div>
                    <div className="text-emerald-400">[a, b, c, d] = snap_to_manhattan_axes(plane_model)</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: NAVMESH & ADA ROUTING */}
          {activeTab === 'navmesh' && (
            <div className="space-y-8 animate-in fade-in duration-300">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#C5A059]/20 pb-6">
                <div>
                  <span className="text-xs font-mono uppercase tracking-widest text-[#C5A059]">
                    STAGE 08 · INDOOR WAYFINDING & ACCESSIBILITY
                  </span>
                  <h3 className="text-2xl sm:text-3xl font-serif font-bold text-[#FAF7F0] mt-1">
                    Obstacle-Aware 3D NavMesh & ADA A* Routing Engine
                  </h3>
                </div>
                <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
                  <span className="px-3 py-1 rounded bg-[#1A1714] border border-[#C5A059]/30 text-[#E8C982]">
                    Topological 3D Graph
                  </span>
                  <span className="px-3 py-1 rounded bg-emerald-950/40 border border-emerald-500/30 text-emerald-400">
                    ADA Slope ≤ 4.76° (1:12)
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="space-y-4 text-sm text-[#C4B9AC] leading-relaxed font-light">
                  <p>
                    Unlike Matterport or static 360° panoramas where users jump blindly between camera nodes, VĀSTU computes a true <strong>3D obstacle-aware NavMesh</strong>:
                  </p>

                  <div className="p-4 rounded-xl bg-[#141210] border border-[#C5A059]/30 font-mono text-xs text-[#E8C982] space-y-2">
                    <div className="text-[10px] text-[#A6998A] uppercase">3D A* Shortest-Path Traversal:</div>
                    <div>
                      f(n) = g(n) + h(n), where h(n) = ||p_n - p_goal||₂
                    </div>
                    <div className="text-[11px] text-[#C4B9AC]">
                      Slope constraint: tan(θ) = Δz / √(Δx² + Δy²) ≤ 1/12 ≈ 4.76° (ADA Section 405)
                    </div>
                  </div>

                  <p>
                    Traversable floor planes are identified, and obstacle hulls (furniture, walls, structural columns) are expanded by an agent radius r = 0.35m (Minkowski sum).
                  </p>

                  <p>
                    The navigation graph router generates smooth 3D Bezier splines and synthesizes real-time turn-by-turn guidance displayed both in the 3D WebGL viewer and on mobile WebAR camera feeds.
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/30 space-y-3">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-[#E8C982] font-semibold">
                      Accessibility & Spatial Compliance:
                    </h4>
                    <ul className="space-y-2 text-xs text-[#C4B9AC]">
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>ADA Wheelchair Clearance:</strong> Enforces minimum 915mm clear passage width between furniture bounding boxes.</span>
                      </li>
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>Ramp Slope Enforcement:</strong> Automatically flags steps or threshold drops &gt; 13mm that violate wheelchair accessibility.</span>
                      </li>
                      <li className="flex items-start space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span><strong>Dynamic Waypointing:</strong> Real-time distance and estimated walking time calculated dynamically.</span>
                      </li>
                    </ul>
                  </div>

                  <div className="p-4 rounded-xl bg-[#1A1714] border border-[#C5A059]/20 font-mono text-[11px] text-[#9C9183] space-y-1">
                    <div className="text-[#C5A059] font-bold"># ADA Slope Verifier in Router</div>
                    <div>slope_angle = math.degrees(math.atan2(dz, horizontal_dist))</div>
                    <div>if slope_angle &gt; 4.76:</div>
                    <div className="pl-4 text-amber-400">edge.is_ada_accessible = False</div>
                    <div>nav_graph.add_edge(node_a, node_b, weight=dist, ada=edge.is_ada_accessible)</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: POSTGIS 3.4 GEODATABASE */}
          {activeTab === 'postgis' && (
            <div className="space-y-8 animate-in fade-in duration-300">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#C5A059]/20 pb-6">
                <div>
                  <span className="text-xs font-mono uppercase tracking-widest text-[#C5A059]">
                    DATABASE ARCHITECTURE · SPATIAL INDEXING
                  </span>
                  <h3 className="text-2xl sm:text-3xl font-serif font-bold text-[#FAF7F0] mt-1">
                    PostgreSQL 16 + PostGIS 3.4 Metric Geodatabase
                  </h3>
                </div>
                <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
                  <span className="px-3 py-1 rounded bg-[#1A1714] border border-[#C5A059]/30 text-[#E8C982]">
                    Local Cartesian SRID: 0
                  </span>
                  <span className="px-3 py-1 rounded bg-emerald-950/40 border border-emerald-500/30 text-emerald-400">
                    3D GiST Spatial Indexing
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="space-y-4 text-sm text-[#C4B9AC] leading-relaxed font-light">
                  <p>
                    Rather than treating 3D digital twins as static opaque files, VĀSTU indexes every spatial node, room polygon, and point of interest (POI) into <strong>PostgreSQL 16 with PostGIS 3.4</strong>:
                  </p>

                  <div className="p-4 rounded-xl bg-[#141210] border border-[#C5A059]/30 font-mono text-xs text-[#E8C982] space-y-2">
                    <div className="text-[10px] text-[#A6998A] uppercase">PostGIS 3D Point Column Type:</div>
                    <div>
                      geom_pointz GEOMETRY(POINTZ, 0)
                    </div>
                    <div className="text-[11px] text-[#C4B9AC]">
                      where SRID 0 represents a metric Euclidean Cartesian space (1 unit = 1.000 meter in physical space).
                    </div>
                  </div>

                  <p>
                    Every spatial query—such as finding the nearest fire exit, measuring clearance to a structural pillar, or checking if furniture violates an ADA corridor—is executed directly via native PostGIS 3D spatial operators (<code>ST_3DDistance</code>, <code>ST_3DIntersects</code>).
                  </p>

                  <p>
                    PostGIS 3D GiST indexes provide millisecond query latency across hundreds of thousands of spatial nodes and multi-tenant organizations.
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/30 space-y-3">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-[#E8C982] font-semibold">
                      Production SQL Spatial Query:
                    </h4>
                    <div className="p-3 rounded-lg bg-[#0E0C0A] border border-[#C5A059]/20 font-mono text-[11px] text-[#FAF7F0] space-y-1">
                      <div className="text-[#C5A059]">-- Find nearest POI to visitor position</div>
                      <div>SELECT p.name, p.category,</div>
                      <div className="pl-4 text-emerald-400">ROUND(ST_3DDistance(p.geom_pointz, ST_SetSRID(ST_MakePoint(1.2, 1.65, -3.8), 0))::numeric, 2) AS distance_meters</div>
                      <div>FROM spatial_pois p</div>
                      <div>WHERE p.model_id = '5425ee6c-460a-4508-8e84-918cbcc57f42'</div>
                      <div>ORDER BY p.geom_pointz &lt;-&gt; ST_SetSRID(ST_MakePoint(1.2, 1.65, -3.8), 0)</div>
                      <div>LIMIT 3;</div>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-[#1A1714] border border-[#C5A059]/20 font-mono text-[11px] text-[#9C9183] space-y-1">
                    <div className="text-[#C5A059] font-bold"># PostGIS 3.4 Spatial Table Indices</div>
                    <div>CREATE INDEX idx_spatial_pois_3d ON spatial_pois USING GIST (geom_pointz);</div>
                    <div>CREATE INDEX idx_nav_nodes_3d ON nav_nodes USING GIST (geom_pointz);</div>
                    <div className="text-emerald-400">-- Sub-millisecond KNN neighbor search enabled</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

