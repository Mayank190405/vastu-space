import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { Project, OrganizationDocument } from '../../types';
import {
  Box,
  FolderGit2,
  Layers,
  HardDrive,
  Plus,
  ArrowRight,
  Sparkles,
  UploadCloud,
  FileSpreadsheet,
  Search,
  Activity,
  Cpu,
  Clock,
  MapPin,
  Compass,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  Building2
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user, activeOrg } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [totalSpaces, setTotalSpaces] = useState<number>(0);
  const [totalObjects, setTotalObjects] = useState<number>(0);
  const [storageText, setStorageText] = useState<string>('0 B');
  const [activeJobs, setActiveJobs] = useState<any[]>([]);
  const [recentActivities, setRecentActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch projects, documents, and join requests from real backend
      const [projs, docs] = await Promise.all([
        api.listProjects().catch(() => [] as Project[]),
        api.listDocuments().catch(() => [] as OrganizationDocument[]),
      ]);

      const safeProjects = Array.isArray(projs) ? projs : [];
      setProjects(safeProjects);

      // Calculate real total spaces count
      let spacesCount = 0;
      safeProjects.forEach((p) => {
        if (p.floors && Array.isArray(p.floors)) {
          spacesCount += p.floors.length;
        } else if (p.total_floors_count) {
          spacesCount += p.total_floors_count;
        }
      });
      setTotalSpaces(spacesCount);

      // Fetch real POIs/objects and jobs for all projects
      let objectsCount = 0;
      const jobsList: any[] = [];
      const activitiesList: any[] = [];

      await Promise.all(
        safeProjects.map(async (p) => {
          try {
            const [pois, jobs] = await Promise.all([
              api.listPOIs(p.id).catch(() => []),
              api.listJobs(p.id).catch(() => []),
            ]);
            if (Array.isArray(pois)) objectsCount += pois.length;
            if (Array.isArray(jobs)) {
              jobs.forEach((j) => {
                if (j.status === 'PROCESSING' || j.status === 'QUEUED' || j.status === 'RUNNING') {
                  jobsList.push({ ...j, projectName: p.name });
                }
              });
            }
          } catch (err) {
            // Ignore individual project fetch errors
          }
        })
      );

      setTotalObjects(objectsCount);
      setActiveJobs(jobsList);

      // Calculate real storage size from uploaded organization documents and files
      let totalBytes = 0;
      if (Array.isArray(docs)) {
        docs.forEach((d) => {
          if (d.file_size) totalBytes += d.file_size;
        });
      }
      if (totalBytes === 0) {
        setStorageText('0 B');
      } else if (totalBytes < 1024 * 1024) {
        setStorageText(`${(totalBytes / 1024).toFixed(1)} KB`);
      } else if (totalBytes < 1024 * 1024 * 1024) {
        setStorageText(`${(totalBytes / (1024 * 1024)).toFixed(1)} MB`);
      } else {
        setStorageText(`${(totalBytes / (1024 * 1024 * 1024)).toFixed(2)} GB`);
      }

      // Generate real activity items from projects
      safeProjects.forEach((p) => {
        if (p.updated_at) {
          activitiesList.push({
            id: p.id,
            title: `Project "${p.name}" updated`,
            subtitle: `${p.project_type || 'Spatial Model'} · ${p.address?.city || 'Location registered'}`,
            timestamp: p.updated_at,
            type: 'project',
          });
        }
      });
      activitiesList.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      setRecentActivities(activitiesList.slice(0, 5));
    } catch (err: any) {
      console.error('Error fetching spatial dashboard data:', err);
      setError(err.message || 'Unable to load spatial dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeOrg) {
      fetchDashboardData();
    }
  }, [activeOrg]);

  // Determine time of day greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  // Format relative timestamp
  const formatRelativeTime = (isoString?: string) => {
    if (!isoString) return 'Recently';
    const date = new Date(isoString);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (diffSec < 60) return 'Just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)} minutes ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} hours ago`;
    if (diffSec < 172800) return 'Yesterday';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  // Determine Continue Working space
  const latestProject = projects.length > 0 ? projects[0] : null;

  return (
    <div className="space-y-8">
      {/* 6. WELCOME HEADER (Compact Vertical Footprint) */}
      <div className="relative overflow-hidden rounded-3xl p-6 bg-gradient-to-r from-[#241A13] via-[#2E2016] to-[#3D2C1F] border border-[#C5A059]/40 shadow-xl text-[#F7F2EA]">
        <div className="absolute top-0 right-0 w-80 h-80 bg-[#C5A059]/10 blur-[100px] rounded-full pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-serif-brand">
              {getGreeting()}, {user?.full_name || 'Architect'}
            </h1>
            <p className="text-xs text-[#D9CAB8] font-medium">
              Manage, explore and understand your physical spaces.
            </p>
          </div>

          <div className="flex items-center space-x-3 shrink-0">
            <Link
              to="/viewer"
              className="px-4 py-2 rounded-xl bg-[#2A1E14] hover:bg-[#36271C] border border-[#C5A059]/40 text-[#F2DFB8] text-xs font-bold transition-all flex items-center space-x-1.5 shadow-sm"
            >
              <Compass className="w-3.5 h-3.5 text-[#C5A059]" />
              <span>Open Spatial Viewer</span>
            </Link>

            <Link
              to="/projects/create"
              className="btn-brand-primary py-2 px-4 rounded-xl text-xs font-bold flex items-center space-x-1.5 shadow-md hover:shadow-lg transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>New Capture</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Error state alert */}
      {error && (
        <div className="p-4 rounded-2xl bg-red-950/70 border border-red-800 flex items-center justify-between text-red-200 text-xs shadow-md">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchDashboardData}
            className="px-3 py-1 bg-red-900/60 hover:bg-red-900 text-white rounded-lg font-bold flex items-center space-x-1 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* 7. SPATIAL SUMMARY CARDS (4 CARDS) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* CARD 1: PROJECTS */}
        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm relative overflow-hidden group">
          <div className="flex justify-between items-center text-[#5C4A38] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider text-[#8F7864]">Projects</span>
            <FolderGit2 className="w-4 h-4 text-[#8F6834]" />
          </div>
          {loading ? (
            <div className="text-2xl font-bold text-[#8F7864] animate-pulse">████</div>
          ) : (
            <div className="text-3xl font-black text-[#1F150D] font-serif-brand">{projects.length}</div>
          )}
          <span className="text-[11px] text-[#6E5945] font-medium mt-1 block">Active spatial workspaces</span>
        </div>

        {/* CARD 2: SPACES */}
        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm relative overflow-hidden group">
          <div className="flex justify-between items-center text-[#5C4A38] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider text-[#8F7864]">Spaces</span>
            <Layers className="w-4 h-4 text-[#8F6834]" />
          </div>
          {loading ? (
            <div className="text-2xl font-bold text-[#8F7864] animate-pulse">████</div>
          ) : (
            <div className="text-3xl font-black text-[#1F150D] font-serif-brand">{totalSpaces}</div>
          )}
          <span className="text-[11px] text-[#6E5945] font-medium mt-1 block font-mono">Floors & scanned rooms</span>
        </div>

        {/* CARD 3: SPATIAL OBJECTS */}
        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm relative overflow-hidden group">
          <div className="flex justify-between items-center text-[#5C4A38] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider text-[#8F7864]">Spatial Objects</span>
            <Box className="w-4 h-4 text-[#8F6834]" />
          </div>
          {loading ? (
            <div className="text-2xl font-bold text-[#8F7864] animate-pulse">████</div>
          ) : (
            <div className="text-3xl font-black text-[#1F150D] font-serif-brand">{totalObjects}</div>
          )}
          <span className="text-[11px] text-[#6E5945] font-medium mt-1 block font-mono">3D assets & waypoints</span>
        </div>

        {/* CARD 4: STORAGE */}
        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm relative overflow-hidden group">
          <div className="flex justify-between items-center text-[#5C4A38] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider text-[#8F7864]">Storage</span>
            <HardDrive className="w-4 h-4 text-[#8F6834]" />
          </div>
          {loading ? (
            <div className="text-2xl font-bold text-[#8F7864] animate-pulse">████</div>
          ) : (
            <div className="text-3xl font-black text-[#1F150D] font-serif-brand">{storageText}</div>
          )}
          <span className="text-[11px] text-[#6E5945] font-medium mt-1 block font-mono">Digital twin & model data</span>
        </div>
      </div>

      {/* 8. RECENT SPATIAL PROJECTS (LARGEST & MOST IMPORTANT SECTION) */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold text-[#1F150D] font-serif-brand tracking-wide">
              Recent Spatial Projects
            </h2>
            <p className="text-xs text-[#5C4A38] font-medium">
              Explore your digital twins and physical environment models.
            </p>
          </div>
          <Link
            to="/projects"
            className="text-xs font-bold text-[#8F6834] hover:text-[#2E2016] flex items-center space-x-1 transition-colors"
          >
            <span>View all</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="glass-panel p-5 rounded-2xl border border-[#C5A059]/30 space-y-4 animate-pulse">
                <div className="w-full h-40 bg-[#E8DEC9] rounded-xl" />
                <div className="h-4 w-3/4 bg-[#E8DEC9] rounded" />
                <div className="h-3 w-1/2 bg-[#E8DEC9] rounded" />
              </div>
            ))}
          </div>
        ) : projects.length === 0 ? (
          /* HONEST EMPTY STATE */
          <div className="glass-panel p-12 rounded-3xl border border-[#C5A059]/30 text-center space-y-4 shadow-md bg-[#FAF7F2]">
            <div className="w-16 h-16 rounded-2xl bg-[#EDE6DB] border border-[#C5A059]/40 flex items-center justify-center mx-auto text-[#8F6834]">
              <Box className="w-8 h-8" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-[#1F150D] font-serif-brand">No spatial projects yet</h3>
              <p className="text-xs text-[#695541] max-w-md mx-auto leading-relaxed">
                Your spatial workspace is ready. Create a project to start managing digital twins and physical 3D spaces.
              </p>
            </div>
            <div className="flex items-center justify-center space-x-3 pt-2">
              <Link
                to="/projects/create"
                className="btn-brand-primary py-2.5 px-5 rounded-xl text-xs font-bold flex items-center space-x-2 shadow-md"
              >
                <Plus className="w-4 h-4" />
                <span>Create Your First Project</span>
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.slice(0, 6).map((proj) => {
              const statusPillColor =
                proj.status === 'READY' || proj.status === 'ACTIVE'
                  ? 'bg-emerald-950/40 text-emerald-700 border-emerald-600/40'
                  : proj.status === 'PROCESSING'
                  ? 'bg-amber-950/40 text-amber-700 border-amber-600/40'
                  : 'bg-[#EDE6DB] text-[#8F6834] border-[#C5A059]/50';

              return (
                <div
                  key={proj.id}
                  className="glass-panel p-5 rounded-2xl border border-[#C5A059]/35 hover:border-[#C5A059] transition-all shadow-sm hover:shadow-lg flex flex-col justify-between space-y-4 group bg-white/70"
                >
                  <div className="space-y-3">
                    {/* Project Preview */}
                    <div className="relative w-full h-44 rounded-xl overflow-hidden bg-[#241A13] border border-[#C5A059]/30 flex items-center justify-center group-hover:border-[#C5A059] transition-colors">
                      {proj.cover_image_url ? (
                        <img
                          src={proj.cover_image_url}
                          alt={proj.name}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      ) : (
                        <div className="text-center p-4 space-y-2">
                          <Building2 className="w-8 h-8 text-[#C5A059] mx-auto opacity-70" />
                          <span className="text-[11px] text-[#A6998A] font-semibold block">
                            No spatial preview available
                          </span>
                        </div>
                      )}

                      {/* Status Pill */}
                      <div className="absolute top-3 right-3">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider uppercase border shadow-sm ${statusPillColor}`}>
                          ● {proj.status || 'READY'}
                        </span>
                      </div>
                    </div>

                    {/* Meta info */}
                    <div>
                      <h3 className="text-base font-bold text-[#1F150D] font-serif-brand group-hover:text-[#8F6834] transition-colors truncate">
                        {proj.name}
                      </h3>
                      <div className="flex items-center space-x-2 text-xs text-[#5C4A38] mt-1 font-medium truncate">
                        <MapPin className="w-3.5 h-3.5 text-[#8F6834] shrink-0" />
                        <span className="truncate">
                          {proj.address?.city ? `${proj.address.city}, ${proj.address.state || 'IN'}` : proj.project_type || 'Spatial Model'}
                        </span>
                      </div>
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#E8DEC9] text-[11px] text-[#5C4A38] font-semibold">
                      <div>
                        <span className="text-[#8F7864] block text-[10px] uppercase font-bold">Structure</span>
                        <span>{proj.total_floors_count || proj.floors?.length || 1} Floors</span>
                      </div>
                      <div>
                        <span className="text-[#8F7864] block text-[10px] uppercase font-bold">Updated</span>
                        <span>{formatRelativeTime(proj.updated_at)}</span>
                      </div>
                    </div>
                  </div>

                  <Link
                    to={`/projects/${proj.id}`}
                    className="btn-brand-primary w-full py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all group-hover:shadow-md"
                  >
                    <span>Open Project</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 10. CONTINUE WORKING & 11. SPATIAL PROCESSING (2-COLUMN GRID) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CONTINUE WORKING */}
        <div className="glass-panel p-6 rounded-2xl border border-[#C5A059]/35 space-y-4 bg-white/70 shadow-sm flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-[#E8DEC9] pb-3">
              <h3 className="text-sm font-bold text-[#1F150D] font-serif-brand flex items-center space-x-2">
                <Clock className="w-4 h-4 text-[#8F6834]" />
                <span>Continue Working</span>
              </h3>
              <span className="text-[10px] font-bold text-[#8F7864] uppercase tracking-wider">Recent Activity</span>
            </div>

            {latestProject ? (
              <div className="p-4 rounded-xl bg-[#FAF7F2] border border-[#C5A059]/30 space-y-2">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="text-sm font-bold text-[#1F150D]">{latestProject.name}</h4>
                    <p className="text-xs text-[#5C4A38]">
                      {latestProject.project_type || 'Spatial Model'} · {latestProject.address?.city || 'Location registered'}
                    </p>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-[#EDE6DB] border border-[#C5A059]/40 text-[#8F6834] font-bold">
                    Last viewed {formatRelativeTime(latestProject.updated_at)}
                  </span>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-xs text-[#8F7864] italic">
                No recent spaces viewed.
              </div>
            )}
          </div>

          {latestProject ? (
            <Link
              to={`/projects/${latestProject.id}/viewer`}
              className="btn-brand-primary w-full py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all mt-2"
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Open Digital Twin →</span>
            </Link>
          ) : (
            <Link
              to="/projects"
              className="btn-brand-secondary w-full py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all mt-2"
            >
              <span>Browse Projects →</span>
            </Link>
          )}
        </div>

        {/* SPATIAL PROCESSING CENTER */}
        <div className="glass-panel p-6 rounded-2xl border border-[#C5A059]/35 space-y-4 bg-white/70 shadow-sm flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-[#E8DEC9] pb-3">
              <h3 className="text-sm font-bold text-[#1F150D] font-serif-brand flex items-center space-x-2">
                <Cpu className="w-4 h-4 text-[#8F6834]" />
                <span>Spatial Processing Center</span>
              </h3>
              <span className="text-[10px] font-bold text-[#8F7864] uppercase tracking-wider">Pipeline Status</span>
            </div>

            {activeJobs.length > 0 ? (
              <div className="space-y-2">
                {activeJobs.map((job) => (
                  <div key={job.id} className="p-3.5 rounded-xl bg-[#FAF7F2] border border-[#C5A059]/30 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-bold text-[#1F150D]">{job.projectName}</div>
                      <div className="text-[10px] text-[#5C4A38]">Stage: {job.stage || 'Reconstructing spatial model...'}</div>
                    </div>
                    <span className="px-2 py-1 rounded-full bg-amber-950/30 border border-amber-600/40 text-amber-700 text-[10px] font-bold animate-pulse">
                      PROCESSING
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center space-y-1">
                <CheckCircle2 className="w-6 h-6 text-emerald-600 mx-auto" />
                <div className="text-xs font-bold text-[#1F150D]">No active processing jobs</div>
                <div className="text-[10px] text-[#695541]">All spatial reconstruction pipelines are idle or complete.</div>
              </div>
            )}
          </div>

          {activeJobs.length > 0 && (
            <Link
              to={`/projects/${activeJobs[0].project_id || ''}`}
              className="btn-brand-primary w-full py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all mt-2"
            >
              <span>View Processing →</span>
            </Link>
          )}
        </div>
      </div>

      {/* 12. RECENT ACTIVITY (FULL-WIDTH SECTION) */}
      <div className="glass-panel p-6 rounded-2xl border border-[#C5A059]/35 space-y-4 bg-white/70 shadow-sm">
        <div className="flex items-center justify-between border-b border-[#E8DEC9] pb-3">
          <h3 className="text-sm font-bold text-[#1F150D] font-serif-brand flex items-center space-x-2">
            <Activity className="w-4 h-4 text-[#8F6834]" />
            <span>Recent Activity</span>
          </h3>
          <span className="text-[10px] font-bold text-[#8F7864] uppercase tracking-wider">Audit Log</span>
        </div>

        {recentActivities.length === 0 ? (
          <div className="py-6 text-center text-xs text-[#8F7864] italic">
            No recent activity recorded in your workspace.
          </div>
        ) : (
          <div className="divide-y divide-[#E8DEC9]">
            {recentActivities.map((act) => (
              <div key={act.id} className="py-3 flex items-center justify-between first:pt-0 last:pb-0">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 rounded-full bg-[#C5A059] shrink-0" />
                  <div>
                    <div className="text-xs font-bold text-[#1F150D]">{act.title}</div>
                    <div className="text-[10px] text-[#5C4A38]">{act.subtitle}</div>
                  </div>
                </div>
                <span className="text-[10px] font-bold text-[#8F7864]">
                  {formatRelativeTime(act.timestamp)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 13. QUICK ACTIONS SECTION */}
      <div className="glass-panel p-6 rounded-2xl border border-[#C5A059]/35 space-y-4 bg-white/70 shadow-sm">
        <h3 className="text-sm font-bold text-[#1F150D] font-serif-brand">Quick Actions</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <Link
            to="/projects/create"
            className="p-3.5 rounded-xl bg-[#FAF7F2] hover:bg-[#F2EBDC] border border-[#C5A059]/40 text-center space-y-1.5 transition-all group shadow-sm hover:shadow"
          >
            <Plus className="w-5 h-5 text-[#8F6834] mx-auto group-hover:scale-110 transition-transform" />
            <div className="text-xs font-bold text-[#1F150D]">New Capture</div>
          </Link>

          <Link
            to="/projects/create"
            className="p-3.5 rounded-xl bg-[#FAF7F2] hover:bg-[#F2EBDC] border border-[#C5A059]/40 text-center space-y-1.5 transition-all group shadow-sm hover:shadow"
          >
            <UploadCloud className="w-5 h-5 text-[#8F6834] mx-auto group-hover:scale-110 transition-transform" />
            <div className="text-xs font-bold text-[#1F150D]">Upload Scan</div>
          </Link>

          <Link
            to="/viewer"
            className="p-3.5 rounded-xl bg-[#FAF7F2] hover:bg-[#F2EBDC] border border-[#C5A059]/40 text-center space-y-1.5 transition-all group shadow-sm hover:shadow"
          >
            <Compass className="w-5 h-5 text-[#8F6834] mx-auto group-hover:scale-110 transition-transform" />
            <div className="text-xs font-bold text-[#1F150D]">Open Viewer</div>
          </Link>

          <Link
            to="/projects/create"
            className="p-3.5 rounded-xl bg-[#FAF7F2] hover:bg-[#F2EBDC] border border-[#C5A059]/40 text-center space-y-1.5 transition-all group shadow-sm hover:shadow"
          >
            <FileSpreadsheet className="w-5 h-5 text-[#8F6834] mx-auto group-hover:scale-110 transition-transform" />
            <div className="text-xs font-bold text-[#1F150D]">Import Floor Plan</div>
          </Link>

          <Link
            to="/projects/create"
            className="p-3.5 rounded-xl bg-[#FAF7F2] hover:bg-[#F2EBDC] border border-[#C5A059]/40 text-center space-y-1.5 transition-all group shadow-sm hover:shadow"
          >
            <FolderGit2 className="w-5 h-5 text-[#8F6834] mx-auto group-hover:scale-110 transition-transform" />
            <div className="text-xs font-bold text-[#1F150D]">Create Project</div>
          </Link>

          <Link
            to="/projects"
            className="p-3.5 rounded-xl bg-[#FAF7F2] hover:bg-[#F2EBDC] border border-[#C5A059]/40 text-center space-y-1.5 transition-all group shadow-sm hover:shadow"
          >
            <Search className="w-5 h-5 text-[#8F6834] mx-auto group-hover:scale-110 transition-transform" />
            <div className="text-xs font-bold text-[#1F150D]">Search Spaces</div>
          </Link>
        </div>
      </div>
    </div>
  );
};
;
