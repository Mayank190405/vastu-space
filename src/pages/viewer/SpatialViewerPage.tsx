import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  Box,
  Sparkles,
  Database,
  Layers,
  ShieldCheck,
  Download,
  FolderGit2,
  ChevronDown
} from 'lucide-react';
import { Spatial3DViewer } from '../../components/viewer/Spatial3DViewer';
import { api } from '../../services/api';
import { Project } from '../../types';

export const SpatialViewerPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loadingProjects, setLoadingProjects] = useState<boolean>(true);

  // Fetch project list and auto-select the FIRST project by default
  useEffect(() => {
    let isMounted = true;
    setLoadingProjects(true);
    api
      .listProjects()
      .then((list) => {
        if (!isMounted) return;
        const safeList = Array.isArray(list) ? list : [];
        setProjects(safeList);

        const urlProjId = searchParams.get('projectId');
        if (urlProjId) {
          const match = safeList.find((p) => p.id === urlProjId);
          if (match) {
            setSelectedProject(match);
            return;
          }
        }

        // Auto-select first project by default
        if (safeList.length > 0) {
          setSelectedProject(safeList[0]);
        }
      })
      .catch((err) => {
        console.error('Failed to load projects list for 3D viewer:', err);
        if (isMounted) setProjects([]);
      })
      .finally(() => {
        if (isMounted) setLoadingProjects(false);
      });

    return () => {
      isMounted = false;
    };
  }, [searchParams]);

  const activeProjectId = selectedProject?.id || searchParams.get('projectId') || '';
  const modelUrl =
    searchParams.get('model') ||
    (activeProjectId ? `/renders/${activeProjectId}/textured_mesh.obj` : '');
  const title = selectedProject?.name || searchParams.get('title') || 'VĀSTU Spatial Digital Twin';

  const handleSelectProject = (projectId: string) => {
    const proj = projects.find((p) => p.id === projectId);
    if (proj) {
      setSelectedProject(proj);
      setSearchParams({ projectId: proj.id });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/80 backdrop-blur-md p-6 rounded-2xl border border-[#D9CEBD] shadow-sm">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2.5 rounded-xl border border-[#D9CEBD] text-slate-600 hover:text-slate-900 hover:bg-[#F2ECE1] transition shadow-sm shrink-0"
            title="Go Back"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#C5A059]/15 text-[#8C6D23] border border-[#C5A059]/30">
                <Box className="w-3.5 h-3.5" /> 3D SPATIAL ENGINE
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                <ShieldCheck className="w-3.5 h-3.5" /> Calibrated Metric Evidence
              </span>
            </div>

            <div className="flex items-center gap-3 mt-1.5">
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900 font-serif-brand">
                {title}
              </h1>

              {/* Active Project Badge */}
              {selectedProject && (
                <span className="hidden sm:inline-block font-mono text-[11px] font-extrabold px-2.5 py-0.5 rounded-md bg-[#241A13] text-[#F2DFB8] border border-[#C5A059]/40">
                  {selectedProject.project_code || selectedProject.id.substring(0, 8).toUpperCase()}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Project Selector & Actions */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Project Selector Dropdown */}
          {projects.length > 0 && (
            <div className="flex items-center gap-2">
              <div className="relative">
                <select
                  value={activeProjectId}
                  onChange={(e) => handleSelectProject(e.target.value)}
                  className="appearance-none bg-[#241A13] hover:bg-[#322319] text-[#F2DFB8] font-bold text-xs pl-9 pr-8 py-2.5 rounded-xl border border-[#C5A059]/50 shadow-md focus:outline-none focus:ring-2 focus:ring-[#C5A059] cursor-pointer transition-all"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.project_code || p.id.substring(0, 8).toUpperCase()})
                    </option>
                  ))}
                </select>
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#C5A059]">
                  <FolderGit2 className="w-4 h-4" />
                </div>
                <div className="absolute inset-y-0 right-0 pr-2.5 flex items-center pointer-events-none text-[#C5A059]">
                  <ChevronDown className="w-4 h-4" />
                </div>
              </div>
            </div>
          )}

          {modelUrl && (
            <a
              href={modelUrl}
              download
              className="flex items-center gap-2 px-4 py-2.5 bg-slate-900 hover:bg-black text-white text-xs font-semibold rounded-xl transition shadow-sm"
            >
              <Download className="w-4 h-4" /> Download 3D Model
            </a>
          )}
        </div>
      </div>

      {/* 3D Viewport Component */}
      <div className="w-full">
        <Spatial3DViewer
          key={activeProjectId || 'default-viewer'}
          projectId={activeProjectId || undefined}
          initialModelUrl={modelUrl}
          modelName={title}
          projectCode={selectedProject?.project_code}
          projectType={selectedProject?.project_type}
        />
      </div>

      {/* Feature Information Cards */}
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
