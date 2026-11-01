import React, { useEffect } from 'react';
import { WebsiteNavbar } from './components/WebsiteNavbar';
import { HeroSection } from './components/HeroSection';
import { ProblemSolutionSection } from './components/ProblemSolutionSection';
import { ApproachDeepDiveSection } from './components/ApproachDeepDiveSection';
import { PipelineExplorerSection } from './components/PipelineExplorerSection';
import { SopSimulatorSection } from './components/SopSimulatorSection';
import { Showcase3DViewer } from './components/Showcase3DViewer';
import { HowToUseSection } from './components/HowToUseSection';
import { VastuShastraSection } from './components/VastuShastraSection';
import { BenchmarksSection } from './components/BenchmarksSection';
import { DeveloperRefSection } from './components/DeveloperRefSection';
import { FaqSection } from './components/FaqSection';
import { WebsiteFooter } from './components/WebsiteFooter';

export const ProjectWebsitePage: React.FC = () => {
  useEffect(() => {
    document.title = 'VĀSTU / Namma Space — Autonomous Smartphone-to-3D Spatial Intelligence';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  return (
    <div className="min-h-screen bg-[#0E0C0A] text-[#FAF7F0] font-sans selection:bg-[#C5A059] selection:text-black">
      {/* 1. Sticky Navigation Bar & Top Academic Banner */}
      <WebsiteNavbar />

      {/* 2. Majestic Hero Section with Archway & Live Telemetry HUD */}
      <HeroSection />

      {/* 3. Problem vs Solution & Create Fo'em Dadar Pilot Study */}
      <ProblemSolutionSection />

      {/* 4. Scientific Approach & Mathematical Foundations (5 Interactive Tabs) */}
      <ApproachDeepDiveSection />

      {/* 5. 9-Stage Asynchronous Reconstruction Pipeline Explorer */}
      <PipelineExplorerSection />

      {/* 6. Interactive Standard Operating Procedure (SOP) Capture Simulator */}
      <SopSimulatorSection />

      {/* 7. Interactive 3D Architectural Digital Twin Showcase (Three.js WebGL) */}
      <Showcase3DViewer />

      {/* 8. Comprehensive "How to Use" Step-by-Step Manual by Role */}
      <HowToUseSection />

      {/* 9. Vāstu Shastra & Cardinal Directional Energy Engine */}
      <VastuShastraSection />

      {/* 10. Laser Ground-Truth Validation Data & Benchmarks (Leica Disto D2) */}
      <BenchmarksSection />

      {/* 11. Microservice Topology, Developer APIs & Production CLI */}
      <DeveloperRefSection />

      {/* 12. Technical Knowledge Base & FAQ Accordion */}
      <FaqSection />

      {/* 13. Enterprise & Academic Footer */}
      <WebsiteFooter />
    </div>
  );
};

