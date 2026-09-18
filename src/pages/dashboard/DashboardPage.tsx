import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import {
  Building2,
  Users,
  Copy,
  Check,
  Share2,
  MessageCircle,
  FolderGit2,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  FileText
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user, activeOrg, activeRole } = useAuth();

  const [orgProfile, setOrgProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [copiedCode, setCopiedCode] = useState(false);
  const [copiedInvite, setCopiedInvite] = useState(false);
  const [inviteData, setInviteData] = useState<{
    invite_url: string;
    whatsapp_message: string;
  } | null>(null);
  const [generatingInvite, setGeneratingInvite] = useState(false);

  useEffect(() => {
    const fetchOrgData = async () => {
      try {
        setLoading(true);
        const data = await api.getMyOrg();
        setOrgProfile(data);
      } catch (err) {
        console.error('Failed to load org profile:', err);
      } finally {
        setLoading(false);
      }
    };
    if (activeOrg) {
      fetchOrgData();
    }
  }, [activeOrg]);

  const handleGenerateInvite = async () => {
    try {
      setGeneratingInvite(true);
      const res = await api.createInvite();
      setInviteData({
        invite_url: res.invite_url,
        whatsapp_message: res.whatsapp_message,
      });
    } catch (err) {
      console.error('Error generating invite:', err);
    } finally {
      setGeneratingInvite(false);
    }
  };

  const copyOrgCode = () => {
    if (activeOrg?.org_code) {
      navigator.clipboard.writeText(activeOrg.org_code);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    }
  };

  const copyInviteLink = () => {
    if (inviteData?.invite_url) {
      navigator.clipboard.writeText(inviteData.invite_url);
      setCopiedInvite(true);
      setTimeout(() => setCopiedInvite(false), 2000);
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl p-6 sm:p-8 bg-gradient-to-r from-[#241A13] via-[#302319] to-[#3D2C1F] border border-[#C5A059]/40 shadow-xl text-[#F7F2EA]">
        <div className="absolute top-0 right-0 w-96 h-96 bg-[#C5A059]/15 blur-[120px] rounded-full pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-[#3D2C1F] border border-[#C5A059]/50 text-[#F2DFB8] text-xs font-bold">
              <ShieldCheck className="w-3.5 h-3.5 text-[#C5A059]" />
              <span>Enterprise Workspace Active</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white font-serif-brand">
              {activeOrg?.name || 'VĀSTU Workspace'}
            </h1>
            <p className="text-xs sm:text-sm text-[#D9CAB8]">
              Welcome back, <strong className="text-white">{user?.full_name}</strong>. You are logged in with role{' '}
              <span className="font-bold text-[#F2DFB8] uppercase">{activeRole || 'Member'}</span>.
            </p>
          </div>

          {/* 12-char Org Code Card */}
          {activeOrg?.org_code && (
            <div className="bg-[#18110B] border border-[#C5A059]/40 p-4 rounded-2xl flex items-center space-x-4 shadow-xl">
              <div>
                <div className="text-[10px] uppercase font-bold text-[#C4B4A2] tracking-wider">
                  Official Org Code
                </div>
                <div className="font-mono text-xl font-black text-[#F2DFB8] tracking-[0.15em] mt-0.5">
                  {activeOrg.org_code}
                </div>
              </div>
              <button
                onClick={copyOrgCode}
                className="p-2.5 rounded-xl bg-[#2A1E14] hover:bg-[#36271C] text-[#F2DFB8] border border-[#C5A059]/40 transition-colors"
                title="Copy 12-character Organization Code"
              >
                {copiedCode ? <Check className="w-4 h-4 text-[#F2DFB8]" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Quick Stats Grid - High Contrast, No Camouflage */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm">
          <div className="flex justify-between items-center text-[#5C4A38] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider">Members</span>
            <Users className="w-4 h-4 text-[#8F6834]" />
          </div>
          <div className="text-3xl font-black text-[#1F150D] font-serif-brand">
            {orgProfile?.members_count ?? 1}
          </div>
          <span className="text-[11px] text-[#6E5945] font-medium mt-1 block">Active workspace users</span>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm">
          <div className="flex justify-between items-center text-[#5C4A38] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider">Compliance & Tax</span>
            <FileText className="w-4 h-4 text-[#8F6834]" />
          </div>
          <div className="text-base font-bold text-[#8F6834] truncate mt-1">
            {activeOrg?.legal_name ? 'Registered' : 'Pending Verification'}
          </div>
          <span className="text-[11px] text-[#6E5945] font-medium mt-1 block">GSTIN / Business Identifiers</span>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm">
          <div className="flex justify-between items-center text-[#5C4A38] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider">Spatial Projects</span>
            <FolderGit2 className="w-4 h-4 text-[#8F6834]" />
          </div>
          <div className="text-3xl font-black text-[#1F150D] font-serif-brand">0</div>
          <span className="text-[11px] text-[#6E5945] font-medium mt-1 block">Point cloud models & scans</span>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-[#C5A059]/30 shadow-sm">
          <div className="flex justify-between items-center text-[#5C4A38] mb-2 font-semibold">
            <span className="text-xs font-bold uppercase tracking-wider">Role Level</span>
            <Building2 className="w-4 h-4 text-[#8F6834]" />
          </div>
          <div className="text-lg font-bold text-[#8F6834] uppercase mt-1">
            {activeRole || 'Member'}
          </div>
          <span className="text-[11px] text-[#6E5945] font-medium mt-1 block">Workspace governance status</span>
        </div>
      </div>

      {/* Invite & Fast Action Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Invite Generator Card */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-[#C5A059]/35 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-bold text-[#1F150D] flex items-center space-x-2 font-serif-brand">
                <Share2 className="w-4 h-4 text-[#8F6834]" />
                <span>Invite Colleagues & Contractors</span>
              </h3>
              <p className="text-xs text-[#5C4A38] font-medium mt-1">
                Generate an invitation link to onboard team members directly into your space.
              </p>
            </div>

            {!inviteData && (
              <button
                onClick={handleGenerateInvite}
                disabled={generatingInvite}
                className="btn-brand-primary py-2 px-4 rounded-xl text-xs font-bold flex items-center space-x-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{generatingInvite ? 'Generating...' : 'Create Invite Link'}</span>
              </button>
            )}
          </div>

          {inviteData && (
            <div className="p-4 rounded-xl bg-white border border-[#C5A059]/35 space-y-3 shadow-sm">
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  readOnly
                  value={inviteData.invite_url}
                  className="input-brand flex-1 px-3 py-2 bg-[#FAF7F2] border border-[#C5A059]/40 rounded-lg text-xs font-mono text-[#1F150D] font-bold"
                />
                <button
                  onClick={copyInviteLink}
                  className="px-3.5 py-2 bg-white hover:bg-[#FAF7F2] border border-[#C5A059]/40 text-[#8F6834] text-xs font-bold rounded-lg flex items-center space-x-1.5 transition-colors shadow-sm"
                >
                  {copiedInvite ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedInvite ? 'Copied' : 'Copy'}</span>
                </button>
              </div>

              <div className="flex items-center space-x-3 pt-1">
                <a
                  href={`https://wa.me/?text=${encodeURIComponent(inviteData.whatsapp_message)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 rounded-lg bg-[#25D366] hover:bg-[#20bd5a] text-black font-bold text-xs flex items-center space-x-2 transition-colors shadow-sm"
                >
                  <MessageCircle className="w-4 h-4" />
                  <span>Share on WhatsApp</span>
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Organization Admin Shortcut Card */}
        <div className="glass-panel p-6 rounded-2xl border border-[#C5A059]/35 flex flex-col justify-between space-y-4">
          <div>
            <h3 className="text-lg font-bold text-[#1F150D] flex items-center space-x-2 font-serif-brand">
              <Users className="w-4 h-4 text-[#8F6834]" />
              <span>Organization Management</span>
            </h3>
            <p className="text-xs text-[#5C4A38] font-medium mt-1 leading-relaxed">
              Review pending employee join requests, approve roles, and update company profile.
            </p>
          </div>

          <Link
            to="/organization"
            className="btn-brand-primary w-full py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 transition-all group"
          >
            <span>Manage Members & Requests</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>
    </div>
  );
};
