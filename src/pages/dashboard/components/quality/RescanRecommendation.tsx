import React from 'react';
import { RefreshCw, QrCode, AlertOctagon, ArrowRight, ShieldX } from 'lucide-react';

interface RescanRecommendationProps {
  roomName: string;
  verdict: string;
  issues: string[];
  onRequestRescan: () => void;
}

export const RescanRecommendation: React.FC<RescanRecommendationProps> = ({
  roomName,
  verdict,
  issues,
  onRequestRescan,
}) => {
  const isRescanRecommended = verdict === 'REQUIRES_RESCAN' || verdict === 'FAILED';

  if (!isRescanRecommended && issues.length === 0) {
    return null;
  }

  return (
    <div className="bg-red-950/30 border border-red-500/40 rounded-2xl p-6 shadow-xl space-y-4 text-white">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-red-500/20 text-red-400 rounded-xl border border-red-500/30">
            <AlertOctagon className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-red-200">
              Targeted Rescan Recommended for {roomName}
            </h4>
            <div className="text-xs text-red-300/80 mt-0.5">
              Identified geometric defects prevent certification of this room
            </div>
          </div>
        </div>

        <button
          onClick={onRequestRescan}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-bold text-xs rounded-xl transition shadow-lg shrink-0"
        >
          <QrCode className="w-4 h-4" />
          <span>Generate Rescan QR Session</span>
        </button>
      </div>

      <div className="bg-black/30 rounded-xl p-3.5 border border-red-500/20 space-y-1.5 text-xs">
        <div className="text-[11px] font-bold text-red-400 uppercase tracking-wider">
          Actionable Operator Diagnostics:
        </div>
        <ul className="list-disc list-inside space-y-1 text-slate-300">
          {issues.length > 0 ? (
            issues.map((issue, idx) => (
              <li key={idx} className="text-red-200/90 font-medium">
                {issue}
              </li>
            ))
          ) : (
            <li className="text-red-200/90 font-medium">
              Insufficient visual-inertial baseline movement detected. Operator should slow walking speed and capture opposite wall corners.
            </li>
          )}
        </ul>
      </div>
    </div>
  );
};

