import React, { useState } from 'react';
import {
  HelpCircle,
  ChevronDown,
  Sparkles,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';

interface FaqItem {
  question: string;
  answer: string;
  category: string;
}

export const FaqSection: React.FC = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const faqs: FaqItem[] = [
    {
      category: 'HARDWARE & CAPTURE',
      question: 'Does VĀSTU require an iPhone Pro with built-in LiDAR?',
      answer: 'No. Unlike legacy tools that depend on hardware LiDAR or time-of-flight sensors, VĀSTU is built from the ground up on uncalibrated RGB photogrammetry and visual-inertial odometry. It works on standard consumer iPhones (non-Pro) and Android devices (ARCore compatible). The edge SOP engine ensures camera poses and keyframe overlap meet the mathematical standards for sub-centimeter cloud reconstruction without specialized hardware.',
    },
    {
      category: 'GEOMETRY & ACCURACY',
      question: 'How does VĀSTU establish absolute metric scale without a physical laser?',
      answer: 'Scale is established through a combination of mobile visual-inertial sensor fusion (6-DoF linear acceleration and rotational velocity priors) and our Corner Anchor Sweep protocol. By holding the smartphone steady for 1.5 seconds at room corner vertices, the system calibrates baseline distances against known physical floor planes. In our Dadar Studio pilot, this produced a mean absolute error of just 1.11 cm across 10-meter spans.',
    },
    {
      category: 'FEATURE MATCHING',
      question: 'How does the pipeline reconstruct plain, featureless white walls?',
      answer: 'Plain monochrome walls are the classic failure mode of naive photogrammetry. VĀSTU overcomes this through Manhattan-World architectural plane regularization: the system first locks onto high-contrast structural features (baseboards, floor tiles, switch plates, ceiling beams, door frames) to solve camera trajectory. Once the bounding vertices are established, RANSAC 3D planar fitting interpolates the untextured wall plane between known structural boundaries.',
    },
    {
      category: 'CAD & EXPORT',
      question: 'What CAD and 3D file formats can be exported from the platform?',
      answer: 'VĀSTU exports to open, industry-standard CAD and 3D formats: AutoCAD DXF (R14 and 2000 format) for 2D architectural drawings with layer segregation, Scalable Vector Graphics (SVG), GeoJSON/JSON structural schemas, watertight Draco-compressed GLB and GLTF 2.0 3D models with 4K photometric texture atlases, and raw PLY/OBJ dense point clouds.',
    },
    {
      category: 'NAVIGATION & ACCESSIBILITY',
      question: 'How does the ADA wheelchair accessibility routing work?',
      answer: 'When a model is meshed, the floor plane is extracted to create a 3D NavMesh. Obstacles (walls, furniture bounding boxes, fixtures) are subtracted with an agent clearance radius (0.35m). Our 3D A* router enforces Americans with Disabilities Act (ADA Section 405) slope constraints: any ramp or elevation transition with a slope angle exceeding 4.76° (1:12 rise-to-run ratio) or threshold drops greater than 13mm are disqualified from wheelchair routes.',
    },
    {
      category: 'ENTERPRISE & SECURITY',
      question: 'Can VĀSTU be deployed fully on-premises or in private sovereign clouds?',
      answer: 'Yes. The entire VĀSTU stack is containerized via Docker Compose and Kubernetes manifests. It includes PostgreSQL 16 + PostGIS 3.4 for spatial indexing, MinIO for S3-compatible local object storage, Redis for asynchronous task queuing, and standalone Python/C++ worker nodes. It can run in air-gapped data centers with zero external telemetry dependencies.',
    },
    {
      category: 'EDGE SOP ENGINE',
      question: 'How does the mobile Standard Operating Procedure (SOP) prevent capture errors?',
      answer: 'During video capture, the edge client continuously computes the variance of the discrete 3x3 Laplacian convolution kernel (∇²I). If the surveyor moves too fast or pans erratically, the Laplacian variance drops below 120.0, immediately triggering an auditory speech synthesis cue ("Please slow down — motion blur detected") and vibrating the device, preventing defective datasets before cloud upload.',
    },
    {
      category: 'PERFORMANCE & SCALE',
      question: 'What is the maximum space size supported in a single scan?',
      answer: 'A standard single continuous video capture comfortably covers up to 3,500 sq.ft. (approx. 325 m²) across 4 to 8 contiguous rooms in 10 to 15 minutes. For multi-floor commercial complexes, our chunked session aggregator allows independent room captures to be globally aligned and registered into a unified PostGIS project hierarchy.',
    },
  ];

  return (
    <section id="faq" className="py-24 bg-[#141210] relative border-t border-[#C5A059]/20">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-[#1A1714] border border-[#C5A059]/40 text-[#E8C982] text-xs font-mono uppercase tracking-wider">
            <HelpCircle className="w-3.5 h-3.5 text-[#C5A059]" />
            <span>Technical Knowledge Base</span>
          </div>

          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold text-[#FAF7F0] tracking-tight">
            Frequently Asked{' '}
            <span className="text-[#E8C982]">Questions</span>
          </h2>

          <p className="text-[#C4B9AC] text-sm sm:text-base font-light leading-relaxed">
            Detailed answers regarding our photogrammetric mathematics, hardware support, CAD exports, and enterprise deployment options.
          </p>
        </div>

        {/* FAQ Accordion List */}
        <div className="mt-14 space-y-4">
          {faqs.map((faq, idx) => {
            const isOpen = openIndex === idx;
            return (
              <div
                key={idx}
                className="rounded-2xl bg-[#0E0C0A] border border-[#C5A059]/30 overflow-hidden transition-all shadow-md"
              >
                <button
                  onClick={() => setOpenIndex(isOpen ? null : idx)}
                  className="w-full p-6 text-left flex items-start justify-between space-x-4 hover:bg-[#141210] transition-colors"
                >
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono text-[#C5A059] uppercase tracking-wider font-semibold">
                      {faq.category}
                    </span>
                    <h3 className="font-serif font-bold text-base sm:text-lg text-[#FAF7F0]">
                      {faq.question}
                    </h3>
                  </div>
                  <div
                    className={`w-8 h-8 rounded-full border border-[#C5A059]/40 bg-[#1A1714] flex items-center justify-center shrink-0 text-[#E8C982] transition-transform duration-300 ${
                      isOpen ? 'rotate-180 bg-[#C5A059] text-black' : ''
                    }`}
                  >
                    <ChevronDown className="w-4 h-4" />
                  </div>
                </button>

                {isOpen && (
                  <div className="px-6 pb-6 pt-2 text-sm text-[#C4B9AC] font-light leading-relaxed border-t border-[#C5A059]/10 animate-in fade-in duration-200">
                    {faq.answer}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

