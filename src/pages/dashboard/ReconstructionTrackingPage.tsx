import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { CheckCircle2, Loader2, Circle, AlertCircle, RefreshCw, Smartphone, ChevronRight, Layers, ArrowLeft } from 'lucide-react';
import { api } from '../../services/api';
import { PipelineStageRecord, CaptureSessionRecord, ConnectedDevice } from '../../types';

export const ReconstructionTrackingPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const activeSessionId = sessionId || '';
  const [session, setSession] = useState<CaptureSessionRecord | null>(null);
  const [stages, setStages] = useState<PipelineStageRecord[]>([]);
  const [device, setDevice] = useState<ConnectedDevice | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLiveConnected, setIsLiveConnected] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  // Authenticated polling avoids EventSource's inability to send the bearer header.
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        if (!activeSessionId.startsWith('sess_')) throw new Error('A capture-session ID is required. Open monitoring from the session list.');
        const record = await api.getQRSession(activeSessionId);
        const stageList = await api.getPipelineStages(activeSessionId);
        const devices = await api.listDevices();
        if (!active) return;
        setSession(record);
        setStages(stageList || []);
        setDevice((devices || []).find(d => d.current_session_id === record.id && d.device_uuid === record.device_id) || null);
        setError(null);
        setIsLiveConnected(true);
        if (!['COMPLETED', 'REVOKED', 'EXPIRED'].includes(record.status) &&
            !stageList?.some(s => s.status === 'FAILED' || (s.stage_name === 'COMPLETED' && s.status === 'COMPLETED'))) {
          timer = setTimeout(poll, 3000);
        }
      } catch (err: any) {
        if (active) { setError(err.message || 'Unable to load pipeline'); setIsLiveConnected(false); }
      } finally { if (active) setIsLoading(false); }
    };
    setIsLoading(true);
    setSession(null);
    setStages([]);
    poll();
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [activeSessionId, retryKey]);
  const fetchData = () => setRetryKey(key => key + 1);
  const lastHeartbeatSec = device ? Math.max(0, Math.floor((Date.now() - Date.parse(device.last_heartbeat_at)) / 1000)) : null;

  const renderStageIcon = (status: string) => {
    switch (status.toUpperCase()) {
      case 'COMPLETED':
        return <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />;
      case 'RUNNING':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin flex-shrink-0" />;
      case 'FAILED':
        return <AlertCircle className="w-5 h-5 text-rose-500 flex-shrink-0" />;
      case 'RETRYING':
        return <RefreshCw className="w-5 h-5 text-amber-500 animate-spin flex-shrink-0" />;
      default:
        return <Circle className="w-5 h-5 text-gray-400 fill-gray-400 flex-shrink-0" />;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status.toUpperCase()) {
      case 'COMPLETED':
        return 'Completed';
      case 'RUNNING':
        return 'Running';
      case 'FAILED':
        return 'Failed';
      case 'RETRYING':
        return 'Retrying';
      case 'SKIPPED':
        return 'Skipped';
      default:
        return 'Pending';
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-[#1E293B] p-4 md:p-8 font-sans antialiased">
      <div className="max-w-3xl mx-auto space-y-6">
        
        {/* Navigation & Breadcrumb */}
        <div className="flex items-center justify-between">
          <Link
            to="/dashboard/sessions"
            className="inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Sessions
          </Link>
          <div className="flex items-center gap-2 text-xs">
            <span className={`w-2 h-2 rounded-full ${isLiveConnected ? 'bg-emerald-500' : 'bg-amber-400'}`} />
            <span className="text-gray-500">{isLiveConnected ? 'Backend status loaded' : 'Status unavailable'}</span>
          </div>
        </div>

        {/* Primary Dashboard Card (Pixel-matched with design directive) */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 space-y-8">
          
          {/* Top Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <h1 className="text-xl font-bold text-gray-900 tracking-tight">VĀSTU Admin</h1>
              <p className="text-sm text-gray-500">
                {session?.project_name || 'Project'} / {session?.floor_name || 'Floor 1'} / {session?.room_name || 'Living Room'}
              </p>
            </div>
            <span className="inline-flex items-center px-3.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-600 border border-blue-100/50">
              {session?.status || 'Unavailable'}
            </span>
          </div>

          {/* Device & Capture Status Banner */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">Connected device</p>
              <h3 className="text-lg font-bold text-gray-900">
                {device ? `${device.device_model} · ${device.device_os} · ${device.status}` : 'No verified device presence'}
              </h3>
              <p className="flex items-center text-xs font-medium text-emerald-600 mt-1">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-500" />
                {lastHeartbeatSec === null ? 'Heartbeat unavailable' : `Last heartbeat: ${lastHeartbeatSec}s ago`}
              </p>
            </div>

            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">Capture status</p>
              <h3 className="text-lg font-bold text-gray-900">{stages.some(s => s.stage_name === 'UPLOAD_VERIFIED' && s.status === 'COMPLETED') ? 'Upload verified' : 'Upload not verified'}</h3>
              <p className="text-xs text-gray-500 mt-1">
                Session {session?.session_code || '#S-1042'}
              </p>
            </div>
          </div>

          {session?.video_url && session.upload_verified_at && (
            <div className="space-y-2"><h2 className="font-bold">Verified uploaded video</h2>
              <video controls preload="metadata" src={session.video_url} className="w-full max-h-96 rounded-xl" />
              <p className="text-xs text-gray-500">Storage verified · Capture {session.capture_id} · Processing job {session.job_id || 'Pending submission'}</p>
            </div>
          )}
          {session?.viewer_url && session.status === 'COMPLETED' && (
            <a className="inline-block rounded-xl bg-emerald-700 px-5 py-3 text-white" href={session.viewer_url} target="_blank" rel="noreferrer">Open completed 3D viewer</a>
          )}
          {stages.some(s => s.status === 'FAILED') && <button className="rounded-lg border px-4 py-2" onClick={async () => {
            try { await api.retryCaptureProcessing(activeSessionId); fetchData(); } catch (err: any) { setError(err.message); }
          }}>Retry failed processing</button>}
          {/* Reconstruction Pipeline Stage List */}
          <div className="pt-4 border-t border-gray-100 space-y-6">
            <h2 className="text-base font-bold text-gray-900">Reconstruction pipeline</h2>

            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
              </div>
            ) : error ? (
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-100 text-rose-600 text-sm">
                {error}
              </div>
            ) : (
              <div className="space-y-4">
                {stages.map((st) => (
                  <div
                    key={st.stage_name}
                    className="flex items-center justify-between py-1 px-1 group hover:bg-gray-50/50 rounded-lg transition-colors"
                  >
                    <div className="flex items-center space-x-3.5">
                      {renderStageIcon(st.status)}
                      <span className={`text-sm font-medium ${
                        st.status === 'RUNNING' ? 'text-gray-900 font-semibold' :
                        st.status === 'COMPLETED' ? 'text-gray-800' : 'text-gray-600'
                      }`}>
                        {st.stage_name}
                      </span>
                    </div>

                    <div className="flex items-center space-x-3">
                      {st.status === 'RUNNING' && st.progress_percentage > 0 && (
                        <span className="text-xs font-mono text-blue-600">
                          {st.progress_percentage}%
                        </span>
                      )}
                      <span className={`text-sm ${
                        st.status === 'COMPLETED' ? 'text-gray-500' :
                        st.status === 'RUNNING' ? 'text-blue-600 font-semibold' :
                        st.status === 'FAILED' ? 'text-rose-600 font-semibold' : 'text-gray-400'
                      }`}>
                        {getStatusLabel(st.status)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer note matching mockup requirement */}
          <div className="pt-4 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
            <span>Status reflects persisted backend events.</span>
            <span className="font-mono text-[11px] text-gray-400">SESSION: {activeSessionId}</span>
          </div>

        </div>


      </div>
    </div>
  );
};

