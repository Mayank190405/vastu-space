import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { BrandLogo } from '../brand/BrandLogo';
import { Project, OrganizationDocument } from '../../types';
import {
  LayoutDashboard,
  FolderGit2,
  Box,
  Layers3,
  Cuboid,
  Activity,
  Search,
  UsersRound,
  Settings,
  Copy,
  Check,
  LogOut,
  Plus,
  Share2,
  MessageCircle,
  Menu,
  X,
  Bell,
  ArrowRight,
  FileText,
  ChevronDown,
  Building2,
  User,
  Shield,
  ExternalLink
} from 'lucide-react';

export const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, activeOrg, activeRole, memberships, switchOrganization, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [copiedCode, setCopiedCode] = useState(false);
  const [copyToastVisible, setCopyToastVisible] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [workspaceDropdownOpen, setWorkspaceDropdownOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  // Invite Modal
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteData, setInviteData] = useState<{ invite_url: string; whatsapp_message: string } | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);
  const [generatingInvite, setGeneratingInvite] = useState(false);

  // Pending join requests count badge
  const [pendingCount, setPendingCount] = useState(0);

  // Global Search Modal State
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchResults, setSearchResults] = useState<{
    projects: Project[];
    documents: OrganizationDocument[];
  }>({ projects: [], documents: [] });
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (activeOrg) {
      api.listJoinRequests()
        .then((reqs) => setPendingCount(reqs?.length || 0))
        .catch(() => setPendingCount(0));
    }
  }, [activeOrg, location.pathname]);

  // Global search query debouncer
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults({ projects: [], documents: [] });
      return;
    }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const [projs, docs] = await Promise.all([
          api.listProjects().catch(() => []),
          api.listDocuments().catch(() => []),
        ]);
        const q = searchQuery.toLowerCase();
        const filteredProjects = projs.filter(
          (p) =>
            p.name?.toLowerCase().includes(q) ||
            p.project_type?.toLowerCase().includes(q) ||
            p.address?.city?.toLowerCase().includes(q) ||
            p.address?.address_line_1?.toLowerCase().includes(q)
        );
        const filteredDocs = docs.filter((d) => d.file_name?.toLowerCase().includes(q) || d.document_type?.toLowerCase().includes(q));
        setSearchResults({ projects: filteredProjects, documents: filteredDocs });
      } catch (err) {
        console.error('Search query failed:', err);
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const copyOrgCode = () => {
    if (activeOrg?.org_code) {
      navigator.clipboard.writeText(activeOrg.org_code);
      setCopiedCode(true);
      setCopyToastVisible(true);
      setTimeout(() => setCopiedCode(false), 2000);
      setTimeout(() => setCopyToastVisible(false), 3000);
    }
  };

  const openInviteModal = async () => {
    setInviteModalOpen(true);
    if (!inviteData) {
      try {
        setGeneratingInvite(true);
        const res = await api.createInvite();
        setInviteData({
          invite_url: res.invite_url,
          whatsapp_message: res.whatsapp_message,
        });
      } catch (err) {
        console.error('Failed to create invite:', err);
      } finally {
        setGeneratingInvite(false);
      }
    }
  };

  const copyInviteLink = () => {
    if (inviteData?.invite_url) {
      navigator.clipboard.writeText(inviteData.invite_url);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  // Extract real user initials dynamically (e.g. "Mayank Bajaj" -> "MB", "Mayank" -> "M")
  const getUserInitials = () => {
    if (!user?.full_name) return 'U';
    const parts = user.full_name.trim().split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0].substring(0, 2).toUpperCase();
  };

  // STRICT SINGLE ACTIVE STATE RESOLVER
  const getActiveNavItem = (): string => {
    const p = location.pathname;
    if (p === '/dashboard') return 'dashboard';
    if (p === '/projects' || p.startsWith('/projects/')) {
      if (p.includes('/viewer')) return 'viewer';
      return 'projects';
    }
    if (p === '/viewer' || p.startsWith('/viewer') || p.startsWith('/3d') || p.startsWith('/view/')) return 'viewer';
    if (p === '/captures') return 'captures';
    if (p === '/assets') return 'assets';
    if (p === '/activity') return 'activity';
    if (p === '/search') return 'search';
    if (p === '/team' || p.startsWith('/organization')) return 'team';
    if (p === '/settings') return 'settings';
    return 'dashboard';
  };

  const activeKey = getActiveNavItem();

  const navSections = [
    {
      title: 'SPATIAL',
      items: [
        { key: 'dashboard', label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
        { key: 'projects', label: 'Projects', path: '/projects', icon: FolderGit2 },
        { key: 'viewer', label: 'Spatial Viewer', path: '/viewer', icon: Box },
        { key: 'captures', label: 'Captures', path: '/captures', icon: Layers3 },
        { key: 'assets', label: 'Assets', path: '/assets', icon: Cuboid },
      ],
    },
    {
      title: 'WORKSPACE',
      items: [
        { key: 'activity', label: 'Activity', path: '/activity', icon: Activity },
        { key: 'search', label: 'Search', path: '/search', icon: Search, onClick: () => setIsSearchOpen(true) },
      ],
    },
    {
      title: 'ORGANIZATION',
      items: [
        { key: 'team', label: 'Team', path: '/team', icon: UsersRound, badge: pendingCount },
        { key: 'settings', label: 'Settings', path: '/settings', icon: Settings },
      ],
    },
  ];

  return (
    <div className="min-h-screen bg-[#E3DACA] text-[#2B2219] flex flex-col md:flex-row">
      {/* Toast Notification for Org ID Copy */}
      {copyToastVisible && (
        <div className="fixed bottom-5 right-5 z-50 px-4 py-2.5 rounded-xl bg-[#241A13] border border-[#C5A059]/60 text-[#F2DFB8] text-xs font-bold shadow-2xl flex items-center space-x-2 animate-in fade-in slide-in-from-bottom-2">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>Organization ID copied</span>
        </div>
      )}

      {/* Mobile Top Header */}
      <div className="md:hidden flex items-center justify-between p-4 border-b border-[#C5A059]/30 bg-[#211710] sticky top-0 z-40">
        <Link to="/dashboard" className="flex items-center space-x-2">
          <BrandLogo size="sm" theme="dark" />
        </Link>
        <div className="flex items-center space-x-2">
          <Link
            to="/projects/create"
            className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-[#C5A059] to-[#9A7B3E] text-black text-xs font-bold flex items-center space-x-1 shadow"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Capture</span>
          </Link>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg bg-[#3D2C1F] border border-[#C5A059]/50 text-[#F2DFB8]"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* LEFT SIDEBAR — 220px Fixed Width */}
      <aside
        className={`fixed md:sticky top-0 inset-y-0 left-0 z-50 w-[220px] bg-[#211710] border-r border-[#C5A059]/30 flex flex-col justify-between transition-transform duration-200 shadow-2xl backdrop-blur-xl h-screen ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="p-4 space-y-4 overflow-y-auto flex-1">
          {/* 4. BRAND AREA (80–110px Compact Height) */}
          <div className="pt-2 pb-2 border-b border-[#36271C]">
            <Link to="/dashboard" className="block group">
              <BrandLogo size="md" theme="dark" showText={true} showTagline={false} />
            </Link>
          </div>

          {/* 6. WORKSPACE SELECTOR */}
          {activeOrg && (
            <div className="p-3 rounded-xl bg-[#17100A] border border-[#C5A059]/30 space-y-2 relative shadow-inner">
              {/* Header: WORKSPACE & ROLE BADGE */}
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-black uppercase text-[#8F7864] tracking-widest">
                  WORKSPACE
                </span>
                <span className="text-[9px] px-1.5 py-0.5 rounded border border-[#C5A059]/50 text-[#F2DFB8] font-extrabold uppercase tracking-wider bg-[#2A1E14]">
                  {activeRole || 'OWNER'}
                </span>
              </div>

              {/* Selectable Workspace Box */}
              <button
                onClick={() => setWorkspaceDropdownOpen(!workspaceDropdownOpen)}
                className="w-full text-left flex items-center justify-between py-1 px-1.5 rounded-lg hover:bg-[#2E2015] transition-colors group"
              >
                <div className="text-xs font-bold text-white truncate font-serif-brand pr-1">
                  {activeOrg.name}
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-[#C5A059] shrink-0 group-hover:translate-y-0.5 transition-transform" />
              </button>

              {/* Workspace Dropdown Popover */}
              {workspaceDropdownOpen && (
                <div className="absolute left-0 right-0 top-14 z-50 p-2 bg-[#1C140E] border border-[#C5A059]/50 rounded-xl shadow-2xl space-y-1 animate-in fade-in zoom-in-95">
                  <div className="px-2 py-1 text-[9px] font-black uppercase text-[#8F7864] tracking-wider border-b border-[#2E2015]">
                    Workspaces
                  </div>
                  {memberships
                    .filter((m) => m.status === 'active')
                    .map((m) => {
                      const isCurrent = m.org_id === activeOrg.id;
                      const name = m.organization?.name || m.org_name || activeOrg.name;
                      return (
                        <button
                          key={m.org_id}
                          onClick={() => {
                            switchOrganization(m.org_id);
                            setWorkspaceDropdownOpen(false);
                          }}
                          className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-bold flex items-center justify-between transition-colors ${
                            isCurrent
                              ? 'bg-[#3D2C1F] text-[#F2DFB8]'
                              : 'text-[#C4B4A2] hover:text-white hover:bg-[#2A1E15]'
                          }`}
                        >
                          <span className="truncate">{name}</span>
                        </button>
                      );
                    })}

                  <div className="pt-1 border-t border-[#2E2015] space-y-1">
                    <Link
                      to="/signup/organization"
                      onClick={() => setWorkspaceDropdownOpen(false)}
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-[11px] font-bold text-[#C5A059] hover:bg-[#2A1E15] flex items-center space-x-1.5 transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Create Workspace</span>
                    </Link>
                    <Link
                      to="/organization"
                      onClick={() => setWorkspaceDropdownOpen(false)}
                      className="w-full text-left px-2.5 py-1.5 rounded-lg text-[11px] font-bold text-[#C4B4A2] hover:bg-[#2A1E15] flex items-center space-x-1.5 transition-colors"
                    >
                      <span>Manage Workspaces →</span>
                    </Link>
                  </div>
                </div>
              )}

              {/* Organization Code Row */}
              <div className="flex items-center justify-between pt-1.5 border-t border-[#2E2015]">
                <span className="font-mono text-[10px] text-[#F2DFB8] font-extrabold tracking-wider">
                  {activeOrg.org_code}
                </span>
                <button
                  onClick={copyOrgCode}
                  title="Copy Organization ID"
                  className="px-1.5 py-0.5 rounded text-[10px] font-bold hover:bg-[#2A1E15] text-[#C4B4A2] hover:text-[#F2DFB8] transition-colors flex items-center space-x-1 border border-[#C5A059]/30"
                >
                  {copiedCode ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-[#C5A059]" />}
                  <span>{copiedCode ? 'Copied' : 'copy'}</span>
                </button>
              </div>
            </div>
          )}

          {/* NAVIGATION SECTIONS: SPATIAL, WORKSPACE, ORGANIZATION */}
          <div className="space-y-4 pt-1">
            {navSections.map((sec) => (
              <div key={sec.title} className="space-y-1">
                <div className="px-2 text-[10px] font-black uppercase text-[#8F7864] tracking-[0.14em]">
                  {sec.title}
                </div>
                <div className="space-y-0.5 pt-0.5">
                  {sec.items.map((item) => {
                    const active = activeKey === item.key;
                    const Icon = item.icon;
                    if (item.onClick) {
                      return (
                        <button
                          key={item.key}
                          onClick={() => {
                            setMobileMenuOpen(false);
                            item.onClick!();
                          }}
                          className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                            active
                              ? 'bg-gradient-to-r from-[#C59A4E] to-[#B08538] text-white shadow-md shadow-[#C59A4E]/20 font-bold'
                              : 'text-[#C4B4A2] hover:text-white hover:bg-[#2E2016]'
                          }`}
                        >
                          <div className="flex items-center space-x-2.5">
                            <Icon className={`w-4 h-4 ${active ? 'text-white' : 'text-[#8F6834]'}`} />
                            <span>{item.label}</span>
                          </div>
                        </button>
                      );
                    }
                    return (
                      <Link
                        key={item.key}
                        to={item.path}
                        onClick={() => setMobileMenuOpen(false)}
                        className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                          active
                            ? 'bg-gradient-to-r from-[#C59A4E] to-[#B08538] text-white shadow-md shadow-[#C59A4E]/20 font-bold'
                            : 'text-[#C4B4A2] hover:text-white hover:bg-[#2E2016]'
                        }`}
                      >
                        <div className="flex items-center space-x-2.5">
                          <Icon className={`w-4 h-4 ${active ? 'text-white' : 'text-[#8F6834]'}`} />
                          <span>{item.label}</span>
                        </div>
                        {Boolean(item.badge && item.badge > 0) && (
                          <span className="px-1.5 py-0.5 rounded-full bg-white text-[#211710] text-[9px] font-black shadow-sm">
                            {item.badge}
                          </span>
                        )}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 31. USER ACCOUNT AREA (Bottom of Sidebar) */}
        <div className="p-3 border-t border-[#C5A059]/25 bg-[#17100A] relative">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center space-x-2.5 truncate text-left hover:opacity-95 transition-opacity"
            >
              {/* Dynamic User Avatar Initials */}
              <div className="w-8 h-8 rounded-full bg-[#3D2C1F] border border-[#C5A059]/50 flex items-center justify-center text-xs font-black text-[#F2DFB8] shrink-0 shadow-sm">
                {getUserInitials()}
              </div>
              <div className="truncate">
                <div className="text-xs font-bold text-white truncate">{user?.full_name || 'User'}</div>
                <div className="text-[10px] text-[#A6998A] truncate font-medium">{user?.email}</div>
              </div>
            </button>

            {/* Direct Sign-Out Button [→] */}
            <button
              onClick={() => logout()}
              title="Sign Out"
              className="p-1.5 rounded-lg text-[#C4B4A2] hover:text-red-400 hover:bg-red-950/30 transition-colors shrink-0"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>

          {/* User Account Popover */}
          {userMenuOpen && (
            <div className="absolute bottom-14 left-3 right-3 z-50 p-2 bg-[#1C140E] border border-[#C5A059]/50 rounded-xl shadow-2xl space-y-1 animate-in fade-in zoom-in-95">
              <Link
                to="/settings"
                onClick={() => setUserMenuOpen(false)}
                className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-bold text-[#C4B4A2] hover:text-white hover:bg-[#2A1E15] flex items-center space-x-2 transition-colors"
              >
                <User className="w-3.5 h-3.5 text-[#C5A059]" />
                <span>Profile Settings</span>
              </Link>
              <Link
                to="/settings"
                onClick={() => setUserMenuOpen(false)}
                className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-bold text-[#C4B4A2] hover:text-white hover:bg-[#2A1E15] flex items-center space-x-2 transition-colors"
              >
                <Shield className="w-3.5 h-3.5 text-[#C5A059]" />
                <span>Security & Sessions</span>
              </Link>
              <div className="pt-1 border-t border-[#2E2015]">
                <button
                  onClick={() => {
                    setUserMenuOpen(false);
                    logout();
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-bold text-red-400 hover:bg-red-950/40 flex items-center space-x-2 transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navigation Bar */}
        <header className="h-16 border-b border-[#C5A059]/30 bg-[#EDE6DB]/90 backdrop-blur-lg px-6 flex items-center justify-between shrink-0 gap-4">
          {/* Left: Current Page Title */}
          <div className="flex items-center space-x-3 shrink-0">
            <span className="text-sm font-bold text-[#241A12] capitalize tracking-wide font-serif-brand">
              {location.pathname === '/dashboard'
                ? 'Spatial Cloud Dashboard'
                : location.pathname.replace('/', '').replace('-', ' ')}
            </span>
          </div>

          {/* Center: Global Search Bar */}
          <div className="flex-1 max-w-md hidden sm:block">
            <div className="relative">
              <Search className="w-4 h-4 text-[#8F6834] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search spaces, rooms, objects..."
                value={searchQuery}
                onFocus={() => setIsSearchOpen(true)}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setIsSearchOpen(true);
                }}
                className="w-full bg-[#FAF7F2] border border-[#C5A059]/40 rounded-xl pl-9 pr-4 py-1.5 text-xs text-[#1F150D] placeholder-[#8F7864] focus:outline-none focus:ring-1 focus:ring-[#C5A059] shadow-inner font-medium"
              />
            </div>
          </div>

          {/* Right Controls & Primary CTA */}
          <div className="flex items-center space-x-3 shrink-0">
            <button
              onClick={openInviteModal}
              title="Invite Team"
              className="p-2 rounded-xl bg-[#FAF7F2] hover:bg-[#F2EBDC] border border-[#C5A059]/40 text-[#8F6834] text-xs font-bold flex items-center space-x-1.5 transition-colors"
            >
              <Share2 className="w-4 h-4" />
              <span className="hidden md:inline">Invite</span>
            </button>

            <button
              onClick={() => setIsSearchOpen(true)}
              className="sm:hidden p-2 rounded-xl bg-[#FAF7F2] border border-[#C5A059]/40 text-[#8F6834]"
            >
              <Search className="w-4 h-4" />
            </button>

            <div className="p-2 rounded-xl bg-[#FAF7F2] border border-[#C5A059]/40 text-[#8F6834] relative">
              <Bell className="w-4 h-4" />
            </div>

            {/* PRIMARY ACTION: New Capture */}
            <Link
              to="/projects/create"
              className="btn-brand-primary py-2 px-4 rounded-xl text-xs font-bold flex items-center space-x-1.5 shadow-md hover:shadow-lg transition-all"
            >
              <Plus className="w-4 h-4" />
              <span>New Capture</span>
            </Link>
          </div>
        </header>

        {/* Global Search Modal Overlay */}
        {isSearchOpen && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-20 p-4">
            <div className="glass-panel max-w-xl w-full p-6 rounded-2xl border border-[#C5A059]/40 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 bg-[#211710] text-white">
              <div className="flex justify-between items-center pb-2 border-b border-[#C5A059]/30">
                <div className="flex items-center space-x-2 flex-1">
                  <Search className="w-4 h-4 text-[#C5A059]" />
                  <input
                    type="text"
                    autoFocus
                    placeholder="Search spaces, rooms, objects, projects..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-transparent border-none text-sm text-white placeholder-[#A6998A] focus:outline-none font-medium"
                  />
                </div>
                <button
                  onClick={() => {
                    setIsSearchOpen(false);
                    setSearchQuery('');
                  }}
                  className="text-[#A6998A] hover:text-white p-1"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {searching ? (
                <div className="py-8 text-center text-xs text-[#A6998A]">Searching spatial data...</div>
              ) : searchQuery.trim() === '' ? (
                <div className="py-8 text-center text-xs text-[#A6998A]">
                  Type to search across projects, spaces, floors, spatial objects, and documents.
                </div>
              ) : (
                <div className="space-y-4 max-h-96 overflow-y-auto pr-1">
                  {/* Projects Results */}
                  <div>
                    <div className="text-[10px] uppercase font-black text-[#C5A059] tracking-wider mb-2">
                      Projects ({searchResults.projects.length})
                    </div>
                    {searchResults.projects.length === 0 ? (
                      <div className="text-xs text-[#8F7864] italic">No matching projects found.</div>
                    ) : (
                      <div className="space-y-2">
                        {searchResults.projects.map((p) => (
                          <Link
                            key={p.id}
                            to={`/projects/${p.id}`}
                            onClick={() => {
                              setIsSearchOpen(false);
                              setSearchQuery('');
                            }}
                            className="p-3 rounded-xl bg-[#17100A] hover:bg-[#2E2015] border border-[#C5A059]/30 flex items-center justify-between transition-colors"
                          >
                            <div>
                              <div className="text-xs font-bold text-white">{p.name}</div>
                              <div className="text-[10px] text-[#A6998A]">
                                {p.project_type} · {p.address?.city || 'Location registered'}
                              </div>
                            </div>
                            <ArrowRight className="w-4 h-4 text-[#C5A059]" />
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Documents Results */}
                  <div>
                    <div className="text-[10px] uppercase font-black text-[#C5A059] tracking-wider mb-2">
                      Documents ({searchResults.documents.length})
                    </div>
                    {searchResults.documents.length === 0 ? (
                      <div className="text-xs text-[#8F7864] italic">No matching documents found.</div>
                    ) : (
                      <div className="space-y-2">
                        {searchResults.documents.map((d) => (
                          <div
                            key={d.id}
                            className="p-3 rounded-xl bg-[#17100A] border border-[#C5A059]/30 flex items-center space-x-3"
                          >
                            <FileText className="w-4 h-4 text-[#C5A059]" />
                            <div>
                              <div className="text-xs font-bold text-white">{d.file_name}</div>
                              <div className="text-[10px] text-[#A6998A]">{d.document_type}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Page Content Container */}
        <div className="p-6 md:p-8 flex-1">{children}</div>
      </div>

      {/* Global Invite Team Modal */}
      {inviteModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full p-6 rounded-2xl border border-[#C5A059]/30 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 bg-[#211710] text-white">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-base font-bold text-white flex items-center space-x-2 font-serif-brand">
                  <Share2 className="w-4 h-4 text-[#C5A059]" />
                  <span>Invite to {activeOrg?.name}</span>
                </h3>
                <p className="text-xs text-[#A6998A] mt-1">
                  Share this link with team members to onboard them to your spatial cloud workspace.
                </p>
              </div>
              <button onClick={() => setInviteModalOpen(false)} className="text-[#A6998A] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {generatingInvite ? (
              <div className="py-6 text-center text-xs text-[#A6998A]">Generating invitation link...</div>
            ) : inviteData ? (
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    readOnly
                    value={inviteData.invite_url}
                    className="input-brand flex-1 px-3 py-2 bg-[#FAF7F2] border border-[#C5A059]/40 rounded-xl text-xs font-mono text-[#1F150D] font-bold"
                  />
                  <button
                    onClick={copyInviteLink}
                    className="btn-brand-secondary px-3.5 py-2 text-xs font-bold rounded-xl flex items-center space-x-1.5 shadow-sm"
                  >
                    {copiedLink ? <Check className="w-3.5 h-3.5 text-[#8F6834]" /> : <Copy className="w-3.5 h-3.5 text-[#8F6834]" />}
                    <span>{copiedLink ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>

                <a
                  href={`https://wa.me/?text=${encodeURIComponent(inviteData.whatsapp_message)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2.5 px-4 rounded-xl bg-[#25D366] hover:bg-[#20bd5a] text-black font-bold text-xs flex items-center justify-center space-x-2 transition-colors shadow-lg shadow-[#25D366]/20"
                >
                  <MessageCircle className="w-4 h-4" />
                  <span>Share on WhatsApp</span>
                </a>
              </div>
            ) : (
              <div className="text-xs text-red-400">Could not generate invite link.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};


