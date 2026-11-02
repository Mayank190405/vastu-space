import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Compass,
  Smartphone,
  Eye,
  Layers,
  ArrowRight,
  CheckCircle2,
  Box,
  Square,
  FileCode,
  Users,
  Building2,
  QrCode,
  ShieldCheck,
  Download,
  Share2
} from 'lucide-react';

export const HowToUseSection: React.FC = () => {
  const [activeRole, setActiveRole] = useState<'surveyor' | 'architect' | 'pm' | 'visitor'>('surveyor');

  const roles = [
    {
      id: 'surveyor',
      label: 'Field Surveyor',
      subtitle: 'Mobile SOP capture, corner anchoring & chunked upload',
      icon: Smartphone,
    },
    {
      id: 'architect',
      label: 'Architect & Designer',
      subtitle: '3D dimensioning, CAD floor plans & DXF export',
      icon: Square,
    },
    {
      id: 'pm',
      label: 'Project Manager',
      subtitle: 'Multi-tenant pipeline monitoring & quality gates',
      icon: Building2,
    },
    {
      id: 'visitor',
      label: 'Client & Visitor',
      subtitle: 'Zero-install 3D roaming & live AR wayfinding',
      icon: Compass,
    },
  ];

  return (
    <section id="how-to-use" className="py-24 bg-[#141210] relative border-t border-[#C5A059]/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-[#1A1714] border border-[#C5A059]/40 text-[#E8C982] text-xs font-mono uppercase tracking-wider">
            <Compass className="w-3.5 h-3.5 text-[#C5A059]" />
            <span>End-to-End Operational Manual</span>
          </div>

          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold text-[#FAF7F0] tracking-tight">
            How to Use VĀSTU:{' '}
            <span className="text-[#E8C982]">Step-by-Step</span>
          </h2>

          <p className="text-[#C4B9AC] text-sm sm:text-base font-light leading-relaxed">
            Tailored workflows for field surveyors, interior designers, engineering leads, and facility visitors. Select your role below to explore the exact operational procedure.
          </p>
        </div>

        {/* Role Selector Tabs */}
        <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 max-w-5xl mx-auto">
          {roles.map((role) => {
            const Icon = role.icon;
            const isSelected = activeRole === role.id;
            return (
              <button
                key={role.id}
                onClick={() => setActiveRole(role.id as any)}
                className={`p-4 rounded-xl border text-left transition-all ${
                  isSelected
                    ? 'bg-gradient-to-b from-[#C5A059]/25 to-[#1A1714] border-[#C5A059] shadow-lg shadow-[#C5A059]/15'
                    : 'bg-[#0E0C0A] border-[#C5A059]/20 hover:border-[#C5A059]/40 hover:bg-[#1A1714]'
                }`}
              >
                <div className="flex items-center space-x-3 mb-2">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                      isSelected ? 'bg-[#C5A059] text-black' : 'bg-[#141210] text-[#C5A059]'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <span
                    className={`font-serif font-bold text-sm ${
                      isSelected ? 'text-[#FAF7F0]' : 'text-[#C4B9AC]'
                    }`}
                  >
                    {role.label}
                  </span>
                </div>
                <p className="text-[11px] text-[#9C9183] leading-snug line-clamp-2">
                  {role.subtitle}
                </p>
              </button>
            );
          })}
        </div>

        {/* Role Content Card */}
        <div className="mt-8 rounded-2xl bg-[#0E0C0A] border border-[#C5A059]/40 p-6 sm:p-10 shadow-2xl">
          {/* ROLE 1: FIELD SURVEYOR */}
          {activeRole === 'surveyor' && (
            <div className="space-y-8 animate-in fade-in duration-300">
              <div className="border-b border-[#C5A059]/20 pb-4">
                <span className="text-xs font-mono uppercase tracking-widest text-[#C5A059]">
                  FIELD SURVEYOR PROTOCOL · EDGE CAPTURE
                </span>
                <h3 className="text-2xl font-serif font-bold text-[#FAF7F0] mt-1">
                  Smartphone SOP Field Recording & Resumable Ingestion
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* Step 1 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    01
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Launch Guided Studio
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Open the web app at <code>/captures</code> or scan the project QR code with your iPhone or Android. Ensure lighting is uniform (minimum 250 lux).
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-[#C5A059]">
                    ✓ No app store install required
                  </div>
                </div>

                {/* Step 2 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    02
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Maintain Standoff & Speed
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Walk steadily around the room perimeter at <strong>0.20 m/s</strong>, keeping the camera <strong>1.5 to 2.0 meters</strong> from walls. Follow the live speedometer HUD.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ 70% to 80% overlap target
                  </div>
                </div>

                {/* Step 3 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    03
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Lock Corner Anchors
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    At each 90° corner vertex, hold the camera steady for <strong>1.5 seconds</strong>. Listen for the audio confirmation: <em>"Corner anchor locked"</em> to anchor metric scale.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ Metric scale calibration
                  </div>
                </div>

                {/* Step 4 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    04
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Chunked Upload
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Hit finish. The edge client automatically splits video into 5MB chunks with SHA-256 hashes, streaming to MinIO S3 even over spotty 4G/5G connections.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ Resumable upload engine
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ROLE 2: ARCHITECT & INTERIOR DESIGNER */}
          {activeRole === 'architect' && (
            <div className="space-y-8 animate-in fade-in duration-300">
              <div className="border-b border-[#C5A059]/20 pb-4">
                <span className="text-xs font-mono uppercase tracking-widest text-[#C5A059]">
                  ARCHITECT & DESIGNER PROTOCOL · CAD & METROLOGY
                </span>
                <h3 className="text-2xl font-serif font-bold text-[#FAF7F0] mt-1">
                  Inspect Watertight Meshes, Measure Clearances & Export CAD Vectors
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* Step 1 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    01
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Load 3D Spatial Twin
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Open <code>/viewer</code> to inspect the reconstructed watertight mesh. Switch between Orbit mode (360° overview) and First-Person Walkthrough mode (WASD + mouse look).
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-[#C5A059]">
                    ✓ 60 FPS WebGL rendering
                  </div>
                </div>

                {/* Step 2 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    02
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    3D Euclidean Distance Ruler
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Double-click any two 3D vertices to measure wall-to-wall clearances, doorway heights, or custom cabinetry spans with ±0.01m accuracy.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ Verified vs Leica Disto
                  </div>
                </div>

                {/* Step 3 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    03
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    2D CAD Floor Plan Studio
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Jump to <code>/cad</code> to inspect extracted Manhattan wall boundaries. Adjust wall thickness (100mm to 230mm) and toggle magnetic vertex endpoint snapping.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ Orthogonal regularization
                  </div>
                </div>

                {/* Step 4 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    04
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Export DXF / SVG
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Download production-ready AutoCAD DXF files (R14/2000 format) or vector SVGs directly into AutoCAD, Revit, or SketchUp for immediate millwork drafting.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ 100% CAD compatible
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ROLE 3: PROJECT MANAGER */}
          {activeRole === 'pm' && (
            <div className="space-y-8 animate-in fade-in duration-300">
              <div className="border-b border-[#C5A059]/20 pb-4">
                <span className="text-xs font-mono uppercase tracking-widest text-[#C5A059]">
                  PROJECT MANAGER PROTOCOL · PIPELINE & QUALITY AUDIT
                </span>
                <h3 className="text-2xl font-serif font-bold text-[#FAF7F0] mt-1">
                  Orchestrate Reconstruction Jobs, Enforce Quality Gates & Manage Access
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* Step 1 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    01
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Create Spatial Workspace
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Define project typologies (Residential, Commercial, Hospitality), target carpet area, and set accuracy tolerance gates (e.g. 2.5cm).
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-[#C5A059]">
                    ✓ Multi-tenant governance
                  </div>
                </div>

                {/* Step 2 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    02
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Dispatch Capture Links
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Generate secure single-click capture invites or WhatsApp links for site surveyors. Assign role-based permissions (Viewer, Surveyor, Admin).
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ 1-click mobile pairing
                  </div>
                </div>

                {/* Step 3 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    03
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Monitor Pipeline Center
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Track the 9-stage asynchronous pipeline in real time at <code>/pipeline</code>. Observe keyframe extraction, SfM reprojection error, and GPU worker nodes.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ Real-time Celery telemetry
                  </div>
                </div>

                {/* Step 4 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    04
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Audit Metric Score & Share
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Verify composite quality scores (≥ 85/100). Generate signed public view links (<code>/view/:projectId</code>) to share interactive 3D twins with clients.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ Automated quality assurance
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ROLE 4: CLIENT & VISITOR */}
          {activeRole === 'visitor' && (
            <div className="space-y-8 animate-in fade-in duration-300">
              <div className="border-b border-[#C5A059]/20 pb-4">
                <span className="text-xs font-mono uppercase tracking-widest text-[#C5A059]">
                  CLIENT & VISITOR PROTOCOL · ZERO-INSTALL EXPERIENCE
                </span>
                <h3 className="text-2xl font-serif font-bold text-[#FAF7F0] mt-1">
                  Zero-Install 3D Roaming & Live Mobile AR Wayfinding
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* Step 1 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    01
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Open Any Web Browser
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Click the shared digital twin link on any desktop Chrome, Safari, or mobile browser. Loads under 2.5 seconds without installing any plugins or software.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-[#C5A059]">
                    ✓ Zero installation barrier
                  </div>
                </div>

                {/* Step 2 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    02
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Free Roaming Walkthrough
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Roam fluidly using WASD keys on desktop or virtual joystick on mobile. Camera height is automatically constrained to eye level (1.65m) above floor.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ Collision-aware physics
                  </div>
                </div>

                {/* Step 3 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    03
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Search Rooms & Amenities
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    Type in any destination (e.g. <em>"Master Bedroom"</em>, <em>"Conference Room"</em>). An animated glowing 3D path line appears on the floor guiding you around obstacles.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ Obstacle-aware 3D routing
                  </div>
                </div>

                {/* Step 4 */}
                <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/20 space-y-3">
                  <div className="w-7 h-7 rounded-lg bg-[#C5A059]/20 text-[#E8C982] font-mono text-xs font-bold flex items-center justify-center">
                    04
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#FAF7F0]">
                    Mobile AR Navigation
                  </h4>
                  <p className="text-xs text-[#9C9183] leading-relaxed">
                    When standing on-site, switch to AR mode (<code>/ar</code>). Real-time directional arrows are overlaid directly onto your smartphone's camera feed.
                  </p>
                  <div className="pt-2 text-[11px] font-mono text-emerald-400">
                    ✓ Live spatial wayfinding
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

