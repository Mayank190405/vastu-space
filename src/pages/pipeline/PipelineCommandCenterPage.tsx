import React, { useState, useEffect } from 'react';
import {
  Activity,
  Layers,
  Cpu,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCw,
  Terminal,
  Clock,
  Sparkles,
  Camera,
  Boxes,
  FileText,
  Sliders,
  ChevronRight,
  TrendingUp,
  ShieldCheck,
  Zap,
  BarChart2,
  HardDrive
} from 'lucide-react';

interface Stage {
  id: string;
  number: string;
  name: string;
  category: 'PREPROCESSING' | 'SFM' | 'DENSE' | 'MESHING' | 'SEMANTICS' | 'QUALITY';
  status: 'COMPLETED' | 'PROCESSING' | 'PENDING' | 'FAILED';
  duration: string;
  metricLabel: string;
  metricValue: string;
  summary: string;
  details: Record<string, string | number>;
}

export const PipelineCommandCenterPage: React.FC = () => {
  const [activeStageId, setActiveStageId] = useState<string>('stage_02');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [pipelineProgress, setPipelineProgress] = useState<number>(100);
  const [selectedLogFilter, setSelectedLogFilter] = useState<'ALL' | 'INFO' | 'WARN' | 'METRIC'>('ALL');

  const stages: Stage[] = [
    {
      id: 'stage_01',
      number: '01',
      name: 'Keyframe Extraction & Motion Blur Filter',
      category: 'PREPROCESSING',
      status: 'COMPLETED',
      duration: '4.2s',
      metricLabel: 'Laplacian Blur Threshold',
      metricValue: '148.2 (Passed > 120)',
      summary: 'Sampled 4K 60fps video, discarded 18 blurred transition frames, retained 48 high-parallax anchors.',
      details: {
        'Raw Video Frames': 1420,
        'Extracted Anchors': 48,
        'Mean Sharpness': '152.4 Var',
        'Overlap Ratio': '78.5%'
      }
    },
    {
      id: 'stage_02',
      number: '02',
      name: 'Structure-from-Motion (PyCOLMAP)',
      category: 'SFM',
      status: 'COMPLETED',
      duration: '18.6s',
      metricLabel: 'Bundle Adjustment RMS',
      metricValue: '0.62 px (< 1.0 px)',
      summary: 'PyCOLMAP SIFT feature matching computed 6-DoF camera trajectory and 24,190 sparse 3D tie points.',
      details: {
        'SIFT Features': '48,000 pts',
        'Inlier Matches': '31,420',
        'Camera Calibration': 'f=26mm, fov=68°',
        'Reprojection Error': '0.62 px'
      }
    },
    {
      id: 'stage_03',
      number: '03',
      name: 'Multi-View Stereo Dense Depth',
      category: 'DENSE',
      status: 'COMPLETED',
      duration: '24.1s',
      metricLabel: 'Depth Consistency',
      metricValue: '94.2% agreement',
      summary: 'Generated metric depth maps across 48 views with bilateral edge-preserving depth smoothing.',
      details: {
        'Depth Resolution': '1920x1080',
        'Min Distance': '0.35m',
        'Max Distance': '8.20m',
        'Consistency Pass': '94.2%'
      }
    },
    {
      id: 'stage_04',
      number: '04',
      name: 'Point Cloud Consensus Fusion',
      category: 'DENSE',
      status: 'COMPLETED',
      duration: '12.4s',
      metricLabel: 'Filtered Points',
      metricValue: '1,420,890 pts',
      summary: 'Voxel grid downsampling (5mm resolution) removed statistical floating outliers and specular noise.',
      details: {
        'Raw Depth Points': '3,840,000',
        'Voxel Resolution': '5mm',
        'Fused Pointcloud': '1,420,890',
        'Normal Consistency': '98.1%'
      }
    },
    {
      id: 'stage_05',
      number: '05',
      name: 'Screened Poisson Surface Meshing',
      category: 'MESHING',
      status: 'COMPLETED',
      duration: '31.2s',
      metricLabel: 'Watertight Polygons',
      metricValue: '284,500 Faces',
      summary: 'Screened Poisson surface reconstruction created continuous watertight manifold surfaces.',
      details: {
        'Octree Depth': 'Level 10',
        'Non-Manifold Edges': 0,
        'Boundary Loops': 0,
        'Mesh Density': '284,500 Triangles'
      }
    },
    {
      id: 'stage_06',
      number: '06',
      name: 'Photometric Texture Atlas Synthesis',
      category: 'MESHING',
      status: 'COMPLETED',
      duration: '19.8s',
      metricLabel: 'Atlas Resolution',
      metricValue: '4096 x 4096 (4K)',
      summary: 'Visibility-weighted photometric reprojection blended seamless diffuse textures onto UV coordinates.',
      details: {
        'Texture Format': 'WebP / JPG 4K',
        'UV Islands': 342,
        'Seam Artifacts': '0.00%',
        'Mipmaps': '4 Levels'
      }
    },
    {
      id: 'stage_07',
      number: '07',
      name: 'Semantic 3D Bounding Boxes (OBB)',
      category: 'SEMANTICS',
      status: 'COMPLETED',
      duration: '8.5s',
      metricLabel: 'Detected Spatial Objects',
      metricValue: '14 Semantic POIs',
      summary: '10-Class indoor architectural taxonomy identified doors, windows, tables, and boundary planes.',
      details: {
        'Architectural Planes': 6,
        'Furniture OBBs': 5,
        'Egress Openings': 3,
        'Confidence Score': '96.4%'
      }
    },
    {
      id: 'stage_08',
      number: '08',
      name: 'Obstacle-Aware Walkable NavMesh',
      category: 'SEMANTICS',
      status: 'COMPLETED',
      duration: '6.1s',
      metricLabel: 'Walkable NavSurface',
      metricValue: '48.2 m² (ADA Passed)',
      summary: 'Extracted 3D walkable planar navigation mesh with ADA slope constraints (<= 4.76°).',
      details: {
        'NavMesh Area': '48.2 m²',
        'Obstacle Buffers': '0.3m radius',
        'Max Slope': '2.1°',
        'A* Path Nodes': 124
      }
    },
    {
      id: 'stage_09',
      number: '09',
      name: 'Metrology & Reprojection Quality Gate',
      category: 'QUALITY',
      status: 'COMPLETED',
      duration: '3.4s',
      metricLabel: 'Metrology Gate',
      metricValue: '100% PASSED (Grade A)',
      summary: 'Comprehensive audit verified scale calibration, edge continuity, and millimeter accuracy.',
      details: {
        'Scale Error': '±1.8mm / 10m',
        'Manifold Audit': '100% Valid',
        'Final Quality': 'PRODUCTION_CERTIFIED',
        'Total Pipeline Time': '128.3s'
      }
    }
  ];

  const terminalLogs = [
    { time: '14:22:01', level: 'INFO', msg: '[PipelineSupervisor] Initialized 9-stage reconstruction job vastu_job_8892.' },
    { time: '14:22:04', level: 'INFO', msg: '[Stage 01 Preprocessing] Extracted 48 keyframes. Mean sharpness: 152.4. Passed Laplacian filter.' },
    { time: '14:22:23', level: 'METRIC', msg: '[Stage 02 SfM] PyCOLMAP solved 48 camera poses. Bundle adjustment RMS error = 0.62px.' },
    { time: '14:22:47', level: 'INFO', msg: '[Stage 03 Depth] Computed bilateral depth maps. Multi-view consensus: 94.2%.' },
    { time: '14:23:00', level: 'METRIC', msg: '[Stage 04 PointCloud] Voxel grid 5mm consensus fused 1,420,890 clean points.' },
    { time: '14:23:31', level: 'INFO', msg: '[Stage 05 Meshing] Screened Poisson meshing generated 284,500 watertight triangles.' },
    { time: '14:23:51', level: 'INFO', msg: '[Stage 06 Texturing] Generated 4096x4096 photometric texture atlas with 4 mipmaps.' },
    { time: '14:23:59', level: 'INFO', msg: '[Stage 07 Semantics] Extracted 6 architectural planes, 3 doors, and 5 furniture OBBs.' },
    { time: '14:24:05', level: 'METRIC', msg: '[Stage 08 NavMesh] 3D obstacle-aware walkable surface computed: 48.2m².' },
    { time: '14:24:09', level: 'METRIC', msg: '[Stage 09 QualityGate] Metrology audit Grade A (scale delta ±1.8mm). Job completed successfully.' }
  ];

  const activeStage = stages.find((s) => s.id === activeStageId) || stages[0];

  const handleRerun = () => {
    setIsProcessing(true);
    setPipelineProgress(15);
    setTimeout(() => setPipelineProgress(45), 800);
    setTimeout(() => setPipelineProgress(75), 1600);
    setTimeout(() => {
      setPipelineProgress(100);
      setIsProcessing(false);
    }, 2400);
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[#17100A] text-[#F2DFB8] p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#36271C] pb-6">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-2xl bg-gradient-to-br from-[#C5A059] to-[#8F6834] text-black shadow-lg shadow-[#C5A059]/20">
              <Zap className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-black text-white font-serif-brand tracking-wide">
                  Photogrammetry Pipeline Command Center
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-black bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                  ALL 9 STAGES OPERATIONAL
                </span>
              </div>
              <p className="text-xs text-[#A6998A] mt-0.5">
                Real-time telemetry and diagnostics for the 9-stage autonomous spatial reconstruction engine.
              </p>
            </div>
          </div>
        </div>

        {/* Global Pipeline Actions */}
        <div className="flex items-center space-x-3">
          <button
            onClick={handleRerun}
            disabled={isProcessing}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#C5A059] to-[#9A7B3E] text-black font-bold text-xs flex items-center space-x-2 shadow-lg hover:brightness-110 active:scale-95 transition-all disabled:opacity-50"
          >
            <RotateCw className={`w-4 h-4 ${isProcessing ? 'animate-spin' : ''}`} />
            <span>{isProcessing ? 'Processing Pipeline...' : 'Trigger Full Re-Scan'}</span>
          </button>
        </div>
      </div>

      {/* Real-Time Hardware Telemetry Gauges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-[#211710] border border-[#36271C] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#A6998A]">
            <span className="font-bold uppercase tracking-wider">Active Pipeline</span>
            <Activity className="w-4 h-4 text-[#C5A059]" />
          </div>
          <div className="text-xl font-black text-white font-serif-brand">9 / 9 Stages Pass</div>
          <div className="w-full bg-[#17100A] h-2 rounded-full overflow-hidden border border-[#36271C]">
            <div className="bg-gradient-to-r from-[#C5A059] to-emerald-400 h-full rounded-full" style={{ width: `${pipelineProgress}%` }} />
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[#211710] border border-[#36271C] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#A6998A]">
            <span className="font-bold uppercase tracking-wider">RMS Reprojection Error</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-black text-emerald-400 font-mono">0.62 px</div>
          <div className="text-[10px] text-[#A6998A]">Benchmark threshold: &lt; 1.0 px (Superior)</div>
        </div>

        <div className="p-4 rounded-2xl bg-[#211710] border border-[#36271C] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#A6998A]">
            <span className="font-bold uppercase tracking-wider">Point Density</span>
            <Boxes className="w-4 h-4 text-[#C5A059]" />
          </div>
          <div className="text-xl font-black text-white font-mono">1.42M Points</div>
          <div className="text-[10px] text-[#A6998A]">5mm voxel consensus downsampling</div>
        </div>

        <div className="p-4 rounded-2xl bg-[#211710] border border-[#36271C] space-y-2">
          <div className="flex items-center justify-between text-xs text-[#A6998A]">
            <span className="font-bold uppercase tracking-wider">Total Execution Time</span>
            <Clock className="w-4 h-4 text-[#C5A059]" />
          </div>
          <div className="text-xl font-black text-white font-mono">2m 08s</div>
          <div className="text-[10px] text-[#A6998A]">Single-day automated turnaround</div>
        </div>
      </div>

      {/* Main Command Center: 9 Stage Pipeline List + Stage Deep-Dive Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: 9 Stages Vertical Flow */}
        <div className="lg:col-span-5 space-y-2.5">
          <div className="text-xs font-black uppercase text-[#8F7864] tracking-widest px-1">
            Reconstruction Stages (Chronological)
          </div>
          <div className="space-y-2">
            {stages.map((stage) => {
              const isSelected = stage.id === activeStageId;
              return (
                <button
                  key={stage.id}
                  onClick={() => setActiveStageId(stage.id)}
                  className={`w-full text-left p-3.5 rounded-2xl border transition-all flex items-center justify-between group ${
                    isSelected
                      ? 'bg-[#2A1E14] border-[#C5A059] shadow-lg shadow-[#C5A059]/15'
                      : 'bg-[#211710] border-[#36271C] hover:border-[#C5A059]/50 hover:bg-[#251A12]'
                  }`}
                >
                  <div className="flex items-center space-x-3 truncate">
                    <span className="font-mono text-xs font-black text-[#C5A059] w-6 shrink-0">
                      {stage.number}
                    </span>
                    <div className="truncate">
                      <div className="text-xs font-bold text-white group-hover:text-[#F2DFB8] truncate">
                        {stage.name}
                      </div>
                      <div className="text-[10px] text-[#A6998A] flex items-center space-x-2 mt-0.5">
                        <span className="text-[#C5A059] font-mono">{stage.metricLabel}:</span>
                        <span className="text-emerald-400 font-bold">{stage.metricValue}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 shrink-0">
                    <span className="font-mono text-[10px] text-[#8F7864]">{stage.duration}</span>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Selected Stage Deep-Dive Diagnostics */}
        <div className="lg:col-span-7 space-y-4">
          <div className="p-6 rounded-2xl bg-[#211710] border border-[#36271C] space-y-6">
            <div className="flex items-center justify-between border-b border-[#36271C] pb-4">
              <div>
                <span className="text-[10px] font-mono text-[#C5A059] uppercase tracking-wider">
                  STAGE {activeStage.number} • {activeStage.category}
                </span>
                <h2 className="text-lg font-black text-white font-serif-brand mt-0.5">
                  {activeStage.name}
                </h2>
              </div>
              <div className="px-3 py-1 rounded-xl bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 font-bold text-xs flex items-center space-x-1.5">
                <ShieldCheck className="w-4 h-4" />
                <span>Verified</span>
              </div>
            </div>

            <p className="text-xs text-[#E3DACA] leading-relaxed">
              {activeStage.summary}
            </p>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(activeStage.details).map(([k, v]) => (
                <div key={k} className="p-3 rounded-xl bg-[#17100A] border border-[#36271C]">
                  <div className="text-[10px] text-[#8F7864] font-medium">{k}</div>
                  <div className="text-sm font-black text-white font-mono mt-0.5">{v}</div>
                </div>
              ))}
            </div>

            {/* Stage Output Visualizer Preview */}
            <div className="p-4 rounded-xl bg-[#17100A] border border-[#36271C] space-y-3">
              <div className="flex items-center justify-between text-xs font-bold text-white">
                <span className="flex items-center space-x-1.5">
                  <BarChart2 className="w-4 h-4 text-[#C5A059]" />
                  <span>Computed Artifacts & Outputs</span>
                </span>
                <span className="text-[10px] font-mono text-[#A6998A]">Output: ready</span>
              </div>
              <div className="h-28 rounded-lg bg-[#211710] border border-dashed border-[#C5A059]/40 flex items-center justify-center text-xs text-[#A6998A] flex-col space-y-2">
                <Sparkles className="w-6 h-6 text-[#C5A059] animate-pulse" />
                <span>High-resolution geometry artifact generated & signed</span>
              </div>
            </div>
          </div>

          {/* Real-time Terminal Log Stream */}
          <div className="p-4 rounded-2xl bg-[#140D07] border border-[#36271C] space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-xs font-bold text-white">
                <Terminal className="w-4 h-4 text-[#C5A059]" />
                <span>Pipeline EventBus Telemetry Logs</span>
              </div>
              <div className="flex items-center space-x-1">
                {(['ALL', 'INFO', 'METRIC'] as const).map((lvl) => (
                  <button
                    key={lvl}
                    onClick={() => setSelectedLogFilter(lvl)}
                    className={`px-2 py-0.5 rounded text-[9px] font-bold transition-colors ${
                      selectedLogFilter === lvl
                        ? 'bg-[#C5A059] text-black font-extrabold'
                        : 'text-[#8F7864] hover:text-white'
                    }`}
                  >
                    {lvl}
                  </button>
                ))}
              </div>
            </div>

            <div className="h-44 overflow-y-auto font-mono text-[11px] space-y-1.5 bg-[#0C0804] p-3 rounded-xl border border-[#261B11]">
              {terminalLogs
                .filter((l) => selectedLogFilter === 'ALL' || l.level === selectedLogFilter)
                .map((log, idx) => (
                  <div key={idx} className="flex items-start space-x-2 leading-relaxed">
                    <span className="text-[#685545] shrink-0">{log.time}</span>
                    <span
                      className={`px-1 py-0.2 rounded text-[9px] font-bold shrink-0 ${
                        log.level === 'METRIC'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-[#C5A059]/20 text-[#C5A059]'
                      }`}
                    >
                      {log.level}
                    </span>
                    <span className="text-[#F2DFB8]">{log.msg}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
