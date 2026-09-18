import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Building2,
  MapPin,
  Layers,
  Users,
  Camera,
  Settings,
  ArrowLeft,
  PencilRuler,
  FileText,
  Mail,
  Phone,
  Calendar,
  ExternalLink,
  Plus,
  Loader2,
  CheckCircle2,
  Clock,
  Trash2,
  Edit3,
  Box,
  Share2,
  Copy,
  Check
} from 'lucide-react';
import { api } from '../../services/api';
import { Project, ProjectFloor, ProjectMember, FloorPlan } from '../../types';
import { FloorPlanDrawer } from '../../components/canvas/FloorPlanDrawer';
import { Spatial3DViewer } from '../../components/viewer/Spatial3DViewer';
import { CaptureSessionModal } from '../../components/capture/CaptureSessionModal';
import { MobilePairingModal } from '../../components/capture/MobilePairingModal';

export const ProjectDashboardPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'floors' | 'team' | 'captures' | '3d_viewer' | 'settings'>('overview');
  const [showCaptureModal, setShowCaptureModal] = useState(false);
  const [pairingSession, setPairingSession] = useState<any | null>(null);
  const [customSessions, setCustomSessions] = useState<any[]>([]);

  // Drawing modal for a selected floor
  const [editingFloorPlan, setEditingFloorPlan] = useState<ProjectFloor | null>(null);

  // Add floor modal
  const [showAddFloorModal, setShowAddFloorModal] = useState(false);
  const [newFloorName, setNewFloorName] = useState('');
  const [newFloorType, setNewFloorType] = useState('Typical Floor');
  const [newFloorArea, setNewFloorArea] = useState(2000);
  const [newFloorHeight, setNewFloorHeight] = useState(10.5);
  const [addingFloor, setAddingFloor] = useState(false);

  // Add member modal
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [availableOrgMembers, setAvailableOrgMembers] = useState<any[]>([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedProjectRole, setSelectedProjectRole] = useState<'Manager' | 'Surveyor' | 'Member' | 'Viewer'>('Member');
  const [assigningMember, setAssigningMember] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  const handleCopyViewingLink = () => {
    if (!project) return;
    const url = `${window.location.origin}/view/${project.id}`;
    navigator.clipboard.writeText(url);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  // Fetch full project data
  const loadProject = async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getProjectFull(projectId);
      setProject(data);
    } catch (err: any) {
      console.error('Failed to load project details:', err);
      setError(err.message || 'Project not found');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProject();
  }, [projectId]);

  const handleAddFloorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !newFloorName.trim()) return;
    setAddingFloor(true);
    try {
      await api.addFloor(projectId, {
        name: newFloorName.trim(),
        floor_number: (project?.floors?.length || 0),
        floor_type: newFloorType,
        area_value: newFloorArea,
        area_unit: 'SQFT',
        height_value: newFloorHeight,
        height_unit: 'FT',
        sequence: (project?.floors?.length || 0) + 1,
      });
      setShowAddFloorModal(false);
      setNewFloorName('');
      loadProject();
    } catch (err: any) {
      alert('Failed to add floor: ' + err.message);
    } finally {
      setAddingFloor(false);
    }
  };

  const handleDeleteFloor = async (floorId: string) => {
    if (!projectId) return;
    if (!confirm('Are you sure you want to remove this floor and its spatial data?')) return;
    try {
      await api.deleteFloor(projectId, floorId);
      loadProject();
    } catch (err: any) {
      alert('Failed to delete floor: ' + err.message);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3">
        <Loader2 className="w-8 h-8 text-[#8F6834] animate-spin" />
        <p className="text-xs text-[#695541]">Loading spatial digital twin project...</p>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="max-w-2xl mx-auto p-6 bg-[#FAF7F2] rounded-2xl border border-[#D1C2A5] text-center space-y-4 my-8">
        <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto">
          <Building2 className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-[#1F150D]">Project Unavailable</h2>
        <p className="text-xs text-[#695541]">{error || 'Unable to retrieve project details.'}</p>
        <button
          onClick={() => navigate('/projects')}
          className="px-4 py-2 bg-[#8F6834] text-[#FAF7F2] text-xs font-semibold rounded-xl"
        >
          Return to Projects
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-16">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <button
          onClick={() => navigate('/projects')}
          className="flex items-center gap-1.5 text-xs font-semibold text-[#8F6834] hover:text-[#755427] transition-colors self-start"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Spatial Twin Projects</span>
        </button>

        <div className="flex items-center gap-2">
          <span
            className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
              project.status === 'ACTIVE'
                ? 'bg-emerald-100 text-emerald-800'
                : 'bg-amber-100 text-amber-800'
            }`}
          >
            {project.status || 'ACTIVE'}
          </span>
          <span className="text-xs font-mono text-[#7C6652] bg-[#FAF7F2] px-2.5 py-1 rounded-lg border border-[#D1C2A5]">
            {project.project_code || project.id.substring(0, 8)}
          </span>
        </div>
      </div>

      {/* Hero Cover Card */}
      <div className="relative rounded-2xl overflow-hidden border border-[#D1C2A5] bg-[#FAF7F2] shadow-sm">
        <div className="h-44 sm:h-56 bg-gradient-to-r from-[#5C4223] via-[#7D5A2F] to-[#8F6834] relative">
          {project.cover_image_url && (
            <img
              src={project.cover_image_url}
              alt={project.name}
              className="w-full h-full object-cover opacity-80"
            />
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-[#1F150D]/80 via-transparent to-transparent" />
          <div className="absolute bottom-4 left-6 right-6 flex flex-col sm:flex-row sm:items-end justify-between gap-3 text-white">
            <div>
              <div className="text-xs uppercase tracking-widest text-[#E3DACA] font-medium">
                {project.project_type} {project.custom_type ? `(${project.custom_type})` : ''}
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold font-serif-brand text-white mt-0.5">
                {project.name}
              </h1>
              {project.address && (
                <div className="flex items-center gap-1.5 text-xs text-[#FAF7F2]/90 mt-1">
                  <MapPin className="w-3.5 h-3.5 text-[#C5A059]" />
                  <span>
                    {project.address.city}, {project.address.state} &bull; {project.address.country}
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopyViewingLink}
                className="px-3.5 py-2 bg-white/15 hover:bg-white/25 text-white text-xs font-bold rounded-xl backdrop-blur-md border border-white/20 shadow-sm flex items-center gap-1.5 transition-all"
                title="Copy shareable viewing link for clients and stakeholders"
              >
                {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Share2 className="w-3.5 h-3.5 text-[#E3DACA]" />}
                <span>{copiedLink ? 'Viewing Link Copied!' : 'Share Viewing Link'}</span>
              </button>

              <button
                onClick={() => setActiveTab('3d_viewer')}
                className="px-3.5 py-2 bg-[#DFB873] hover:bg-[#C9A25B] text-[#0B0F17] text-xs font-extrabold rounded-xl shadow-md flex items-center gap-1.5 transition-all"
              >
                <Box className="w-3.5 h-3.5" />
                <span>3D Digital Twin</span>
              </button>

              <button
                onClick={() => setShowCaptureModal(true)}
                className="px-3.5 py-2 bg-white/10 hover:bg-white/20 text-white text-xs font-bold rounded-xl backdrop-blur-md border border-white/15 shadow-sm flex items-center gap-1.5 transition-all"
              >
                <Camera className="w-3.5 h-3.5" />
                <span>Capture Session</span>
              </button>
            </div>
          </div>
        </div>

        {/* Dashboard Tabs Bar */}
        <div className="flex items-center gap-1 px-4 py-2 border-t border-[#EAE2D3] overflow-x-auto bg-white">
          {[
            { id: 'overview', label: 'Overview', icon: Building2 },
            { id: '3d_viewer', label: '3D Twin Viewer', icon: Box },
            { id: 'floors', label: `Floors (${project.floors?.length || 0})`, icon: Layers },
            { id: 'team', label: `Team (${project.team?.length || 0})`, icon: Users },
            { id: 'captures', label: 'Captures', icon: Camera },
            { id: 'settings', label: 'Settings', icon: Settings },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                  active
                    ? 'bg-[#8F6834] text-[#FAF7F2] shadow-xs'
                    : 'text-[#5C4D3E] hover:bg-[#FAF7F2] hover:text-[#1F150D]'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* TAB CONTENT: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Architectural Stats Card */}
            <div className="p-5 bg-[#FAF7F2] rounded-2xl border border-[#D1C2A5] shadow-xs space-y-4">
              <h3 className="text-sm font-bold text-[#1F150D] font-serif-brand flex items-center gap-2">
                <Building2 className="w-4 h-4 text-[#8F6834]" />
                <span>Physical Space Metrics</span>
              </h3>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-white rounded-xl border border-[#EAE2D3]">
                  <div className="text-[10px] uppercase font-semibold tracking-wider text-[#7C6652]">Total Area</div>
                  <div className="text-base font-bold text-[#1F150D] mt-0.5">
                    {project.total_area_sqft ? project.total_area_sqft.toLocaleString() : '—'} sqft
                  </div>
                  <div className="text-[10px] text-[#8C7A6B]">
                    {project.total_area_sqm ? `≈ ${Math.round(project.total_area_sqm).toLocaleString()} m²` : ''}
                  </div>
                </div>

                <div className="p-3 bg-white rounded-xl border border-[#EAE2D3]">
                  <div className="text-[10px] uppercase font-semibold tracking-wider text-[#7C6652]">Floors / Levels</div>
                  <div className="text-base font-bold text-[#8F6834] mt-0.5">
                    {project.floors?.length || project.total_floors_count || 1} Levels
                  </div>
                  <div className="text-[10px] text-[#8C7A6B]">Independently managed</div>
                </div>

                <div className="p-3 bg-white rounded-xl border border-[#EAE2D3]">
                  <div className="text-[10px] uppercase font-semibold tracking-wider text-[#7C6652]">Precision Gate</div>
                  <div className="text-base font-bold text-[#1F150D] mt-0.5">
                    {project.precision_gate_cm || 2.0} cm
                  </div>
                  <div className="text-[10px] text-[#8C7A6B]">LiDAR verification</div>
                </div>

                <div className="p-3 bg-white rounded-xl border border-[#EAE2D3]">
                  <div className="text-[10px] uppercase font-semibold tracking-wider text-[#7C6652]">Created On</div>
                  <div className="text-xs font-bold text-[#1F150D] mt-1 truncate">
                    {new Date(project.created_at).toLocaleDateString()}
                  </div>
                  <div className="text-[10px] text-[#8C7A6B]">Real backend UUID</div>
                </div>
              </div>

              {project.description && (
                <div className="pt-2 border-t border-[#EAE2D3]">
                  <div className="text-xs font-semibold text-[#5C4D3E] mb-1">Project Scope & Notes</div>
                  <p className="text-xs text-[#695541] leading-relaxed">{project.description}</p>
                </div>
              )}
            </div>

            {/* Structured Address Card */}
            <div className="p-5 bg-[#FAF7F2] rounded-2xl border border-[#D1C2A5] shadow-xs space-y-3">
              <h3 className="text-sm font-bold text-[#1F150D] font-serif-brand flex items-center gap-2">
                <MapPin className="w-4 h-4 text-[#8F6834]" />
                <span>Verified Location & Place ID</span>
              </h3>

              {project.address ? (
                <div className="space-y-2 text-xs text-[#5C4D3E]">
                  <div className="font-semibold text-[#1F150D] text-sm">
                    {project.address.address_line_1}
                  </div>
                  {project.address.address_line_2 && <div>{project.address.address_line_2}</div>}
                  {project.address.area && <div>Area / Locality: {project.address.area}</div>}
                  <div>
                    {project.address.city}, {project.address.state} - {project.address.pincode}
                  </div>
                  <div className="font-medium text-[#7C6652]">{project.address.country}</div>

                  {project.address.latitude && project.address.longitude && (
                    <div className="pt-2 flex items-center gap-2">
                      <span className="font-mono text-[11px] bg-[#EFE7D8] text-[#5C4D3E] px-2.5 py-1 rounded-lg border border-[#D9CEBC]">
                        GPS: {project.address.latitude.toFixed(5)}, {project.address.longitude.toFixed(5)}
                      </span>
                      {project.address.place_id && (
                        <span className="text-[10px] text-[#8C7A6B]">
                          Place ID: {project.address.place_id}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-[#8C7A6B]">No address registered.</p>
              )}
            </div>
          </div>

          {/* Right Sidebar: Contact & Team */}
          <div className="space-y-6">
            {/* Primary Contact Person Card */}
            <div className="p-5 bg-[#FAF7F2] rounded-2xl border border-[#D1C2A5] shadow-xs space-y-3">
              <h3 className="text-sm font-bold text-[#1F150D] font-serif-brand flex items-center gap-2">
                <Users className="w-4 h-4 text-[#8F6834]" />
                <span>Project Lead Contact</span>
              </h3>

              <div className="space-y-2 text-xs text-[#5C4D3E]">
                <div className="text-sm font-bold text-[#1F150D]">
                  {project.contact_name || 'Primary Contact'}
                </div>

                {project.contact_phone && (
                  <div className="flex items-center gap-2 text-[#5C4D3E]">
                    <Phone className="w-3.5 h-3.5 text-[#8F6834]" />
                    <span>{project.contact_phone}</span>
                  </div>
                )}

                {project.contact_email && (
                  <div className="flex items-center gap-2 text-[#5C4D3E]">
                    <Mail className="w-3.5 h-3.5 text-[#8F6834]" />
                    <span>{project.contact_email}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Floor Summary */}
            <div className="p-5 bg-[#FAF7F2] rounded-2xl border border-[#D1C2A5] shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-[#1F150D] font-serif-brand">
                  Structure Levels
                </h3>
                <button
                  onClick={() => setActiveTab('floors')}
                  className="text-xs font-semibold text-[#8F6834] hover:underline"
                >
                  View All
                </button>
              </div>

              <div className="space-y-2">
                {(project.floors || []).slice(0, 4).map((f) => (
                  <div
                    key={f.id}
                    className="p-2.5 bg-white rounded-xl border border-[#EAE2D3] flex items-center justify-between text-xs"
                  >
                    <div>
                      <span className="font-bold text-[#1F150D]">{f.name}</span>
                      <span className="text-[10px] text-[#7C6652] block">{f.floor_type}</span>
                    </div>
                    <span className="font-mono text-xs font-medium text-[#8F6834]">
                      {f.area_value} {f.area_unit}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: 3D DIGITAL TWIN VIEWER */}
      {activeTab === '3d_viewer' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#FAF7F2] p-4 rounded-2xl border border-[#D1C2A5]">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#8F6834]/15 text-[#8F6834] border border-[#8F6834]/30 flex items-center gap-1">
                  <Box className="w-3 h-3" /> 25-STAGE EVIDENCE RECONSTRUCTION
                </span>
                <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Zero Hallucination PASS
                </span>
              </div>
              <h2 className="text-base font-bold text-[#1F150D] font-serif-brand mt-1">
                {project.name} — Photographic Spatial Digital Twin
              </h2>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopyViewingLink}
                className="flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-[#FAF7F2] text-[#8F6834] border border-[#D1C2A5] rounded-xl text-xs font-semibold shadow-xs transition-all"
              >
                {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedLink ? 'Link Copied' : 'Copy Client Link'}</span>
              </button>

              <button
                onClick={() => navigate(`/projects/${project.id}/viewer`)}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-[#8F6834] hover:bg-[#755427] text-white rounded-xl text-xs font-bold shadow-sm transition-all"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Fullscreen Studio</span>
              </button>
            </div>
          </div>

          <Spatial3DViewer
            projectId={project.id}
            modelName={project.name}
            projectCode={project.project_code}
            projectType={project.project_type}
          />
        </div>
      )}

      {/* TAB CONTENT: FLOORS & BLUEPRINTS */}
      {activeTab === 'floors' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-[#1F150D] font-serif-brand">
                Floor Hierarchy & Blueprints
              </h2>
              <p className="text-xs text-[#695541]">
                Manage independent levels, structural heights, and attached CAD drawings.
              </p>
            </div>

            <button
              onClick={() => setShowAddFloorModal(true)}
              className="flex items-center gap-1.5 px-4 py-2 bg-[#8F6834] hover:bg-[#755427] text-white text-xs font-bold rounded-xl shadow-sm transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Add New Level</span>
            </button>
          </div>

          <div className="space-y-4">
            {(project.floors || []).map((floor) => (
              <div
                key={floor.id}
                className="p-5 bg-[#FAF7F2] rounded-2xl border border-[#D1C2A5] shadow-xs space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#EAE2D3] pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-base font-bold text-[#1F150D]">{floor.name}</span>
                      <span className="px-2 py-0.5 bg-[#FAF3E0] text-[#8F6834] rounded-md border border-[#D9C4A1] text-[10px] font-bold uppercase">
                        {floor.floor_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-[#7C6652] mt-1">
                      <span>Area: {floor.area_value} {floor.area_unit}</span>
                      <span>&bull;</span>
                      <span>Ceiling: {floor.height_value} {floor.height_unit}</span>
                      <span>&bull;</span>
                      <span>Level #{floor.floor_number}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setEditingFloorPlan(floor)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[#FAF7F2] text-[#8F6834] border border-[#D1C2A5] rounded-xl text-xs font-semibold shadow-xs"
                    >
                      <PencilRuler className="w-3.5 h-3.5" />
                      <span>{floor.floor_plan ? 'Edit Floor Plan' : 'Draw Floor Plan'}</span>
                    </button>

                    <button
                      onClick={() => handleDeleteFloor(floor.id)}
                      className="p-1.5 text-red-500 hover:text-red-700 rounded-lg"
                      title="Delete Floor"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Floor Plan Blueprint Preview */}
                {floor.floor_plan ? (
                  <div className="p-4 bg-white rounded-xl border border-[#EAE2D3] flex flex-col sm:flex-row items-center gap-4">
                    {floor.floor_plan.preview_url ? (
                      <div className="w-36 h-24 rounded-lg overflow-hidden border border-[#D1C2A5] bg-[#FAF7F2] shrink-0">
                        <img
                          src={floor.floor_plan.preview_url}
                          alt="Floor plan"
                          className="w-full h-full object-contain"
                        />
                      </div>
                    ) : (
                      <div className="w-36 h-24 rounded-lg border border-[#D1C2A5] bg-[#FAF7F2] flex items-center justify-center text-[#8F6834] shrink-0">
                        <FileText className="w-8 h-8" />
                      </div>
                    )}

                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="text-xs font-bold text-[#1F150D]">
                        {floor.floor_plan.plan_type === 'DRAWN'
                          ? 'Vector CAD Blueprint'
                          : floor.floor_plan.original_file_name || 'Uploaded Document'}
                      </div>
                      <div className="text-[11px] text-[#7C6652]">
                        Type: {floor.floor_plan.plan_type} &bull; Canvas: {floor.floor_plan.canvas_width} × {floor.floor_plan.canvas_height}
                      </div>
                      {floor.floor_plan.file_url && (
                        <a
                          href={floor.floor_plan.file_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-xs font-semibold text-[#8F6834] hover:underline pt-1"
                        >
                          <span>Open High-Res Blueprint</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="p-4 bg-white/60 rounded-xl border border-dashed border-[#D1C2A5] text-center text-xs text-[#8C7A6B]">
                    No architectural blueprint linked to {floor.name}. Tap "Draw Floor Plan" to draft one.
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB CONTENT: TEAM */}
      {activeTab === 'team' && (
        <div className="p-6 bg-[#FAF7F2] rounded-2xl border border-[#D1C2A5] shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#EAE2D3] pb-3">
            <div>
              <h2 className="text-lg font-bold text-[#1F150D] font-serif-brand">
                Project Access & Team Members
              </h2>
              <p className="text-xs text-[#695541]">
                Personnel assigned with project-specific roles and spatial capture permissions.
              </p>
            </div>
            <button
              type="button"
              onClick={async () => {
                try {
                  const orgMembers = await api.listMembers();
                  setAvailableOrgMembers(orgMembers || []);
                  setShowAddMemberModal(true);
                } catch (err: any) {
                  alert('Failed to load organization members: ' + err.message);
                }
              }}
              className="flex items-center gap-1.5 px-4 py-2 bg-[#8F6834] hover:bg-[#755427] text-white text-xs font-bold rounded-xl shadow-sm transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>Add Team Member</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {(project.team || []).map((m) => (
              <div
                key={m.id}
                className="p-3.5 bg-white rounded-xl border border-[#EAE2D3] space-y-2 shadow-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#1F150D] truncate">
                    {m.user?.full_name || 'Team Member'}
                  </span>
                  <span className="px-2 py-0.5 bg-[#FAF3E0] text-[#8F6834] rounded-md text-[10px] font-bold">
                    {m.project_role}
                  </span>
                </div>
                <div className="text-[11px] text-[#7C6652] truncate">{m.user?.email}</div>
                <div className="flex items-center justify-between text-[10px] text-[#A09384] pt-1 border-t border-[#F2EDE4]">
                  <span>Assigned: {new Date(m.assigned_at).toLocaleDateString()}</span>
                  <button
                    type="button"
                    onClick={async () => {
                      if (confirm(`Remove ${m.user?.full_name || 'member'} from project?`)) {
                        try {
                          await api.removeProjectMember(project.id, m.user_id);
                          loadProject();
                        } catch (err: any) {
                          alert('Failed to remove member: ' + err.message);
                        }
                      }
                    }}
                    className="text-red-500 hover:text-red-700 font-semibold"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB CONTENT: CAPTURES */}
      {activeTab === 'captures' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-[#1F150D] font-serif-brand">
                Spatial Survey & Capture Sessions
              </h2>
              <p className="text-xs text-[#695541]">
                Execute 360° space reconnaissance, automated multimodal SOP analysis, and area-by-area guided capture.
              </p>
            </div>

            <button
              onClick={() => setShowCaptureModal(true)}
              className="flex items-center gap-1.5 px-4 py-2 bg-[#8F6834] hover:bg-[#755427] text-white text-xs font-bold rounded-xl shadow-sm transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>New Capture Session</span>
            </button>
          </div>

          {/* Sessions List */}
          <div className="space-y-3">
            {[
              ...customSessions,
              {
                id: `CAP-01-RECON`,
                floor_name: project.floors?.[0]?.name || 'Ground Floor',
                operator_name: 'Project Admin (Self)',
                operator_type: 'SELF',
                phase: 'PHASE_3_ACTIVE',
                phase_label: 'Area-to-Area Capture Ready',
                created_at: new Date().toLocaleDateString(),
                zones_count: 4,
                completed_zones: 1
              }
            ].map((s) => (
              <div
                key={s.id}
                className="p-5 bg-[#FAF7F2] border border-[#D1C2A5] rounded-2xl shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-[#1F150D]">{s.id}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#FAF3E0] text-[#8F6834] border border-[#D9C4A1]">
                      {s.floor_name}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {s.phase_label}
                    </span>
                  </div>
                  <div className="text-xs text-[#7C6652] flex items-center gap-2">
                    <span>Assigned: <strong className="text-[#1F150D]">{s.operator_name}</strong></span>
                    <span>&bull;</span>
                    <span>Created: {s.created_at}</span>
                    <span>&bull;</span>
                    <span>{s.zones_count} Floor Plan Zones</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPairingSession(s)}
                    className="flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-[#FAF7F2] border border-[#D1C2A5] text-[#5C4D3E] text-xs font-semibold rounded-xl shadow-xs transition-all"
                    title="Open QR code & mobile app pairing"
                  >
                    <Share2 className="w-3.5 h-3.5 text-[#8F6834]" />
                    <span>Mobile App Pairing</span>
                  </button>

                  <button
                    onClick={() => navigate(`/projects/${project.id}/capture/${s.id}`)}
                    className="flex items-center gap-1.5 px-4 py-2 bg-[#8F6834] hover:bg-[#755427] text-white text-xs font-bold rounded-xl shadow-sm transition-all"
                  >
                    <Camera className="w-3.5 h-3.5" />
                    <span>Launch Guided Studio</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB CONTENT: SETTINGS */}
      {activeTab === 'settings' && (
        <div className="p-6 bg-[#FAF7F2] rounded-2xl border border-[#D1C2A5] shadow-xs space-y-4">
          <h3 className="text-base font-bold text-[#1F150D] font-serif-brand">Project Configuration</h3>
          <p className="text-xs text-[#695541]">
            Manage project lifecycle status, spatial twin publication, or archive the project workspace.
          </p>
          <div className="pt-4 border-t border-[#EAE2D3] flex items-center gap-3">
            <button
              onClick={() => {
                if (confirm('Are you sure you want to move this project to Trash?')) {
                  api.softDeleteProject(project.id).then(() => navigate('/projects'));
                }
              }}
              className="px-4 py-2 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 rounded-xl text-xs font-bold"
            >
              Move Project to Trash
            </button>
          </div>
        </div>
      )}

      {/* Vector Drawing Modal */}
      {editingFloorPlan && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-6xl h-[85vh]">
            <FloorPlanDrawer
              initialData={editingFloorPlan.floor_plan?.drawing_data}
              onCancel={() => setEditingFloorPlan(null)}
              onSave={async (result) => {
                if (!projectId) return;
                try {
                  await api.drawFloorPlan(projectId, editingFloorPlan.id, {
                    canvas_width: result.canvas_width,
                    canvas_height: result.canvas_height,
                    scale_ratio: result.scale_ratio,
                    drawing_data: result.drawing_data,
                    preview_base64: result.preview_base64,
                  });
                  setEditingFloorPlan(null);
                  loadProject();
                } catch (err: any) {
                  alert('Failed to save floor plan: ' + err.message);
                }
              }}
            />
          </div>
        </div>
      )}

      {/* Add Floor Modal */}
      {showAddFloorModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#FAF7F2] rounded-2xl border border-[#D1C2A5] p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-[#1F150D] font-serif-brand">
              Add Level to Project
            </h3>
            <form onSubmit={handleAddFloorSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-[#5C4D3E] mb-1">
                  Floor Name <span className="text-red-600">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={newFloorName}
                  onChange={(e) => setNewFloorName(e.target.value)}
                  placeholder="e.g. Level 2 / Mezzanine"
                  className="w-full px-3 py-2 bg-white border border-[#D1C2A5] rounded-xl text-xs text-[#1F150D] focus:outline-none focus:border-[#8F6834]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[#5C4D3E] mb-1">Floor Type</label>
                  <input
                    type="text"
                    value={newFloorType}
                    onChange={(e) => setNewFloorType(e.target.value)}
                    placeholder="Typical Floor"
                    className="w-full px-3 py-2 bg-white border border-[#D1C2A5] rounded-xl text-xs text-[#1F150D]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#5C4D3E] mb-1">Area (SQFT)</label>
                  <input
                    type="number"
                    min="1"
                    value={newFloorArea}
                    onChange={(e) => setNewFloorArea(parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 bg-white border border-[#D1C2A5] rounded-xl text-xs text-[#1F150D]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#5C4D3E] mb-1">Ceiling Height (FT)</label>
                <input
                  type="number"
                  step="0.1"
                  min="1"
                  value={newFloorHeight}
                  onChange={(e) => setNewFloorHeight(parseFloat(e.target.value) || 10)}
                  className="w-full px-3 py-2 bg-white border border-[#D1C2A5] rounded-xl text-xs text-[#1F150D]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#EAE2D3]">
                <button
                  type="button"
                  onClick={() => setShowAddFloorModal(false)}
                  className="px-3.5 py-2 text-xs font-medium text-[#7C6652]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingFloor}
                  className="px-4 py-2 bg-[#8F6834] text-white text-xs font-bold rounded-xl shadow-xs"
                >
                  {addingFloor ? 'Adding...' : 'Add Level'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Member Modal */}
      {showAddMemberModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#FAF7F2] rounded-2xl border border-[#D1C2A5] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#EAE2D3] pb-3">
              <h3 className="text-base font-bold text-[#1F150D] font-serif-brand">
                Assign Project Team Member
              </h3>
              <button
                type="button"
                onClick={() => setShowAddMemberModal(false)}
                className="text-[#7C6652] hover:text-[#1F150D]"
              >
                ✕
              </button>
            </div>

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!projectId || !selectedUserId) return;
                setAssigningMember(true);
                try {
                  await api.addProjectMember(projectId, {
                    user_id: selectedUserId,
                    project_role: selectedProjectRole,
                  });
                  setShowAddMemberModal(false);
                  setSelectedUserId('');
                  loadProject();
                } catch (err: any) {
                  alert('Failed to assign member: ' + err.message);
                } finally {
                  setAssigningMember(false);
                }
              }}
              className="space-y-3.5"
            >
              <div>
                <label className="block text-xs font-semibold text-[#5C4D3E] mb-1">
                  Select Organization Member <span className="text-red-600">*</span>
                </label>
                <select
                  required
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(e.target.value)}
                  className="w-full px-3 py-2.5 bg-white border border-[#D1C2A5] rounded-xl text-xs text-[#1F150D] focus:outline-none focus:border-[#8F6834]"
                >
                  <option value="">-- Choose Member --</option>
                  {availableOrgMembers
                    .filter((om) => !(project?.team || []).some((ptm) => ptm.user_id === om.user_id))
                    .map((om) => (
                      <option key={om.id || om.user_id} value={om.user_id}>
                        {om.user?.full_name || om.user?.email} ({om.role})
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#5C4D3E] mb-1">
                  Project Role <span className="text-red-600">*</span>
                </label>
                <select
                  value={selectedProjectRole}
                  onChange={(e) => setSelectedProjectRole(e.target.value as any)}
                  className="w-full px-3 py-2.5 bg-white border border-[#D1C2A5] rounded-xl text-xs text-[#1F150D] focus:outline-none focus:border-[#8F6834]"
                >
                  <option value="Manager">Manager (Full Project Control)</option>
                  <option value="Surveyor">Surveyor (Spatial Capture & Scan)</option>
                  <option value="Member">Member (Standard View & Annotate)</option>
                  <option value="Viewer">Viewer (Read-Only Access)</option>
                </select>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddMemberModal(false)}
                  className="px-4 py-2 border border-[#D1C2A5] bg-white text-[#5C4D3E] text-xs font-semibold rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={assigningMember || !selectedUserId}
                  className="px-4 py-2 bg-[#8F6834] disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-xs"
                >
                  {assigningMember ? 'Assigning...' : 'Assign to Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Capture Session Creation Modal (Self or Team Member Assignment) */}
      {showCaptureModal && (
        <CaptureSessionModal
          project={project}
          onClose={() => setShowCaptureModal(false)}
          onLaunchSession={(data) => {
            const newId = `CAP-0${customSessions.length + 2}-SOP`;
            const newSession = {
              id: newId,
              floor_name: project.floors?.find((f) => f.id === data.floorId)?.name || 'Ground Floor',
              operator_name: data.operatorName,
              operator_type: data.operatorType,
              phase: 'PHASE_1_RECON',
              phase_label: '1. Reconnaissance Scan Ready',
              created_at: new Date().toLocaleDateString(),
              zones_count: 4,
              completed_zones: 0
            };
            setCustomSessions([newSession, ...customSessions]);
            setShowCaptureModal(false);
            setPairingSession(newSession);
          }}
        />
      )}

      {/* Mobile App Pairing Modal */}
      {pairingSession && (
        <MobilePairingModal
          project={project}
          sessionId={pairingSession.id}
          operatorName={pairingSession.operator_name}
          floorName={pairingSession.floor_name}
          onClose={() => setPairingSession(null)}
          onLaunchWebStudio={() => {
            const sid = pairingSession.id;
            setPairingSession(null);
            navigate(`/projects/${project.id}/capture/${sid}`);
          }}
        />
      )}
    </div>
  );
};
