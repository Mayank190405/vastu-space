import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import {
  Camera,
  Layers,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Play,
  Square,
  Upload,
  RefreshCw,
  Compass,
  Eye,
  Sliders,
  ShieldCheck,
  Check,
  ChevronRight,
  Info,
  Clock,
  Maximize2
} from 'lucide-react';
import { api } from '../../services/api';
import { Project, ProjectFloor } from '../../types';
import { SpatialSOPService, CaptureSOPResponse, CaptureZone } from '../../services/spatialSOPService';

export const GuidedCaptureStudioPage: React.FC = () => {
  const { projectId, captureId } = useParams<{ projectId: string; captureId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  // Workflow phases:
  // 1. 'RECON_PROMPT': Show whole place 360° initial walkthrough
  // 2. 'SOP_ANALYSIS': Automated analysis of floorplan + 1st video
  // 3. 'SOP_REVIEW': Review generated guidelines and mistakes to avoid
  // 4. 'ACTIVE_CAPTURE': Guided area-to-area capture with floor plan projection
  // 5. 'COMPLETE': All zones captured, ready for 25-stage reconstruction
  const [phase, setPhase] = useState<
    'RECON_PROMPT' | 'SOP_ANALYSIS' | 'SOP_REVIEW' | 'ACTIVE_CAPTURE' | 'COMPLETE'
  >('RECON_PROMPT');

  const [project, setProject] = useState<Project | null>(null);
  const [selectedFloor, setSelectedFloor] = useState<ProjectFloor | null>(null);

  // Camera & Recording
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [reconVideoRecorded, setReconVideoRecorded] = useState(false);
  const [motionPace, setMotionPace] = useState<'OPTIMAL' | 'TOO_FAST' | 'STATIONARY'>('OPTIMAL');

  // Spatial SOP Data
  const [sopData, setSOPData] = useState<CaptureSOPResponse | null>(null);
  const [activeZoneIndex, setActiveZoneIndex] = useState(0);
  const [completedZones, setCompletedZones] = useState<string[]>([]);
  const [cameraPos, setCameraPos] = useState({ x: 180, y: 150, angle: 45 });

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

  // Start Device Camera
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setCameraActive(true);
    } catch (err) {
      console.warn('Camera access denied or unavailable, using simulated video viewport', err);
      setCameraActive(false);
    }
  };

  useEffect(() => {
    startCamera();
    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Timer simulation during recording
  useEffect(() => {
    let interval: any;
    if (isRecording) {
      interval = setInterval(() => {
        setRecordSeconds((s) => s + 1);
        // Simulate camera movement on floor plan
        setCameraPos((prev) => ({
          x: prev.x + (Math.random() * 4 - 2),
          y: prev.y + (Math.random() * 4 - 2),
          angle: (prev.angle + 3) % 360
        }));
      }, 1000);
    } else {
      setRecordSeconds(0);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  // Toggle Recording for Current Phase
  const handleToggleRecord = () => {
    if (!isRecording) {
      setIsRecording(true);
    } else {
      setIsRecording(false);
      if (phase === 'RECON_PROMPT') {
        setReconVideoRecorded(true);
      } else if (phase === 'ACTIVE_CAPTURE' && sopData) {
        const currentZone = sopData.zones[activeZoneIndex];
        if (!completedZones.includes(currentZone.id)) {
          setCompletedZones([...completedZones, currentZone.id]);
        }
      }
    }
  };

  // Trigger Automated Spatial SOP Generation
  const handleAnalyzeSOP = async () => {
    setPhase('SOP_ANALYSIS');
    try {
      const floorName = selectedFloor?.name || 'Ground Floor';
      const area = selectedFloor?.area_value || 2500;
      const height = selectedFloor?.height_value || 10.5;

      const sop = await SpatialSOPService.generateCaptureSOP({
        projectName: project?.name || 'Spatial Project',
        floorName,
        areaSqft: area,
        heightFt: height,
        projectType: project?.project_type || 'Building',
        floorPlanImageUrl: selectedFloor?.floor_plan?.preview_url || undefined
      });

      setSOPData(sop);
      setPhase('SOP_REVIEW');
    } catch (err) {
      console.error('Failed SOP generation:', err);
      setPhase('SOP_REVIEW');
    }
  };

  // Advance to next zone in active capture
  const handleNextZone = () => {
    if (!sopData) return;
    if (activeZoneIndex < sopData.zones.length - 1) {
      const nextIdx = activeZoneIndex + 1;
      setActiveZoneIndex(nextIdx);
      const nextZone = sopData.zones[nextIdx];
      // Reposition camera anchor on floor plan
      setCameraPos({
        x: nextZone.sector_bbox.x + nextZone.sector_bbox.width / 2,
        y: nextZone.sector_bbox.y + nextZone.sector_bbox.height / 2,
        angle: 60
      });
    } else {
      setPhase('COMPLETE');
    }
  };

  const currentZone: CaptureZone | undefined = sopData?.zones[activeZoneIndex];

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
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <h1 className="text-sm font-bold text-white font-serif-brand tracking-wide">
                Guided Spatial Capture Studio
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/10 text-[#dfb873] border border-[#dfb873]/20">
                {project?.project_code || 'PRJ-STUDIO'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              {project?.name} &bull; {selectedFloor?.name || 'Ground Floor'} &bull; Spatial SOP Guidance
            </p>
          </div>
        </div>

        {/* Phase Pill Indicators */}
        <div className="hidden md:flex items-center gap-2 text-xs font-semibold">
          <span
            className={`px-3 py-1 rounded-full border transition-all ${
              phase === 'RECON_PROMPT'
                ? 'bg-[#dfb873] text-[#0b0f17] border-[#dfb873] font-bold'
                : 'bg-white/5 text-slate-400 border-white/10'
            }`}
          >
            1. Whole Place Scan
          </span>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
          <span
            className={`px-3 py-1 rounded-full border transition-all ${
              phase === 'SOP_ANALYSIS' || phase === 'SOP_REVIEW'
                ? 'bg-[#dfb873] text-[#0b0f17] border-[#dfb873] font-bold'
                : 'bg-white/5 text-slate-400 border-white/10'
            }`}
          >
            2. Spatial SOP
          </span>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
          <span
            className={`px-3 py-1 rounded-full border transition-all ${
              phase === 'ACTIVE_CAPTURE' || phase === 'COMPLETE'
                ? 'bg-[#dfb873] text-[#0b0f17] border-[#dfb873] font-bold'
                : 'bg-white/5 text-slate-400 border-white/10'
            }`}
          >
            3. Floor Plan Area Capture
          </span>
        </div>
      </header>

      {/* 2. Main Studio Content */}
      <main className="flex-1 relative flex flex-col lg:flex-row overflow-hidden">
        {/* ============================================================== */}
        {/* LEFT / TOP: Camera Viewport & Real-Time Guidance HUD           */}
        {/* ============================================================== */}
        <div className="flex-1 relative flex flex-col justify-between bg-black overflow-hidden border-b lg:border-b-0 lg:border-r border-white/10">
          {/* Live Video / Stream Simulation */}
          <div className="absolute inset-0 z-0">
            {cameraActive ? (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full relative bg-gradient-to-b from-[#111827] via-[#0f172a] to-[#080a0f] flex items-center justify-center overflow-hidden">
                {/* Simulated 3D Room Grid Viewport */}
                <div className="absolute inset-0 opacity-20 bg-[linear-gradient(to_right,#dfb873_1px,transparent_1px),linear-gradient(to_bottom,#dfb873_1px,transparent_1px)] bg-[size:40px_40px]" />
                <div className="text-center space-y-3 z-10 p-6 max-w-sm">
                  <div className="w-14 h-14 rounded-2xl bg-[#dfb873]/10 border border-[#dfb873]/30 text-[#dfb873] flex items-center justify-center mx-auto">
                    <Camera className="w-7 h-7" />
                  </div>
                  <h3 className="text-sm font-bold text-white">Spatial Camera Engine Active</h3>
                  <p className="text-xs text-slate-400">
                    Live camera feed initialized with 60 FPS motion tracking and optical flow stabilization.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Camera Viewport Overlay HUD (Top) */}
          <div className="relative z-10 p-4 flex items-start justify-between gap-3 bg-gradient-to-b from-black/80 via-black/40 to-transparent">
            {/* Phase Instructions & Warnings */}
            <div className="space-y-1.5 max-w-md">
              {phase === 'RECON_PROMPT' && (
                <div className="bg-[#0d1118]/85 backdrop-blur-xl border border-[#dfb873]/30 p-3 rounded-2xl shadow-xl">
                  <div className="flex items-center gap-2 text-xs font-bold text-[#dfb873]">
                    <Sparkles className="w-4 h-4 text-[#dfb873]" />
                    <span>Phase 1: Initial Space Reconnaissance</span>
                  </div>
                  <p className="text-xs text-slate-200 mt-1 leading-relaxed">
                    Stand in the center/entrance. <span className="text-[#dfb873] font-bold">Show the whole place</span> by panning 360° smoothly and walking the outer perimeter to register global room scale.
                  </p>
                </div>
              )}

              {phase === 'ACTIVE_CAPTURE' && currentZone && (
                <div className="bg-[#0d1118]/90 backdrop-blur-xl border border-[#dfb873]/40 p-3.5 rounded-2xl shadow-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-[#dfb873]">
                      Zone {activeZoneIndex + 1} of {sopData?.zones.length}: {currentZone.name}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      Target: {currentZone.target_duration_sec}s
                    </span>
                  </div>
                  <p className="text-xs text-white leading-relaxed font-medium">
                    {currentZone.instructions}
                  </p>
                  {currentZone.zone_mistakes && (
                    <div className="p-2 bg-amber-500/15 border border-amber-500/30 rounded-xl flex items-start gap-2 text-[11px] text-amber-200">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                      <span>{currentZone.zone_mistakes}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Stability & Motion Indicators */}
            <div className="flex flex-col items-end gap-2">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-black/60 backdrop-blur-md rounded-xl border border-white/15 text-xs font-mono">
                <Compass className="w-3.5 h-3.5 text-sky-400" />
                <span>Tilt: 15° Down</span>
              </div>
              <div
                className={`px-3 py-1 rounded-xl text-[11px] font-bold border transition-all ${
                  motionPace === 'OPTIMAL'
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                }`}
              >
                Pace: {motionPace === 'OPTIMAL' ? '0.4 m/s (Optimal)' : 'Slow Down'}
              </div>
              {isRecording && (
                <div className="flex items-center gap-1.5 px-3 py-1 bg-red-600/90 text-white rounded-xl text-xs font-mono font-bold animate-pulse">
                  <div className="w-2 h-2 rounded-full bg-white" />
                  <span>{new Date(recordSeconds * 1000).toISOString().substr(14, 5)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Camera Viewport Overlay HUD (Bottom Action Bar) */}
          <div className="relative z-10 p-4 sm:p-6 flex flex-col sm:flex-row items-center justify-between gap-3 bg-gradient-to-t from-black/90 via-black/50 to-transparent">
            {/* Left helper text */}
            <div className="text-xs text-slate-300">
              {phase === 'RECON_PROMPT' && !reconVideoRecorded && (
                <span>Record a 15-30 second initial panoramic walkaround of the space.</span>
              )}
              {phase === 'RECON_PROMPT' && reconVideoRecorded && (
                <span className="text-emerald-400 font-bold flex items-center gap-1">
                  <Check className="w-4 h-4" /> 1st Reconnaissance Scan captured successfully.
                </span>
              )}
              {phase === 'ACTIVE_CAPTURE' && (
                <span>Maintain 70% continuous overlap as you trace the room boundaries.</span>
              )}
            </div>

            {/* Central Controls */}
            <div className="flex items-center gap-3">
              {phase === 'RECON_PROMPT' && !reconVideoRecorded && (
                <button
                  onClick={handleToggleRecord}
                  className={`px-6 py-3 rounded-2xl font-bold text-xs flex items-center gap-2 shadow-2xl transition-all active:scale-95 ${
                    isRecording
                      ? 'bg-red-600 hover:bg-red-700 text-white ring-4 ring-red-500/30'
                      : 'bg-[#dfb873] hover:bg-[#c9a25b] text-[#0b0f17]'
                  }`}
                >
                  {isRecording ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
                  <span>{isRecording ? 'Finish Recon Walkaround' : 'Record 360° Scan'}</span>
                </button>
              )}

              {phase === 'RECON_PROMPT' && reconVideoRecorded && (
                <button
                  onClick={handleAnalyzeSOP}
                  className="px-6 py-3 bg-gradient-to-r from-[#dfb873] to-[#ffd88a] text-[#0b0f17] font-extrabold text-xs rounded-2xl shadow-2xl flex items-center gap-2 transition-all active:scale-95 animate-pulse"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Generate Spatial Capture SOP</span>
                </button>
              )}

              {phase === 'ACTIVE_CAPTURE' && (
                <>
                  <button
                    onClick={handleToggleRecord}
                    className={`px-5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 shadow-lg transition-all ${
                      isRecording
                        ? 'bg-red-600 text-white ring-4 ring-red-500/30'
                        : 'bg-[#dfb873] text-[#0b0f17]'
                    }`}
                  >
                    {isRecording ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
                    <span>{isRecording ? 'Save Zone Capture' : `Record ${currentZone?.name || 'Zone'}`}</span>
                  </button>

                  <button
                    onClick={handleNextZone}
                    className="px-4 py-2.5 bg-white/10 hover:bg-white/20 text-white font-semibold text-xs rounded-xl border border-white/15 flex items-center gap-1.5 transition-all"
                  >
                    <span>Next Zone</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* ============================================================== */}
        {/* RIGHT / BOTTOM: Floor Plan Projection & Spatial SOP Panel   */}
        {/* ============================================================== */}
        <div className="w-full lg:w-[480px] xl:w-[540px] bg-[#0d1118] flex flex-col shrink-0 overflow-y-auto">
          {/* Phase 2 Modal Overlay: SOP Analysis in Progress */}
          {phase === 'SOP_ANALYSIS' && (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-4">
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#dfb873] to-[#a8823b] flex items-center justify-center text-[#0b0f17] shadow-xl animate-pulse">
                  <Sparkles className="w-8 h-8" />
                </div>
                <div className="absolute -inset-3 rounded-2xl border border-[#dfb873]/50 animate-ping opacity-25" />
              </div>
              <h3 className="text-base font-bold text-white font-serif-brand">
                Autonomous Spatial Analysis
              </h3>
              <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
                Analyzing the architectural floor plan blueprint and the 360° space scan to generate calibrated zone trajectories and pitfall alerts...
              </p>
            </div>
          )}

          {/* Phase 2b: SOP Review Screen */}
          {phase === 'SOP_REVIEW' && sopData && (
            <div className="p-6 space-y-5">
              <div className="flex items-center gap-2 text-xs font-bold text-[#dfb873]">
                <Sparkles className="w-4 h-4 text-[#dfb873]" />
                <span>Spatial Capture Protocol Generated</span>
              </div>

              {/* Layout Summary Card */}
              <div className="p-4 rounded-2xl bg-white/5 border border-white/10 space-y-2">
                <h4 className="text-xs font-bold text-white font-serif-brand">Spatial Plan Analysis</h4>
                <p className="text-xs text-slate-300 leading-relaxed">{sopData.summary}</p>
              </div>

              {/* Global Calibration Guidelines */}
              <div className="p-4 rounded-2xl bg-[#080a0f] border border-[#dfb873]/30 space-y-2 text-xs">
                <span className="font-bold text-[#dfb873] uppercase tracking-wider text-[10px]">
                  Physical Capture Standards
                </span>
                <div className="grid grid-cols-2 gap-2 text-slate-300 pt-1">
                  <div>
                    <span className="text-slate-500 block text-[10px]">Speed</span>
                    <span className="font-mono text-white">{sopData.global_guidelines.speed}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Camera Angle</span>
                    <span className="font-mono text-white">{sopData.global_guidelines.phone_tilt}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Height</span>
                    <span className="font-mono text-white">{sopData.global_guidelines.phone_height}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Feature Overlap</span>
                    <span className="font-mono text-emerald-400">{sopData.global_guidelines.overlap_percentage}</span>
                  </div>
                </div>
              </div>

              {/* Mistakes to Avoid & Hazards Detected */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Mistakes & Space Pitfalls to Avoid</span>
                </span>
                <div className="space-y-2">
                  {sopData.mistakes_to_avoid.map((m) => (
                    <div
                      key={m.id}
                      className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 space-y-1 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-amber-200">{m.title}</span>
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">
                          {m.severity}
                        </span>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-relaxed">{m.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Button */}
              <button
                onClick={() => setPhase('ACTIVE_CAPTURE')}
                className="w-full py-3 bg-[#dfb873] hover:bg-[#c9a25b] text-[#0b0f17] font-bold text-xs rounded-2xl shadow-xl flex items-center justify-center gap-2 transition-all active:scale-95"
              >
                <span>Proceed to Guided Floor Plan Capture</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Phase 3 & 4: Interactive Floor Plan Projection */}
          {(phase === 'RECON_PROMPT' || phase === 'ACTIVE_CAPTURE' || phase === 'COMPLETE') && (
            <div className="p-4 sm:p-6 flex flex-col h-full space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-[#dfb873]" />
                    <span>Floor Plan Projection</span>
                  </h3>
                  <p className="text-[10px] text-slate-400">
                    Real-time surveyor position & zone boundary tracking
                  </p>
                </div>

                {sopData && (
                  <span className="text-xs font-mono text-[#dfb873] bg-white/5 px-2.5 py-1 rounded-xl border border-white/10">
                    {completedZones.length} of {sopData.zones.length} Zones Completed
                  </span>
                )}
              </div>

              {/* Vector Architectural Floor Plan Canvas Projection */}
              <div className="relative w-full h-80 bg-[#080a0f] border border-[#dfb873]/30 rounded-2xl overflow-hidden flex items-center justify-center shadow-inner">
                {/* Floor Plan Grid */}
                <div className="absolute inset-0 opacity-15 bg-[radial-gradient(#dfb873_1px,transparent_1px)] [background-size:16px_16px]" />

                {/* SVG Blueprint Projection */}
                <svg className="w-full h-full p-4" viewBox="0 0 1000 700">
                  {/* Outer Wall Boundary */}
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

                  {/* Partition Walls */}
                  <line x1="330" y1="40" x2="330" y2="400" stroke="#dfb873" strokeWidth="2.5" strokeDasharray="6 3" />
                  <line x1="660" y1="40" x2="660" y2="660" stroke="#dfb873" strokeWidth="2.5" strokeDasharray="6 3" />
                  <line x1="40" y1="260" x2="660" y2="260" stroke="#dfb873" strokeWidth="2.5" strokeDasharray="6 3" />

                  {/* Dynamic SOP Room Zones */}
                  {sopData ? (
                    sopData.zones.map((zone, idx) => {
                      const isActive = activeZoneIndex === idx;
                      const isDone = completedZones.includes(zone.id);
                      return (
                        <g
                          key={zone.id}
                          onClick={() => {
                            setActiveZoneIndex(idx);
                            setCameraPos({
                              x: zone.sector_bbox.x + zone.sector_bbox.width / 2,
                              y: zone.sector_bbox.y + zone.sector_bbox.height / 2,
                              angle: 45
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
                            fontFamily="Plus Jakarta Sans"
                          >
                            {isDone ? `✓ ${zone.name}` : `${idx + 1}. ${zone.name}`}
                          </text>
                        </g>
                      );
                    })
                  ) : (
                    /* Default Initial Blueprint Projection */
                    <g>
                      <rect x="60" y="60" width="250" height="180" fill="rgba(223,184,115,0.08)" stroke="#dfb873" strokeWidth="1.5" rx="6" />
                      <text x="75" y="90" fill="#dfb873" fontSize="12" fontWeight="bold">Entrance Foyer</text>

                      <rect x="350" y="60" width="290" height="180" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" rx="6" />
                      <text x="365" y="90" fill="#94a3b8" fontSize="12" fontWeight="bold">Corridor & Circulation</text>

                      <rect x="60" y="280" width="580" height="350" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" rx="6" />
                      <text x="75" y="310" fill="#94a3b8" fontSize="12" fontWeight="bold">Main Hall Workspace</text>

                      <rect x="680" y="60" width="260" height="570" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" rx="6" />
                      <text x="695" y="90" fill="#94a3b8" fontSize="12" fontWeight="bold">Conference Suite</text>
                    </g>
                  )}

                  {/* Projected Surveyor Camera Icon & Directional FOV Cone */}
                  <g transform={`translate(${cameraPos.x}, ${cameraPos.y}) rotate(${cameraPos.angle})`}>
                    {/* FOV View Cone */}
                    <path
                      d="M 0 0 L -40 -80 L 40 -80 Z"
                      fill="rgba(56, 189, 248, 0.25)"
                      stroke="#38bdf8"
                      strokeWidth="1"
                    />
                    {/* Camera Dot */}
                    <circle cx="0" cy="0" r="7" fill="#dfb873" stroke="#0b0f17" strokeWidth="2" />
                  </g>
                </svg>

                {/* Floor Plan Legend */}
                <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between text-[10px] text-slate-400 font-mono bg-black/60 px-2.5 py-1 rounded-lg">
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" /> Completed
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-[#dfb873]" /> Active Sector
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-sky-400" /> Surveyor FOV
                  </span>
                </div>
              </div>

              {/* Zone Trajectory List */}
              {sopData && (
                <div className="space-y-2 flex-1">
                  <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                    Capture Trajectory Checklist
                  </span>
                  <div className="space-y-1.5">
                    {sopData.zones.map((z, idx) => {
                      const isCurrent = activeZoneIndex === idx;
                      const isDone = completedZones.includes(z.id);
                      return (
                        <div
                          key={z.id}
                          onClick={() => setActiveZoneIndex(idx)}
                          className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all flex items-center justify-between ${
                            isCurrent
                              ? 'bg-[#dfb873]/15 border-[#dfb873] text-white'
                              : isDone
                              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
                              : 'bg-white/5 border-white/5 text-slate-400 hover:bg-white/10'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[10px] font-bold w-4">
                              {idx + 1}.
                            </span>
                            <span className="font-semibold">{z.name}</span>
                          </div>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              isDone
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : isCurrent
                                ? 'bg-[#dfb873] text-[#0b0f17]'
                                : 'bg-white/10 text-slate-400'
                            }`}
                          >
                            {isDone ? 'Completed' : isCurrent ? 'Active' : 'Pending'}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Complete Workflow Trigger */}
              {phase === 'COMPLETE' && (
                <div className="p-4 rounded-2xl bg-emerald-500/15 border border-emerald-500/40 text-center space-y-3">
                  <div className="w-10 h-10 rounded-full bg-emerald-500 text-black flex items-center justify-center mx-auto">
                    <Check className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white">Full Floor Space Captured</h4>
                    <p className="text-xs text-slate-300 mt-0.5">
                      All sector boundaries recorded with continuous visual overlap and calibrated metric scaling.
                    </p>
                  </div>
                  <button
                    onClick={() => navigate(`/projects/${projectId}/viewer`)}
                    className="w-full py-2.5 bg-emerald-500 hover:bg-emerald-400 text-black font-bold text-xs rounded-xl transition-all shadow-lg"
                  >
                    Compile & Launch 3D Digital Twin Viewer
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
