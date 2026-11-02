import React from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Building2,
  Clock,
  DollarSign,
  Compass,
  FileSpreadsheet,
  Layers,
  ArrowRight
} from 'lucide-react';

export const ProblemSolutionSection: React.FC = () => {
  const comparisonRows = [
    {
      feature: 'Hardware Capital Cost',
      traditional: '$15,000 – $60,000 (Leica BLK360 / Faro Focus)',
      matterport: '$3,500 – $6,000 + Per-Space Monthly Fees',
      manual: '$50 (Laser meter & measuring tapes)',
      vastu: '$0 (Standard Consumer iPhone / Android)',
      highlight: true,
    },
    {
      feature: 'Site Measurement Duration',
      traditional: '2 to 3 Hours (Multiple tripod setups)',
      matterport: '1 to 2 Hours (Slow multi-point scans)',
      manual: '4 to 6 Hours (2 surveyors per 3BHK flat)',
      vastu: '8 to 12 Minutes (Single continuous video sweep)',
      highlight: true,
    },
    {
      feature: 'Average Measurement Error',
      traditional: '± 2 to 4 mm (Industrial grade)',
      matterport: '± 1.0% (Non-exportable mesh)',
      manual: '4.8% Human Error (Documented in Dadar study)',
      vastu: '± 1.4 cm across 10m (< 0.25% verified)',
      highlight: false,
    },
    {
      feature: 'CAD Floor Plan Drafting Time',
      traditional: '6 to 10 Hours manual drafting',
      matterport: 'Additional paid add-on ($40/floor, 48hr turnaround)',
      manual: '8 to 14 Hours manual drafting in AutoCAD',
      vastu: 'Instant Automated Vectorization (DXF / SVG)',
      highlight: true,
    },
    {
      feature: '3D Modeling & Visualization Overhead',
      traditional: '3 to 5 Days in 3ds Max / Revit',
      matterport: 'None (Panoramic photos only, no raw mesh)',
      manual: '3 to 5 Days in SketchUp / 3ds Max',
      vastu: 'Zero Manual CAD (Watertight GLB & Texture Atlas in mins)',
      highlight: true,
    },
    {
      feature: 'Mesh & Raw Geometry Ownership',
      traditional: 'Proprietary binary or massive point clouds',
      matterport: 'Locked in proprietary vendor cloud',
      manual: 'Only 2D manual blueprints',
      vastu: '100% Client-Owned Open Standards (GLB, OBJ, DXF)',
      highlight: false,
    },
    {
      feature: 'Indoor Obstacle & ADA Pathfinding',
      traditional: 'No (Point cloud visualization only)',
      matterport: 'No (Static spherical bubble-hopping)',
      manual: 'No',
      vastu: 'Yes (Topological 3D A* NavMesh, ADA ≤ 4.76°)',
      highlight: true,
    },
    {
      feature: 'Client Access & Walkthrough',
      traditional: 'Heavy desktop software required',
      matterport: 'Proprietary Web player',
      manual: 'Static PDF 2D prints',
      vastu: 'Zero-Install WebGL / Three.js 60 FPS Browser Link',
      highlight: false,
    },
  ];

  return (
    <section id="problem-solution" className="py-20 bg-[#0E0C0A] relative border-t border-[#C5A059]/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-[#1A1714] border border-[#C5A059]/40 text-[#E8C982] text-xs font-mono uppercase tracking-wider">
            <Building2 className="w-3.5 h-3.5 text-[#C5A059]" />
            <span>Industrial Pilot · Dadar West, Mumbai</span>
          </div>

          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold text-[#FAF7F0] tracking-tight">
            The Spatial Survey Bottleneck &{' '}
            <span className="text-[#E8C982]">The VĀSTU Solution</span>
          </h2>

          <p className="text-[#C4B9AC] text-sm sm:text-base font-light leading-relaxed">
            In our intensive industrial research partnership with <strong>Create Fo'em Interior Designing Studio</strong> in Dadar, Mumbai, we tracked dozens of turnkey interior projects to analyze where time, capital, and accuracy are lost in conventional spatial workflows.
          </p>
        </div>

        {/* 4 Core Industry Bottlenecks */}
        <div className="mt-14 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1 */}
          <div className="p-6 rounded-2xl bg-[#141210] border border-red-500/20 hover:border-red-500/40 transition-all space-y-4 relative overflow-hidden group">
            <div className="w-12 h-12 rounded-xl bg-red-950/40 border border-red-500/30 flex items-center justify-center text-red-400">
              <DollarSign className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-serif font-bold text-[#FAF7F0]">
              Extreme Hardware Capital Cost
            </h3>
            <p className="text-xs text-[#9C9183] leading-relaxed">
              Terrestrial laser scanners (Leica, Faro) cost upwards of <strong>$15,000 to $60,000</strong> per unit. Commercial cloud providers (e.g. Matterport) impose recurring monthly hosting fees while locking raw geometric meshes and vector drawings in proprietary silos.
            </p>
            <div className="pt-2 border-t border-white/5 flex items-center space-x-2 text-xs font-mono text-red-400">
              <XCircle className="w-4 h-4 shrink-0" />
              <span>Severe Capex Barrier</span>
            </div>
          </div>

          {/* Card 2 */}
          <div className="p-6 rounded-2xl bg-[#141210] border border-amber-500/20 hover:border-amber-500/40 transition-all space-y-4 relative overflow-hidden group">
            <div className="w-12 h-12 rounded-xl bg-amber-950/40 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Clock className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-serif font-bold text-[#FAF7F0]">
              Manual Survey Fatigue & Errors
            </h3>
            <p className="text-xs text-[#9C9183] leading-relaxed">
              At Create Fo'em, measuring a typical 1,200 sq.ft. 3BHK flat in Mumbai consumed <strong>4 to 6 hours</strong> of two junior architects' time using tape measures and laser distometers. Designers recorded an average <strong>4.8% error rate</strong>, discovered only during modular furniture installation.
            </p>
            <div className="pt-2 border-t border-white/5 flex items-center space-x-2 text-xs font-mono text-amber-400">
              <XCircle className="w-4 h-4 shrink-0" />
              <span>4.8% Human Discrepancy</span>
            </div>
          </div>

          {/* Card 3 */}
          <div className="p-6 rounded-2xl bg-[#141210] border border-blue-500/20 hover:border-blue-500/40 transition-all space-y-4 relative overflow-hidden group">
            <div className="w-12 h-12 rounded-xl bg-blue-950/40 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-serif font-bold text-[#FAF7F0]">
              CAD & 3D Drafting Overhead
            </h3>
            <p className="text-xs text-[#9C9183] leading-relaxed">
              Translating physical field diaries into clean AutoCAD <code>.dwg</code> floor plans required <strong>8 to 14 additional hours</strong>. 3D visualizers spent an additional <strong>3 to 5 days</strong> rebuilding spaces in 3ds Max/SketchUp just for preliminary client sign-offs.
            </p>
            <div className="pt-2 border-t border-white/5 flex items-center space-x-2 text-xs font-mono text-blue-400">
              <XCircle className="w-4 h-4 shrink-0" />
              <span>3 to 5 Days Modeling Lag</span>
            </div>
          </div>

          {/* Card 4 */}
          <div className="p-6 rounded-2xl bg-[#141210] border border-emerald-500/30 hover:border-emerald-500/50 transition-all space-y-4 relative overflow-hidden bg-gradient-to-b from-[#141210] to-[#1A1714]">
            <div className="w-12 h-12 rounded-xl bg-[#C5A059]/20 border border-[#C5A059]/40 flex items-center justify-center text-[#E8C982]">
              <Compass className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-serif font-bold text-[#E8C982]">
              The VĀSTU Breakthrough
            </h3>
            <p className="text-xs text-[#C4B9AC] leading-relaxed">
              Any everyday smartphone captures video following our edge SOP audio guidance. Our cloud pipeline autonomously reconstructs watertight 3D models, vector CAD floor plans, and ADA-compliant NavMeshes in <strong>under 20 minutes</strong> with <strong>&lt; 1.4 cm error</strong>.
            </p>
            <div className="pt-2 border-t border-white/5 flex items-center space-x-2 text-xs font-mono text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>Zero CAD · Single-Day Turnaround</span>
            </div>
          </div>
        </div>

        {/* Industry Technology Truth Table / Comparison Matrix */}
        <div className="mt-16">
          <div className="text-center mb-8">
            <h3 className="font-serif text-2xl font-bold text-[#FAF7F0]">
              Technology Truth Table: Architectural Reality Capture
            </h3>
            <p className="text-xs text-[#9C9183] font-mono mt-1">
              Comparative benchmark across hardware, labor, accuracy, and geometry ownership
            </p>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-[#C5A059]/30 bg-[#141210] shadow-2xl">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#1A1714] border-b border-[#C5A059]/30 font-mono text-[#E8C982]">
                  <th className="p-4 uppercase tracking-wider">Evaluation Parameter</th>
                  <th className="p-4 uppercase tracking-wider text-[#9C9183]">Terrestrial LiDAR</th>
                  <th className="p-4 uppercase tracking-wider text-[#9C9183]">Matterport Cloud</th>
                  <th className="p-4 uppercase tracking-wider text-[#9C9183]">Manual Tape Survey</th>
                  <th className="p-4 uppercase tracking-wider text-[#E8C982] bg-[#C5A059]/10">
                    VĀSTU / Namma Space
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#C5A059]/10 font-sans">
                {comparisonRows.map((row, idx) => (
                  <tr
                    key={idx}
                    className={`hover:bg-white/[0.02] transition-colors ${
                      row.highlight ? 'bg-[#C5A059]/[0.02]' : ''
                    }`}
                  >
                    <td className="p-4 font-semibold text-[#FAF7F0] font-mono text-[11px]">
                      {row.feature}
                    </td>
                    <td className="p-4 text-[#9C9183]">{row.traditional}</td>
                    <td className="p-4 text-[#9C9183]">{row.matterport}</td>
                    <td className="p-4 text-[#9C9183]">{row.manual}</td>
                    <td className="p-4 font-semibold text-[#E8C982] bg-[#C5A059]/10">
                      <div className="flex items-center space-x-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <span>{row.vastu}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
};

