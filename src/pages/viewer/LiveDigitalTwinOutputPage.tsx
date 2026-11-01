import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Box,
  Maximize2,
  Minimize2,
  Download,
  ShieldCheck,
  Sparkles,
  ExternalLink,
  RotateCcw,
  Layers,
  Compass
} from 'lucide-react';

export const LiveDigitalTwinOutputPage: React.FC = () => {
  const navigate = useNavigate();
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
      setIsFullscreen(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#080a0f] text-white flex flex-col">
      {/* Top Navigation Bar */}
      <header className="bg-[#0d1118]/90 border-b border-[#dfb873]/30 px-4 sm:px-6 py-3 flex items-center justify-between shrink-0 backdrop-blur-md z-20">
        <div className="flex items-center space-x-3">
          <Link
            to="/"
            className="p-2 rounded-xl bg-[#1a1714] border border-[#dfb873]/30 text-[#e8c982] hover:text-white hover:border-[#dfb873] transition-colors"
            title="Back to Project Website"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="flex flex-col">
            <div className="flex items-center space-x-2">
              <span className="font-serif font-bold text-base text-[#e8c982] tracking-wide">
                VĀSTU 3D Digital Twin Output
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-500/40">
                LIVE PRODUCTION ASSET
              </span>
            </div>
            <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
              TSDF Volumetric Marching Cubes · 256k Triangles · 2048x2048 Texture Atlas
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-2 sm:space-x-3">
          <a
            href="/output/model.glb"
            download="vastu_digital_twin_model.glb"
            className="px-3 py-1.5 rounded-xl bg-[#1a1714] border border-[#dfb873]/40 text-[#e8c982] hover:text-white hover:border-[#dfb873] text-xs font-semibold flex items-center space-x-1.5 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Download GLB (3.16 MB)</span>
            <span className="sm:hidden">GLB</span>
          </a>

          <a
            href="/output/index.html"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 rounded-xl bg-[#1a1714] border border-white/20 text-slate-300 hover:text-white text-xs font-medium flex items-center space-x-1.5 transition-colors hidden md:flex"
            title="Open raw WebGL viewer in new tab"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Standalone Tab</span>
          </a>

          <button
            onClick={toggleFullscreen}
            className="p-2 rounded-xl bg-[#dfb873] text-black font-bold text-xs hover:brightness-110 shadow flex items-center space-x-1.5 transition-all"
            title="Toggle Fullscreen"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* Main Full-Height Viewport Embedding the Live Reconstructed Model */}
      <main className="flex-1 relative w-full h-[calc(100vh-57px)] bg-[#080a0f] overflow-hidden">
        <iframe
          src="/output/index.html"
          title="VĀSTU Live 3D Digital Twin Viewer"
          className="w-full h-full border-0 select-none"
          allow="accelerometer; gyroscope; vr; xr; pointer-lock"
        />
      </main>
    </div>
  );
};

