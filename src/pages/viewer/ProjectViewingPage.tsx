import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldCheck,
  Download,
  Share2,
  Check,
  AlertTriangle
} from 'lucide-react';
import { api } from '../../services/api';
import { Project } from '../../types';
import { Spatial3DViewer } from '../../components/viewer/Spatial3DViewer';

export const ProjectViewingPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);

  // Check if opened as in-app workspace viewer vs public viewing link
  const isInApp = location.pathname.startsWith('/projects/');

  useEffect(() => {
    if (!projectId) {
      setError('No project ID specified in URL.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    api
      .getProject(projectId)
      .then((data) => {
        setProject(data);
      })
      .catch((err: any) => {
        setError(err.message || 'Project not found or access restricted.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [projectId]);

  const viewingUrl = `${window.location.origin}/view/${projectId}`;

  const handleCopyLink = () => {
    navigator.clipboard.writeText(viewingUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#080a0f] flex items-center justify-center text-slate-200">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-8 h-8 border-2 border-[#dfb873] border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-semibold text-slate-400">Loading spatial project details...</span>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-[#080a0f] flex flex-col items-center justify-center text-slate-200 p-6 text-center">
        <div className="max-w-md bg-[#0d1118] border border-red-900/50 p-6 rounded-2xl space-y-4 shadow-2xl">
          <div className="w-12 h-12 bg-red-950/50 border border-red-800/50 text-red-400 rounded-xl flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-white font-serif-brand">Spatial Project Unavailable</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            {error || `Project ID ${projectId} could not be loaded from the database.`}
          </p>
          <div className="pt-2 flex justify-center gap-3">
            <button
              onClick={() => navigate('/projects')}
              className="px-4 py-2 bg-[#dfb873] hover:bg-[#c9a25b] text-[#0b0f17] font-bold text-xs rounded-xl transition"
            >
              Go to Projects
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#080a0f] text-slate-100 flex flex-col">
      {/* Top Navigation & Project Evidence Header */}
      <header className="h-16 px-4 sm:px-6 bg-[#0d1118]/90 backdrop-blur-xl border-b border-[#dfb873]/20 flex items-center justify-between z-30 shrink-0">
        <div className="flex items-center gap-3 sm:gap-4">
          {isInApp && (
            <button
              onClick={() => navigate(`/projects/${projectId}`)}
              className="p-2 rounded-xl border border-white/10 hover:bg-white/5 text-slate-400 hover:text-white transition-all shadow-xs"
              title="Return to Project Dashboard"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}

          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#dfb873] to-[#9c7834] flex items-center justify-center font-black text-[#0b0f17] text-base shadow-lg shadow-[#dfb873]/10">
              V
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm sm:text-base font-bold text-white font-serif-brand tracking-wide truncate max-w-[200px] sm:max-w-md">
                  {project.name}
                </h1>
                <span className="hidden sm:inline-block font-mono text-[10px] px-2 py-0.5 rounded bg-white/10 text-[#dfb873] border border-[#dfb873]/25 font-semibold">
                  {project.project_code || projectId?.substring(0, 8).toUpperCase()}
                </span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-slate-400">
                <span className="flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400 font-semibold">Evidence-Driven Standard</span>
                </span>
                <span>&bull;</span>
                <span>Spatial Digital Twin</span>
              </div>
            </div>
          </div>
        </div>

        {/* Header Action Buttons */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Shareable Viewing Link Button */}
          <button
            onClick={handleCopyLink}
            className="flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 bg-[#dfb873] hover:bg-[#c9a25b] text-[#0b0f17] font-bold text-xs rounded-xl shadow-lg transition-all active:scale-95"
            title="Copy shareable client viewing link"
          >
            {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-950" /> : <Share2 className="w-3.5 h-3.5" />}
            <span className="hidden xs:inline">{copiedLink ? 'Link Copied!' : 'Copy Viewing Link'}</span>
          </button>

          {/* Export Deliverables Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-slate-200 rounded-xl transition-all"
            >
              <Download className="w-3.5 h-3.5 text-[#dfb873]" />
              <span className="hidden sm:inline">Deliverables</span>
            </button>

            {showExportMenu && (
              <div className="absolute right-0 mt-2 w-64 bg-[#0d1118] border border-[#dfb873]/30 rounded-xl shadow-2xl p-2 z-50 space-y-1">
                <a
                  href={`/renders/${projectId}/textured_mesh.obj`}
                  download={`${project.name}-textured-mesh.obj`}
                  className="flex items-center justify-between px-3 py-2 text-xs text-slate-200 hover:bg-white/5 rounded-lg transition-all"
                >
                  <span>Textured 3D Mesh (.OBJ)</span>
                  <Download className="w-3.5 h-3.5 text-[#dfb873]" />
                </a>
                <a
                  href={`/renders/${projectId}/dense_pointcloud_clean.ply`}
                  download={`${project.name}-pointcloud.ply`}
                  className="flex items-center justify-between px-3 py-2 text-xs text-slate-200 hover:bg-white/5 rounded-lg transition-all"
                >
                  <span>Consensus Point Cloud (.PLY)</span>
                  <Download className="w-3.5 h-3.5 text-[#dfb873]" />
                </a>
                <a
                  href={`/renders/${projectId}/digital_twin_summary.json`}
                  download={`${project.name}-summary.json`}
                  className="flex items-center justify-between px-3 py-2 text-xs text-slate-200 hover:bg-white/5 rounded-lg transition-all"
                >
                  <span>Audit & Metric Summary (.JSON)</span>
                  <Download className="w-3.5 h-3.5 text-[#dfb873]" />
                </a>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main 3D Viewport */}
      <main className="flex-1 relative w-full h-[calc(100vh-4rem)]">
        <Spatial3DViewer
          projectId={projectId}
          modelName={project.name}
          projectCode={project.project_code}
          projectType={project.project_type}
          isStandalone={true}
        />
      </main>
    </div>
  );
};
