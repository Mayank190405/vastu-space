import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Package,
  Plus,
  Search,
  Filter,
  Box,
  Layers,
  MapPin,
  Eye,
  Trash2,
  Download,
  X,
  Check,
  AlertTriangle,
  RefreshCw,
  Cpu,
  ShieldAlert,
  Zap,
  Tag,
  Calendar,
  FileText,
  Info,
  Maximize2,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';
import { api } from '../../services/api';
import { Project, SpatialAsset } from '../../types';

// Supported Asset Categories per specification
const ASSET_CATEGORIES = [
  'ALL',
  'FURNITURE',
  'HVAC',
  'SAFETY',
  'ELECTRICAL',
  'LIGHTING',
  'EQUIPMENT',
  'PLUMBING',
  'APPLIANCES',
  'DOORS',
  'WINDOWS',
  'FIXTURES',
  'IT EQUIPMENT',
  'SECURITY',
  'OTHER',
] as const;

// Supported Statuses per specification
const ASSET_STATUSES = [
  'ALL',
  'ACTIVE',
  'MAINTENANCE',
  'MISSING',
  'DAMAGED',
  'ARCHIVED',
] as const;

export const AssetsPage: React.FC = () => {
  const navigate = useNavigate();

  // Core Data States
  const [projects, setProjects] = useState<Project[]>([]);
  const [assets, setAssets] = useState<SpatialAsset[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // UI View States
  const [viewMode, setViewMode] = useState<'list' | 'spatial'>('list');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [selectedProject, setSelectedProject] = useState<string>('ALL');
  const [selectedSource, setSelectedSource] = useState<string>('ALL');

  // Drawer & Modal States
  const [selectedAsset, setSelectedAsset] = useState<SpatialAsset | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [selectedAssetIds, setSelectedAssetIds] = useState<string[]>([]);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Add Asset Form State
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [newAssetForm, setNewAssetForm] = useState({
    title: '',
    category: 'FURNITURE',
    project_id: '',
    space_name: '',
    floor_name: '',
    status: 'ACTIVE',
    source: 'MANUAL',
    pos_x: '0',
    pos_y: '0',
    pos_z: '0',
    manufacturer: '',
    model: '',
    serial_number: '',
    description: '',
  });

  // Fetch real projects and assets from Go Backend
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch user's active projects
      const loadedProjects = await api.listProjects();
      const validProjects = loadedProjects || [];
      setProjects(validProjects);

      // Default project for add modal
      if (validProjects.length > 0 && !newAssetForm.project_id) {
        setNewAssetForm((prev) => ({ ...prev, project_id: validProjects[0].id }));
      }

      // 2. Fetch assets / POIs across all projects
      const allLoadedAssets = await api.listAllAssets(
        validProjects.map((p) => ({ id: p.id, name: p.name }))
      );

      // Normalize assets data structure
      const normalizedAssets: SpatialAsset[] = (allLoadedAssets || []).map((item: any) => ({
        id: item.id || `AST-${Math.random().toString(36).substring(2, 9).toUpperCase()}`,
        project_id: item.project_id,
        level_id: item.level_id,
        section_id: item.section_id,
        title: item.title || item.name || 'Unnamed Asset',
        description: item.description,
        category: (item.category || 'OTHER').toUpperCase(),
        pos_x: item.pos_x ?? 0,
        pos_y: item.pos_y ?? 0,
        pos_z: item.pos_z ?? 0,
        normal_x: item.normal_x,
        normal_y: item.normal_y,
        normal_z: item.normal_z,
        custom_metadata: item.custom_metadata || {},
        created_at: item.created_at || new Date().toISOString(),
        updated_at: item.updated_at || item.created_at || new Date().toISOString(),
        project_name: item.project_name || validProjects.find((p) => p.id === item.project_id)?.name || 'Unknown Project',
      }));

      setAssets(normalizedAssets);
    } catch (err: any) {
      console.error('Failed to fetch real assets:', err);
      setError(err.message || 'Unable to load assets from the backend server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filtered Assets Computation
  const filteredAssets = useMemo(() => {
    return assets.filter((asset) => {
      // 1. Search filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesTitle = asset.title.toLowerCase().includes(query);
        const matchesId = asset.id.toLowerCase().includes(query);
        const matchesCategory = asset.category.toLowerCase().includes(query);
        const matchesProject = (asset.project_name || '').toLowerCase().includes(query);
        const matchesSpace = (asset.custom_metadata?.space_name || '').toLowerCase().includes(query);
        const matchesMfr = (asset.custom_metadata?.manufacturer || '').toLowerCase().includes(query);
        const matchesModel = (asset.custom_metadata?.model || '').toLowerCase().includes(query);
        const matchesSerial = (asset.custom_metadata?.serial_number || '').toLowerCase().includes(query);

        if (
          !matchesTitle &&
          !matchesId &&
          !matchesCategory &&
          !matchesProject &&
          !matchesSpace &&
          !matchesMfr &&
          !matchesModel &&
          !matchesSerial
        ) {
          return false;
        }
      }

      // 2. Category Filter
      if (selectedCategory !== 'ALL' && asset.category !== selectedCategory) {
        return false;
      }

      // 3. Status Filter
      const assetStatus = (asset.custom_metadata?.status || 'ACTIVE').toUpperCase();
      if (selectedStatus !== 'ALL' && assetStatus !== selectedStatus) {
        return false;
      }

      // 4. Project Filter
      if (selectedProject !== 'ALL' && asset.project_id !== selectedProject) {
        return false;
      }

      // 5. Source Filter
      const assetSource = (asset.custom_metadata?.source || 'DETECTED').toUpperCase();
      if (selectedSource !== 'ALL') {
        if (selectedSource === 'DETECTED' && !assetSource.includes('DETECT')) return false;
        if (selectedSource === 'MANUAL' && assetSource !== 'MANUAL') return false;
        if (selectedSource === 'IMPORTED' && assetSource !== 'IMPORTED') return false;
      }

      return true;
    });
  }, [assets, searchQuery, selectedCategory, selectedStatus, selectedProject, selectedSource]);

  // Real Metric Statistics (Derived strictly from real data)
  const metrics = useMemo(() => {
    const total = assets.length;
    let detected = 0;
    let manual = 0;
    let unassigned = 0;

    assets.forEach((a) => {
      const src = (a.custom_metadata?.source || 'DETECTED').toUpperCase();
      if (src.includes('DETECT')) {
        detected++;
      } else if (src === 'MANUAL') {
        manual++;
      }

      // Check if unassigned space
      const hasSpace = a.custom_metadata?.space_name || a.level_id || a.section_id;
      if (!hasSpace) {
        unassigned++;
      }
    });

    return { total, detected, manual, unassigned };
  }, [assets]);

  // Bulk Selection Handlers
  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedAssetIds(filteredAssets.map((a) => a.id));
    } else {
      setSelectedAssetIds([]);
    }
  };

  const handleSelectOne = (id: string) => {
    setSelectedAssetIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // Create Asset Handler
  const handleCreateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAssetForm.title.trim()) return;
    if (!newAssetForm.project_id) {
      alert('Please select a project for this asset.');
      return;
    }

    setIsSubmitting(true);
    try {
      const posX = parseFloat(newAssetForm.pos_x) || 0;
      const posY = parseFloat(newAssetForm.pos_y) || 0;
      const posZ = parseFloat(newAssetForm.pos_z) || 0;

      await api.createAsset({
        project_id: newAssetForm.project_id,
        level_id: newAssetForm.floor_name || undefined,
        title: newAssetForm.title.trim(),
        category: newAssetForm.category,
        pos_x: posX,
        pos_y: posY,
        pos_z: posZ,
        description: newAssetForm.description.trim(),
        custom_metadata: {
          status: newAssetForm.status,
          source: newAssetForm.source,
          space_name: newAssetForm.space_name.trim(),
          floor_name: newAssetForm.floor_name.trim(),
          manufacturer: newAssetForm.manufacturer.trim(),
          model: newAssetForm.model.trim(),
          serial_number: newAssetForm.serial_number.trim(),
        },
      });

      setIsAddModalOpen(false);
      setNewAssetForm({
        title: '',
        category: 'FURNITURE',
        project_id: projects[0]?.id || '',
        space_name: '',
        floor_name: '',
        status: 'ACTIVE',
        source: 'MANUAL',
        pos_x: '0',
        pos_y: '0',
        pos_z: '0',
        manufacturer: '',
        model: '',
        serial_number: '',
        description: '',
      });

      // Reload real assets
      await loadData();
    } catch (err: any) {
      alert(`Failed to create asset: ${err.message || 'Unknown error'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Asset Handler
  const handleDeleteAsset = async (assetId: string) => {
    try {
      await api.deletePOI(assetId);
      if (selectedAsset?.id === assetId) {
        setSelectedAsset(null);
      }
      setSelectedAssetIds((prev) => prev.filter((id) => id !== assetId));
      setDeleteConfirmId(null);
      await loadData();
    } catch (err: any) {
      alert(`Failed to delete asset: ${err.message}`);
    }
  };

  // Bulk Export CSV Handler
  const handleExportCSV = () => {
    const exportItems = assets.filter((a) => selectedAssetIds.includes(a.id));
    if (exportItems.length === 0) return;

    const headers = [
      'Asset ID',
      'Name',
      'Category',
      'Project',
      'Space',
      'Status',
      'Source',
      'Position X',
      'Position Y',
      'Position Z',
      'Manufacturer',
      'Model',
      'Serial Number',
      'Created At',
    ];

    const rows = exportItems.map((a) => [
      `"${a.id}"`,
      `"${a.title.replace(/"/g, '""')}"`,
      `"${a.category}"`,
      `"${(a.project_name || '').replace(/"/g, '""')}"`,
      `"${(a.custom_metadata?.space_name || '').replace(/"/g, '""')}"`,
      `"${a.custom_metadata?.status || 'ACTIVE'}"`,
      `"${a.custom_metadata?.source || 'DETECTED'}"`,
      a.pos_x,
      a.pos_y,
      a.pos_z,
      `"${(a.custom_metadata?.manufacturer || '').replace(/"/g, '""')}"`,
      `"${(a.custom_metadata?.model || '').replace(/"/g, '""')}"`,
      `"${(a.custom_metadata?.serial_number || '').replace(/"/g, '""')}"`,
      `"${a.created_at}"`,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `vastu_assets_export_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Render Category Badge Color & Icon
  const renderCategoryBadge = (category: string) => {
    const cat = category.toUpperCase();
    let badgeColor = 'bg-[#2B2219]/60 text-[#D4C3A3] border-[#3B3228]';

    if (cat === 'HVAC' || cat === 'EQUIPMENT') {
      badgeColor = 'bg-blue-900/30 text-blue-300 border-blue-800/40';
    } else if (cat === 'SAFETY') {
      badgeColor = 'bg-red-900/30 text-red-300 border-red-800/40';
    } else if (cat === 'ELECTRICAL' || cat === 'LIGHTING') {
      badgeColor = 'bg-amber-900/30 text-amber-300 border-amber-800/40';
    } else if (cat === 'FURNITURE') {
      badgeColor = 'bg-[#C5A059]/15 text-[#D4C3A3] border-[#C5A059]/30';
    }

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${badgeColor}`}>
        <Tag className="w-3 h-3" />
        {cat}
      </span>
    );
  };

  // Render Status Badge
  const renderStatusBadge = (status?: string) => {
    const st = (status || 'ACTIVE').toUpperCase();
    let color = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
    let dot = 'bg-emerald-400';

    if (st === 'MAINTENANCE') {
      color = 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      dot = 'bg-amber-400 animate-pulse';
    } else if (st === 'MISSING' || st === 'DAMAGED') {
      color = 'bg-red-500/15 text-red-400 border-red-500/30';
      dot = 'bg-red-400';
    } else if (st === 'ARCHIVED' || st === 'INACTIVE') {
      color = 'bg-neutral-500/15 text-neutral-400 border-neutral-500/30';
      dot = 'bg-neutral-500';
    }

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${color}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
        {st}
      </span>
    );
  };

  // Render Source Badge
  const renderSourceBadge = (source?: string) => {
    const src = (source || 'DETECTED').toUpperCase();
    const isAuto = src.includes('DETECT');

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium border ${
        isAuto
          ? 'bg-purple-950/40 text-purple-300 border-purple-800/40'
          : 'bg-neutral-900/60 text-neutral-300 border-neutral-700/50'
      }`}>
        {isAuto ? <Cpu className="w-3 h-3 text-purple-400" /> : <Zap className="w-3 h-3 text-neutral-400" />}
        {isAuto ? 'AUTO DETECTED' : src}
      </span>
    );
  };

  return (
    <div className="space-y-6 pb-12">
      {/* 1. PAGE HEADER */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-[#2B2219]/60 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-[#2B2219] uppercase font-mono">
              ASSETS
            </h1>
            <span className="px-2 py-0.5 text-xs font-mono bg-[#C5A059]/15 text-[#9E742A] rounded border border-[#C5A059]/30">
              REAL SPATIAL OBJECTS
            </span>
          </div>
          <p className="text-sm text-[#2B2219]/70 mt-1 font-sans">
            Manage and locate physical assets across your digital spaces.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* View Mode Toggle: List vs Spatial */}
          <div className="flex items-center bg-[#E0D5C1] border border-[#C5A059]/40 rounded-lg p-1">
            <button
              onClick={() => setViewMode('list')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                viewMode === 'list'
                  ? 'bg-[#2B2219] text-[#E3DACA] shadow-sm'
                  : 'text-[#2B2219]/70 hover:text-[#2B2219]'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              List
            </button>
            <button
              onClick={() => setViewMode('spatial')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                viewMode === 'spatial'
                  ? 'bg-[#2B2219] text-[#E3DACA] shadow-sm'
                  : 'text-[#2B2219]/70 hover:text-[#2B2219]'
              }`}
            >
              <Box className="w-3.5 h-3.5" />
              Spatial
            </button>
          </div>

          {/* Primary Action: + Add Asset */}
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#2B2219] hover:bg-[#3B3228] text-[#E3DACA] text-sm font-semibold rounded-lg shadow-sm transition-all border border-[#C5A059]/30 hover:border-[#C5A059]"
          >
            <Plus className="w-4 h-4 text-[#C5A059]" />
            Add Asset
          </button>
        </div>
      </div>

      {/* 2. REAL ASSET SUMMARY METRICS */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* TOTAL ASSETS */}
        <div className="bg-[#EADFCB]/80 border border-[#C5A059]/30 rounded-xl p-4 transition-all hover:border-[#C5A059]/60">
          <div className="flex items-center justify-between text-xs font-mono text-[#2B2219]/70 uppercase tracking-wider">
            <span>TOTAL ASSETS</span>
            <Package className="w-4 h-4 text-[#C5A059]" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-[#2B2219]">
              {loading ? '-' : metrics.total}
            </span>
            <span className="text-xs text-[#2B2219]/60">records</span>
          </div>
        </div>

        {/* AUTO DETECTED */}
        <div className="bg-[#EADFCB]/80 border border-[#C5A059]/30 rounded-xl p-4 transition-all hover:border-[#C5A059]/60">
          <div className="flex items-center justify-between text-xs font-mono text-[#2B2219]/70 uppercase tracking-wider">
            <span>AUTO DETECTED</span>
            <Cpu className="w-4 h-4 text-purple-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-[#2B2219]">
              {loading ? '-' : metrics.detected}
            </span>
            <span className="text-xs text-[#2B2219]/60">AI spatial</span>
          </div>
        </div>

        {/* MANUAL */}
        <div className="bg-[#EADFCB]/80 border border-[#C5A059]/30 rounded-xl p-4 transition-all hover:border-[#C5A059]/60">
          <div className="flex items-center justify-between text-xs font-mono text-[#2B2219]/70 uppercase tracking-wider">
            <span>MANUAL</span>
            <Zap className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-[#2B2219]">
              {loading ? '-' : metrics.manual}
            </span>
            <span className="text-xs text-[#2B2219]/60">user added</span>
          </div>
        </div>

        {/* UNASSIGNED */}
        <div className="bg-[#EADFCB]/80 border border-[#C5A059]/30 rounded-xl p-4 transition-all hover:border-[#C5A059]/60">
          <div className="flex items-center justify-between text-xs font-mono text-[#2B2219]/70 uppercase tracking-wider">
            <span>UNASSIGNED</span>
            <AlertTriangle className="w-4 h-4 text-orange-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-[#2B2219]">
              {loading ? '-' : metrics.unassigned}
            </span>
            <span className="text-xs text-[#2B2219]/60">no space link</span>
          </div>
        </div>
      </div>

      {/* 3. SEARCH & FILTERS BAR */}
      <div className="bg-[#EADFCB]/60 border border-[#C5A059]/30 rounded-xl p-4 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#2B2219]/50" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search assets, types, projects, spaces, serial numbers..."
              className="w-full pl-10 pr-4 py-2 bg-[#E3DACA] border border-[#C5A059]/40 rounded-lg text-sm text-[#2B2219] placeholder-[#2B2219]/50 focus:outline-none focus:border-[#C5A059] focus:ring-1 focus:ring-[#C5A059]"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#2B2219]/50 hover:text-[#2B2219]"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Status Pills */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 lg:pb-0 scrollbar-none">
            {ASSET_STATUSES.map((st) => (
              <button
                key={st}
                onClick={() => setSelectedStatus(st)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium font-mono transition-all whitespace-nowrap ${
                  selectedStatus === st
                    ? 'bg-[#2B2219] text-[#E3DACA] shadow-sm'
                    : 'bg-[#E3DACA]/60 text-[#2B2219]/70 hover:bg-[#E3DACA] hover:text-[#2B2219]'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Dropdown Filters Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-[#C5A059]/20">
          {/* Asset Category Filter */}
          <div>
            <label className="block text-[11px] font-mono text-[#2B2219]/70 uppercase mb-1">
              Asset Type
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full px-3 py-1.5 bg-[#E3DACA] border border-[#C5A059]/40 rounded-lg text-xs text-[#2B2219] focus:outline-none focus:border-[#C5A059]"
            >
              {ASSET_CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat === 'ALL' ? 'All Asset Types' : cat}
                </option>
              ))}
            </select>
          </div>

          {/* Project Filter */}
          <div>
            <label className="block text-[11px] font-mono text-[#2B2219]/70 uppercase mb-1">
              Project
            </label>
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="w-full px-3 py-1.5 bg-[#E3DACA] border border-[#C5A059]/40 rounded-lg text-xs text-[#2B2219] focus:outline-none focus:border-[#C5A059]"
            >
              <option value="ALL">All Projects</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Detection Source Filter */}
          <div>
            <label className="block text-[11px] font-mono text-[#2B2219]/70 uppercase mb-1">
              Detection Source
            </label>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="w-full px-3 py-1.5 bg-[#E3DACA] border border-[#C5A059]/40 rounded-lg text-xs text-[#2B2219] focus:outline-none focus:border-[#C5A059]"
            >
              <option value="ALL">All Sources</option>
              <option value="DETECTED">Auto Detected</option>
              <option value="MANUAL">Manual</option>
              <option value="IMPORTED">Imported</option>
            </select>
          </div>
        </div>
      </div>

      {/* 4. BULK ACTION BAR */}
      {selectedAssetIds.length > 0 && (
        <div className="bg-[#2B2219] text-[#E3DACA] px-4 py-3 rounded-xl flex items-center justify-between shadow-lg border border-[#C5A059]/40 animate-fade-in">
          <div className="flex items-center gap-3 text-sm">
            <span className="font-mono font-semibold text-[#C5A059]">
              {selectedAssetIds.length} {selectedAssetIds.length === 1 ? 'asset' : 'assets'} selected
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportCSV}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#3B3228] hover:bg-[#4B4238] text-xs font-medium rounded-lg text-[#E3DACA] border border-[#C5A059]/30 transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-[#C5A059]" />
              Export CSV
            </button>

            <button
              onClick={() => {
                if (confirm(`Delete ${selectedAssetIds.length} selected asset(s)?`)) {
                  Promise.all(selectedAssetIds.map((id) => api.deletePOI(id)))
                    .then(() => {
                      setSelectedAssetIds([]);
                      loadData();
                    })
                    .catch((err) => alert(`Delete error: ${err.message}`));
                }
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-900/60 hover:bg-red-900 text-xs font-medium rounded-lg text-red-200 border border-red-700/50 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete Selected
            </button>

            <button
              onClick={() => setSelectedAssetIds([])}
              className="p-1 hover:bg-[#3B3228] rounded-md text-[#E3DACA]/70 hover:text-[#E3DACA]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* 5. ERROR STATE */}
      {error && (
        <div className="bg-red-950/30 border border-red-800/50 rounded-xl p-4 flex items-center justify-between text-red-300 text-sm">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={loadData}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-900/40 hover:bg-red-900/60 border border-red-700/50 rounded-lg text-xs font-medium transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry
          </button>
        </div>
      )}

      {/* 6. MAIN CONTENT AREA (LOADING / LIST / SPATIAL / EMPTY) */}
      {loading ? (
        // Loading State
        <div className="bg-[#EADFCB]/60 border border-[#C5A059]/30 rounded-xl p-8 space-y-4">
          <div className="flex items-center justify-center gap-3 text-[#2B2219]/70 py-12">
            <RefreshCw className="w-6 h-6 animate-spin text-[#C5A059]" />
            <span className="font-mono text-sm">Loading real spatial assets...</span>
          </div>
        </div>
      ) : assets.length === 0 ? (
        // Honest Empty State per spec #34
        <div className="bg-[#EADFCB]/40 border border-dashed border-[#C5A059]/40 rounded-2xl p-12 text-center space-y-4">
          <div className="w-16 h-16 bg-[#C5A059]/15 border border-[#C5A059]/30 rounded-full flex items-center justify-center mx-auto text-[#9E742A]">
            <Package className="w-8 h-8" />
          </div>
          <div className="max-w-md mx-auto space-y-1">
            <h3 className="text-lg font-bold text-[#2B2219]">
              No assets have been added or detected yet.
            </h3>
            <p className="text-xs text-[#2B2219]/70">
              Assets will appear here when they are detected from spatial captures or added manually.
            </p>
          </div>
          <div className="pt-2 flex items-center justify-center gap-3">
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#2B2219] hover:bg-[#3B3228] text-[#E3DACA] text-xs font-semibold rounded-lg shadow-sm transition-all border border-[#C5A059]/30"
            >
              <Plus className="w-4 h-4 text-[#C5A059]" />
              Add Asset
            </button>
            <button
              onClick={() => navigate('/captures')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#E3DACA] hover:bg-[#E0D5C1] text-[#2B2219] text-xs font-semibold rounded-lg shadow-sm border border-[#C5A059]/40 transition-all"
            >
              <Layers className="w-4 h-4 text-[#C5A059]" />
              Open Captures
            </button>
          </div>
        </div>
      ) : filteredAssets.length === 0 ? (
        // No Search Results per spec #35
        <div className="bg-[#EADFCB]/40 border border-[#C5A059]/30 rounded-xl p-10 text-center space-y-3">
          <p className="text-sm font-semibold text-[#2B2219]">No assets match your search.</p>
          <div className="flex items-center justify-center gap-2">
            <button
              onClick={() => setSearchQuery('')}
              className="px-3 py-1.5 bg-[#2B2219] text-[#E3DACA] text-xs font-medium rounded-lg"
            >
              Clear Search
            </button>
            <button
              onClick={() => {
                setSelectedCategory('ALL');
                setSelectedStatus('ALL');
                setSelectedProject('ALL');
                setSelectedSource('ALL');
                setSearchQuery('');
              }}
              className="px-3 py-1.5 bg-[#E3DACA] border border-[#C5A059]/40 text-[#2B2219] text-xs font-medium rounded-lg"
            >
              Clear Filters
            </button>
          </div>
        </div>
      ) : viewMode === 'spatial' ? (
        // Spatial View Mode per spec #41 & #42
        <div className="bg-[#EADFCB]/60 border border-[#C5A059]/30 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-[#C5A059]/20 pb-4">
            <div>
              <h3 className="text-sm font-bold font-mono text-[#2B2219] uppercase">
                SPATIAL ASSET DISTRIBUTION MATRIX
              </h3>
              <p className="text-xs text-[#2B2219]/70">
                Visualizing physical coordinates relative to project 3D spatial space
              </p>
            </div>
            <span className="text-xs font-mono bg-[#2B2219] text-[#C5A059] px-2.5 py-1 rounded">
              {filteredAssets.length} SPATIAL OBJECTS
            </span>
          </div>

          {/* Spatial Grid Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredAssets.map((asset) => (
              <div
                key={asset.id}
                onClick={() => setSelectedAsset(asset)}
                className="bg-[#2B2219] text-[#E3DACA] border border-[#C5A059]/30 rounded-xl p-4 space-y-3 hover:border-[#C5A059] cursor-pointer transition-all hover:scale-[1.01]"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-[10px] font-mono text-[#C5A059]">{asset.id}</span>
                    <h4 className="text-sm font-bold text-white line-clamp-1">{asset.title}</h4>
                  </div>
                  {renderStatusBadge(asset.custom_metadata?.status)}
                </div>

                <div className="text-xs text-[#E3DACA]/70 space-y-1">
                  <div className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-[#C5A059]" />
                    <span className="line-clamp-1">
                      {asset.project_name} {asset.custom_metadata?.space_name ? `/ ${asset.custom_metadata.space_name}` : ''}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 font-mono text-[11px] text-[#C5A059] bg-black/40 px-2.5 py-1 rounded border border-[#C5A059]/20">
                    <span>X: {asset.pos_x.toFixed(2)}m</span>
                    <span>Y: {asset.pos_y.toFixed(2)}m</span>
                    <span>Z: {asset.pos_z.toFixed(2)}m</span>
                  </div>
                </div>

                <div className="pt-2 flex items-center justify-between border-t border-[#3B3228]">
                  {renderSourceBadge(asset.custom_metadata?.source)}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/projects/${asset.project_id}/viewer?assetId=${asset.id}`);
                    }}
                    className="inline-flex items-center gap-1 text-xs text-[#C5A059] hover:underline font-medium"
                  >
                    <Box className="w-3.5 h-3.5" />
                    Digital Twin →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        // List / Table View Mode per spec #7 & #8
        <div className="bg-[#EADFCB]/80 border border-[#C5A059]/30 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#E0D5C1] border-b border-[#C5A059]/30 text-[11px] font-mono text-[#2B2219]/80 uppercase tracking-wider">
                  <th className="py-3 px-4 w-10 text-center">
                    <input
                      type="checkbox"
                      checked={
                        filteredAssets.length > 0 &&
                        selectedAssetIds.length === filteredAssets.length
                      }
                      onChange={handleSelectAll}
                      className="rounded border-[#C5A059]/40 text-[#2B2219] focus:ring-[#C5A059]"
                    />
                  </th>
                  <th className="py-3 px-4">ASSET</th>
                  <th className="py-3 px-4">TYPE</th>
                  <th className="py-3 px-4">PROJECT / SPACE</th>
                  <th className="py-3 px-4">STATUS</th>
                  <th className="py-3 px-4">SOURCE</th>
                  <th className="py-3 px-4">UPDATED</th>
                  <th className="py-3 px-4 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#C5A059]/20 text-xs text-[#2B2219]">
                {filteredAssets.map((asset) => {
                  const isSelected = selectedAssetIds.includes(asset.id);
                  const spaceName = asset.custom_metadata?.space_name || asset.level_id || 'Unassigned';

                  return (
                    <tr
                      key={asset.id}
                      onClick={() => setSelectedAsset(asset)}
                      className={`hover:bg-[#E0D5C1]/50 cursor-pointer transition-colors ${
                        isSelected ? 'bg-[#C5A059]/10' : ''
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3.5 px-4 text-center" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleSelectOne(asset.id)}
                          className="rounded border-[#C5A059]/40 text-[#2B2219] focus:ring-[#C5A059]"
                        />
                      </td>

                      {/* ASSET NAME & ID */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-[#2B2219] border border-[#C5A059]/30 flex items-center justify-center text-[#C5A059] shrink-0 font-mono text-xs">
                            <Box className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="font-bold text-sm text-[#2B2219] line-clamp-1">
                              {asset.title}
                            </div>
                            <div className="font-mono text-[10px] text-[#2B2219]/60">
                              {asset.id}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* TYPE / CATEGORY */}
                      <td className="py-3.5 px-4 font-mono">
                        {renderCategoryBadge(asset.category)}
                      </td>

                      {/* PROJECT / SPACE */}
                      <td className="py-3.5 px-4">
                        <div className="font-medium text-[#2B2219]">
                          {asset.project_name}
                        </div>
                        <div className="text-[11px] text-[#2B2219]/70 flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-[#C5A059]" />
                          {spaceName}
                        </div>
                      </td>

                      {/* STATUS */}
                      <td className="py-3.5 px-4">
                        {renderStatusBadge(asset.custom_metadata?.status)}
                      </td>

                      {/* SOURCE */}
                      <td className="py-3.5 px-4 font-mono">
                        {renderSourceBadge(asset.custom_metadata?.source)}
                      </td>

                      {/* UPDATED */}
                      <td className="py-3.5 px-4 font-mono text-[11px] text-[#2B2219]/70">
                        {new Date(asset.updated_at).toLocaleDateString()}
                      </td>

                      {/* ACTIONS */}
                      <td className="py-3.5 px-4 text-right space-x-2" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => setSelectedAsset(asset)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 bg-[#2B2219] text-[#E3DACA] hover:bg-[#3B3228] text-xs font-semibold rounded transition-colors"
                        >
                          View →
                        </button>

                        <button
                          onClick={() =>
                            navigate(`/projects/${asset.project_id}/viewer?assetId=${asset.id}`)
                          }
                          title="View in Digital Twin"
                          className="inline-flex items-center justify-center p-1 bg-[#E3DACA] hover:bg-[#E0D5C1] text-[#2B2219] border border-[#C5A059]/40 rounded transition-colors"
                        >
                          <Box className="w-3.5 h-3.5 text-[#9E742A]" />
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

      {/* 7. ASSET DETAIL DRAWER per spec #14 */}
      {selectedAsset && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-xs flex justify-end animate-fade-in">
          <div className="w-full max-w-md bg-[#2B2219] text-[#E3DACA] h-full shadow-2xl border-l border-[#C5A059]/40 flex flex-col justify-between overflow-y-auto">
            {/* Drawer Header */}
            <div className="p-6 border-b border-[#3B3228] space-y-4">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setSelectedAsset(null)}
                  className="flex items-center gap-1.5 text-xs text-[#C5A059] hover:underline"
                >
                  ← Back to Assets
                </button>
                <button
                  onClick={() => setSelectedAsset(null)}
                  className="p-1 text-[#E3DACA]/60 hover:text-white rounded-md"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div>
                <div className="flex items-center justify-between gap-2">
                  <h2 className="text-xl font-bold text-white uppercase tracking-wide">
                    {selectedAsset.title}
                  </h2>
                  {renderStatusBadge(selectedAsset.custom_metadata?.status)}
                </div>
                <p className="font-mono text-xs text-[#C5A059] mt-1">{selectedAsset.id}</p>
              </div>

              {/* Digital Twin Focus Action */}
              <button
                onClick={() =>
                  navigate(`/projects/${selectedAsset.project_id}/viewer?assetId=${selectedAsset.id}`)
                }
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-[#C5A059] hover:bg-[#D4B069] text-[#2B2219] font-bold text-xs uppercase tracking-wider rounded-lg transition-all shadow-md"
              >
                <Box className="w-4 h-4" />
                View in Digital Twin
              </button>
            </div>

            {/* Drawer Body Details */}
            <div className="p-6 space-y-6 flex-1 text-xs">
              {/* Location Relationship */}
              <div className="space-y-2">
                <h3 className="font-mono text-[11px] text-[#C5A059] uppercase tracking-wider border-b border-[#3B3228] pb-1">
                  LOCATION RELATIONSHIP
                </h3>
                <div className="bg-black/30 p-3 rounded-lg border border-[#3B3228] space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-[#E3DACA]/60">Project:</span>
                    <span className="font-semibold text-white">{selectedAsset.project_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#E3DACA]/60">Floor:</span>
                    <span className="text-[#E3DACA]">
                      {selectedAsset.custom_metadata?.floor_name || selectedAsset.level_id || 'Not specified'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#E3DACA]/60">Space / Room:</span>
                    <span className="text-[#E3DACA]">
                      {selectedAsset.custom_metadata?.space_name || 'Unassigned'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Asset Information */}
              <div className="space-y-2">
                <h3 className="font-mono text-[11px] text-[#C5A059] uppercase tracking-wider border-b border-[#3B3228] pb-1">
                  ASSET INFORMATION
                </h3>
                <div className="bg-black/30 p-3 rounded-lg border border-[#3B3228] space-y-2">
                  <div className="flex justify-between">
                    <span className="text-[#E3DACA]/60">Type / Category:</span>
                    <span>{renderCategoryBadge(selectedAsset.category)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#E3DACA]/60">Detection Source:</span>
                    <span>{renderSourceBadge(selectedAsset.custom_metadata?.source)}</span>
                  </div>
                  {selectedAsset.custom_metadata?.confidence !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-[#E3DACA]/60">AI Confidence:</span>
                      <span className="font-mono font-bold text-purple-400">
                        {Math.round(selectedAsset.custom_metadata.confidence * 100)}%
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-[#E3DACA]/60">Manufacturer:</span>
                    <span className="text-[#E3DACA]">
                      {selectedAsset.custom_metadata?.manufacturer || 'Not available'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#E3DACA]/60">Model:</span>
                    <span className="text-[#E3DACA]">
                      {selectedAsset.custom_metadata?.model || 'Not available'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#E3DACA]/60">Serial Number:</span>
                    <span className="font-mono text-[#E3DACA]">
                      {selectedAsset.custom_metadata?.serial_number || 'Not available'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#E3DACA]/60">Created:</span>
                    <span className="font-mono text-[#E3DACA]/80">
                      {new Date(selectedAsset.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Spatial Position */}
              <div className="space-y-2">
                <h3 className="font-mono text-[11px] text-[#C5A059] uppercase tracking-wider border-b border-[#3B3228] pb-1">
                  SPATIAL POSITION (METERS)
                </h3>
                {selectedAsset.pos_x !== 0 || selectedAsset.pos_y !== 0 || selectedAsset.pos_z !== 0 ? (
                  <div className="grid grid-cols-3 gap-2 text-center font-mono">
                    <div className="bg-black/40 p-2 rounded border border-[#3B3228]">
                      <span className="block text-[10px] text-[#C5A059]">X</span>
                      <span className="font-bold text-white">{selectedAsset.pos_x.toFixed(3)}</span>
                    </div>
                    <div className="bg-black/40 p-2 rounded border border-[#3B3228]">
                      <span className="block text-[10px] text-[#C5A059]">Y</span>
                      <span className="font-bold text-white">{selectedAsset.pos_y.toFixed(3)}</span>
                    </div>
                    <div className="bg-black/40 p-2 rounded border border-[#3B3228]">
                      <span className="block text-[10px] text-[#C5A059]">Z</span>
                      <span className="font-bold text-white">{selectedAsset.pos_z.toFixed(3)}</span>
                    </div>
                  </div>
                ) : (
                  <div className="bg-black/30 p-3 rounded-lg border border-[#3B3228] text-[#E3DACA]/60 italic font-mono">
                    Location unavailable
                  </div>
                )}
              </div>

              {/* Description & Notes */}
              {selectedAsset.description && (
                <div className="space-y-1">
                  <h3 className="font-mono text-[11px] text-[#C5A059] uppercase tracking-wider border-b border-[#3B3228] pb-1">
                    DESCRIPTION / NOTES
                  </h3>
                  <div className="bg-black/30 p-3 rounded-lg border border-[#3B3228] text-[#E3DACA]/90">
                    {selectedAsset.description}
                  </div>
                </div>
              )}
            </div>

            {/* Drawer Footer Actions */}
            <div className="p-6 border-t border-[#3B3228] flex items-center justify-between">
              {deleteConfirmId === selectedAsset.id ? (
                <div className="flex items-center gap-2 w-full">
                  <span className="text-xs text-red-400 font-semibold">Confirm delete?</span>
                  <button
                    onClick={() => handleDeleteAsset(selectedAsset.id)}
                    className="px-3 py-1 bg-red-600 text-white rounded text-xs font-bold"
                  >
                    Yes, Delete
                  </button>
                  <button
                    onClick={() => setDeleteConfirmId(null)}
                    className="px-2 py-1 bg-[#3B3228] text-white rounded text-xs"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <>
                  <button
                    onClick={() => setDeleteConfirmId(selectedAsset.id)}
                    className="inline-flex items-center gap-1.5 text-red-400 hover:text-red-300 text-xs font-medium"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Delete Asset
                  </button>

                  <button
                    onClick={() => setSelectedAsset(null)}
                    className="px-4 py-1.5 bg-[#3B3228] hover:bg-[#4B4238] text-white rounded-lg text-xs font-medium"
                  >
                    Close
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 8. ADD ASSET MODAL per spec #19 */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-[#2B2219] text-[#E3DACA] border border-[#C5A059]/40 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-[#3B3228] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Box className="w-5 h-5 text-[#C5A059]" />
                <h3 className="text-base font-bold text-white uppercase tracking-wider font-mono">
                  ADD NEW PHYSICAL ASSET
                </h3>
              </div>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="p-1 text-[#E3DACA]/60 hover:text-white rounded-md"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleCreateAsset} className="p-6 space-y-4 text-xs">
              {/* Step 1: Asset Name */}
              <div>
                <label className="block font-mono text-[#C5A059] uppercase mb-1">
                  1. Asset Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder='e.g. "Conference Table", "AC Unit #04", "Fire Extinguisher"'
                  value={newAssetForm.title}
                  onChange={(e) => setNewAssetForm({ ...newAssetForm, title: e.target.value })}
                  className="w-full px-3 py-2 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059]"
                />
              </div>

              {/* Step 2 & 3: Category & Project */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-mono text-[#C5A059] uppercase mb-1">
                    2. Asset Type *
                  </label>
                  <select
                    value={newAssetForm.category}
                    onChange={(e) => setNewAssetForm({ ...newAssetForm, category: e.target.value })}
                    className="w-full px-3 py-2 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059]"
                  >
                    {ASSET_CATEGORIES.filter((c) => c !== 'ALL').map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-mono text-[#C5A059] uppercase mb-1">
                    3. Target Project *
                  </label>
                  <select
                    required
                    value={newAssetForm.project_id}
                    onChange={(e) => setNewAssetForm({ ...newAssetForm, project_id: e.target.value })}
                    className="w-full px-3 py-2 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059]"
                  >
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Step 4: Space & Floor */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-mono text-[#C5A059] uppercase mb-1">
                    4. Space / Room Name
                  </label>
                  <input
                    type="text"
                    placeholder='e.g. "Conference Room"'
                    value={newAssetForm.space_name}
                    onChange={(e) => setNewAssetForm({ ...newAssetForm, space_name: e.target.value })}
                    className="w-full px-3 py-2 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059]"
                  />
                </div>

                <div>
                  <label className="block font-mono text-[#C5A059] uppercase mb-1">
                    Floor Level
                  </label>
                  <input
                    type="text"
                    placeholder='e.g. "Floor 2"'
                    value={newAssetForm.floor_name}
                    onChange={(e) => setNewAssetForm({ ...newAssetForm, floor_name: e.target.value })}
                    className="w-full px-3 py-2 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059]"
                  />
                </div>
              </div>

              {/* Step 5: Spatial Coordinates */}
              <div>
                <label className="block font-mono text-[#C5A059] uppercase mb-1">
                  5. Spatial Position (X, Y, Z meters)
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <input
                    type="number"
                    step="0.01"
                    placeholder="X pos"
                    value={newAssetForm.pos_x}
                    onChange={(e) => setNewAssetForm({ ...newAssetForm, pos_x: e.target.value })}
                    className="px-3 py-2 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059] font-mono"
                  />
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Y pos"
                    value={newAssetForm.pos_y}
                    onChange={(e) => setNewAssetForm({ ...newAssetForm, pos_y: e.target.value })}
                    className="px-3 py-2 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059] font-mono"
                  />
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Z pos"
                    value={newAssetForm.pos_z}
                    onChange={(e) => setNewAssetForm({ ...newAssetForm, pos_z: e.target.value })}
                    className="px-3 py-2 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059] font-mono"
                  />
                </div>
              </div>

              {/* Step 6: Metadata */}
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block font-mono text-[#C5A059] uppercase mb-1">Manufacturer</label>
                  <input
                    type="text"
                    placeholder="e.g. LG"
                    value={newAssetForm.manufacturer}
                    onChange={(e) => setNewAssetForm({ ...newAssetForm, manufacturer: e.target.value })}
                    className="w-full px-2.5 py-1.5 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059]"
                  />
                </div>
                <div>
                  <label className="block font-mono text-[#C5A059] uppercase mb-1">Model</label>
                  <input
                    type="text"
                    placeholder="e.g. AC-2024"
                    value={newAssetForm.model}
                    onChange={(e) => setNewAssetForm({ ...newAssetForm, model: e.target.value })}
                    className="w-full px-2.5 py-1.5 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059]"
                  />
                </div>
                <div>
                  <label className="block font-mono text-[#C5A059] uppercase mb-1">Serial Number</label>
                  <input
                    type="text"
                    placeholder="SN-XXXX"
                    value={newAssetForm.serial_number}
                    onChange={(e) => setNewAssetForm({ ...newAssetForm, serial_number: e.target.value })}
                    className="w-full px-2.5 py-1.5 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059]"
                  />
                </div>
              </div>

              <div>
                <label className="block font-mono text-[#C5A059] uppercase mb-1">Description / Notes</label>
                <textarea
                  rows={2}
                  placeholder="Optional technical notes or maintenance instructions..."
                  value={newAssetForm.description}
                  onChange={(e) => setNewAssetForm({ ...newAssetForm, description: e.target.value })}
                  className="w-full px-3 py-2 bg-black/40 border border-[#3B3228] rounded-lg text-white focus:outline-none focus:border-[#C5A059]"
                />
              </div>

              {/* Submit Buttons */}
              <div className="pt-4 border-t border-[#3B3228] flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 bg-[#3B3228] hover:bg-[#4B4238] text-white rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-[#C5A059] hover:bg-[#D4B069] text-[#2B2219] rounded-lg text-xs font-bold uppercase tracking-wider shadow-md disabled:opacity-50"
                >
                  {isSubmitting ? 'Saving...' : 'Save Asset'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
