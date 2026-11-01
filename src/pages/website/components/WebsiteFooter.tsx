import React from 'react';
import { Link } from 'react-router-dom';
import {
  Compass,
  Box,
  Building2,
  Shield,
  FileText,
  ExternalLink,
  MapPin,
  ArrowRight,
  Sparkles,
  Award
} from 'lucide-react';

export const WebsiteFooter: React.FC = () => {
  return (
    <footer className="bg-[#080706] text-[#A6998A] border-t border-[#C5A059]/30 text-xs font-sans">
      {/* Top Academic & Industrial Banner Box */}
      <div className="border-b border-[#C5A059]/20 bg-[#0E0C0A] py-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-xl bg-[#1A1714] border border-[#C5A059]/40 flex items-center justify-center p-2 shrink-0">
              <img
                src="/vastu-brand.png"
                alt="VĀSTU Compass"
                className="w-full h-full object-contain filter drop-shadow-[0_2px_8px_rgba(197,160,89,0.3)]"
              />
            </div>
            <div>
              <h4 className="font-serif font-bold text-base text-[#FAF7F0] tracking-wide">
                VĀSTU / Namma Space Spatial Division
              </h4>
              <p className="text-xs text-[#9C9183]">
                In Academic & Industrial Collaboration with <strong>Create Fo'em Studio</strong>, Dadar West, Mumbai
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/viewer"
              className="px-4 py-2 rounded-xl border border-[#C5A059]/40 bg-[#141210] text-[#E8C982] hover:bg-[#26221D] hover:border-[#C5A059] font-medium text-xs transition-colors flex items-center space-x-1.5"
            >
              <Box className="w-3.5 h-3.5 text-[#C5A059]" />
              <span>Launch 3D Studio</span>
            </Link>

            <Link
              to="/login"
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#C5A059] to-[#9A7B3E] text-black font-bold text-xs hover:brightness-110 shadow-lg shadow-[#C5A059]/20 transition-all flex items-center space-x-1.5"
            >
              <span>Enter Cloud Console</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Main Footer Links Columns */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10">
        {/* Column 1: Brand & Document Control */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center space-x-2">
            <span className="font-serif font-bold text-lg text-[#E8C982] tracking-[0.18em]">
              VĀSTU
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#C5A059]/20 text-[#C5A059] border border-[#C5A059]/40">
              DOC-VSP-2026-REP-001-REV2
            </span>
          </div>

          <p className="text-xs text-[#9C9183] leading-relaxed pr-6">
            Autonomous Smartphone-to-3D Spatial Computing Platform. Converts handheld smartphone video into millimeter-accurate 3D watertight digital twins, vector CAD floor plans, and ADA-compliant indoor obstacle navigation meshes.
          </p>

          <div className="pt-2 space-y-1.5 font-mono text-[11px] text-[#A6998A]">
            <div className="flex items-center space-x-2">
              <MapPin className="w-3.5 h-3.5 text-[#C5A059]" />
              <span>Pilot Host: Create Fo'em Studio, Dadar West, Mumbai 400028</span>
            </div>
            <div className="flex items-center space-x-2">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span>PostgreSQL 16 + PostGIS 3.4 Metric Cartesian SRID: 0</span>
            </div>
          </div>
        </div>

        {/* Column 2: Platform Modules */}
        <div className="space-y-3">
          <h5 className="font-mono text-xs uppercase tracking-wider text-[#FAF7F0] font-bold">
            Platform Modules
          </h5>
          <ul className="space-y-2 text-xs">
            <li>
              <Link to="/dashboard" className="hover:text-[#E8C982] transition-colors">
                Console Dashboard
              </Link>
            </li>
            <li>
              <Link to="/projects" className="hover:text-[#E8C982] transition-colors">
                Spatial Projects
              </Link>
            </li>
            <li>
              <Link to="/viewer" className="hover:text-[#E8C982] transition-colors">
                3D Spatial Twin Studio
              </Link>
            </li>
            <li>
              <Link to="/cad" className="hover:text-[#E8C982] transition-colors">
                2D CAD Floor Plan Studio
              </Link>
            </li>
            <li>
              <Link to="/captures" className="hover:text-[#E8C982] transition-colors">
                Guided Captures
              </Link>
            </li>
            <li>
              <Link to="/assets" className="hover:text-[#E8C982] transition-colors">
                Digital Twin Assets
              </Link>
            </li>
          </ul>
        </div>

        {/* Column 3: Engine & Pipeline */}
        <div className="space-y-3">
          <h5 className="font-mono text-xs uppercase tracking-wider text-[#FAF7F0] font-bold">
            Engine & Pipeline
          </h5>
          <ul className="space-y-2 text-xs">
            <li>
              <Link to="/pipeline" className="hover:text-[#E8C982] transition-colors">
                Pipeline Command Center
              </Link>
            </li>
            <li>
              <Link to="/ar" className="hover:text-[#E8C982] transition-colors">
                Live Mobile AR Navigation
              </Link>
            </li>
            <li>
              <Link to="/tours" className="hover:text-[#E8C982] transition-colors">
                Virtual Tour Studio
              </Link>
            </li>
            <li>
              <a href="#pipeline" className="hover:text-[#E8C982] transition-colors">
                9-Stage Reconstruction
              </a>
            </li>
            <li>
              <a href="#sop-simulator" className="hover:text-[#E8C982] transition-colors">
                Capture SOP Simulator
              </a>
            </li>
            <li>
              <a href="#developer" className="hover:text-[#E8C982] transition-colors">
                Developer REST APIs
              </a>
            </li>
          </ul>
        </div>

        {/* Column 4: IEEE References & Research */}
        <div className="space-y-3">
          <h5 className="font-mono text-xs uppercase tracking-wider text-[#FAF7F0] font-bold">
            Scientific Foundation
          </h5>
          <ul className="space-y-2 text-[11px] text-[#9C9183]">
            <li className="leading-snug">
              Hartley & Zisserman: <em>Multiple View Geometry in Computer Vision</em> (Cambridge Univ Press).
            </li>
            <li className="leading-snug">
              Kazhdan & Hoppe: <em>Screened Poisson Surface Reconstruction</em> (ACM TOG 2013).
            </li>
            <li className="leading-snug">
              Schönberger: <em>Structure-from-Motion Revisited</em> (PyCOLMAP, CVPR 2016).
            </li>
            <li className="leading-snug">
              Americans with Disabilities Act (ADA): Section 405 Ramp Slope Standards.
            </li>
          </ul>
        </div>
      </div>

      {/* Bottom Legal & Copyright Bar */}
      <div className="border-t border-[#C5A059]/20 py-6 px-4 sm:px-6 lg:px-8 text-center text-[#736A5E] font-mono text-[11px]">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            © 2026 VĀSTU / Namma Space Technologies. All rights reserved.
          </span>
          <span>
            Released under Enterprise Spatial Architecture Guidelines · Mumbai, Dadar Pilot
          </span>
        </div>
      </div>
    </footer>
  );
};

