import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FolderGit2,
  Plus,
  Search,
  Building2,
  MapPin,
  Layers,
  ArrowRight,
  Loader2,
  AlertCircle,
  Box,
  Share2,
  Copy,
  Check
} from 'lucide-react';
import { api } from '../../services/api';
import { Project } from '../../types';

export const ProjectsPage: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyViewingLink = (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation();
    const url = `${window.location.origin}/view/${projectId}`;
    navigator.clipboard.writeText(url);
    setCopiedId(projectId);
    setTimeout(() => setCopiedId(null), 2500);
  };

  const fetchProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listProjects();
      setProjects(data || []);
    } catch (err: any) {
      console.error('Failed to load projects:', err);
      setError(err.message || 'Failed to load projects from backend');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const filtered = projects.filter((p) => {
    const q = searchQuery.toLowerCase();
    return (
      p.name?.toLowerCase().includes(q) ||
      p.project_type?.toLowerCase().includes(q) ||
      p.address?.city?.toLowerCase().includes(q) ||
      p.project_code?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#1F150D] flex items-center space-x-2 font-serif-brand">
            <FolderGit2 className="w-5 h-5 text-[#8F6834]" />
            <span>Spatial Twin Projects</span>
          </h1>
          <p className="text-xs text-[#695541] mt-0.5">
            Manage LiDAR captures, photogrammetry models, BIM digital twins, and multi-floor buildings.
          </p>
        </div>

        <button
          onClick={() => navigate('/projects/create')}
          className="btn-brand-primary py-2 px-4 rounded-xl text-xs font-bold flex items-center space-x-2 self-start sm:self-auto shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>New Spatial Project</span>
        </button>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#8F6834] pointer-events-none" />
        <input
          type="text"
          placeholder="Filter by project name, structure type, city..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-[#FAF7F2] border border-[#D1C2A5] rounded-xl text-xs text-[#1F150D] placeholder-[#A09384] focus:outline-none focus:ring-2 focus:ring-[#8F6834]/30 focus:border-[#8F6834] transition-all shadow-xs"
        />
      </div>

      {/* Error Notice */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-800 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[300px] space-y-3">
          <Loader2 className="w-8 h-8 text-[#8F6834] animate-spin" />
          <p className="text-xs text-[#695541]">Retrieving live projects from spatial database...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-[#FAF7F2] border border-dashed border-[#D1C2A5] rounded-2xl p-12 text-center max-w-md mx-auto space-y-4 shadow-xs">
          <div className="w-12 h-12 rounded-full bg-[#FAF3E0] text-[#8F6834] flex items-center justify-center mx-auto">
            <Building2 className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#1F150D]">No Spatial Twin Projects Found</h3>
            <p className="text-xs text-[#695541] mt-1">
              {searchQuery
                ? 'No projects matching your search query.'
                : 'Get started by creating your first multi-floor or single-level digital twin project.'}
            </p>
          </div>
          <button
            onClick={() => navigate('/projects/create')}
            className="btn-brand-primary py-2 px-4 rounded-xl text-xs font-bold inline-flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Create First Project</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((proj) => (
            <div
              key={proj.id}
              onClick={() => navigate(`/projects/${proj.id}`)}
              className="bg-[#FAF7F2] border border-[#D1C2A5] hover:border-[#8F6834] rounded-2xl overflow-hidden shadow-xs hover:shadow-md transition-all cursor-pointer group flex flex-col"
            >
              {/* Cover Banner */}
              <div className="h-36 bg-gradient-to-r from-[#5C4223] to-[#8F6834] relative overflow-hidden">
                {proj.cover_image_url ? (
                  <img
                    src={proj.cover_image_url}
                    alt={proj.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-white/40">
                    <Building2 className="w-12 h-12" />
                  </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                <div className="absolute top-3 right-3">
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                      proj.status === 'ACTIVE'
                        ? 'bg-emerald-500/90 text-white'
                        : 'bg-amber-500/90 text-white'
                    }`}
                  >
                    {proj.status || 'ACTIVE'}
                  </span>
                </div>
                <div className="absolute bottom-2 left-3 right-3 text-white">
                  <span className="text-[10px] uppercase font-semibold tracking-wider text-[#E3DACA]">
                    {proj.project_type || 'Building'}
                  </span>
                  <h3 className="text-sm font-bold truncate text-white">
                    {proj.name}
                  </h3>
                </div>
              </div>

              {/* Card Body */}
              <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                <div className="space-y-2">
                  {proj.address && (
                    <div className="flex items-center gap-1.5 text-xs text-[#5C4D3E]">
                      <MapPin className="w-3.5 h-3.5 text-[#8F6834] shrink-0" />
                      <span className="truncate">
                        {proj.address.city}, {proj.address.state}
                      </span>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs text-[#7C6652] pt-1">
                    <span className="flex items-center gap-1">
                      <Layers className="w-3.5 h-3.5 text-[#8F6834]" />
                      <span>{proj.floors?.length || proj.total_floors_count || 1} Levels</span>
                    </span>
                    <span className="font-mono text-[11px] font-medium text-[#1F150D]">
                      {proj.total_area_sqft ? `${proj.total_area_sqft.toLocaleString()} sqft` : '—'}
                    </span>
                  </div>
                </div>

                <div className="pt-2.5 border-t border-[#EAE2D3] flex items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/projects/${proj.id}/viewer`);
                      }}
                      className="flex items-center gap-1 px-2.5 py-1 bg-[#8F6834]/15 hover:bg-[#8F6834] text-[#8F6834] hover:text-white font-bold rounded-lg transition-all text-[11px]"
                      title="Open 3D Spatial Twin Studio"
                    >
                      <Box className="w-3 h-3" />
                      <span>3D Twin</span>
                    </button>

                    <button
                      onClick={(e) => handleCopyViewingLink(e, proj.id)}
                      className="flex items-center gap-1 px-2.5 py-1 bg-white hover:bg-[#FAF7F2] border border-[#D1C2A5] text-[#5C4D3E] hover:text-[#1F150D] font-semibold rounded-lg transition-all text-[11px]"
                      title="Copy public client viewing link"
                    >
                      {copiedId === proj.id ? (
                        <Check className="w-3 h-3 text-emerald-600" />
                      ) : (
                        <Share2 className="w-3 h-3 text-[#8F6834]" />
                      )}
                      <span>{copiedId === proj.id ? 'Copied' : 'Link'}</span>
                    </button>
                  </div>

                  <span className="flex items-center gap-1 font-semibold text-[#8F6834] group-hover:text-[#755427] transition-colors text-[11px]">
                    <span>Workspace</span>
                    <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
