import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Building2, Copy, Check, LogOut, Shield, User as UserIcon, Users } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, activeOrg, activeRole, logout } = useAuth();
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);

  const copyOrgCode = () => {
    if (activeOrg?.org_code) {
      navigator.clipboard.writeText(activeOrg.org_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!user) return null;

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link to="/dashboard" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 p-0.5 shadow-lg shadow-emerald-500/20 group-hover:scale-105 transition-all">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center font-bold text-emerald-400 tracking-wider text-sm">
                VĀ
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-base font-bold tracking-tight text-white group-hover:text-emerald-400 transition-colors">
                VĀSTU
              </span>
              <span className="text-[10px] uppercase font-semibold tracking-wider text-emerald-500">
                Spatial Cloud
              </span>
            </div>
          </Link>

          {activeOrg && (
            <div className="hidden md:flex items-center space-x-2 pl-4 border-l border-slate-800">
              <Building2 className="w-4 h-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-200">{activeOrg.name}</span>
              <button
                onClick={copyOrgCode}
                title="Click to copy 12-char Organization Code"
                className="ml-2 flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-emerald-950/50 border border-emerald-800/50 text-emerald-400 text-xs font-mono font-medium hover:bg-emerald-900/50 transition-colors"
              >
                <span>{activeOrg.org_code}</span>
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-4">
          {activeOrg && (
            <Link
              to="/organization"
              className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-all"
            >
              <Users className="w-3.5 h-3.5 text-emerald-400" />
              <span className="hidden sm:inline">Manage Organization</span>
            </Link>
          )}

          <div className="flex items-center space-x-3 pl-3 border-l border-slate-800">
            <div className="flex flex-col text-right">
              <span className="text-xs font-semibold text-slate-200">{user.full_name}</span>
              <span className="text-[10px] text-slate-400 capitalize flex items-center justify-end space-x-1">
                <Shield className="w-2.5 h-2.5 text-emerald-400 inline" />
                <span>{activeRole || user.global_role || 'User'}</span>
              </span>
            </div>
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-semibold text-xs">
              {user.avatar_url ? (
                <img src={user.avatar_url} alt={user.full_name} className="w-full h-full rounded-full object-cover" />
              ) : (
                <UserIcon className="w-4 h-4 text-slate-400" />
              )}
            </div>
            <button
              onClick={() => logout()}
              title="Sign Out"
              className="p-1.5 text-slate-400 hover:text-red-400 rounded-lg hover:bg-red-950/30 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
