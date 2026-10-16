import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { OrganizationMember } from '../../types';
import { Users, Search, Share2, Copy, Check, MessageCircle, Calendar } from 'lucide-react';

export const OrganizationMembersPage: React.FC = () => {
  const { activeOrg } = useAuth();
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Invite Generator
  const [inviteData, setInviteData] = useState<{ invite_url: string; whatsapp_message: string } | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);
  const [generating, setGenerating] = useState(false);

  const fetchMembers = async () => {
    try {
      setLoading(true);
      const data = await api.listMembers();
      setMembers(data || []);
    } catch (err) {
      console.error('Failed to load members:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMembers();
  }, []);

  const handleGenerateInvite = async () => {
    try {
      setGenerating(true);
      const res = await api.createInvite();
      setInviteData({
        invite_url: res.invite_url,
        whatsapp_message: res.whatsapp_message,
      });
    } catch (err) {
      console.error('Error generating invite:', err);
    } finally {
      setGenerating(false);
    }
  };

  const copyInvite = () => {
    if (inviteData?.invite_url) {
      navigator.clipboard.writeText(inviteData.invite_url);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  const safeMembers = Array.isArray(members) ? members : [];
  const filtered = safeMembers.filter(
    (m) =>
      m.user?.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.user?.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.role?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#1F150D] flex items-center space-x-2 font-serif-brand">
            <Users className="w-5 h-5 text-[#8F6834]" />
            <span>Organization Members</span>
          </h1>
          <p className="text-xs text-[#695541] mt-0.5">
            Active collaborators, employees, and administrators in {activeOrg?.name}.
          </p>
        </div>

        <button
          onClick={handleGenerateInvite}
          disabled={generating}
          className="btn-brand-primary py-2 px-4 rounded-xl text-xs font-bold flex items-center space-x-2 self-start sm:self-auto"
        >
          <Share2 className="w-4 h-4" />
          <span>{generating ? 'Generating...' : 'Invite New Colleague'}</span>
        </button>
      </div>

      {/* Invite Card if generated */}
      {inviteData && (
        <div className="p-4 rounded-2xl bg-[#241A13] border border-[#C5A059]/40 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
          <div className="space-y-1">
            <span className="text-xs font-bold text-[#F2DFB8]">Shareable Invite Link Active</span>
            <div className="text-xs font-mono text-[#F4EFEB] break-all">{inviteData.invite_url}</div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={copyInvite}
              className="py-1.5 px-3 bg-[#3D2C1F] hover:bg-[#4E3827] border border-[#C5A059]/40 text-xs font-bold rounded-lg text-[#F2DFB8] flex items-center space-x-1.5 transition-colors"
            >
              {copiedLink ? <Check className="w-3.5 h-3.5 text-[#F2DFB8]" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedLink ? 'Copied' : 'Copy'}</span>
            </button>
            <a
              href={`https://wa.me/?text=${encodeURIComponent(inviteData.whatsapp_message)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="py-1.5 px-3 bg-[#25D366] hover:bg-[#20bd5a] text-black font-bold text-xs rounded-lg flex items-center space-x-1.5 shadow-sm"
            >
              <MessageCircle className="w-3.5 h-3.5" />
              <span>WhatsApp</span>
            </a>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#8F6834] pointer-events-none" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter members by name, email, or role..."
          className="input-brand w-full pl-10 pr-4 py-2 bg-white border border-[#C5A059]/40 rounded-xl text-xs text-[#241A12] placeholder-[#9C8E7E] focus:outline-none focus:ring-2 focus:ring-[#8F6834]/20 focus:border-[#8F6834] shadow-sm"
        />
      </div>

      {/* Members Directory */}
      {loading ? (
        <div className="py-12 text-center text-xs text-[#695541]">Loading members...</div>
      ) : filtered.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl border border-[#C5A059]/30 text-center space-y-2">
          <Users className="w-8 h-8 text-[#8F6834] mx-auto" />
          <h3 className="text-sm font-bold text-[#2E2218] font-serif-brand">No Members Match Filter</h3>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl border border-[#C5A059]/30 overflow-hidden divide-y divide-[#E8DEC9] shadow-md">
          {filtered.map((m) => (
            <div
              key={m.id}
              className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-[#FAF7F2] transition-colors"
            >
              <div className="flex items-center space-x-3.5">
                <div className="w-10 h-10 rounded-full bg-[#EDE6DB] border border-[#C5A059]/50 flex items-center justify-center text-xs font-bold text-[#8F6834] uppercase shadow-sm">
                  {m.user?.full_name ? m.user.full_name.charAt(0) : 'U'}
                </div>
                <div>
                  <div className="text-sm font-bold text-[#1F150D] flex items-center space-x-2">
                    <span>{m.user?.full_name || 'Member'}</span>
                    <span className="px-2 py-0.5 rounded-full bg-[#EDE6DB] border border-[#C5A059]/50 text-[10px] font-bold text-[#8F6834] uppercase">
                      {m.role}
                    </span>
                  </div>
                  <div className="text-xs text-[#695541] mt-0.5">{m.user?.email || 'N/A'}</div>
                </div>
              </div>

              <div className="flex items-center space-x-4 text-xs text-[#695541]">
                <span className="flex items-center space-x-1 text-[11px] text-[#8C7A68]">
                  <Calendar className="w-3.5 h-3.5 text-[#8F6834]" />
                  <span>Joined {new Date(m.created_at).toLocaleDateString()}</span>
                </span>
                <span className="px-2.5 py-1 rounded-full bg-[#EDE6DB] border border-[#C5A059]/50 text-[#8F6834] text-[10px] font-bold uppercase">
                  {m.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
