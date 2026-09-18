import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { BrandLogo } from '../brand/BrandLogo';
import {
  LayoutDashboard,
  FolderGit2,
  Building2,
  Users,
  UserCheck,
  Settings,
  Copy,
  Check,
  LogOut,
  Shield,
  Share2,
  MessageCircle,
  Menu,
  X,
  Box
} from 'lucide-react';

export const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, activeOrg, activeRole, memberships, switchOrganization, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [copiedCode, setCopiedCode] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Invite Modal
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteData, setInviteData] = useState<{ invite_url: string; whatsapp_message: string } | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);
  const [generatingInvite, setGeneratingInvite] = useState(false);

  // Pending join requests count badge
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    if (activeOrg) {
      api.listJoinRequests()
        .then((reqs) => setPendingCount(reqs?.length || 0))
        .catch(() => setPendingCount(0));
    }
  }, [activeOrg, location.pathname]);

  const copyOrgCode = () => {
    if (activeOrg?.org_code) {
      navigator.clipboard.writeText(activeOrg.org_code);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
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

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { label: '3D Spatial Viewer', path: '/viewer', icon: Box },
    { label: 'Spatial Projects', path: '/projects', icon: FolderGit2 },
    { label: 'Organization', path: '/organization', icon: Building2 },
    { label: 'Team Members', path: '/organization/members', icon: Users },
    { label: 'Join Requests', path: '/organization/requests', icon: UserCheck, badge: pendingCount },
    { label: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-[#E3DACA] text-[#2B2219] flex flex-col md:flex-row">
      {/* Mobile Top Nav */}
      <div className="md:hidden flex items-center justify-between p-4 border-b border-[#C5A059]/30 bg-[#241A13] sticky top-0 z-40">
        <Link to="/dashboard" className="flex items-center space-x-2">
          <BrandLogo size="sm" theme="dark" />
        </Link>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 rounded-lg bg-[#3D2C1F] border border-[#C5A059]/50 text-[#F2DFB8]"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Sidebar for Desktop */}
      <aside
        className={`fixed md:sticky top-0 inset-y-0 left-0 z-50 w-64 bg-[#241A13] border-r border-[#C5A059]/30 flex flex-col justify-between transition-transform duration-200 shadow-2xl backdrop-blur-xl ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="p-5 space-y-6">
          {/* Logo */}
          <div className="flex items-center justify-between">
            <Link to="/dashboard" className="flex items-center space-x-3 group">
              <BrandLogo size="md" theme="dark" />
            </Link>
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="md:hidden text-[#C4B4A2] hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Active Organization Widget */}
          {activeOrg && (
            <div className="p-3.5 rounded-xl bg-[#1C140E] border border-[#C5A059]/35 space-y-2 shadow-inner">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold text-[#A6998A] tracking-wider">
                  Workspace
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-[#3D2C1F] border border-[#C5A059]/50 text-[#F2DFB8] font-bold uppercase tracking-wider">
                  {activeRole || 'Member'}
                </span>
              </div>
              {memberships.filter((m) => m.status === 'active' && (m.org_name || m.organization)).length > 1 ? (
                <select
                  value={activeOrg.id}
                  onChange={(e) => switchOrganization(e.target.value)}
                  className="w-full text-xs font-semibold text-[#F7F2EA] bg-[#2A1E15] border border-[#C5A059]/40 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#C5A059] truncate"
                >
                  {memberships
                    .filter((m) => m.status === 'active')
                    .map((m) => (
                      <option key={m.org_id} value={m.org_id}>
                        {m.organization?.name || m.org_name || activeOrg.name}
                      </option>
                    ))}
                </select>
              ) : (
                <div className="text-xs font-bold text-white truncate font-serif-brand tracking-wide">
                  {activeOrg.name}
                </div>
              )}
              <div className="flex items-center justify-between pt-1.5 border-t border-[#36271C]">
                <span className="font-mono text-[11px] text-[#F2DFB8] font-bold tracking-wider">
                  {activeOrg.org_code}
                </span>
                <button
                  onClick={copyOrgCode}
                  title="Copy 12-char Organization Code"
                  className="p-1 rounded hover:bg-[#2A1E15] text-[#C4B4A2] hover:text-[#F2DFB8] transition-colors"
                >
                  {copiedCode ? <Check className="w-3.5 h-3.5 text-[#F2DFB8]" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>
          )}

          {/* Nav Items */}
          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const active = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                    active
                      ? 'bg-gradient-to-r from-[#C59A4E] to-[#B08538] text-white shadow-md shadow-[#C59A4E]/30'
                      : 'text-[#C4B4A2] hover:text-white hover:bg-[#2F2218]'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className={`w-4 h-4 ${active ? 'text-white' : 'text-[#8F6834]'}`} />
                    <span>{item.label}</span>
                  </div>
                  {Boolean(item.badge && item.badge > 0) && (
                    <span className="px-1.5 py-0.5 rounded-full bg-white text-[#241A13] text-[10px] font-black shadow-sm">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Card at bottom */}
        <div className="p-4 border-t border-[#C5A059]/25 bg-[#1C140E]">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3 truncate">
              <div className="w-8 h-8 rounded-full bg-[#3D2C1F] border border-[#C5A059]/40 flex items-center justify-center text-xs font-black text-[#F2DFB8] shrink-0 shadow-sm">
                {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="truncate">
                <div className="text-xs font-bold text-white truncate">{user?.full_name}</div>
                <div className="text-[10px] text-[#BCAEA0] truncate font-medium">{user?.email}</div>
              </div>
            </div>

            <button
              onClick={() => logout()}
              title="Sign Out"
              className="p-1.5 rounded-lg text-[#C4B4A2] hover:text-red-400 hover:bg-red-950/30 transition-colors shrink-0"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-16 border-b border-[#C5A059]/30 bg-[#EDE6DB]/90 backdrop-blur-lg px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <span className="text-sm text-[#241A12] capitalize font-bold tracking-wide">
              {location.pathname.replace('/', '').replace('-', ' ') || 'Dashboard'}
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={openInviteModal}
              className="btn-brand-primary py-1.5 px-3.5 rounded-xl text-xs font-bold flex items-center space-x-2"
            >
              <Share2 className="w-3.5 h-3.5" />
              <span>Invite Team</span>
            </button>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-6 md:p-8 flex-1">{children}</div>
      </div>

      {/* Global Invite Team Modal */}
      {inviteModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full p-6 rounded-2xl border border-[#C5A059]/30 space-y-4 shadow-2xl animate-in fade-in zoom-in-95">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-base font-bold text-white flex items-center space-x-2 font-serif-brand">
                  <Share2 className="w-4 h-4 text-[#C5A059]" />
                  <span>Invite to {activeOrg?.name}</span>
                </h3>
                <p className="text-xs text-[#A6998A] mt-1">
                  Share this link with colleagues. When they register, their request will appear in your Join Requests queue.
                </p>
              </div>
              <button
                onClick={() => setInviteModalOpen(false)}
                className="text-[#A6998A] hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {generatingInvite ? (
              <div className="py-6 text-center text-xs text-[#A6998A]">
                Generating invitation link...
              </div>
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
