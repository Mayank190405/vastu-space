import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Compass,
  Box,
  Layers,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Zap,
  Activity,
  Play,
  CheckCircle2,
  Cpu,
  Eye,
  Sliders,
  Maximize2
} from 'lucide-react';

export const HeroSection: React.FC = () => {
  // Live animated telemetry ticker simulation for visual dynamism
  const [telemetry, setTelemetry] = useState({
    camX: 1.24,
    camY: 1.65,
    camZ: -3.88,
    laplacianVariance: 184.6,
    activeNodes: 1420,
    reprojectionErr: 0.84,
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setTelemetry((prev) => ({
        camX: Number((prev.camX + (Math.random() * 0.04 - 0.02)).toFixed(2)),
        camY: Number((1.65 + Math.sin(Date.now() / 2000) * 0.03).toFixed(2)),
        camZ: Number((prev.camZ + (Math.random() * 0.04 - 0.02)).toFixed(2)),
        laplacianVariance: Number((180 + Math.random() * 12).toFixed(1)),
        activeNodes: 1420 + Math.floor(Math.sin(Date.now() / 5000) * 15),
        reprojectionErr: Number((0.82 + Math.random() * 0.05).toFixed(2)),
      }));
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  return (
    <section id="overview" className="relative pt-12 pb-24 overflow-hidden">
      {/* Background Radial Glow & Grid Elements */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[600px] pointer-events-none opacity-40">
        <div className="absolute top-10 left-1/4 w-96 h-96 bg-[#C5A059]/20 rounded-full blur-[120px]" />
        <div className="absolute top-24 right-1/4 w-[450px] h-[450px] bg-[#9A7B3E]/15 rounded-full blur-[140px]" />
      </div>

      {/* Subtle Blueprint Grid Pattern */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(#C5A059 1px, transparent 1px), linear-gradient(to right, #C5A059 1px, transparent 1px)`,
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Top Eyebrow Badge */}
        <div className="flex justify-center mb-6">
          <div className="inline-flex items-center space-x-2.5 px-4 py-1.5 rounded-full bg-[#1A1714] border border-[#C5A059]/40 shadow-lg shadow-black/40">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-[11px] font-mono uppercase tracking-[0.2em] text-[#E8C982] font-semibold">
              Autonomous Smartphone-to-3D Spatial Intelligence
            </span>
            <span className="text-[#6D5020]">|</span>
            <span className="text-[11px] font-mono text-[#A6998A] hidden sm:inline">
              Zero-LiDAR Photogrammetry
            </span>
          </div>
        </div>

        {/* Main Hero Header */}
        <div className="text-center max-w-4xl mx-auto space-y-6">
          <h1 className="font-serif text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-[#FAF7F0] leading-[1.12]">
            Transform Casual Phone Video into{' '}
            <span className="bg-gradient-to-r from-[#E8C982] via-[#C5A059] to-[#D9C099] bg-clip-text text-transparent">
              Metric 3D Architectural Twins
            </span>
          </h1>

          <p className="font-sans text-base sm:text-lg md:text-xl text-[#C4B9AC] font-light leading-relaxed max-w-3xl mx-auto">
            VĀSTU eliminates expensive terrestrial laser scanners and manual CAD drafting. Using consumer smartphones, our edge Standard Operating Procedure (SOP) guidance and 9-stage asynchronous photogrammetric pipeline synthesize millimeter-accurate 3D watertight meshes, 2D vector CAD floor plans, and ADA-compliant indoor obstacle navigation meshes in minutes.
          </p>

          {/* Quick Stats Pill Ribbon */}
          <div className="pt-2 pb-2 flex flex-wrap items-center justify-center gap-3 sm:gap-6 font-mono text-xs">
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#141210]/90 border border-[#C5A059]/30">
              <span className="text-[#C5A059] font-bold">0 mm</span>
              <span className="text-[#A6998A]">LiDAR Needed</span>
            </div>
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#141210]/90 border border-[#C5A059]/30">
              <span className="text-emerald-400 font-bold">± 1.4 cm</span>
              <span className="text-[#A6998A]">Laser-Verified Error</span>
            </div>
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#141210]/90 border border-[#C5A059]/30">
              <span className="text-[#E8C982] font-bold">9 Stages</span>
              <span className="text-[#A6998A]">Autonomous Pipeline</span>
            </div>
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#141210]/90 border border-[#C5A059]/30">
              <span className="text-blue-400 font-bold">60 FPS</span>
              <span className="text-[#A6998A]">Zero-Install WebGL</span>
            </div>
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#141210]/90 border border-[#C5A059]/30">
              <span className="text-[#E8C982] font-bold">100% Open</span>
              <span className="text-[#A6998A]">GLB / DXF / PostGIS</span>
            </div>
          </div>

          {/* Primary Action Buttons */}
          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/login"
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-gradient-to-r from-[#C5A059] via-[#E8C982] to-[#B08940] text-black font-semibold text-sm hover:brightness-110 shadow-xl shadow-[#C5A059]/25 transition-all flex items-center justify-center space-x-2 group"
            >
              <span>Launch Cloud Console</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link
              to="/viewer"
              className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-[#1A1714] border border-[#C5A059]/50 text-[#FAF7F0] font-semibold text-sm hover:bg-[#26221D] hover:border-[#C5A059] transition-all flex items-center justify-center space-x-2"
            >
              <Box className="w-4 h-4 text-[#C5A059]" />
              <span>Explore 3D Twin Viewer</span>
            </Link>

            <a
              href="#sop-simulator"
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl border border-white/10 text-[#C4B9AC] hover:text-white hover:border-[#C5A059]/30 text-sm font-medium transition-all flex items-center justify-center space-x-2"
            >
              <Sliders className="w-4 h-4 text-[#C5A059]" />
              <span>Test SOP Simulator</span>
            </a>
          </div>
        </div>

        {/* Visual Hero Showcase Display with Interactive Architectural HUD */}
        <div className="mt-16 relative max-w-5xl mx-auto">
          {/* Outer Ornamental Frame */}
          <div className="relative rounded-2xl p-1 bg-gradient-to-b from-[#C5A059]/50 via-[#4A3515]/30 to-[#0E0C0A] shadow-[0_20px_60px_-15px_rgba(0,0,0,0.9)]">
            <div className="relative rounded-[15px] bg-[#141210] overflow-hidden border border-[#C5A059]/30">
              {/* Top Studio Header Bar */}
              <div className="flex items-center justify-between px-4 py-2.5 bg-[#0E0C0A] border-b border-[#C5A059]/20 text-xs font-mono">
                <div className="flex items-center space-x-2 text-[#A6998A]">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                  <span className="ml-2 text-[#E8C982]">VASTU_SPATIAL_ENGINE_v3.0</span>
                  <span className="text-[#6D5020]">|</span>
                  <span className="text-[#9C9183]">SESSION_ID: DADAR-CFM-04963</span>
                </div>
                <div className="flex items-center space-x-4 text-[#9C9183]">
                  <span className="hidden sm:inline">PROJECTION: METRIC EPSG:0</span>
                  <span className="inline-flex items-center text-emerald-400 space-x-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>TELEMETRY STREAMING</span>
                  </span>
                </div>
              </div>

              {/* Main Image with Architectural Overlays */}
              <div className="relative aspect-[16/9] sm:aspect-[21/9] w-full bg-[#0E0C0A] flex items-center justify-center overflow-hidden">
                <img
                  src="/vastu_archway_hero.png"
                  alt="VĀSTU Architectural Archway Digital Twin"
                  className="w-full h-full object-cover object-center filter contrast-105 brightness-95"
                />

                {/* Subtle Vignette Gradient */}
                <div className="absolute inset-0 bg-gradient-to-t from-[#0E0C0A] via-transparent to-[#0E0C0A]/40" />

                {/* Overlaid Telemetry HUD Elements */}
                {/* 1. Camera Coordinates HUD (Top-Left) */}
                <div className="absolute top-4 left-4 p-3 rounded-xl bg-[#0E0C0A]/80 backdrop-blur-md border border-[#C5A059]/30 font-mono text-[11px] text-[#C4B9AC] space-y-1 shadow-lg">
                  <div className="text-[#E8C982] font-bold flex items-center space-x-1.5">
                    <Eye className="w-3.5 h-3.5 text-[#C5A059]" />
                    <span>6-DoF VIO CAMERA TRACKING</span>
                  </div>
                  <div className="text-[10px] text-[#A6998A]">
                    POS: [{telemetry.camX.toFixed(2)}, {telemetry.camY.toFixed(2)}, {telemetry.camZ.toFixed(2)}] m
                  </div>
                  <div className="text-[10px] text-emerald-400">
                    FLOOR NORMAL: [0.00, 1.00, 0.00] (Manhattan Snapped)
                  </div>
                </div>

                {/* 2. Quality Gate Indicators (Top-Right) */}
                <div className="absolute top-4 right-4 p-3 rounded-xl bg-[#0E0C0A]/80 backdrop-blur-md border border-[#C5A059]/30 font-mono text-[11px] text-[#C4B9AC] space-y-1 shadow-lg hidden sm:block">
                  <div className="text-[#E8C982] font-bold flex items-center space-x-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                    <span>EDGE QUALITY GATES</span>
                  </div>
                  <div className="text-[10px] text-[#A6998A] flex justify-between space-x-3">
                    <span>Laplacian Var:</span>
                    <span className="text-emerald-400 font-semibold">{telemetry.laplacianVariance} (≥ 120.0)</span>
                  </div>
                  <div className="text-[10px] text-[#A6998A] flex justify-between space-x-3">
                    <span>Reproj. Error:</span>
                    <span className="text-emerald-400 font-semibold">{telemetry.reprojectionErr} px (≤ 1.2 px)</span>
                  </div>
                </div>

                {/* 3. Center Target Reticle */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="relative w-28 h-28 border border-[#C5A059]/40 rounded-full flex items-center justify-center animate-pulse">
                    <div className="w-2 h-2 rounded-full bg-[#C5A059]" />
                    <div className="absolute -top-3 text-[9px] font-mono text-[#E8C982] bg-[#0E0C0A]/80 px-1 rounded">
                      CORNER ANCHOR LOCKED
                    </div>
                  </div>
                </div>

                {/* 4. Bottom Metric Readout Strip */}
                <div className="absolute bottom-4 inset-x-4 p-3 rounded-xl bg-[#0E0C0A]/90 backdrop-blur-md border border-[#C5A059]/30 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-[#C5A059]" />
                      <span className="text-[#A6998A]">PostGIS SRID:0 Nodes:</span>
                      <span className="text-[#FAF7F0] font-bold">{telemetry.activeNodes}</span>
                    </div>
                    <div className="hidden md:flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-400" />
                      <span className="text-[#A6998A]">ADA A* NavMesh:</span>
                      <span className="text-emerald-400 font-bold">OPTIMAL (Slope 2.1° ≤ 4.76°)</span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    <Link
                      to="/viewer"
                      className="px-3 py-1 rounded-lg bg-[#C5A059]/20 hover:bg-[#C5A059]/30 border border-[#C5A059]/40 text-[#E8C982] text-xs font-semibold flex items-center space-x-1.5 transition-colors"
                    >
                      <Maximize2 className="w-3.5 h-3.5" />
                      <span>Launch Full-Screen Interactive 3D</span>
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

