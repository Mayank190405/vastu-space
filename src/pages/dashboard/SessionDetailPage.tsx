import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { QrCode, ArrowLeft, Smartphone, ShieldCheck, Clock, AlertTriangle, Play, RefreshCw, XCircle, ExternalLink, CheckCircle2 } from 'lucide-react';
import { api } from '../../services/api';
import { CaptureSessionRecord } from '../../types';

export const SessionDetailPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<CaptureSessionRecord | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isRevoking, setIsRevoking] = useState<boolean>(false);
  const [copySuccess, setCopySuccess] = useState<boolean>(false);

  const fetchSession = async () => {
    if (!sessionId) return;
    try {
      setError(null);
      const data = await api.getQRSession(sessionId);
      setSession(data);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve capture session');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSession();
    const interval = setInterval(fetchSession, 4000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const handleRevoke = async () => {
    if (!sessionId || !window.confirm('Are you sure you want to revoke this session? The mobile app will be immediately locked from recording.')) {
      return;
    }
    try {
      setIsRevoking(true);
      await api.revokeQRSession(sessionId);
      await fetchSession();
    } catch (err: any) {
      alert(err.message || 'Failed to revoke session');
    } finally {
      setIsRevoking(false);
    }
  };

  const copyQRPayload = () => {
    if (session?.qr_payload) {
      navigator.clipboard.writeText(session.qr_payload);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  // Generate SVG QR representation using Google Chart API or inline data URL for clean offline/sandboxed rendering
  const qrImageUrl = session?.qr_payload
    ? `https://api.qrserver.com/v1/create-qr-code/?size=280x280&data=${encodeURIComponent(session.qr_payload)}`
    : '';

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-[#1E293B] p-4 md:p-8 font-sans antialiased">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Back link */}
        <Link
          to="/dashboard/sessions"
          className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          Back to Sessions List
        </Link>

        {isLoading ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center text-gray-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading capture session details...
          </div>
        ) : error ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center space-y-4">
            <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto" />
            <h3 className="text-lg font-bold text-gray-900">Session Not Found</h3>
            <p className="text-sm text-gray-500">{error}</p>
            <button
              onClick={() => navigate('/dashboard/sessions')}
              className="px-4 py-2 bg-gray-900 text-white rounded-xl text-sm font-medium hover:bg-gray-800"
            >
              Return to Sessions
            </button>
          </div>
        ) : session ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

            {/* Left 2 Cols: Session Details & Status */}
            <div className="md:col-span-2 space-y-6">
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-6">
                
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-xs font-mono font-bold text-blue-600 bg-blue-50 px-2.5 py-1 rounded-md">
                      {session.session_code}
                    </span>
                    <h1 className="text-2xl font-bold text-gray-900 mt-2">{session.room_name}</h1>
                    <p className="text-sm text-gray-500 mt-0.5">
                      {session.project_name} • {session.floor_name || 'Floor 1'}
                    </p>
                  </div>

                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold ${
                    session.status === 'AUTHORIZED' || session.status === 'RECORDING' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' :
                    session.status === 'COMPLETED' ? 'bg-blue-50 text-blue-600 border border-blue-100' :
                    session.status === 'EXPIRED' || session.status === 'REVOKED' ? 'bg-rose-50 text-rose-600 border border-rose-100' :
                    'bg-amber-50 text-amber-600 border border-amber-100'
                  }`}>
                    {session.status}
                  </span>
                </div>

                {/* Key Details Grid */}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100 text-sm">
                  <div>
                    <p className="text-xs text-gray-400 font-medium">Session ID</p>
                    <p className="font-mono text-gray-900 mt-0.5 break-all">{session.id}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 font-medium">Single-Use Challenge</p>
                    <p className="font-mono text-gray-900 mt-0.5 truncate">{session.challenge_token}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 font-medium">Expires At</p>
                    <p className="text-gray-900 mt-0.5">{new Date(session.expires_at).toLocaleTimeString()} ({new Date(session.expires_at).toLocaleDateString()})</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 font-medium">Redeemed Device</p>
                    <p className="text-gray-900 mt-0.5 font-medium flex items-center">
                      <Smartphone className="w-3.5 h-3.5 mr-1 text-gray-400" />
                      {session.device_id ? session.device_id : 'Waiting for scan...'}
                    </p>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="pt-4 border-t border-gray-100 flex flex-wrap gap-3">
                  <Link
                    to={`/dashboard/reconstruction/${session.id}`}
                    className="inline-flex items-center px-4 py-2 bg-gray-900 text-white rounded-xl text-sm font-semibold hover:bg-gray-800 transition-colors shadow-sm"
                  >
                    <Play className="w-4 h-4 mr-2 text-emerald-400" />
                    Open Real-Time Pipeline Tracker
                  </Link>

                  {session.status !== 'REVOKED' && session.status !== 'COMPLETED' && (
                    <button
                      onClick={handleRevoke}
                      disabled={isRevoking}
                      className="inline-flex items-center px-4 py-2 bg-rose-50 text-rose-600 rounded-xl text-sm font-medium hover:bg-rose-100 transition-colors"
                    >
                      <XCircle className="w-4 h-4 mr-1.5" />
                      {isRevoking ? 'Revoking...' : 'Revoke Session'}
                    </button>
                  )}
                </div>

              </div>

              {/* Security & Anti-Replay Info Card */}
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-3">
                <div className="flex items-center space-x-2 text-gray-900 font-bold text-sm">
                  <ShieldCheck className="w-4 h-4 text-emerald-500" />
                  <span>Anti-Replay & Session Security Active</span>
                </div>
                <p className="text-xs text-gray-500 leading-relaxed">
                  Every VĀSTU QR challenge is bound to an encrypted nonce. Once redeemed by an iPhone, the challenge token is marked as authorized on the server and cannot be reused or replayed. The mobile app cannot start recording until server validation completes.
                </p>
              </div>
            </div>

            {/* Right Col: High-Resolution QR Card */}
            <div className="space-y-6">
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 text-center space-y-4">
                <div className="space-y-1">
                  <h3 className="font-bold text-gray-900">Scan Session QR</h3>
                  <p className="text-xs text-gray-500">Scan using the native VĀSTU Capture iPhone app</p>
                </div>

                {/* QR Display */}
                <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-inner flex items-center justify-center">
                  {qrImageUrl ? (
                    <img
                      src={qrImageUrl}
                      alt="Capture Session QR Code"
                      className="w-56 h-56 rounded-lg object-contain"
                    />
                  ) : (
                    <div className="w-56 h-56 flex items-center justify-center text-gray-400">
                      <QrCode className="w-16 h-16 animate-pulse" />
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <button
                    onClick={copyQRPayload}
                    className="w-full py-2 px-3 border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    {copySuccess ? 'Copied Deep Link!' : 'Copy Mobile Deep-Link'}
                  </button>

                  <p className="text-[11px] text-gray-400 font-mono break-all line-clamp-2">
                    {session.qr_payload}
                  </p>
                </div>

                {session.status === 'AUTHORIZED' && (
                  <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100 text-xs text-emerald-700 font-medium flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 mr-1.5 text-emerald-600" />
                    Device Authorized & Ready to Capture
                  </div>
                )}
              </div>
            </div>

          </div>
        ) : null}

      </div>
    </div>
  );
};

