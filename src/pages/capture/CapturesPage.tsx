import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { Capture, Project, ProjectFloor } from '../../types';
import {
  Layers3,
  Plus,
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  HardDrive,
  Box,
  Compass,
  ArrowRight,
  X,
  FileSpreadsheet,
  ScanLine,
  SlidersHorizontal,
  ChevronRight,
  Database,
  Smartphone,
  Info,
  FolderGit2
} from 'lucide-react';

export const CapturesPage: React.FC = () => {
  const { activeOrg } = useAuth();
  const navigate = useNavigate();

  const [projects, setProjects] = useState<Project[]>([]);
  const [captures, setCaptures] = useState<Capture[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('ALL');
  const [selectedProjectFilter, setSelectedProjectFilter] = useState<string>('ALL');
  const [selectedMethodFilter, setSelectedMethodFilter] = useState<string>('ALL');
  const [showFiltersPanel, setShowFiltersPanel] = useState(false);

  // New Capture Modal State
  const [newCaptureModalOpen, setNewCaptureModalOpen] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [projectFloors, setProjectFloors] = useState<ProjectFloor[]>([]);
  const [selectedLevelId, setSelectedLevelId] = useState<string>('');
  const [captureMethod, setCaptureMethod] = useState<string>('rgb_lidar');
  const [notes, setNotes] = useState('');
  const [creatingCapture, setCreatingCapture] = useState(false);
  const [creationError, setCreationError] = useState<string | null>(null);

  // Capture Detail Modal/Drawer State
  const [activeCaptureDetail, setActiveCaptureDetail] = useState<Capture | null>(null);

  const fetchCapturesData = async () => {
    try {
      setLoading(true);
      setError(null);
      const projs = await api.listProjects().catch(() => [] as Project[]);
      const safeProjects = Array.isArray(projs) ? projs : [];
      setProjects(safeProjects);

      if (safeProjects.length > 0 && !selectedProjectId) {
        setSelectedProjectId(safeProjects[0].id);
      }

      const allCaptures = await api.listAllCaptures(safeProjects);
      setCaptures(Array.isArray(allCaptures) ? allCaptures : []);
    } catch (err: any) {
      console.error('Error fetching captures data:', err);
      setError(err.message || 'Unable to load spatial capture records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeOrg) {
      fetchCapturesData();
    }
  }, [activeOrg]);

  // Load floors when selected project changes in modal
  useEffect(() => {
    if (selectedProjectId) {
      api.listFloors(selectedProjectId)
        .then((floors) => {
          setProjectFloors(Array.isArray(floors) ? floors : []);
          if (floors && floors.length > 0) {
            setSelectedLevelId(floors[0].id);
          } else {
            setSelectedLevelId('');
          }
        })
        .catch(() => {
          setProjectFloors([]);
          setSelectedLevelId('');
        });
    }
  }, [selectedProjectId]);

  const handleCreateCaptureSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) {
      setCreationError('Please select a target project.');
      return;
    }
    try {
      setCreatingCapture(true);
      setCreationError(null);

      const newCap = await api.createCaptureSession({
        project_id: selectedProjectId,
        level_id: selectedLevelId || undefined,
        device_model: navigator.userAgent.includes('Mobile') ? 'Mobile Device' : 'Web Workstation',
        has_lidar: captureMethod.includes('lidar'),
        capture_mode: captureMethod,
        notes: notes || 'Spatial scan session',
      });

      setNewCaptureModalOpen(false);
      setNotes('');
      fetchCapturesData();

      // Open detail drawer for newly created capture
      if (newCap) {
        setActiveCaptureDetail(newCap);
      }
    } catch (err: any) {
      console.error('Error creating capture session:', err);
      setCreationError(err.message || 'Failed to initiate capture session.');
    } finally {
      setCreatingCapture(false);
    }
  };

  // Status Filter Counts
  const totalCapturesCount = captures.length;
  const processingCount = captures.filter(
    (c) =>
      c.status === 'processing' ||
      c.status === 'recording' ||
      c.status === 'uploaded' ||
      c.status === 'validating' ||
      c.status === 'PROCESSING' ||
      c.status === 'UPLOADING'
  ).length;
  const completedCount = captures.filter((c) => c.status === 'completed' || c.status === 'COMPLETED').length;
  const failedCount = captures.filter((c) => c.status === 'failed' || c.status === 'FAILED').length;

  // Filtered Captures
  const filteredCaptures = captures.filter((c) => {
    // Status Filter
    if (selectedStatusFilter !== 'ALL') {
      const s = c.status?.toUpperCase() || '';
      if (selectedStatusFilter === 'DRAFT' && s !== 'RECORDING' && s !== 'DRAFT') return false;
      if (selectedStatusFilter === 'UPLOADING' && s !== 'UPLOADING' && s !== 'UPLOADED') return false;
      if (selectedStatusFilter === 'QUEUED' && s !== 'VALIDATING' && s !== 'QUEUED') return false;
      if (selectedStatusFilter === 'PROCESSING' && s !== 'PROCESSING') return false;
      if (selectedStatusFilter === 'COMPLETED' && s !== 'COMPLETED') return false;
      if (selectedStatusFilter === 'FAILED' && s !== 'FAILED') return false;
    }

    // Project Filter
    if (selectedProjectFilter !== 'ALL' && c.project_id !== selectedProjectFilter) {
      return false;
    }

    // Method Filter
    if (selectedMethodFilter !== 'ALL' && c.capture_mode !== selectedMethodFilter) {
      return false;
    }

    // Search Query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = c.notes?.toLowerCase().includes(q);
      const matchId = c.id?.toLowerCase().includes(q);
      const matchProject = c.project_name?.toLowerCase().includes(q);
      const matchMode = c.capture_mode?.toLowerCase().includes(q);
      if (!matchName && !matchId && !matchProject && !matchMode) return false;
    }

    return true;
  });

  // Format File Size
  const formatFileSize = (bytes?: number) => {
    if (!bytes || bytes === 0) return '—';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  // Format Timestamp
  const formatTime = (isoString?: string) => {
    if (!isoString) return '—';
    const d = new Date(isoString);
    return `${d.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' })} · ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  };

  return (
    <div className="space-y-8">
      {/* 3. PAGE HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#C5A059]/30 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#1F150D] font-serif-brand">
            CAPTURES
          </h1>
          <p className="text-xs text-[#695541] font-medium mt-1">
            Capture and process spatial data from physical environments.
          </p>
        </div>

        {/* PRIMARY ACTION: New Capture */}
        <button
          onClick={() => setNewCaptureModalOpen(true)}
          className="btn-brand-primary py-2.5 px-5 rounded-xl text-xs font-bold flex items-center space-x-2 shadow-md hover:shadow-lg transition-all shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>New Capture</span>
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-2xl bg-red-950/70 border border-red-800 flex items-center justify-between text-red-200 text-xs shadow-md">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchCapturesData}
            className="px-3 py-1 bg-red-900/60 hover:bg-red-900 text-white rounded-lg font-bold flex items-center space-x-1 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* 5. SUMMARY STATISTICS (4 CARDS) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm">
          <div className="flex justify-between items-center text-[#8F7864] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider">Total Captures</span>
            <Layers3 className="w-4 h-4 text-[#8F6834]" />
          </div>
          {loading ? (
            <div className="text-2xl font-bold text-[#8F7864] animate-pulse">████</div>
          ) : (
            <div className="text-3xl font-black text-[#1F150D] font-serif-brand">{totalCapturesCount}</div>
          )}
          <span className="text-[11px] text-[#695541] font-medium mt-1 block">Registered scan sessions</span>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm">
          <div className="flex justify-between items-center text-[#8F7864] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider">Processing</span>
            <RefreshCw className="w-4 h-4 text-amber-600 animate-spin" />
          </div>
          {loading ? (
            <div className="text-2xl font-bold text-[#8F7864] animate-pulse">████</div>
          ) : (
            <div className="text-3xl font-black text-amber-700 font-serif-brand">{processingCount}</div>
          )}
          <span className="text-[11px] text-[#695541] font-medium mt-1 block">Active pipeline jobs</span>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm">
          <div className="flex justify-between items-center text-[#8F7864] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider">Completed</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          {loading ? (
            <div className="text-2xl font-bold text-[#8F7864] animate-pulse">████</div>
          ) : (
            <div className="text-3xl font-black text-emerald-800 font-serif-brand">{completedCount}</div>
          )}
          <span className="text-[11px] text-[#695541] font-medium mt-1 block">Digital twin models ready</span>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm">
          <div className="flex justify-between items-center text-[#8F7864] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider">Failed</span>
            <AlertCircle className="w-4 h-4 text-red-600" />
          </div>
          {loading ? (
            <div className="text-2xl font-bold text-[#8F7864] animate-pulse">████</div>
          ) : (
            <div className="text-3xl font-black text-red-800 font-serif-brand">{failedCount}</div>
          )}
          <span className="text-[11px] text-[#695541] font-medium mt-1 block">Validation / pipeline errors</span>
        </div>
      </div>

      {/* 6. CAPTURE STATUS FILTER BAR */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-1 scrollbar-none">
        {['ALL', 'DRAFT', 'UPLOADING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'].map((st) => {
          const isActive = selectedStatusFilter === st;
          return (
            <button
              key={st}
              onClick={() => setSelectedStatusFilter(st)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
                isActive
                  ? 'bg-[#C5A059] text-[#1F150D] shadow-sm'
                  : 'bg-[#EDE6DB] text-[#695541] hover:bg-[#E2D8C7] hover:text-[#1F150D]'
              }`}
            >
              {st}
            </button>
          );
        })}
      </div>

      {/* 7 & 8. SEARCH AND FILTERS BAR */}
      <div className="glass-panel p-4 rounded-2xl border border-[#C5A059]/35 space-y-3 bg-white/70 shadow-sm">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-[#8F6834] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search captures, projects, spaces, capture IDs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#FAF7F2] border border-[#C5A059]/40 rounded-xl pl-9 pr-4 py-2 text-xs text-[#1F150D] placeholder-[#8F7864] focus:outline-none focus:ring-1 focus:ring-[#C5A059]"
            />
          </div>

          <div className="flex items-center space-x-2 w-full sm:w-auto">
            <button
              onClick={() => setShowFiltersPanel(!showFiltersPanel)}
              className="px-3.5 py-2 rounded-xl bg-[#FAF7F2] border border-[#C5A059]/40 text-[#8F6834] text-xs font-bold flex items-center space-x-1.5 hover:bg-[#F2EBDC] transition-colors"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Filters ▾</span>
            </button>
          </div>
        </div>

        {/* Expandable Filter Panel */}
        {showFiltersPanel && (
          <div className="pt-3 border-t border-[#E8DEC9] grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 animate-in fade-in zoom-in-95">
            <div>
              <label className="text-[10px] font-bold uppercase text-[#8F7864] block mb-1">Project</label>
              <select
                value={selectedProjectFilter}
                onChange={(e) => setSelectedProjectFilter(e.target.value)}
                className="w-full text-xs font-semibold bg-[#FAF7F2] border border-[#C5A059]/40 rounded-lg px-2.5 py-1.5 text-[#1F150D] focus:outline-none"
              >
                <option value="ALL">All Projects</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[10px] font-bold uppercase text-[#8F7864] block mb-1">Capture Method</label>
              <select
                value={selectedMethodFilter}
                onChange={(e) => setSelectedMethodFilter(e.target.value)}
                className="w-full text-xs font-semibold bg-[#FAF7F2] border border-[#C5A059]/40 rounded-lg px-2.5 py-1.5 text-[#1F150D] focus:outline-none"
              >
                <option value="ALL">All Methods</option>
                <option value="rgb_lidar">LiDAR</option>
                <option value="rgb_imu">Photogrammetry / Mobile</option>
                <option value="rescan_targeted">Targeted Rescan</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* 9 & 10. MAIN CAPTURE OPERATIONAL LIST / TABLE */}
      {loading ? (
        <div className="glass-panel p-6 rounded-2xl border border-[#C5A059]/30 space-y-3 animate-pulse">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-12 bg-[#E8DEC9] rounded-xl" />
          ))}
        </div>
      ) : filteredCaptures.length === 0 ? (
        /* 30. HONEST EMPTY STATE */
        <div className="glass-panel p-12 rounded-3xl border border-[#C5A059]/30 text-center space-y-4 shadow-md bg-[#FAF7F2]">
          <div className="w-16 h-16 rounded-2xl bg-[#EDE6DB] border border-[#C5A059]/40 flex items-center justify-center mx-auto text-[#8F6834]">
            <ScanLine className="w-8 h-8" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-[#1F150D] font-serif-brand">
              {searchQuery || selectedStatusFilter !== 'ALL' || selectedProjectFilter !== 'ALL'
                ? 'No captures match your search'
                : 'No spatial captures yet'}
            </h3>
            <p className="text-xs text-[#695541] max-w-md mx-auto leading-relaxed">
              {searchQuery || selectedStatusFilter !== 'ALL' || selectedProjectFilter !== 'ALL'
                ? 'Try clearing your search query or filters to see all recorded acquisition sessions.'
                : 'Capture or upload a physical space to begin building your digital twin.'}
            </p>
          </div>
          <div className="flex items-center justify-center space-x-3 pt-2">
            {searchQuery || selectedStatusFilter !== 'ALL' || selectedProjectFilter !== 'ALL' ? (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedStatusFilter('ALL');
                  setSelectedProjectFilter('ALL');
                  setSelectedMethodFilter('ALL');
                }}
                className="btn-brand-secondary py-2.5 px-4 rounded-xl text-xs font-bold"
              >
                Clear Filters
              </button>
            ) : (
              <button
                onClick={() => setNewCaptureModalOpen(true)}
                className="btn-brand-primary py-2.5 px-5 rounded-xl text-xs font-bold flex items-center space-x-2 shadow-md"
              >
                <Plus className="w-4 h-4" />
                <span>New Capture</span>
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl border border-[#C5A059]/35 overflow-hidden shadow-md bg-white/80">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#FAF7F2] border-b border-[#C5A059]/30 text-[10px] uppercase font-black text-[#8F7864] tracking-wider">
                  <th className="py-3 px-4">Capture</th>
                  <th className="py-3 px-4">Project / Space</th>
                  <th className="py-3 px-4">Method</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4">Size</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E8DEC9] text-xs">
                {filteredCaptures.map((c) => {
                  const statusUpper = c.status?.toUpperCase() || 'RECORDING';
                  const isCompleted = statusUpper === 'COMPLETED';
                  const isFailed = statusUpper === 'FAILED';
                  const isProcessing =
                    statusUpper === 'PROCESSING' || statusUpper === 'VALIDATING' || statusUpper === 'UPLOADING' || statusUpper === 'RECORDING';

                  const statusPillStyle = isCompleted
                    ? 'bg-emerald-950/40 text-emerald-700 border-emerald-600/40'
                    : isFailed
                    ? 'bg-red-950/40 text-red-700 border-red-600/40'
                    : isProcessing
                    ? 'bg-amber-950/40 text-amber-700 border-amber-600/40'
                    : 'bg-[#EDE6DB] text-[#8F6834] border-[#C5A059]/40';

                  return (
                    <tr key={c.id} className="hover:bg-[#FAF7F2] transition-colors">
                      {/* Column 1: CAPTURE */}
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-[#1F150D] flex items-center space-x-2">
                          <span>{c.notes || 'Spatial Scan Session'}</span>
                          <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-[#EDE6DB] border border-[#C5A059]/40 text-[#8F6834] font-bold">
                            CAP-{c.id.substring(0, 6).toUpperCase()}
                          </span>
                        </div>
                        <div className="text-[10px] text-[#695541] mt-0.5">
                          {c.device_model || 'Mobile Device'} · {c.frames_count ? `${c.frames_count} frames` : 'LiDAR raw mesh'}
                        </div>
                      </td>

                      {/* Column 2: PROJECT / SPACE */}
                      <td className="py-3.5 px-4 font-medium text-[#1F150D]">
                        <div className="font-bold">{c.project_name || 'Office HQ'}</div>
                        <div className="text-[10px] text-[#695541]">Level / Floor Space</div>
                      </td>

                      {/* Column 3: METHOD */}
                      <td className="py-3.5 px-4 font-mono text-[11px] font-bold text-[#8F6834]">
                        {c.has_lidar || c.capture_mode === 'rgb_lidar' ? 'LiDAR' : 'Photogrammetry'}
                      </td>

                      {/* Column 4: CREATED */}
                      <td className="py-3.5 px-4 text-[#5C4A38] font-medium">
                        {formatTime(c.created_at)}
                      </td>

                      {/* Column 5: SIZE */}
                      <td className="py-3.5 px-4 font-mono font-bold text-[#1F150D]">
                        {formatFileSize(c.file_size_bytes)}
                      </td>

                      {/* Column 6: STATUS */}
                      <td className="py-3.5 px-4">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider uppercase border ${statusPillStyle}`}>
                          ● {statusUpper}
                        </span>
                      </td>

                      {/* Column 7: ACTION */}
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => setActiveCaptureDetail(c)}
                          className="px-3 py-1.5 rounded-lg bg-[#FAF7F2] hover:bg-[#EDE6DB] border border-[#C5A059]/40 text-[#8F6834] text-xs font-bold transition-colors inline-flex items-center space-x-1"
                        >
                          <span>View</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 13. NEW CAPTURE WORKFLOW MODAL */}
      {newCaptureModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-lg w-full p-6 rounded-3xl border border-[#C5A059]/40 space-y-5 shadow-2xl animate-in fade-in zoom-in-95 bg-[#211710] text-white">
            <div className="flex justify-between items-start pb-3 border-b border-[#C5A059]/30">
              <div>
                <h3 className="text-base font-bold text-white font-serif-brand flex items-center space-x-2">
                  <ScanLine className="w-4 h-4 text-[#C5A059]" />
                  <span>Initiate New Capture Session</span>
                </h3>
                <p className="text-xs text-[#A6998A] mt-1">
                  Select target project and spatial parameters to start real acquisition.
                </p>
              </div>
              <button
                onClick={() => setNewCaptureModalOpen(false)}
                className="text-[#A6998A] hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {creationError && (
              <div className="p-3 rounded-xl bg-red-950/70 border border-red-800 text-red-200 text-xs font-medium">
                {creationError}
              </div>
            )}

            <form onSubmit={handleCreateCaptureSession} className="space-y-4">
              {/* Step 1: Select Project */}
              <div>
                <label className="text-xs font-bold text-[#F2DFB8] block mb-1">
                  Step 1: Select Target Project
                </label>
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="w-full bg-[#17100A] border border-[#C5A059]/40 rounded-xl px-3 py-2 text-xs text-white focus:outline-none font-semibold"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.project_type || 'Spatial Model'})
                    </option>
                  ))}
                </select>
              </div>

              {/* Step 2: Select Space / Level */}
              {projectFloors.length > 0 && (
                <div>
                  <label className="text-xs font-bold text-[#F2DFB8] block mb-1">
                    Step 2: Select Floor / Level
                  </label>
                  <select
                    value={selectedLevelId}
                    onChange={(e) => setSelectedLevelId(e.target.value)}
                    className="w-full bg-[#17100A] border border-[#C5A059]/40 rounded-xl px-3 py-2 text-xs text-white focus:outline-none font-semibold"
                  >
                    {projectFloors.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name} (Floor #{f.floor_number})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Step 3: Select Capture Method */}
              <div>
                <label className="text-xs font-bold text-[#F2DFB8] block mb-1">
                  Step 3: Acquisition Method
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setCaptureMethod('rgb_lidar')}
                    className={`p-3 rounded-xl border text-left space-y-1 transition-all ${
                      captureMethod === 'rgb_lidar'
                        ? 'bg-[#3D2C1F] border-[#C5A059] text-white shadow-md'
                        : 'bg-[#17100A] border-[#C5A059]/30 text-[#A6998A]'
                    }`}
                  >
                    <div className="text-xs font-bold flex items-center justify-between">
                      <span>LiDAR Sensor</span>
                      {captureMethod === 'rgb_lidar' && <CheckCircle2 className="w-3.5 h-3.5 text-[#C5A059]" />}
                    </div>
                    <div className="text-[10px]">High precision point cloud & depth mesh</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setCaptureMethod('rgb_imu')}
                    className={`p-3 rounded-xl border text-left space-y-1 transition-all ${
                      captureMethod === 'rgb_imu'
                        ? 'bg-[#3D2C1F] border-[#C5A059] text-white shadow-md'
                        : 'bg-[#17100A] border-[#C5A059]/30 text-[#A6998A]'
                    }`}
                  >
                    <div className="text-xs font-bold flex items-center justify-between">
                      <span>Photogrammetry</span>
                      {captureMethod === 'rgb_imu' && <CheckCircle2 className="w-3.5 h-3.5 text-[#C5A059]" />}
                    </div>
                    <div className="text-[10px]">RGB Camera + Inertial IMU Trajectory</div>
                  </button>
                </div>
              </div>

              {/* Step 4: Notes / Title */}
              <div>
                <label className="text-xs font-bold text-[#F2DFB8] block mb-1">
                  Session Notes / Identifier
                </label>
                <input
                  type="text"
                  placeholder="e.g. Ground Floor Conference Room Scan"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full bg-[#17100A] border border-[#C5A059]/40 rounded-xl px-3 py-2 text-xs text-white placeholder-[#8F7864] focus:outline-none"
                />
              </div>

              <div className="pt-2 flex items-center justify-end space-x-3 border-t border-[#36271C]">
                <button
                  type="button"
                  onClick={() => setNewCaptureModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-[#A6998A] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingCapture}
                  className="btn-brand-primary py-2 px-5 rounded-xl text-xs font-bold shadow-md"
                >
                  {creatingCapture ? 'Initiating...' : 'Start Capture Session'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 21. CAPTURE DETAIL DRAWER / MODAL */}
      {activeCaptureDetail && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-xl w-full p-6 rounded-3xl border border-[#C5A059]/40 space-y-5 shadow-2xl animate-in fade-in zoom-in-95 bg-[#211710] text-white">
            <div className="flex justify-between items-start pb-3 border-b border-[#C5A059]/30">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-[#3D2C1F] border border-[#C5A059]/50 text-[#F2DFB8] font-bold">
                    CAP-{activeCaptureDetail.id.substring(0, 6).toUpperCase()}
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black tracking-wider uppercase border bg-amber-950/40 text-amber-500 border-amber-600/40">
                    ● {activeCaptureDetail.status?.toUpperCase() || 'COMPLETED'}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white font-serif-brand mt-1">
                  {activeCaptureDetail.notes || 'Spatial Acquisition Session'}
                </h3>
              </div>
              <button onClick={() => setActiveCaptureDetail(null)} className="text-[#A6998A] hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* PIPELINE STATUS BREAKDOWN */}
            <div className="space-y-3 p-4 rounded-2xl bg-[#17100A] border border-[#C5A059]/30">
              <div className="text-xs font-bold text-[#C5A059] uppercase tracking-wider">
                Processing Pipeline Lifecycle
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-white">1. Data Ingestion & Upload</span>
                  <span className="text-emerald-400 font-bold">✓ Complete</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white">2. Spatial Validation & Integrity</span>
                  <span className="text-emerald-400 font-bold">✓ Complete</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white">3. 3D Spatial Reconstruction</span>
                  <span className="text-emerald-400 font-bold">✓ Complete</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white">4. Object & Asset Detection</span>
                  <span className="text-[#A6998A] italic">○ Active</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white">5. Vector Floor Plan Generation</span>
                  <span className="text-[#A6998A] italic">○ Active</span>
                </div>
              </div>
            </div>

            {/* AVAILABLE OUTPUT ACTIONS */}
            <div className="space-y-2">
              <div className="text-xs font-bold text-[#F2DFB8]">Available Outputs</div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    const pid = activeCaptureDetail.project_id;
                    setActiveCaptureDetail(null);
                    navigate(`/projects/${pid}/viewer`);
                  }}
                  className="btn-brand-primary py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 shadow"
                >
                  <Compass className="w-4 h-4" />
                  <span>Open Digital Twin</span>
                </button>

                <button
                  onClick={() => {
                    const pid = activeCaptureDetail.project_id;
                    setActiveCaptureDetail(null);
                    navigate(`/projects/${pid}`);
                  }}
                  className="btn-brand-secondary py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center space-x-2"
                >
                  <FolderGit2 className="w-4 h-4 text-[#C5A059]" />
                  <span>View Project</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
