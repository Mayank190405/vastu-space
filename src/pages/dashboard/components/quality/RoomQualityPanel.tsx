import React from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  HelpCircle,
  RefreshCw,
  CheckCircle2,
  Maximize,
  Compass,
  Layers,
  Sparkles
} from 'lucide-react';

export interface RoomQualityMetrics {
  compositeScore: number;
  verdict: 'PASSED' | 'WARNING' | 'FAILED' | 'REQUIRES_RESCAN' | 'REQUIRES_MANUAL_REVIEW';
  canPublish: boolean;
  wallFitRmseCm: number;
  cornerOrthoDevDeg: number;
  dimensionErrorCm: number;
  structuralCoveragePct: number;
  psnrDb: number;
  isCollisionWatertight: boolean;
  isScaleConsistent: boolean;
}

interface RoomQualityPanelProps {
  roomName: string;
  metrics: RoomQualityMetrics;
}

export const RoomQualityPanel: React.FC<RoomQualityPanelProps> = ({ roomName, metrics }) => {
  const getBadge = () => {
    switch (metrics.verdict) {
      case 'PASSED':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" /> CERTIFIED PASSED
          </span>
        );
      case 'WARNING':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3.5 h-3.5" /> APPROVED WITH WARNING
          </span>
        );
      case 'REQUIRES_MANUAL_REVIEW':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-500/15 text-blue-400 border border-blue-500/30">
            <HelpCircle className="w-3.5 h-3.5" /> REQUIRES MANUAL REVIEW
          </span>
        );
      case 'REQUIRES_RESCAN':
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-500/15 text-red-400 border border-red-500/30">
            <RefreshCw className="w-3.5 h-3.5" /> REQUIRES RESCAN
          </span>
        );
      case 'FAILED':
      default:
        return (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-500/20 text-red-500 border border-red-500/40">
            <XCircle className="w-3.5 h-3.5" /> REJECTED FAILED
          </span>
        );
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6 text-white">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="text-xs font-bold text-[#C5A059] uppercase tracking-wider">
            Reconstruction Quality Gate (Phase 9)
          </div>
          <h3 className="text-lg font-bold text-white mt-0.5">{roomName}</h3>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-2xl font-black text-white">{metrics.compositeScore}</div>
            <div className="text-[10px] text-slate-400 uppercase font-mono">Composite Index</div>
          </div>
          {getBadge()}
        </div>
      </div>

      {/* Accuracy Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Wall Fit RMSE</span>
            <Layers className="w-3.5 h-3.5 text-[#C5A059]" />
          </div>
          <div className="text-base font-bold text-white">
            {metrics.wallFitRmseCm.toFixed(1)} cm
          </div>
          <div className="text-[10px] text-emerald-400 font-medium">Target: ≤ 1.5 cm</div>
        </div>

        <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Corner Dev</span>
            <Compass className="w-3.5 h-3.5 text-[#C5A059]" />
          </div>
          <div className="text-base font-bold text-white">
            {metrics.cornerOrthoDevDeg.toFixed(1)}°
          </div>
          <div className="text-[10px] text-emerald-400 font-medium">Target: ≤ 1.0°</div>
        </div>

        <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Dimension Delta</span>
            <Maximize className="w-3.5 h-3.5 text-[#C5A059]" />
          </div>
          <div className="text-base font-bold text-white">
            {metrics.dimensionErrorCm.toFixed(1)} cm
          </div>
          <div className="text-[10px] text-emerald-400 font-medium">Target: ≤ 3.0 cm</div>
        </div>

        <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Coverage</span>
            <ShieldCheck className="w-3.5 h-3.5 text-[#C5A059]" />
          </div>
          <div className="text-base font-bold text-white">
            {metrics.structuralCoveragePct.toFixed(1)}%
          </div>
          <div className="text-[10px] text-emerald-400 font-medium">Target: ≥ 90.0%</div>
        </div>
      </div>

      {/* Visual & Physics Checklist */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-slate-800/80 text-xs text-slate-300">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#C5A059]" />
          <span>
            Gaussian Photorealism: <strong className="text-white">{metrics.psnrDb.toFixed(1)} dB PSNR</strong>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <ShieldCheck
            className={`w-4 h-4 ${metrics.isCollisionWatertight ? 'text-emerald-400' : 'text-red-400'}`}
          />
          <span>
            Collision Watertight:{' '}
            <strong className={metrics.isCollisionWatertight ? 'text-emerald-400' : 'text-red-400'}>
              {metrics.isCollisionWatertight ? 'Verified Zero Penetration' : 'Penetration Detected'}
            </strong>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <CheckCircle2
            className={`w-4 h-4 ${metrics.isScaleConsistent ? 'text-emerald-400' : 'text-amber-400'}`}
          />
          <span>
            ARKit Scale Anchored:{' '}
            <strong className={metrics.isScaleConsistent ? 'text-emerald-400' : 'text-amber-400'}>
              {metrics.isScaleConsistent ? '≤ 3% Deviation' : 'Drift Warning'}
            </strong>
          </span>
        </div>
      </div>
    </div>
  );
};

