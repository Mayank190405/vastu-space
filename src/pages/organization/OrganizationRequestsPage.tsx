import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { OrganizationJoinRequest } from '../../types';
import { UserCheck, UserX, Clock, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react';

export const OrganizationRequestsPage: React.FC = () => {
  const { activeOrg } = useAuth();
  const [requests, setRequests] = useState<OrganizationJoinRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Modal
  const [selectedReq, setSelectedReq] = useState<OrganizationJoinRequest | null>(null);
  const [assignedRole, setAssignedRole] = useState<string>('Employee');
  const [processing, setProcessing] = useState(false);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listJoinRequests();
      setRequests(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch join requests');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleApprove = async () => {
    if (!selectedReq) return;
    setProcessing(true);
    setError(null);
    try {
      await api.reviewJoinRequest(selectedReq.id, 'APPROVED', assignedRole);
      setSuccess(`Approved ${selectedReq.applicant_name} as ${assignedRole}`);
      setSelectedReq(null);
      await fetchRequests();
    } catch (err: any) {
      setError(err.message || 'Approval failed');
    } finally {
      setProcessing(false);
    }
  };

  const handleReject = async (reqId: string, name: string) => {
    if (!confirm(`Are you sure you want to reject ${name}'s join request?`)) return;
    setProcessing(true);
    setError(null);
    try {
      await api.reviewJoinRequest(reqId, 'REJECTED', '');
      setSuccess(`Rejected request from ${name}`);
      await fetchRequests();
    } catch (err: any) {
      setError(err.message || 'Rejection failed');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#1F150D] flex items-center space-x-2 font-serif-brand">
            <Clock className="w-5 h-5 text-[#8F6834]" />
            <span>Pending Join Requests</span>
          </h1>
          <p className="text-xs text-[#695541] mt-0.5">
            Review and grant organization access permissions to incoming employee applications.
          </p>
        </div>

        <button
          onClick={fetchRequests}
          disabled={loading}
          className="btn-brand-secondary p-2.5 rounded-xl text-[#8F6834] shadow-sm"
          title="Refresh"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

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

      {loading ? (
        <div className="py-12 text-center text-xs text-[#695541]">Loading pending requests...</div>
      ) : (!Array.isArray(requests) || requests.length === 0) ? (
        <div className="glass-panel p-12 rounded-2xl border border-[#C5A059]/30 text-center space-y-2 shadow-md">
          <UserCheck className="w-10 h-10 text-[#8F6834] mx-auto" />
          <h3 className="text-sm font-bold text-[#2E2218] font-serif-brand">All Requests Clear</h3>
          <p className="text-xs text-[#695541]">There are no pending join requests requiring review at this time.</p>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl border border-[#C5A059]/30 overflow-hidden divide-y divide-[#E8DEC9] shadow-md">
          {requests.map((r) => (
            <div
              key={r.id}
              className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-[#FAF7F2] transition-colors"
            >
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-sm text-[#1F150D]">{r.applicant_name}</span>
                  <span className="px-2 py-0.5 rounded-full bg-[#EDE6DB] border border-[#C5A059]/50 text-[#8F6834] text-[10px] font-bold">
                    PENDING APPROVAL
                  </span>
                </div>
                <div className="text-xs text-[#695541]">
                  {r.applicant_email} {r.applicant_phone ? `• ${r.applicant_phone}` : ''}
                </div>
                <div className="text-[10px] text-[#8C7A68]">
                  Submitted: {new Date(r.created_at).toLocaleString()}
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => {
                    setSelectedReq(r);
                    setAssignedRole('Employee');
                  }}
                  className="btn-brand-primary py-2 px-4 rounded-xl text-xs font-bold flex items-center space-x-1.5 shadow-sm"
                >
                  <UserCheck className="w-3.5 h-3.5" />
                  <span>Assign Role & Approve</span>
                </button>
                <button
                  onClick={() => handleReject(r.id, r.applicant_name)}
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

      {/* Approval Modal */}
      {selectedReq && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full p-6 rounded-2xl border border-[#C5A059]/40 space-y-4 shadow-2xl animate-in fade-in zoom-in-95">
            <div>
              <h3 className="text-base font-bold text-[#1F150D] font-serif-brand">
                Approve {selectedReq.applicant_name}
              </h3>
              <p className="text-xs text-[#695541] mt-0.5">
                Select the organizational governance role to assign to this user.
              </p>
            </div>

            <div className="space-y-2">
              {[
                { role: 'Employee', desc: 'Standard member with project capture and viewer permissions' },
                { role: 'Manager', desc: 'Can manage project deliverables, timelines, and clients' },
                { role: 'Project Manager', desc: 'Can coordinate spatial models, scans, and task queues' },
                { role: 'Admin', desc: 'Full workspace administrative & member management control' },
              ].map((item) => (
                <label
                  key={item.role}
                  onClick={() => setAssignedRole(item.role)}
                  className={`flex items-start space-x-3 p-3 rounded-xl border cursor-pointer transition-all shadow-sm ${
                    assignedRole === item.role
                      ? 'bg-[#FAF7F2] border-[#8F6834] ring-2 ring-[#8F6834]/20'
                      : 'bg-white border-[#C5A059]/35 hover:border-[#8F6834]/50'
                  }`}
                >
                  <input
                    type="radio"
                    name="modalAssignedRole"
                    checked={assignedRole === item.role}
                    onChange={() => setAssignedRole(item.role)}
                    className="mt-0.5 text-[#8F6834] focus:ring-[#8F6834]"
                  />
                  <div>
                    <div className="text-xs font-bold text-[#1F150D]">{item.role}</div>
                    <div className="text-[11px] text-[#695541]">{item.desc}</div>
                  </div>
                </label>
              ))}
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setSelectedReq(null)}
                disabled={processing}
                className="btn-brand-secondary py-2 px-4 rounded-xl text-xs font-bold shadow-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApprove}
                disabled={processing}
                className="btn-brand-primary py-2 px-5 rounded-xl text-xs font-bold shadow-sm"
              >
                {processing ? 'Confirming...' : `Approve as ${assignedRole}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
