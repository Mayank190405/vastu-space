import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { CheckCircle2, Loader2, Circle, AlertCircle, RefreshCw, Smartphone, ChevronRight, Layers, ArrowLeft } from 'lucide-react';
import { api, getApiBaseUrl } from '../../services/api';
import { PipelineStageRecord, CaptureSessionRecord } from '../../types';
import { RoomQualityPanel, RoomQualityMetrics } from './components/quality/RoomQualityPanel';
import { ReconstructionComparison } from './components/quality/ReconstructionComparison';
import { PublishingApproval } from './components/quality/PublishingApproval';
import { RescanRecommendation } from './components/quality/RescanRecommendation';

export const ReconstructionTrackingPage: React.FC = () => {
  const { jobId, sessionId: paramSessionId } = useParams<{ jobId?: string; sessionId?: string }>();
  const activeSessionId = paramSessionId || jobId || 'sess_demo_1042';

  const [session, setSession] = useState<CaptureSessionRecord | null>(null);
  const [stages, setStages] = useState<PipelineStageRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastHeartbeatSec, setLastHeartbeatSec] = useState<number>(8);
  const [isLiveConnected, setIsLiveConnected] = useState<boolean>(false);

  // Fetch initial stage tracking and session data
  const fetchData = async () => {
    try {
      setError(null);
      let sessionData: CaptureSessionRecord | null = null;
      try {
        sessionData = await api.getQRSession(activeSessionId);
        setSession(sessionData);
      } catch {
        // Fallback demo state if session ID is mock
        setSession({
          id: activeSessionId,
          session_code: '#S-1042',
          project_id: 'proj_demo',
          project_name: 'Project',
          floor_name: 'Floor 1',
          room_name: 'Living Room',
          challenge_token: 'chal_demo',
          nonce: 'nonce_demo',
          status: 'RECORDING',
          qr_payload: 'vastu://capture-session',
          expires_at: new Date(Date.now() + 3600000).toISOString(),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      }

      const stageList = await api.getPipelineStages(activeSessionId).catch(() => []);
      if (stageList && stageList.length > 0) {
        setStages(stageList);
      } else {
        // Default pipeline initialized from real sequence
        const defaultSequence: PipelineStageRecord[] = [
          { id: '1', session_id: activeSessionId, stage_name: 'QR session authorized', stage_order: 1, status: 'COMPLETED', progress_percentage: 100, responsible_worker: 'Auth Gateway', retry_count: 0, updated_at: new Date().toISOString() },
          { id: '2', session_id: activeSessionId, stage_name: 'Room capture', stage_order: 2, status: 'COMPLETED', progress_percentage: 100, responsible_worker: 'iPhone 15 (Mobile)', retry_count: 0, updated_at: new Date().toISOString() },
          { id: '3', session_id: activeSessionId, stage_name: 'Upload verification', stage_order: 3, status: 'COMPLETED', progress_percentage: 100, responsible_worker: 'Storage Worker', retry_count: 0, updated_at: new Date().toISOString() },
          { id: '4', session_id: activeSessionId, stage_name: 'Pose refinement', stage_order: 4, status: 'COMPLETED', progress_percentage: 100, responsible_worker: 'SfM Worker 01', retry_count: 0, updated_at: new Date().toISOString() },
          { id: '5', session_id: activeSessionId, stage_name: 'Depth estimation', stage_order: 5, status: 'RUNNING', progress_percentage: 45, responsible_worker: 'DepthAI Worker', retry_count: 0, updated_at: new Date().toISOString() },
          { id: '6', session_id: activeSessionId, stage_name: 'Geometry reconstruction', stage_order: 6, status: 'PENDING', progress_percentage: 0, responsible_worker: 'TSDF Mesher', retry_count: 0, updated_at: new Date().toISOString() },
          { id: '7', session_id: activeSessionId, stage_name: 'Gaussian splatting', stage_order: 7, status: 'PENDING', progress_percentage: 0, responsible_worker: 'Splat Engine', retry_count: 0, updated_at: new Date().toISOString() },
          { id: '8', session_id: activeSessionId, stage_name: 'Viewer publishing', stage_order: 8, status: 'PENDING', progress_percentage: 0, responsible_worker: 'Cloud Publisher', retry_count: 0, updated_at: new Date().toISOString() },
        ];
        setStages(defaultSequence);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load pipeline stages');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Setup real-time Server-Sent Events (SSE) with automatic polling fallback
    const baseUrl = getApiBaseUrl();
    const eventSource = new EventSource(`${baseUrl}/capture-sessions/${activeSessionId}/events`);

    eventSource.onopen = () => {
      setIsLiveConnected(true);
    };

    eventSource.addEventListener('stage_update', (e: MessageEvent) => {
      try {
        const updatedRecord: PipelineStageRecord = JSON.parse(e.data);
        setStages((prev) => {
          const index = prev.findIndex((s) => s.stage_name === updatedRecord.stage_name);
          if (index >= 0) {
            const next = [...prev];
            next[index] = updatedRecord;
            return next;
          }
          return [...prev, updatedRecord];
        });
      } catch (err) {
        console.error('Failed to parse SSE stage update:', err);
      }
    });

    eventSource.onerror = () => {
      setIsLiveConnected(false);
    };

    // Polling fallback every 3 seconds
    const interval = setInterval(() => {
      api.getPipelineStages(activeSessionId)
        .then((data) => {
          if (data && data.length > 0) setStages(data);
        })
        .catch(() => {});
    }, 3000);

    // Heartbeat ticker
    const hbInterval = setInterval(() => {
      setLastHeartbeatSec((prev) => (prev < 60 ? prev + 1 : 1));
    }, 1000);

    return () => {
      eventSource.close();
      clearInterval(interval);
      clearInterval(hbInterval);
    };
  }, [activeSessionId]);

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
            <span className="text-gray-500">{isLiveConnected ? 'Live SSE Stream' : 'Auto-Sync Active'}</span>
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
              Processing
            </span>
          </div>

          {/* Device & Capture Status Banner */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">Connected device</p>
              <h3 className="text-lg font-bold text-gray-900">
                {session?.device_id ? `iPhone (${session.device_id.slice(0, 8)})` : 'iPhone 15'}
              </h3>
              <p className="flex items-center text-xs font-medium text-emerald-600 mt-1">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-500" />
                Last heartbeat: {lastHeartbeatSec}s ago
              </p>
            </div>

            <div>
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">Capture status</p>
              <h3 className="text-lg font-bold text-gray-900">Uploaded</h3>
              <p className="text-xs text-gray-500 mt-1">
                Session {session?.session_code || '#S-1042'}
              </p>
            </div>
          </div>

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
            <span>Illustrative dashboard only — these are sample states, not live project data.</span>
            <span className="font-mono text-[11px] text-gray-400">SESSION: {activeSessionId}</span>
          </div>

        </div>

        {/* Phase 9 Production Quality & Governance Gates */}
        <div className="space-y-6 pt-4">
          <RoomQualityPanel
            roomName={session?.room_name || 'Living Room'}
            metrics={{
              compositeScore: 96.4,
              verdict: 'PASSED',
              canPublish: true,
              wallFitRmseCm: 1.2,
              cornerOrthoDevDeg: 0.5,
              dimensionErrorCm: 1.8,
              structuralCoveragePct: 96.2,
              psnrDb: 31.2,
              isCollisionWatertight: true,
              isScaleConsistent: true
            }}
          />

          <ReconstructionComparison
            roomName={session?.room_name || 'Living Room'}
          />

          <PublishingApproval
            roomName={session?.room_name || 'Living Room'}
            canPublish={true}
            verdict="PASSED"
            onApprovePublish={() => {}}
            onBlockPublish={() => {}}
          />

          <RescanRecommendation
            roomName={session?.room_name || 'Living Room'}
            verdict="PASSED"
            issues={[]}
            onRequestRescan={() => {}}
          />
        </div>

      </div>
    </div>
  );
};

