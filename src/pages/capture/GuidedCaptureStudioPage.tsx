import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Smartphone,
  Layers,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  RefreshCw,
  Compass,
  ShieldCheck,
  Check,
  ChevronRight,
  Wifi,
  WifiOff,
  Clock,
  Users,
  MapPin,
  Activity,
  Upload,
  QrCode,
  Copy,
} from 'lucide-react';
import { api } from '../../services/api';
import { Project, ProjectFloor } from '../../types';
import { SpatialSOPService, CaptureSOPResponse, CaptureZone } from '../../services/spatialSOPService';

export const GuidedCaptureStudioPage: React.FC = () => {
  const { projectId, captureId } = useParams<{ projectId: string; captureId: string }>();
  const navigate = useNavigate();

  // Workflow phases:
  // 1. 'WAITING_FOR_MOBILE': Waiting for mobile app to connect via QR code/Session ID
  // 2. 'RECON_PHASE': Mobile doing 360° reconnaissance scan
  // 3. 'SOP_ANALYSIS': Backend analyzing space scan + floor plan (if present)
  // 4. 'SOP_READY': SOP generated, waiting for mobile to start guided capture
  // 5. 'ACTIVE_CAPTURE': Mobile doing guided zone-by-zone capture
  // 6. 'COMPLETE': All zones captured, ready for processing
  const [phase, setPhase] = useState<
    'WAITING_FOR_MOBILE' | 'RECON_PHASE' | 'SOP_ANALYSIS' | 'SOP_READY' | 'ACTIVE_CAPTURE' | 'COMPLETE'
  >('WAITING_FOR_MOBILE');

  const [project, setProject] = useState<Project | null>(null);
  const [selectedFloor, setSelectedFloor] = useState<ProjectFloor | null>(null);

  // Mobile Connection Status (STRICT REAL STATE: Default disconnected)
  const [mobileConnected, setMobileConnected] = useState<boolean>(false);
  const [mobileDeviceName, setMobileDeviceName] = useState<string>('No Device Connected');
  const [connectionQuality, setConnectionQuality] = useState<'EXCELLENT' | 'GOOD' | 'POOR' | 'OFFLINE'>('OFFLINE');
  const [lastHeartbeat, setLastHeartbeat] = useState<Date | null>(null);

  // Real-time Capture Monitoring
  const [currentZoneIndex, setCurrentZoneIndex] = useState(0);
  const [completedZones, setCompletedZones] = useState<string[]>([]);
  const [cameraPos, setCameraPos] = useState({ x: 180, y: 150, angle: 45 });
  const [captureQuality, setCaptureQuality] = useState({
    blurScore: 85,
    coverage: 0,
    stability: 90,
  });

  // AR Co-Pilot Metrics & Gated Completion
  const [floorCoveragePct, setFloorCoveragePct] = useState(0);
  const [wallCoveragePct, setWallCoveragePct] = useState(0);
  const [overallCoveragePct, setOverallCoveragePct] = useState(0);
  const [isPivotingInPlace, setIsPivotingInPlace] = useState(false);
  const [gateWarning, setGateWarning] = useState<string | null>(null);

  // Spatial SOP Data
  const [sopData, setSOPData] = useState<CaptureSOPResponse | null>(null);
  const [sopError, setSOPError] = useState<string | null>(null);
  const [copiedSessionId, setCopiedSessionId] = useState(false);

  // Check if project has a real floor plan
  const hasFloorPlan = Boolean(
    selectedFloor?.floor_plan?.file_url ||
      selectedFloor?.floor_plan?.preview_url ||
      (selectedFloor?.floor_plan?.drawing_data?.objects &&
        selectedFloor.floor_plan.drawing_data.objects.length > 0)
  );

  // Load project and floor plan details
  useEffect(() => {
    if (!projectId) return;
    api.getProjectFull(projectId).then((p) => {
      setProject(p);
      if (p.floors && p.floors.length > 0) {
        setSelectedFloor(p.floors[0]);
      }
    });
  }, [projectId]);

  // Handle manual developer simulation trigger for testing
  const handleConnectTestDevice = () => {
    if (!mobileConnected) {
      setMobileConnected(true);
      setMobileDeviceName('Test Mobile Device (iOS/Android)');
      setConnectionQuality('GOOD');
      setLastHeartbeat(new Date());
      setPhase('RECON_PHASE');
    } else {
      setMobileConnected(false);
      setMobileDeviceName('No Device Connected');
      setConnectionQuality('OFFLINE');
      setLastHeartbeat(null);
      setPhase('WAITING_FOR_MOBILE');
    }
  };

  // Heartbeat & Telemetry update (runs ONLY when mobileConnected is true)
  useEffect(() => {
    if (!mobileConnected) return;

    const heartbeatInterval = setInterval(() => {
      setLastHeartbeat(new Date());
      if (phase === 'ACTIVE_CAPTURE' && sopData) {
        setCameraPos((prev) => ({
          x: prev.x + (Math.random() * 6 - 3),
          y: prev.y + (Math.random() * 6 - 3),
          angle: (prev.angle + 2) % 360,
        }));

        setFloorCoveragePct((prev) => Math.min(95, prev + 2));
        setWallCoveragePct((prev) => Math.min(92, prev + 1));
        setOverallCoveragePct((prev) => Math.min(94, Math.round(prev + 1.5)));

        setCaptureQuality((prev) => ({
          blurScore: Math.min(100, Math.max(75, prev.blurScore + (Math.random() * 6 - 3))),
          coverage: Math.min(100, Math.max(65, prev.coverage + 1)),
          stability: Math.min(100, Math.max(80, prev.stability + (Math.random() * 4 - 2))),
        }));
      }
    }, 1000);

    return () => clearInterval(heartbeatInterval);
  }, [mobileConnected, phase, sopData]);

  // Trigger Automated Spatial SOP Generation
  const handleAnalyzeSOP = async () => {
    setPhase('SOP_ANALYSIS');
    setSOPError(null);
    try {
      const floorName = selectedFloor?.name || 'Ground Space';
      const area = selectedFloor?.area_value || 1500;
      const height = selectedFloor?.height_value || 10.0;

      const sop = await SpatialSOPService.generateCaptureSOP({
        projectName: project?.name || 'Spatial Project',
        floorName,
        areaSqft: area,
        heightFt: height,
        projectType: project?.project_type || 'Building',
        floorPlanImageUrl: selectedFloor?.floor_plan?.preview_url || undefined,
        drawingData: selectedFloor?.floor_plan?.drawing_data,
      });

      // If no floor plan exists, customize SOP summary
      if (!hasFloorPlan) {
        sop.summary = `Freeform 360° SLAM Spatial Scan for ${floorName}. No architectural blueprint uploaded. Guided trajectories will use real-time visual feature anchors.`;
      }

      setSOPData(sop);
      setPhase('SOP_READY');
    } catch (err) {
      console.error('Failed SOP generation:', err);
      setSOPError(err instanceof Error ? err.message : 'SOP analysis failed.');
      setPhase('RECON_PHASE');
    }
  };

  const currentZone: CaptureZone | undefined = sopData?.zones[currentZoneIndex];

  return (
    <div className="min-h-screen bg-[#080a0f] text-slate-100 flex flex-col select-none">
      {/* 1. Header Bar */}
      <header className="h-16 px-4 sm:px-6 bg-[#0d1118]/95 border-b border-[#dfb873]/20 flex items-center justify-between z-30 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/projects/${projectId}`)}
            className="p-2 rounded-xl border border-white/10 hover:bg-white/5 text-slate-400 hover:text-white transition-all"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  mobileConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
                }`}
              />
              <h1 className="text-sm font-bold text-white font-serif-brand tracking-wide">
                Mobile Capture Session Monitor
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/10 text-[#dfb873] border border-[#dfb873]/20">
                {project?.project_code || 'PRJ-STUDIO'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 flex items-center gap-2">
              <span>{project?.name}</span>
              <span>&bull;</span>
              <span>{selectedFloor?.name || 'Ground Space'}</span>
              {!hasFloorPlan && (
                <span className="text-amber-400 font-mono text-[10px] bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                  (No Floor Plan)
                </span>
              )}
              <span>&bull;</span>
              <span>Session ID: {captureId?.slice(0, 8).toUpperCase()}</span>
            </p>
          </div>
        </div>

        {/* Mobile Connection Status */}
        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-black/60 backdrop-blur-md rounded-xl border border-white/15 text-xs">
            {mobileConnected ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-300 font-medium">{mobileDeviceName}</span>
                <span className="text-slate-500">•</span>
                <span className="text-slate-400">{connectionQuality} Signal</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
                <span className="text-amber-300 font-medium">NO MOBILE DEVICE CONNECTED</span>
              </>
            )}
          </div>

          {/* Dev / Test Mobile Connect Button */}
          <button
            onClick={handleConnectTestDevice}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
              mobileConnected
                ? 'bg-red-500/20 text-red-300 border-red-500/30 hover:bg-red-500/30'
                : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/30'
            }`}
          >
            {mobileConnected ? 'Disconnect Device' : 'Simulate Mobile Connect'}
          </button>

          {/* Phase Pill Indicators */}
          <div className="hidden lg:flex items-center gap-2 text-xs font-semibold">
            <span
              className={`px-3 py-1 rounded-full border transition-all ${
                phase === 'WAITING_FOR_MOBILE' || phase === 'RECON_PHASE'
                  ? 'bg-[#dfb873] text-[#0b0f17] border-[#dfb873] font-bold'
                  : 'bg-white/5 text-slate-400 border-white/10'
              }`}
            >
              1. Mobile Recon
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
            <span
              className={`px-3 py-1 rounded-full border transition-all ${
                phase === 'SOP_ANALYSIS' || phase === 'SOP_READY'
                  ? 'bg-[#dfb873] text-[#0b0f17] border-[#dfb873] font-bold'
                  : 'bg-white/5 text-slate-400 border-white/10'
              }`}
            >
              2. SOP Analysis
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
            <span
              className={`px-3 py-1 rounded-full border transition-all ${
                phase === 'ACTIVE_CAPTURE' || phase === 'COMPLETE'
                  ? 'bg-[#dfb873] text-[#0b0f17] border-[#dfb873] font-bold'
                  : 'bg-white/5 text-slate-400 border-white/10'
              }`}
            >
              3. Guided Capture
            </span>
          </div>
        </div>
      </header>

      {/* NO FLOOR PLAN ALERT BANNER */}
      {!hasFloorPlan && (
        <div className="bg-amber-950/40 border-b border-amber-500/30 px-6 py-2.5 flex items-center justify-between text-xs text-amber-200">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Project Floor Plan Notice:</strong> This project does not have an uploaded 2D floor plan blueprint. Freeform 360° SLAM Spatial Scanning mode is active.
            </span>
          </div>
          <button
            onClick={() => navigate(`/projects/${projectId}`)}
            className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 rounded-lg text-xs font-semibold transition-all"
          >
            <Upload className="w-3.5 h-3.5" />
            Upload Floor Plan
          </button>
        </div>
      )}

      {/* 2. Main Studio Content */}
      <main className="flex-1 relative flex flex-col lg:flex-row overflow-hidden">
        {/* ============================================================== */}
        {/* LEFT / TOP: Mobile Status Monitor & Real-Time Telemetry        */}
        {/* ============================================================== */}
        <div className="flex-1 relative flex flex-col justify-between bg-black overflow-hidden border-b lg:border-b-0 lg:border-r border-white/10">
          {/* Mobile Status Dashboard */}
          <div className="absolute inset-0 z-0 bg-gradient-to-b from-[#111827] via-[#0f172a] to-[#080a0f]">
            <div className="absolute inset-0 opacity-10 bg-[linear-gradient(to_right,#dfb873_1px,transparent_1px),linear-gradient(to_bottom,#dfb873_1px,transparent_1px)] bg-[size:40px_40px]" />
          </div>

          {/* Status Monitor Content */}
          <div className="relative z-10 p-4 sm:p-6 flex flex-col h-full space-y-4 overflow-y-auto">
            {/* Phase Instructions & Mobile Status */}
            <div className="space-y-2">
              {!mobileConnected && (
                <div className="bg-[#0d1118]/90 backdrop-blur-xl border border-amber-500/40 p-6 rounded-2xl shadow-xl space-y-4">
                  <div className="flex items-start gap-4">
                    <div className="w-14 h-14 rounded-2xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center shrink-0">
                      <Smartphone className="w-7 h-7 text-amber-400" />
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <h3 className="text-base font-bold text-white">
                          No Mobile Device Connected
                        </h3>
                        <span className="px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 text-xs font-mono border border-amber-500/30">
                          Awaiting App Session
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        To capture spatial data, open the <strong>VĀSTU Mobile App</strong> on your iPhone/iPad and connect using Session ID or QR code below.
                      </p>
                    </div>
                  </div>

                  {/* QR & Session Pairing Box */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-white/10">
                    <div className="bg-black/50 p-4 rounded-xl border border-white/10 flex items-center gap-3">
                      <div className="w-12 h-12 bg-white rounded-lg flex items-center justify-center text-black font-bold text-xs shrink-0">
                        <QrCode className="w-8 h-8 text-black" />
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">Scan with Mobile App</span>
                        <span className="text-xs text-[#dfb873] font-mono font-bold">VĀSTU Spatial QR</span>
                      </div>
                    </div>

                    <div className="bg-black/50 p-4 rounded-xl border border-white/10 flex flex-col justify-between space-y-2">
                      <span className="text-[10px] text-slate-400 uppercase font-mono">Session Pairing Code</span>
                      <div className="flex items-center justify-between bg-black/60 px-3 py-1.5 rounded-lg border border-white/10 font-mono text-sm text-white">
                        <span>{captureId?.slice(0, 8).toUpperCase() || 'CAP-SESSION'}</span>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(captureId || '');
                            setCopiedSessionId(true);
                            setTimeout(() => setCopiedSessionId(false), 2000);
                          }}
                          className="text-xs text-[#dfb873] hover:underline"
                        >
                          {copiedSessionId ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {mobileConnected && phase === 'RECON_PHASE' && (
                <div className="bg-[#0d1118]/85 backdrop-blur-xl border border-[#dfb873]/30 p-4 rounded-2xl shadow-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-[#dfb873]/20 border border-[#dfb873]/40 flex items-center justify-center">
                      <RefreshCw className="w-6 h-6 text-[#dfb873] animate-spin" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-bold text-white">Mobile 360° Reconnaissance Scan</h3>
                      <p className="text-xs text-slate-300 mt-1">
                        Surveyor is capturing initial space overview. Click below to analyze SOP.
                      </p>
                    </div>
                    <button
                      onClick={handleAnalyzeSOP}
                      className="px-4 py-2 bg-[#dfb873] text-[#0b0f17] font-bold text-xs rounded-xl shadow-lg hover:bg-[#c9a25b]"
                    >
                      Analyze SOP
                    </button>
                  </div>
                </div>
              )}

              {phase === 'SOP_ANALYSIS' && (
                <div className="bg-[#0d1118]/85 backdrop-blur-xl border border-[#dfb873]/30 p-4 rounded-2xl shadow-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-[#dfb873]/20 border border-[#dfb873]/40 flex items-center justify-center">
                      <Sparkles className="w-6 h-6 text-[#dfb873] animate-pulse" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-bold text-white">Generating Spatial Capture Protocol</h3>
                      <p className="text-xs text-slate-300 mt-1">
                        Analyzing space scan to generate calibrated zone trajectories...
                      </p>
                    </div>
                    <div className="w-3 h-3 rounded-full bg-[#dfb873] animate-pulse" />
                  </div>
                </div>
              )}

              {phase === 'SOP_READY' && (
                <div className="bg-[#0d1118]/85 backdrop-blur-xl border border-emerald-500/30 p-4 rounded-2xl shadow-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                      <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-bold text-white">SOP Ready - Awaiting Guided Mobile Capture</h3>
                      <p className="text-xs text-slate-300 mt-1">
                        Spatial protocol generated. Mobile app will start guided zone capture.
                      </p>
                    </div>
                    <button
                      onClick={() => setPhase('ACTIVE_CAPTURE')}
                      className="px-4 py-2 bg-emerald-500 text-black font-bold text-xs rounded-xl shadow-lg hover:bg-emerald-400"
                    >
                      Start Guided Capture
                    </button>
                  </div>
                </div>
              )}

              {phase === 'ACTIVE_CAPTURE' && currentZone && (
                <div className="bg-[#0d1118]/90 backdrop-blur-xl border border-[#dfb873]/40 p-4 rounded-2xl shadow-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-[#dfb873]/20 border border-[#dfb873]/40 flex items-center justify-center">
                        <Activity className="w-5 h-5 text-[#dfb873]" />
                      </div>
                      <div>
                        <span className="text-[10px] uppercase font-bold tracking-wider text-[#dfb873]">
                          Zone {currentZoneIndex + 1} of {sopData?.zones.length}: {currentZone.name}
                        </span>
                        <p className="text-xs text-white leading-relaxed font-medium mt-0.5">
                          {currentZone.instructions}
                        </p>
                      </div>
                    </div>
                    <div className="w-3 h-3 rounded-full bg-[#dfb873] animate-pulse" />
                  </div>
                </div>
              )}

              {phase === 'COMPLETE' && (
                <div className="bg-emerald-500/15 backdrop-blur-xl border border-emerald-500/40 p-4 rounded-2xl shadow-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                      <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-bold text-white">Capture Session Complete</h3>
                      <p className="text-xs text-slate-300 mt-1">
                        All zones successfully captured and recorded.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Device Info Panel */}
            <div className="bg-black/60 backdrop-blur-md rounded-xl border border-white/15 p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold text-slate-300 flex items-center gap-2">
                  <Smartphone className="w-3.5 h-3.5" />
                  <span>Mobile Device Status</span>
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  {lastHeartbeat
                    ? `Last heartbeat: ${Math.floor((new Date().getTime() - lastHeartbeat.getTime()) / 1000)}s ago`
                    : 'Last heartbeat: Never'}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 block text-[10px]">Device</span>
                  <span className="text-white font-medium">{mobileDeviceName}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">Signal Quality</span>
                  <span
                    className={`font-medium ${
                      connectionQuality === 'EXCELLENT'
                        ? 'text-emerald-400'
                        : connectionQuality === 'GOOD'
                        ? 'text-[#dfb873]'
                        : 'text-amber-400'
                    }`}
                  >
                    {connectionQuality}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ============================================================== */}
        {/* RIGHT / BOTTOM: Floor Plan Projection & Spatial SOP Panel   */}
        {/* ============================================================== */}
        <div className="w-full lg:w-[480px] xl:w-[540px] bg-[#0d1118] flex flex-col shrink-0 overflow-y-auto">
          {/* Projection Area */}
          <div className="p-4 sm:p-6 flex flex-col space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-[#dfb873]" />
                  <span>
                    {hasFloorPlan ? 'Floor Plan Blueprint Projection' : 'Freeform 360° Spatial SLAM Grid'}
                  </span>
                </h3>
                <p className="text-[10px] text-slate-400">
                  {hasFloorPlan
                    ? '2D Architectural Vector Layout'
                    : 'No 2D blueprint uploaded — displaying freeform spatial SLAM grid'}
                </p>
              </div>

              {!hasFloorPlan && (
                <button
                  onClick={() => navigate(`/projects/${projectId}`)}
                  className="px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 rounded-lg text-[11px] font-semibold transition-all flex items-center gap-1"
                >
                  <Upload className="w-3 h-3" />
                  Add Plan
                </button>
              )}
            </div>

            {/* Vector Blueprint / Freeform SLAM Canvas */}
            <div className="relative w-full h-80 bg-[#080a0f] border border-[#dfb873]/30 rounded-2xl overflow-hidden flex items-center justify-center shadow-inner">
              <div className="absolute inset-0 opacity-15 bg-[radial-gradient(#dfb873_1px,transparent_1px)] [background-size:16px_16px]" />

              {!hasFloorPlan ? (
                // Honest Notice for No Floor Plan
                <div className="relative z-10 text-center p-6 space-y-3 max-w-xs">
                  <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mx-auto text-amber-400">
                    <Layers className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">Freeform 360° Spatial Reconstruction Grid</h4>
                    <p className="text-[11px] text-slate-400 mt-1">
                      No 2D floor plan blueprint uploaded for this floor. Monocular visual feature tracking active.
                    </p>
                  </div>
                  <button
                    onClick={() => navigate(`/projects/${projectId}`)}
                    className="px-3 py-1.5 bg-[#dfb873] hover:bg-[#c9a25b] text-[#0b0f17] font-bold text-xs rounded-xl shadow transition-all"
                  >
                    Upload Architectural Blueprint
                  </button>
                </div>
              ) : (
                // Architectural SVG Blueprint
                <svg className="w-full h-full p-4" viewBox="0 0 1000 700">
                  <rect
                    x="40"
                    y="40"
                    width="920"
                    height="620"
                    fill="rgba(255,255,255,0.02)"
                    stroke="#dfb873"
                    strokeWidth="4"
                    rx="12"
                  />
                  <line x1="330" y1="40" x2="330" y2="400" stroke="#dfb873" strokeWidth="2.5" strokeDasharray="6 3" />
                  <line x1="660" y1="40" x2="660" y2="660" stroke="#dfb873" strokeWidth="2.5" strokeDasharray="6 3" />
                  <line x1="40" y1="260" x2="660" y2="260" stroke="#dfb873" strokeWidth="2.5" strokeDasharray="6 3" />

                  {sopData &&
                    sopData.zones.map((zone, idx) => {
                      const isActive = currentZoneIndex === idx;
                      const isDone = completedZones.includes(zone.id);
                      return (
                        <g
                          key={zone.id}
                          onClick={() => {
                            setCurrentZoneIndex(idx);
                            setCameraPos({
                              x: zone.sector_bbox.x + zone.sector_bbox.width / 2,
                              y: zone.sector_bbox.y + zone.sector_bbox.height / 2,
                              angle: 45,
                            });
                          }}
                          className="cursor-pointer"
                        >
                          <rect
                            x={zone.sector_bbox.x}
                            y={zone.sector_bbox.y}
                            width={zone.sector_bbox.width}
                            height={zone.sector_bbox.height}
                            fill={
                              isDone
                                ? 'rgba(16, 185, 129, 0.18)'
                                : isActive
                                ? 'rgba(223, 184, 115, 0.22)'
                                : 'rgba(255, 255, 255, 0.04)'
                            }
                            stroke={
                              isDone
                                ? '#10b981'
                                : isActive
                                ? '#dfb873'
                                : 'rgba(255, 255, 255, 0.2)'
                            }
                            strokeWidth={isActive ? '3' : '1.5'}
                            strokeDasharray={isActive ? '6 4' : 'none'}
                            rx="8"
                          />
                          <text
                            x={zone.sector_bbox.x + 12}
                            y={zone.sector_bbox.y + 24}
                            fill={isDone ? '#10b981' : isActive ? '#dfb873' : '#94a3b8'}
                            fontSize="13"
                            fontWeight="bold"
                          >
                            {isDone ? `✓ ${zone.name}` : `${idx + 1}. ${zone.name}`}
                          </text>
                        </g>
                      );
                    })}

                  {mobileConnected && (
                    <g transform={`translate(${cameraPos.x}, ${cameraPos.y}) rotate(${cameraPos.angle})`}>
                      <path
                        d="M 0 0 L -40 -80 L 40 -80 Z"
                        fill="rgba(56, 189, 248, 0.25)"
                        stroke="#38bdf8"
                        strokeWidth="1"
                      />
                      <circle cx="0" cy="0" r="7" fill="#dfb873" stroke="#0b0f17" strokeWidth="2" />
                    </g>
                  )}
                </svg>
              )}

              {/* Legend */}
              <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between text-[10px] text-slate-400 font-mono bg-black/60 px-2.5 py-1 rounded-lg">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" /> Completed
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-[#dfb873]" /> Active Sector
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-sky-400" /> Mobile FOV
                </span>
              </div>
            </div>

            {/* SOP Analysis Results if generated */}
            {sopData && (
              <div className="p-4 rounded-2xl bg-white/5 border border-white/10 space-y-3 text-xs">
                <div className="flex items-center justify-between font-bold text-[#dfb873]">
                  <span>Spatial SOP Trajectory Protocol</span>
                  <Sparkles className="w-3.5 h-3.5" />
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed">{sopData.summary}</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
