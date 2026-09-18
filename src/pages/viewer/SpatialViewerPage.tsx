import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Box, Sparkles, Database, Layers, ShieldCheck, Download } from 'lucide-react';
import { Spatial3DViewer } from '../../components/viewer/Spatial3DViewer';

export const SpatialViewerPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const modelUrl = searchParams.get('model') || '/models/dense_pointcloud.ply';
  const title = searchParams.get('title') || 'VĀSTU Spatial Digital Twin';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white/80 backdrop-blur-md p-6 rounded-2xl border border-[#D9CEBD] shadow-sm">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2.5 rounded-xl border border-[#D9CEBD] text-slate-600 hover:text-slate-900 hover:bg-[#F2ECE1] transition shadow-sm"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#C5A059]/15 text-[#8C6D23] border border-[#C5A059]/30">
                <Box className="w-3.5 h-3.5" /> 3D SPATIAL ENGINE
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                <ShieldCheck className="w-3.5 h-3.5" /> Calibrated Metric Evidence
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-1">{title}</h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <a
            href="http://localhost:9000/vastu-artifacts/models/dense_pointcloud.ply"
            download
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-900 hover:bg-black text-white text-xs font-semibold rounded-xl transition shadow-sm"
          >
            <Download className="w-4 h-4" /> Download Raw PLY
          </a>
        </div>
      </div>

      {/* 3D Viewport */}
      <div className="w-full">
        <Spatial3DViewer initialModelUrl={modelUrl} modelName={title} />
      </div>

      {/* Feature & Pipeline Information Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white/80 backdrop-blur-md p-5 rounded-2xl border border-[#D9CEBD] shadow-sm">
          <div className="flex items-center gap-3 text-slate-900 font-bold mb-2">
            <div className="p-2 bg-[#C5A059]/20 text-[#8C6D23] rounded-lg">
              <Layers className="w-5 h-5" />
            </div>
            Multi-Modal Geometry
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Switch seamlessly between dense 75,000+ point clouds, wireframe topological surfaces, and watertight architectural triangle meshes.
          </p>
        </div>

        <div className="bg-white/80 backdrop-blur-md p-5 rounded-2xl border border-[#D9CEBD] shadow-sm">
          <div className="flex items-center gap-3 text-slate-900 font-bold mb-2">
            <div className="p-2 bg-blue-100 text-blue-800 rounded-lg">
              <Sparkles className="w-5 h-5" />
            </div>
            Real-Time 3D Measurement
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Click any two physical points on the floor or wall to compute direct Euclidean span and clearance with millimeter-level laser calibration.
          </p>
        </div>

        <div className="bg-white/80 backdrop-blur-md p-5 rounded-2xl border border-[#D9CEBD] shadow-sm">
          <div className="flex items-center gap-3 text-slate-900 font-bold mb-2">
            <div className="p-2 bg-emerald-100 text-emerald-800 rounded-lg">
              <Database className="w-5 h-5" />
            </div>
            MinIO S3 Connected
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            All 3D assets stream securely from MinIO Object Storage bucket <code className="bg-slate-100 px-1 py-0.5 rounded font-mono text-[11px]">vastu-artifacts</code>.
          </p>
        </div>
      </div>
    </div>
  );
};
