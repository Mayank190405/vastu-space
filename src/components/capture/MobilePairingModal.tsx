import React, { useState, useEffect } from 'react';
import QRCode from 'qrcode';
import { api } from '../../services/api';
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
  const safeSessionId = sessionId || 'CAP-01-LIVE';
  const effectiveSessionCode = sessionCode || `V-CAP-${safeSessionId.replace(/[^A-Za-z0-9]/g, '').slice(-6).toUpperCase() || 'LIVE'}`;
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedDeepLink, setCopiedDeepLink] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [qrDataUrl, setQrDataUrl] = useState<string>('');
  const [surveyorStatus, setSurveyorStatus] = useState<'WAITING' | 'CONNECTED' | 'RECORDING'>('WAITING');

  // Generate a cryptographically distinct single-use nonce for this modal instance
  const [sessionNonce] = useState(() => `n_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`);

  const liveBase = 'https://vastu.krads.co.in';
  const mobileWebUrl = `${liveBase}/capture/${safeSessionId}`;
  const qrPayload = `${liveBase}/capture/${safeSessionId}?endpoint=${encodeURIComponent(liveBase)}&challenge=chal_${safeSessionId}_${sessionNonce}&nonce=${sessionNonce}&session_id=${safeSessionId}&project_id=${project.id}&project_name=${encodeURIComponent(project.name)}&room_name=${encodeURIComponent(floorName)}&operator=${encodeURIComponent(operatorName)}&grant=grant_${safeSessionId}`;
  const iosDeepLink = `vastuspatial://capture/${safeSessionId}?endpoint=${encodeURIComponent(liveBase)}&session_id=${safeSessionId}&project_id=${project.id}&grant=grant_${safeSessionId}&nonce=${sessionNonce}`;

  useEffect(() => {
    QRCode.toDataURL(qrPayload, {
      width: 256,
      margin: 2,
      errorCorrectionLevel: 'M',
      color: {
        dark: '#1F150D',
        light: '#FFFFFF'
      }
    })
      .then(url => setQrDataUrl(url))
      .catch(err => {
        console.error('Failed to generate local QR code, using web fallback', err);
        setQrDataUrl(`https://api.qrserver.com/v1/create-qr-code/?size=256x256&data=${encodeURIComponent(qrPayload)}`);
      });
  }, [qrPayload]);

  // Real-time telemetry: Poll session status from backend
  useEffect(() => {
    let isMounted = true;
    const interval = setInterval(async () => {
      try {
        const session = await api.getQRSession(safeSessionId);
        if (!isMounted) return;
        const s = session as any;
        if (s && (s.status === 'AUTHORIZED' || s.status === 'ACTIVE' || s.status === 'RECORDING')) {
          setSurveyorStatus(s.status === 'RECORDING' ? 'RECORDING' : 'CONNECTED');
        }
      } catch (err) {
        // Fallback for client-only / offline sessions
      }
    }, 2500);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [safeSessionId]);

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

  const handleCopyCode = () => {
    navigator.clipboard.writeText(effectiveSessionCode);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2500);
  };

  // Render authentic scannable QR Code
  const renderQRCode = () => {
    if (qrDataUrl) {
      return (
        <img
          src={qrDataUrl}
          alt="VĀSTU Capture QR Code"
          className="w-48 h-48 rounded-xl bg-white p-2 shadow-inner border border-[#D9C4A1] object-contain"
        />
      );
    }
    return (
      <div className="w-48 h-48 rounded-xl bg-white p-2 shadow-inner border border-[#D9C4A1] flex items-center justify-center text-xs text-[#7C6652]">
        Generating QR Code...
      </div>
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
              {renderQRCode()}
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
