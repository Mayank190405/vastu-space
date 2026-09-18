import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { BrandLogo } from '../../components/brand/BrandLogo';
import { Clock, RefreshCw, LogOut } from 'lucide-react';

export const PendingApprovalPage: React.FC = () => {
  const { user, refreshProfile, logout } = useAuth();
  const navigate = useNavigate();
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleCheckStatus = async () => {
    setChecking(true);
    setMessage(null);
    try {
      await refreshProfile();
      const me = await api.getMe();
      if (me.active_org) {
        navigate('/dashboard', { replace: true });
        return;
      }
      setMessage('Your request is still awaiting review by the Organization Administrator.');
    } catch {
      setMessage('Could not refresh status. Please verify your connection.');
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#E3DACA] text-[#2B2219] flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] bg-[#C5A059]/15 blur-[140px] rounded-full pointer-events-none" />

      <div className="glass-panel max-w-md w-full p-8 rounded-2xl border border-[#C5A059]/30 text-center space-y-6 relative z-10 shadow-2xl">
        <div className="flex justify-center items-center mb-2">
          <BrandLogo size="md" theme="light" />
        </div>

        <div className="w-16 h-16 bg-[#EDE6DB] border border-[#8F6834] rounded-full flex items-center justify-center mx-auto text-[#8F6834] shadow-xl shadow-[#8F6834]/20">
          <Clock className="w-8 h-8 animate-pulse text-[#8F6834]" />
        </div>

        <div>
          <span className="inline-block px-3 py-1 rounded-full bg-[#EDE6DB] border border-[#C5A059]/50 text-[#8F6834] text-xs font-bold mb-2">
            PENDING APPROVAL
          </span>
          <h1 className="text-xl font-bold text-[#2B2219] font-serif-brand">Membership Request Submitted</h1>
          <p className="text-xs text-[#695541] mt-2 leading-relaxed">
            Welcome, <strong className="text-[#8F6834] font-bold">{user?.full_name || 'Team Member'}</strong>. Your request to join the organization workspace is waiting for verification and role assignment by an Owner or Administrator.
          </p>
        </div>

        {message && (
          <div className="p-3 bg-white border border-[#C5A059]/40 rounded-xl text-xs text-[#8F6834] font-bold shadow-sm">
            {message}
          </div>
        )}

        <div className="space-y-3 pt-2">
          <button
            onClick={handleCheckStatus}
            disabled={checking}
            className="btn-brand-primary w-full py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
            <span>{checking ? 'Checking Status...' : 'Check Approval Status'}</span>
          </button>

          <button
            onClick={() => logout()}
            className="btn-brand-secondary w-full py-2.5 px-4 rounded-xl text-xs font-bold transition-all flex items-center justify-center space-x-2 shadow-sm"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  );
};
