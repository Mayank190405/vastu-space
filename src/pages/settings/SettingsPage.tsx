import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Settings, User, Shield, LogOut, CheckCircle2 } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { user, activeOrg, activeRole, logout } = useAuth();
  const [success, setSuccess] = useState<string | null>(null);

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold text-[#1F150D] flex items-center space-x-2 font-serif-brand">
          <Settings className="w-5 h-5 text-[#8F6834]" />
          <span>Account & Security Settings</span>
        </h1>
        <p className="text-xs text-[#695541] mt-0.5">
          Manage your personal credentials, identity links, and active workspace session.
        </p>
      </div>

      {success && (
        <div className="p-3 rounded-xl bg-[#EDE6DB] border border-[#C5A059]/50 flex items-center space-x-2 text-[#8F6834] text-xs font-bold shadow-sm">
          <CheckCircle2 className="w-4 h-4 text-[#8F6834]" />
          <span>{success}</span>
        </div>
      )}

      {/* User Profile Card */}
      <div className="glass-panel p-6 rounded-2xl border border-[#C5A059]/30 space-y-4 shadow-md">
        <h2 className="text-sm font-bold text-[#1F150D] flex items-center space-x-2 border-b border-[#E8DEC9] pb-3 font-serif-brand">
          <User className="w-4 h-4 text-[#8F6834]" />
          <span>User Profile</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-[#8F6834] uppercase font-bold text-[10px]">Full Name</span>
            <div className="text-[#1F150D] font-bold mt-1 text-sm">{user?.full_name}</div>
          </div>

          <div>
            <span className="text-[#8F6834] uppercase font-bold text-[10px]">Email Address</span>
            <div className="text-[#1F150D] font-bold mt-1 flex items-center space-x-2 text-sm">
              <span>{user?.email}</span>
              {user?.is_email_verified && (
                <span className="px-2 py-0.5 rounded-full bg-[#EDE6DB] border border-[#C5A059]/50 text-[10px] text-[#8F6834] font-bold">
                  VERIFIED
                </span>
              )}
            </div>
          </div>

          <div>
            <span className="text-[#8F6834] uppercase font-bold text-[10px]">Mobile Phone</span>
            <div className="text-[#5A4838] font-bold mt-1">{user?.phone || 'Not registered'}</div>
          </div>

          <div>
            <span className="text-[#8F6834] uppercase font-bold text-[10px]">Authentication Method</span>
            <div className="text-[#5A4838] font-bold mt-1 uppercase">{user?.auth_provider || 'Email OTP'}</div>
          </div>
        </div>
      </div>

      {/* Workspace Governance */}
      <div className="glass-panel p-6 rounded-2xl border border-[#C5A059]/30 space-y-4 shadow-md">
        <h2 className="text-sm font-bold text-[#1F150D] flex items-center space-x-2 border-b border-[#E8DEC9] pb-3 font-serif-brand">
          <Shield className="w-4 h-4 text-[#8F6834]" />
          <span>Workspace Session & Governance</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-[#8F6834] uppercase font-bold text-[10px]">Active Organization</span>
            <div className="text-[#1F150D] font-bold mt-1 text-sm font-serif-brand">{activeOrg?.name || 'No active organization'}</div>
          </div>

          <div>
            <span className="text-[#8F6834] uppercase font-bold text-[10px]">Assigned Governance Role</span>
            <div className="text-[#8F6834] font-bold uppercase mt-1">{activeRole || 'Member'}</div>
          </div>

          <div>
            <span className="text-[#8F6834] uppercase font-bold text-[10px]">Organization 12-char Code</span>
            <div className="font-mono text-[#1F150D] font-black text-sm mt-1">{activeOrg?.org_code || 'N/A'}</div>
          </div>

          <div>
            <span className="text-[#8F6834] uppercase font-bold text-[10px]">Session Token Security</span>
            <div className="text-[#5A4838] font-medium mt-1">Encrypted JWT with RS256 / HS256</div>
          </div>
        </div>
      </div>

      {/* Session Invalidation */}
      <div className="glass-panel p-6 rounded-2xl border border-[#C5A059]/30 flex items-center justify-between shadow-md">
        <div>
          <h3 className="text-sm font-bold text-[#1F150D] font-serif-brand">Sign Out from Session</h3>
          <p className="text-xs text-[#695541] mt-0.5">Revoke refresh token and terminate active session on this device.</p>
        </div>
        <button
          onClick={() => logout()}
          className="btn-brand-secondary py-2 px-4 rounded-xl text-xs font-bold text-red-700 border-red-300/60 hover:bg-red-50 flex items-center space-x-2 shadow-sm"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );
};
