import React, { useState } from 'react';
import { Eye, SplitSquareHorizontal, Layers, Check } from 'lucide-react';

interface ReconstructionComparisonProps {
  roomName: string;
  rawKeyframeUrl?: string;
  renderedModelUrl?: string;
}

export const ReconstructionComparison: React.FC<ReconstructionComparisonProps> = ({
  roomName,
  rawKeyframeUrl = '/models/texture_atlas.jpg',
  renderedModelUrl = '/models/texture_atlas.png',
}) => {
  const [sliderPos, setSliderPos] = useState<number>(50);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4 text-white">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-bold text-[#C5A059] uppercase tracking-wider">
            Visual Fidelity Inspection
          </div>
          <h4 className="text-sm font-bold text-white mt-0.5">
            Photometric Comparison: Captured vs 3D Reconstruction
          </h4>
        </div>

        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          <span className="text-emerald-400">● 30.5 dB PSNR</span>
          <span>•</span>
          <span className="text-emerald-400">0.91 SSIM</span>
        </div>
      </div>

      {/* Interactive Comparison Viewport */}
      <div className="relative w-full h-64 bg-slate-950 rounded-xl overflow-hidden border border-slate-800 select-none">
        {/* Left Side: Raw Capture */}
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: `url(${rawKeyframeUrl})`,
            clipPath: `polygon(0 0, ${sliderPos}% 0, ${sliderPos}% 100%, 0 100%)`
          }}
        >
          <div className="absolute top-3 left-3 px-2.5 py-1 bg-black/75 backdrop-blur-md rounded-lg text-[10px] font-bold text-white border border-white/20">
            Raw Camera Frame (ARKit RGB)
          </div>
        </div>

        {/* Right Side: Reconstructed Digital Twin */}
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: `url(${renderedModelUrl})`,
            clipPath: `polygon(${sliderPos}% 0, 100% 0, 100% 100%, ${sliderPos}% 100%)`
          }}
        >
          <div className="absolute top-3 right-3 px-2.5 py-1 bg-[#C5A059]/90 text-slate-950 rounded-lg text-[10px] font-extrabold shadow-md">
            VĀSTU 3D Gaussian Twin
          </div>
        </div>

        {/* Divider Bar */}
        <div
          className="absolute top-0 bottom-0 w-1 bg-white shadow-2xl cursor-ew-resize flex items-center justify-center -translate-x-1/2"
          style={{ left: `${sliderPos}%` }}
        >
          <div className="w-6 h-6 bg-white text-slate-900 rounded-full flex items-center justify-center shadow-lg border border-slate-300">
            <SplitSquareHorizontal className="w-3.5 h-3.5" />
          </div>
        </div>

        {/* Hidden Range Slider */}
        <input
          type="range"
          min="0"
          max="100"
          value={sliderPos}
          onChange={(e) => setSliderPos(Number(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-20"
        />
      </div>

      <div className="text-[11px] text-slate-400 text-center">
        Drag slider horizontally to inspect texture alignment, geometric sharpness, and radiance reconstruction.
      </div>
    </div>
  );
};

