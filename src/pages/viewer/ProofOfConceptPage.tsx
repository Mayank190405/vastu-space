import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  Box,
  Maximize2,
  Minimize2,
  Download,
  ShieldCheck,
  Sparkles,
  ExternalLink,
  Compass,
  Monitor,
  CheckCircle2,
  Layers,
  Cpu,
  Eye,
  FileText
} from 'lucide-react';

export const ProofOfConceptPage: React.FC = () => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeTab, setActiveTab] = useState<'viewer' | 'specs' | 'downloads'>('viewer');

  const toggleFullscreen = () => {
    const el = document.getElementById('poc-viewer-frame');
    if (!document.fullscreenElement && el) {
      el.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
      setIsFullscreen(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#080a0f] text-white flex flex-col font-sans">
      {/* Top Banner */}
      <div className="bg-[#14100c] border-b border-[#dfb873]/30 px-4 py-2 text-xs flex items-center justify-between text-[#d8cdba]">
        <div className="flex items-center space-x-2">
          <span className="px-2 py-0.5 rounded-full bg-[#dfb873]/20 text-[#e8c982] border border-[#dfb873]/40 font-mono text-[10px] font-bold uppercase">
            Techfest IIT Bombay 2026 · Round 1 Deliverable
          </span>
          <span className="hidden sm:inline text-slate-300">
            Proof of Concept & Working Free-Roaming Web Viewer
          </span>
        </div>
        <div className="flex items-center space-x-3 text-xs">
          <span className="flex items-center space-x-1 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Production Live (AWS EC2)</span>
          </span>
        </div>
      </div>

      {/* Main Header Bar */}
      <header className="bg-[#0d1118]/90 border-b border-[#dfb873]/20 px-4 sm:px-6 py-3 flex items-center justify-between backdrop-blur-md sticky top-0 z-20">
        <div className="flex items-center space-x-3">
          <Link
            to="/"
            className="p-2 rounded-xl bg-[#1a1714] border border-[#dfb873]/30 text-[#e8c982] hover:text-white hover:border-[#dfb873] transition-colors"
            title="Return to Main Portal"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-serif font-bold text-base sm:text-lg text-[#e8c982]">
                VĀSTU Proof of Concept
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-950/80 text-amber-300 border border-amber-500/40">
                BEDROOM DIGITAL TWIN
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Photogrammetric & Neural Metric TSDF Reconstruction · Zero-Install WebGL Roaming
            </p>
          </div>
        </div>

        {/* Tab Navigation & Fullscreen */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center bg-[#161b22] p-1 rounded-xl border border-white/10 text-xs">
            <button
              onClick={() => setActiveTab('viewer')}
              className={`px-3 py-1 rounded-lg transition-all ${
                activeTab === 'viewer'
                  ? 'bg-[#dfb873] text-black font-bold'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              3D Walkthrough
            </button>
            <button
              onClick={() => setActiveTab('specs')}
              className={`px-3 py-1 rounded-lg transition-all ${
                activeTab === 'specs'
                  ? 'bg-[#dfb873] text-black font-bold'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              System Specs
            </button>
            <button
              onClick={() => setActiveTab('downloads')}
              className={`px-3 py-1 rounded-lg transition-all ${
                activeTab === 'downloads'
                  ? 'bg-[#dfb873] text-black font-bold'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              3D Assets
            </button>
          </div>

          <a
            href="/output/index.html"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-xl bg-[#1a1714] border border-[#dfb873]/30 text-[#e8c982] hover:text-white hidden md:flex items-center space-x-1 text-xs"
            title="Open pure WebGL in standalone tab"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </header>

      {/* Primary Content Area */}
      <main className="flex-1 flex flex-col">
        {activeTab === 'viewer' && (
          <div className="flex-1 flex flex-col">
            {/* Quick Control Bar Overlay */}
            <div className="bg-[#0b0e14] border-b border-white/10 px-4 py-2 text-xs flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center space-x-4">
                <span className="text-slate-400 font-mono text-[11px]">CONTROLS:</span>
                <span className="text-slate-300">
                  <kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-[10px] font-mono border border-slate-700 text-amber-300">W</kbd>
                  <kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-[10px] font-mono border border-slate-700 text-amber-300 ml-1">A</kbd>
                  <kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-[10px] font-mono border border-slate-700 text-amber-300 ml-1">S</kbd>
                  <kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-[10px] font-mono border border-slate-700 text-amber-300 ml-1">D</kbd> / Arrow keys to walk
                </span>
                <span className="hidden md:inline text-slate-300">
                  <strong>Left Click + Drag</strong> to look around (360°)
                </span>
                <span className="hidden lg:inline text-slate-300">
                  <strong>Scroll</strong> to zoom
                </span>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={toggleFullscreen}
                  className="px-2.5 py-1 rounded-lg bg-[#1a1714] border border-[#dfb873]/40 text-[#e8c982] text-xs font-semibold hover:bg-[#26221d] flex items-center space-x-1"
                >
                  {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                  <span>{isFullscreen ? 'Exit Fullscreen' : 'Fullscreen Roam'}</span>
                </button>
              </div>
            </div>

            {/* Embedded 3D Digital Twin Viewport */}
            <div id="poc-viewer-frame" className="flex-1 relative w-full min-h-[550px] bg-[#080a0f]">
              <iframe
                src="/output/index.html"
                title="VĀSTU 3D Proof of Concept Viewer"
                className="w-full h-full border-0"
                allow="accelerometer; gyroscope; vr; xr; pointer-lock"
              />
            </div>

            {/* Bottom Proof of Concept Metrics Bar */}
            <div className="bg-[#0d1118] border-t border-[#dfb873]/20 px-4 py-2.5 flex flex-wrap items-center justify-between text-xs text-slate-300 gap-3">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span>TSDF Marching Cubes: <strong className="text-white">256,632 Triangles</strong></span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <Layers className="w-3.5 h-3.5 text-amber-400" />
                  <span>Point Cloud: <strong className="text-white">437,306 Points</strong></span>
                </div>
                <div className="hidden sm:flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                  <span>Texture Atlas: <strong className="text-white">2048 × 2048 Photographic</strong></span>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-[11px] text-slate-400 font-mono">Metric Dimensions:</span>
                <span className="px-2 py-0.5 rounded bg-black/60 border border-slate-700 text-[#e8c982] font-mono font-bold text-[11px]">
                  7.30m × 4.85m × 5.97m
                </span>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'specs' && (
          <div className="max-w-4xl mx-auto p-6 space-y-6 w-full">
            <div className="p-6 rounded-2xl bg-[#0f141d] border border-[#dfb873]/30">
              <h2 className="text-lg font-serif font-bold text-[#e8c982] mb-3">
                Evaluation Criteria Alignment
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="p-4 rounded-xl bg-black/40 border border-white/10">
                  <h3 className="font-bold text-white mb-1 flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>SOP & Pipeline Soundness</span>
                  </h3>
                  <p className="text-slate-300 leading-relaxed">
                    25-stage evidence-driven architecture enforcing metric scale anchors, RANSAC camera pose trajectory, and zero hallucinated geometry.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-black/40 border border-white/10">
                  <h3 className="font-bold text-white mb-1 flex items-center space-x-1.5">
                    <Eye className="w-4 h-4 text-amber-400" />
                    <span>Visual Quality & Model Fidelity</span>
                  </h3>
                  <p className="text-slate-300 leading-relaxed">
                    Multi-view visibility-aware UV projection over 2048x2048 texture atlas preserving physical materials, textures, and planar wall straightness.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-black/40 border border-white/10">
                  <h3 className="font-bold text-white mb-1 flex items-center space-x-1.5">
                    <Cpu className="w-4 h-4 text-sky-400" />
                    <span>Web Viewer Performance</span>
                  </h3>
                  <p className="text-slate-300 leading-relaxed">
                    Zero-install WebGL 2.0 running at a locked 60 FPS in Chrome, Safari, and Edge on standard integrated GPUs.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-black/40 border border-white/10">
                  <h3 className="font-bold text-white mb-1 flex items-center space-x-1.5">
                    <CheckCircle2 className="w-4 h-4 text-teal-400" />
                    <span>Zero Login & Access Guarantee</span>
                  </h3>
                  <p className="text-slate-300 leading-relaxed">
                    Completely public without paywalls or account barriers. Available 24/7 on AWS EC2 at <code>https://vastu.krads.co.in/output</code>.
                  </p>
                </div>
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-[#0f141d] border border-white/10">
              <h2 className="text-lg font-serif font-bold text-white mb-3">
                Supported Platforms & Browsers
              </h2>
              <div className="overflow-x-auto text-xs">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-white/20 text-[#e8c982]">
                      <th className="py-2 pr-4 font-semibold">Browser / OS</th>
                      <th className="py-2 pr-4 font-semibold">Compatibility</th>
                      <th className="py-2 font-semibold">Accelerated Feature</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10 text-slate-300">
                    <tr>
                      <td className="py-2.5 pr-4 font-medium text-white">Google Chrome (Desktop / Mobile)</td>
                      <td className="py-2.5 pr-4 text-emerald-400">100% Tested</td>
                      <td className="py-2.5">Hardware WebGL 2.0, Pointer Lock WASD Roaming</td>
                    </tr>
                    <tr>
                      <td className="py-2.5 pr-4 font-medium text-white">Apple Safari (macOS / iOS / iPadOS)</td>
                      <td className="py-2.5 pr-4 text-emerald-400">100% Tested</td>
                      <td className="py-2.5">Metal WebGL Backend, Touch Roaming & Pinch-to-Zoom</td>
                    </tr>
                    <tr>
                      <td className="py-2.5 pr-4 font-medium text-white">Microsoft Edge & Mozilla Firefox</td>
                      <td className="py-2.5 pr-4 text-emerald-400">100% Tested</td>
                      <td className="py-2.5">Standard Three.js OBJ/PLY/GLB Loaders</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'downloads' && (
          <div className="max-w-4xl mx-auto p-6 space-y-6 w-full">
            <div className="p-6 rounded-2xl bg-[#0f141d] border border-[#dfb873]/30">
              <h2 className="text-lg font-serif font-bold text-[#e8c982] mb-2">
                Download Reconstructed 3D Assets
              </h2>
              <p className="text-xs text-slate-300 mb-6">
                Evaluators can inspect the raw geometry and texture maps directly in Blender, MeshLab, or CloudCompare:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <a
                  href="/output/model.glb"
                  download="vastu_digital_twin_model.glb"
                  className="p-4 rounded-xl bg-black/40 border border-[#dfb873]/40 hover:border-[#dfb873] transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-3">
                    <Box className="w-8 h-8 text-[#e8c982]" />
                    <div>
                      <div className="font-bold text-white text-sm group-hover:text-[#e8c982] transition-colors">
                        model.glb (GLTF Binary)
                      </div>
                      <div className="text-[11px] text-slate-400">
                        3.16 MB · Packaged PBR Mesh + Textures
                      </div>
                    </div>
                  </div>
                  <Download className="w-4 h-4 text-[#e8c982]" />
                </a>

                <a
                  href="/output/textured_mesh.obj"
                  download="textured_mesh.obj"
                  className="p-4 rounded-xl bg-black/40 border border-white/20 hover:border-white transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-3">
                    <Layers className="w-8 h-8 text-sky-400" />
                    <div>
                      <div className="font-bold text-white text-sm group-hover:text-sky-300 transition-colors">
                        textured_mesh.obj
                      </div>
                      <div className="text-[11px] text-slate-400">
                        7.6 MB · 256k Triangles (Wavefront)
                      </div>
                    </div>
                  </div>
                  <Download className="w-4 h-4 text-slate-300" />
                </a>

                <a
                  href="/output/texture_atlas.jpg"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-4 rounded-xl bg-black/40 border border-white/20 hover:border-white transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-3">
                    <Sparkles className="w-8 h-8 text-amber-400" />
                    <div>
                      <div className="font-bold text-white text-sm group-hover:text-amber-300 transition-colors">
                        texture_atlas.jpg
                      </div>
                      <div className="text-[11px] text-slate-400">
                        1.0 MB · 2048 × 2048 High-Res UV Atlas
                      </div>
                    </div>
                  </div>
                  <Download className="w-4 h-4 text-slate-300" />
                </a>

                <a
                  href="/output/dense_pointcloud.ply"
                  download="dense_pointcloud.ply"
                  className="p-4 rounded-xl bg-black/40 border border-white/20 hover:border-white transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center space-x-3">
                    <Cpu className="w-8 h-8 text-emerald-400" />
                    <div>
                      <div className="font-bold text-white text-sm group-hover:text-emerald-300 transition-colors">
                        dense_pointcloud.ply
                      </div>
                      <div className="text-[11px] text-slate-400">
                        24 MB · 437k Stanford PLY Splats
                      </div>
                    </div>
                  </div>
                  <Download className="w-4 h-4 text-slate-300" />
                </a>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
