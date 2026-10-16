import React, { useState, useEffect } from 'react';
import {
  Smartphone,
  QrCode,
  Share2,
  Copy,
  Check,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  Camera,
  X,
  Sparkles,
  ArrowRight,
  RefreshCw
} from 'lucide-react';
import { Project } from '../../types';

interface MobilePairingModalProps {
  project: Project;
  sessionId: string;
  sessionCode?: string;
  operatorName: string;
  floorName: string;
  onClose: () => void;
  onLaunchWebStudio: () => void;
}

export const MobilePairingModal: React.FC<MobilePairingModalProps> = ({
  project,
  sessionId,
  sessionCode,
  operatorName,
  floorName,
  onClose,
  onLaunchWebStudio
}) => {
  const effectiveSessionCode = sessionCode || `V-${sessionId.slice(0, 4).toUpperCase()}`;
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedDeepLink, setCopiedDeepLink] = useState(false);
  const [surveyorStatus, setSurveyorStatus] = useState<'WAITING' | 'CONNECTED' | 'RECORDING'>('WAITING');

  const mobileWebUrl = `${window.location.origin}/capture/${sessionId}`;
  const iosDeepLink = `vastuspatial://capture/${sessionId}?projectId=${project.id}`;

  const handleCopyLink = () => {
    navigator.clipboard.writeText(mobileWebUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
  };

  const handleCopyDeepLink = () => {
    navigator.clipboard.writeText(iosDeepLink);
    setCopiedDeepLink(true);
    setTimeout(() => setCopiedDeepLink(false), 2500);
  };

  // Generate deterministic QR Code pattern SVG
  const renderSVGQRCode = () => {
    return (
      <svg className="w-48 h-48 rounded-xl bg-white p-2 shadow-inner" viewBox="0 0 200 200">
        {/* Finder Pattern Top-Left */}
        <rect x="15" y="15" width="45" height="45" fill="#0b0f17" rx="6" />
        <rect x="23" y="23" width="29" height="29" fill="#ffffff" rx="3" />
        <rect x="29" y="29" width="17" height="17" fill="#8F6834" rx="2" />

        {/* Finder Pattern Top-Right */}
        <rect x="140" y="15" width="45" height="45" fill="#0b0f17" rx="6" />
        <rect x="148" y="23" width="29" height="29" fill="#ffffff" rx="3" />
        <rect x="154" y="29" width="17" height="17" fill="#8F6834" rx="2" />

        {/* Finder Pattern Bottom-Left */}
        <rect x="15" y="140" width="45" height="45" fill="#0b0f17" rx="6" />
        <rect x="23" y="148" width="29" height="29" fill="#ffffff" rx="3" />
        <rect x="29" y="154" width="17" height="17" fill="#8F6834" rx="2" />

        {/* Brand V Center Logo */}
        <rect x="85" y="85" width="30" height="30" fill="#dfb873" rx="6" />
        <text x="94" y="106" fill="#0b0f17" fontSize="16" fontWeight="bold" fontFamily="sans-serif">V</text>

        {/* Timing & Data Grid Dots */}
        {[
          [70, 20], [90, 20], [110, 20], [130, 20],
          [70, 40], [100, 40], [120, 50],
          [20, 70], [40, 70], [70, 70], [140, 70], [160, 70],
          [20, 90], [50, 90], [130, 90], [170, 90],
          [30, 110], [60, 110], [140, 110], [160, 110],
          [70, 130], [90, 130], [110, 130], [130, 130],
          [70, 150], [100, 150], [120, 150], [150, 150],
          [70, 170], [90, 170], [120, 170], [140, 170], [170, 170]
        ].map(([x, y], idx) => (
          <rect key={idx} x={x} y={y} width="10" height="10" fill="#1f150d" rx="2" />
        ))}
      </svg>
    );
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-xl bg-[#FAF7F2] border border-[#D1C2A5] rounded-3xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="p-5 bg-white border-b border-[#EAE2D3] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[#FAF3E0] text-[#8F6834] flex items-center justify-center font-bold">
              <Smartphone className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-[#1F150D] font-serif-brand">
                  Mobile App Capture Session
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#FAF3E0] text-[#8F6834] border border-[#D9C4A1]">
                  {effectiveSessionCode}
                </span>
              </div>
              <p className="text-xs text-[#695541]">
                Session created on Web &bull; Ready to record on iOS / Android App
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-[#7C6652] hover:text-[#1F150D] hover:bg-[#FAF7F2] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6">
          {/* Surveyor & Floor Confirmation */}
          <div className="p-4 bg-white rounded-2xl border border-[#EAE2D3] flex items-center justify-between text-xs">
            <div>
              <span className="text-[10px] uppercase font-bold text-[#7C6652] tracking-wider block">Target Space</span>
              <span className="font-bold text-[#1F150D] text-sm">{project.name} &bull; {floorName}</span>
            </div>
            <div className="text-right">
              <span className="text-[10px] uppercase font-bold text-[#7C6652] tracking-wider block">Assigned Surveyor</span>
              <span className="font-bold text-[#8F6834]">{operatorName}</span>
            </div>
          </div>

          {/* QR Code & Mobile App Instructions */}
          <div className="flex flex-col sm:flex-row items-center gap-6 p-5 bg-white rounded-2xl border border-[#EAE2D3]">
            <div className="flex flex-col items-center space-y-2 shrink-0">
              {renderSVGQRCode()}
              <span className="text-[11px] font-mono text-[#7C6652] font-semibold">
                Scan with VĀSTU Mobile App
              </span>
            </div>

            <div className="space-y-3 text-xs text-[#5C4D3E] flex-1">
              <div>
                <h4 className="font-bold text-[#1F150D] text-sm flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-[#8F6834]" />
                  <span>How to Record on Mobile:</span>
                </h4>
                <ol className="mt-2 space-y-2 list-decimal list-inside text-xs leading-relaxed text-[#695541]">
                  <li>
                    Open the <strong>VĀSTU Spatial App</strong> on your iPhone or Android phone.
                  </li>
                  <li>
                    Scan this QR code or enter Pairing Code <strong className="font-mono text-[#8F6834] bg-[#FAF3E0] px-1 py-0.5 rounded">{effectiveSessionCode}</strong>.
                  </li>
                  <li>
                    Follow the app prompt to <strong>show the whole place</strong> (360° scan).
                  </li>
                  <li>
                    The spatial engine will synthesize the room SOP and guide your area-to-area recording with the projected floor plan!
                  </li>
                </ol>
              </div>

              {/* Live Connection Telemetry */}
              <div className="p-3 bg-[#FAF7F2] rounded-xl border border-[#EAE2D3] flex items-center justify-between text-xs">
                <span className="flex items-center gap-2">
                  <span
                    className={`w-2.5 h-2.5 rounded-full animate-pulse ${
                      surveyorStatus === 'CONNECTED' ? 'bg-emerald-500' : 'bg-amber-500'
                    }`}
                  />
                  <span>
                    {surveyorStatus === 'CONNECTED'
                      ? 'Mobile App Connected (Ready to Record)'
                      : 'Waiting for Mobile Surveyor Scan...'}
                  </span>
                </span>
                <span className="font-mono text-[11px] text-[#8F6834] font-bold">
                  {surveyorStatus === 'CONNECTED' ? 'PAIRED' : 'LISTENING'}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Sharing & Links */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              onClick={handleCopyLink}
              className="p-3 rounded-xl border border-[#D1C2A5] bg-white hover:bg-[#FAF7F2] text-xs font-semibold text-[#1F150D] flex items-center justify-between transition-all"
            >
              <div className="flex items-center gap-2">
                <Share2 className="w-4 h-4 text-[#8F6834]" />
                <span>Copy Mobile Web Link</span>
              </div>
              {copiedLink ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-[#7C6652]" />}
            </button>

            <button
              onClick={handleCopyDeepLink}
              className="p-3 rounded-xl border border-[#D1C2A5] bg-white hover:bg-[#FAF7F2] text-xs font-semibold text-[#1F150D] flex items-center justify-between transition-all"
            >
              <div className="flex items-center gap-2">
                <Smartphone className="w-4 h-4 text-[#8F6834]" />
                <span>Copy App Deep Link</span>
              </div>
              {copiedDeepLink ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-[#7C6652]" />}
            </button>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-white border-t border-[#EAE2D3] flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-[#7C6652] hover:text-[#1F150D]"
          >
            Close & Monitor on Web
          </button>

          <button
            onClick={onLaunchWebStudio}
            className="px-4 py-2 bg-[#8F6834] hover:bg-[#755427] text-white text-xs font-bold rounded-xl shadow-sm flex items-center gap-1.5 transition-all"
          >
            <span>Simulate / Open Studio on Web</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
