import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { OrganizationMember, OrganizationJoinRequest, OrganizationDocument } from '../../types';
import {
  Building2,
  Users,
  UserCheck,
  UserX,
  Shield,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Share2,
  Copy,
  Check,
  MessageCircle
} from 'lucide-react';

export const OrganizationManagementPage: React.FC = () => {
  const { activeOrg, activeRole } = useAuth();

  const [activeTab, setActiveTab] = useState<'requests' | 'members' | 'details'>('requests');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Data states
  const [joinRequests, setJoinRequests] = useState<OrganizationJoinRequest[]>([]);
  const [members, setMembers] = useState<OrganizationMember[]>([]);

  // Approval modal state
  const [selectedRequest, setSelectedRequest] = useState<OrganizationJoinRequest | null>(null);
  const [assignedRole, setAssignedRole] = useState<string>('Employee');
  const [isProcessing, setIsProcessing] = useState(false);

  // Invite link generation state
  const [inviteLink, setInviteLink] = useState<{ url: string; whatsapp: string } | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [reqs, mems] = await Promise.all([
        api.listJoinRequests().catch(() => []),
        api.listMembers().catch(() => []),
      ]);

      setJoinRequests(Array.isArray(reqs) ? reqs : []);
      setMembers(Array.isArray(mems) ? mems : []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch organization data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleApprove = async () => {
    if (!selectedRequest) return;
    setIsProcessing(true);
    setError(null);
    try {
      await api.reviewJoinRequest(selectedRequest.id, 'APPROVED', assignedRole);
      setSuccess(`Approved ${selectedRequest.applicant_name} as ${assignedRole}`);
      setSelectedRequest(null);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to approve request');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async (requestId: string, name: string) => {
    if (!confirm(`Are you sure you want to reject ${name}'s request?`)) return;
    setIsProcessing(true);
    setError(null);
    try {
      await api.reviewJoinRequest(requestId, 'REJECTED', '');
      setSuccess(`Rejected ${name}'s join request`);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to reject request');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCreateInvite = async () => {
    try {
      const res = await api.createInvite();
      setInviteLink({
        url: res.invite_url,
        whatsapp: res.whatsapp_message,
      });
    } catch (err: any) {
      setError(err.message || 'Failed to create invitation link');
    }
  };

  const copyInvite = () => {
    if (inviteLink?.url) {
      navigator.clipboard.writeText(inviteLink.url);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[#1F150D] flex items-center space-x-2 font-serif-brand">
            <Building2 className="w-6 h-6 text-[#8F6834]" />
            <span>{activeOrg?.name} Administration</span>
          </h1>
          <p className="text-xs text-[#695541] mt-1">
            Manage team membership, approve join requests, and maintain organizational governance.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={fetchData}
            disabled={loading}
            className="btn-brand-secondary p-2.5 rounded-xl text-[#8F6834] shadow-sm"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleCreateInvite}
            className="btn-brand-primary py-2 px-4 rounded-xl text-xs font-bold flex items-center space-x-2 shadow-sm"
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>Generate Invite Link</span>
          </button>
        </div>
      </div>

      {/* Invite Link Banner if generated */}
      {inviteLink && (
        <div className="p-4 rounded-2xl bg-[#241A13] border border-[#C5A059]/40 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
          <div className="space-y-1">
            <span className="text-xs font-bold text-[#F2DFB8]">New Public Join Link Active</span>
            <div className="text-xs font-mono text-[#F4EFEB] break-all">{inviteLink.url}</div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={copyInvite}
              className="py-1.5 px-3 bg-[#3D2C1F] hover:bg-[#4E3827] border border-[#C5A059]/40 text-xs font-bold rounded-lg text-[#F2DFB8] flex items-center space-x-1.5 transition-colors"
            >
              {copiedLink ? <Check className="w-3.5 h-3.5 text-[#F2DFB8]" /> : <Copy className="w-3.5 h-3.5 text-[#F2DFB8]" />}
              <span>{copiedLink ? 'Copied' : 'Copy'}</span>
            </button>
            <a
              href={`https://wa.me/?text=${encodeURIComponent(inviteLink.whatsapp)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="py-1.5 px-3 bg-[#25D366] hover:bg-[#20bd5a] text-black text-xs font-bold rounded-lg flex items-center space-x-1.5 shadow-sm"
            >
              <MessageCircle className="w-3.5 h-3.5" />
              <span>WhatsApp</span>
            </a>
          </div>
        </div>
      )}

      {/* Feedback Banners */}
      {error && (
        <div className="p-3 rounded-xl bg-red-950/60 border border-red-800 flex items-start space-x-2 text-red-200 text-xs">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="p-3 rounded-xl bg-[#EDE6DB] border border-[#C5A059]/50 flex items-start space-x-2 text-[#8F6834] text-xs font-bold shadow-sm">
          <CheckCircle2 className="w-4 h-4 text-[#8F6834] shrink-0 mt-0.5" />
          <span>{success}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#D8CEBE] space-x-6 text-sm font-semibold">
        <button
          onClick={() => setActiveTab('requests')}
          className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
            activeTab === 'requests'
              ? 'border-[#8F6834] text-[#8F6834]'
              : 'border-transparent text-[#695541] hover:text-[#2E2218]'
          }`}
        >
          <Clock className="w-4 h-4" />
          <span>Pending Join Requests</span>
          {(joinRequests || []).length > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-[#8F6834] text-white text-[10px] font-bold">
              {(joinRequests || []).length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('members')}
          className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
            activeTab === 'members'
              ? 'border-[#8F6834] text-[#8F6834]'
              : 'border-transparent text-[#695541] hover:text-[#2E2218]'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Active Members ({(members || []).length})</span>
        </button>

        <button
          onClick={() => setActiveTab('details')}
          className={`pb-3 border-b-2 transition-all flex items-center space-x-2 ${
            activeTab === 'details'
              ? 'border-[#8F6834] text-[#8F6834]'
              : 'border-transparent text-[#695541] hover:text-[#2E2218]'
          }`}
        >
          <Building2 className="w-4 h-4" />
          <span>Organization Profile</span>
        </button>
      </div>

      {/* TAB 1: Join Requests */}
      {activeTab === 'requests' && (
        <div className="space-y-4">
          {(joinRequests || []).length === 0 ? (
            <div className="glass-panel p-12 rounded-2xl border border-[#C5A059]/30 text-center space-y-2 shadow-md">
              <Users className="w-8 h-8 text-[#8F6834] mx-auto" />
              <h3 className="text-sm font-bold text-[#2E2218] font-serif-brand">No Pending Requests</h3>
              <p className="text-xs text-[#695541]">
                New employee join requests from your invitation link will appear here for review.
              </p>
            </div>
          ) : (
            <div className="glass-panel rounded-2xl border border-[#C5A059]/30 overflow-hidden divide-y divide-[#E8DEC9] shadow-md">
              {joinRequests.map((req) => (
                <div key={req.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-[#FAF7F2] transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-sm text-[#1F150D]">{req.applicant_name}</span>
                      <span className="px-2 py-0.5 rounded-full bg-[#EDE6DB] border border-[#C5A059]/50 text-[#8F6834] text-[10px] font-bold">
                        PENDING
                      </span>
                    </div>
                    <div className="text-xs text-[#695541]">
                      {req.applicant_email} {req.applicant_phone ? `• ${req.applicant_phone}` : ''}
                    </div>
                    <div className="text-[10px] text-[#8C7A68]">
                      Applied: {new Date(req.created_at).toLocaleString()}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => {
                        setSelectedRequest(req);
                        setAssignedRole('Employee');
                      }}
                      className="btn-brand-primary py-2 px-4 rounded-xl text-xs font-bold flex items-center space-x-1.5 shadow-sm"
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      <span>Review & Approve</span>
                    </button>

                    <button
                      onClick={() => handleReject(req.id, req.applicant_name)}
                      className="btn-brand-secondary py-2 px-3.5 rounded-xl text-xs font-bold text-red-700 border-red-300/60 hover:bg-red-50 flex items-center space-x-1 shadow-sm"
                    >
                      <UserX className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Members List */}
      {activeTab === 'members' && (
        <div className="glass-panel rounded-2xl border border-[#C5A059]/30 overflow-hidden divide-y divide-[#E8DEC9] shadow-md">
          {members.map((m) => (
            <div key={m.id} className="p-4 sm:p-5 flex items-center justify-between hover:bg-[#FAF7F2] transition-colors">
              <div className="flex items-center space-x-3.5">
                <div className="w-10 h-10 rounded-full bg-[#EDE6DB] border border-[#C5A059]/50 flex items-center justify-center text-xs font-bold text-[#8F6834] shadow-sm">
                  {m.user?.full_name ? m.user.full_name.charAt(0).toUpperCase() : 'U'}
                </div>
                <div>
                  <div className="text-sm font-bold text-[#1F150D]">{m.user?.full_name || 'Member'}</div>
                  <div className="text-xs text-[#695541]">{m.user?.email || 'N/A'}</div>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <span className="px-2.5 py-1 rounded-full bg-[#EDE6DB] border border-[#C5A059]/50 text-[#8F6834] text-xs font-bold uppercase">
                  {m.role}
                </span>
                <span className="text-[11px] text-[#8C7A68] hidden sm:inline">
                  Status: {m.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB 3: Org Details */}
      {activeTab === 'details' && activeOrg && (
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-[#C5A059]/30 space-y-6 shadow-md">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-xs">
            <div>
              <span className="text-[#8F6834] uppercase font-bold text-[10px]">Official 12-char Org Code</span>
              <div className="font-mono text-lg font-black text-[#1F150D] mt-1">{activeOrg.org_code}</div>
            </div>

            <div>
              <span className="text-[#8F6834] uppercase font-bold text-[10px]">Brand / Display Name</span>
              <div className="text-[#1F150D] font-bold text-sm mt-1">{activeOrg.name}</div>
            </div>

            <div>
              <span className="text-[#8F6834] uppercase font-bold text-[10px]">Legal Entity Name</span>
              <div className="text-[#5A4838] text-sm mt-1">{activeOrg.legal_name || activeOrg.name}</div>
            </div>

            <div>
              <span className="text-[#8F6834] uppercase font-bold text-[10px]">Industry & Type</span>
              <div className="text-[#5A4838] text-sm mt-1">{activeOrg.industry || 'N/A'} ({activeOrg.org_type || 'Enterprise'})</div>
            </div>

            <div>
              <span className="text-[#8F6834] uppercase font-bold text-[10px]">Official Contact</span>
              <div className="text-[#5A4838] text-sm mt-1">{activeOrg.official_email || 'N/A'} • {activeOrg.official_phone || 'N/A'}</div>
            </div>

            <div>
              <span className="text-[#8F6834] uppercase font-bold text-[10px]">Website</span>
              <div className="text-[#8F6834] font-bold text-sm mt-1">{activeOrg.website || 'N/A'}</div>
            </div>
          </div>
        </div>
      )}

      {/* Role Assignment & Approval Modal */}
      {selectedRequest && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full p-6 rounded-2xl border border-[#C5A059]/40 space-y-4 shadow-2xl animate-in fade-in zoom-in-95">
            <div>
              <h3 className="text-base font-bold text-[#1F150D] font-serif-brand">
                Approve Join Request
              </h3>
              <p className="text-xs text-[#695541] mt-1">
                Assign a workspace permission role to <strong className="text-[#1F150D] font-bold">{selectedRequest.applicant_name}</strong>.
              </p>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#2E2218] mb-2">
                Select Assigned Role *
              </label>
              <div className="space-y-2">
                {[
                  { role: 'Employee', desc: 'Standard member with project capture and viewer permissions' },
                  { role: 'Manager', desc: 'Can manage project deliverables, timelines, and clients' },
                  { role: 'Project Manager', desc: 'Can coordinate spatial models, scans, and task queues' },
                  { role: 'Admin', desc: 'Full workspace administrative & member management control' },
                ].map((r) => (
                  <label
                    key={r.role}
                    onClick={() => setAssignedRole(r.role)}
                    className={`flex items-start space-x-3 p-3 rounded-xl border cursor-pointer transition-all shadow-sm ${
                      assignedRole === r.role
                        ? 'bg-[#FAF7F2] border-[#8F6834] ring-2 ring-[#8F6834]/20'
                        : 'bg-white border-[#C5A059]/35 hover:border-[#8F6834]/50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="assignedRole"
                      checked={assignedRole === r.role}
                      onChange={() => setAssignedRole(r.role)}
                      className="mt-0.5 text-[#8F6834] focus:ring-[#8F6834]"
                    />
                    <div>
                      <div className="text-xs font-bold text-[#1F150D]">{r.role}</div>
                      <div className="text-[11px] text-[#695541]">{r.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setSelectedRequest(null)}
                disabled={isProcessing}
                className="btn-brand-secondary py-2 px-4 rounded-xl text-xs font-bold shadow-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApprove}
                disabled={isProcessing}
                className="btn-brand-primary py-2 px-5 rounded-xl text-xs font-bold shadow-sm"
              >
                {isProcessing ? 'Confirming...' : `Approve as ${assignedRole}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
