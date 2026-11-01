import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle, XCircle, Lock, Unlock } from 'lucide-react';

interface PublishingApprovalProps {
  roomName: string;
  canPublish: boolean;
  verdict: string;
  onApprovePublish: () => void;
  onBlockPublish: () => void;
}

export const PublishingApproval: React.FC<PublishingApprovalProps> = ({
  roomName,
  canPublish,
  verdict,
  onApprovePublish,
  onBlockPublish,
}) => {
  const [isPublished, setIsPublished] = useState(canPublish && verdict === 'PASSED');
  const isBlockedByGate = !canPublish || verdict === 'FAILED' || verdict === 'REQUIRES_RESCAN';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4 text-white">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-bold text-[#C5A059] uppercase tracking-wider">
            Governance & Publishing Gate
          </div>
          <h4 className="text-sm font-bold text-white mt-0.5">
            Production Publication Control for {roomName}
          </h4>
        </div>

        <div className="flex items-center gap-2">
          {isPublished ? (
            <span className="flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
              <Unlock className="w-3.5 h-3.5" /> Published to Viewer
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs font-bold text-amber-400 bg-amber-500/10 px-3 py-1 rounded-full border border-amber-500/20">
              <Lock className="w-3.5 h-3.5" /> Unpublished / Draft
            </span>
          )}
        </div>
      </div>

      <p className="text-xs text-slate-300 leading-relaxed">
        {isBlockedByGate ? (
          <span className="text-red-400 font-semibold flex items-center gap-1.5">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            Automatic publishing blocked: Room failed one or more critical accuracy gates. Rescan or manual review required.
          </span>
        ) : (
          <span className="text-slate-300">
            All structural tolerances, metric scale checks, and collision watertightness tests passed. This room is verified safe for first-person exploration.
          </span>
        )}
      </p>

      <div className="flex items-center gap-3 pt-2">
        <button
          disabled={isBlockedByGate}
          onClick={() => {
            setIsPublished(true);
            onApprovePublish();
          }}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs transition shadow-md ${
            isBlockedByGate
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
              : 'bg-[#C5A059] hover:bg-[#b08b47] text-slate-950 cursor-pointer'
          }`}
        >
          <CheckCircle className="w-4 h-4" />
          <span>Approve & Publish to 3D Viewer</span>
        </button>

        <button
          onClick={() => {
            setIsPublished(false);
            onBlockPublish();
          }}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs border border-slate-700 transition"
        >
          <XCircle className="w-4 h-4" />
          <span>Block / Unpublish</span>
        </button>
      </div>
    </div>
  );
};

