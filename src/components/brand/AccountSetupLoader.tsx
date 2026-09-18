import React, { useEffect, useState } from 'react';

interface AccountSetupLoaderProps {
  message?: string;
  submessage?: string;
}

export const AccountSetupLoader: React.FC<AccountSetupLoaderProps> = ({
  message = 'Please wait till we setup your account',
  submessage = 'Configuring your organization workspace, spatial registry & encryption keys...',
}) => {
  const [step, setStep] = useState(1);

  useEffect(() => {
    // Increment through drafting stages 1 -> 9
    const interval = setInterval(() => {
      setStep((prev) => (prev >= 9 ? 1 : prev + 1));
    }, 400);

    return () => clearInterval(interval);
  }, []);

  const pad = step < 10 ? `0${step}` : `${step}`;

  return (
    <div className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-[#E3DACA] text-[#2B2219] p-6 select-none transition-all duration-500">
      {/* Background Subtle Radial Vignette */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_40%,rgba(166,134,89,0.18)_100%)] pointer-events-none" />

      {/* Main Assembly Stage */}
      <div className="relative z-10 flex flex-col items-center max-w-md w-full text-center">
        {/* Stage Counter */}
        <div className="font-mono text-xs font-bold tracking-[0.3em] text-[#8F6834] uppercase mb-3">
          STAGE {pad} / 09
        </div>

        {/* Compass Assembly Canvas */}
        <div className="relative w-64 h-64 sm:w-72 sm:h-72 flex items-center justify-center my-2">
          {/* Ambient Rotating Ring */}
          <div className="absolute inset-2 rounded-full border border-[#C5A059]/25 animate-[spin_24s_linear_infinite]" />
          <div className="absolute inset-8 rounded-full border border-dashed border-[#8F6834]/30 animate-[spin_40s_linear_infinite_reverse]" />

          {/* Precision Architectural Compass SVG */}
          <svg className="w-full h-full" viewBox="0 0 400 400">
            {/* 01: Drafting Grid */}
            <g className="transition-opacity duration-500" opacity={step >= 1 ? 0.75 : 0.1}>
              <rect x="70" y="70" width="260" height="260" fill="none" stroke="#B8860B" strokeWidth="1" strokeDasharray="4 3" opacity="0.4" />
              <line x1="36" y1="200" x2="364" y2="200" stroke="#B8860B" strokeWidth="1" strokeDasharray="4 3" opacity="0.5" />
              <line x1="200" y1="36" x2="200" y2="364" stroke="#B8860B" strokeWidth="1" strokeDasharray="4 3" opacity="0.5" />
              <circle cx="200" cy="200" r="8" fill="none" stroke="#8F6834" strokeWidth="1.5" />
            </g>

            {/* 02: Circular Guide & Cardinal Dots */}
            <g className="transition-opacity duration-500" opacity={step >= 2 ? 1 : 0}>
              <circle cx="200" cy="200" r="105" fill="none" stroke="#A67C1E" strokeWidth="1.2" strokeDasharray="6 4" opacity="0.6" />
              <circle cx="200" cy="95" r="3.5" fill="#8F6834" />
              <circle cx="305" cy="200" r="3.5" fill="#8F6834" />
              <circle cx="200" cy="305" r="3.5" fill="#8F6834" />
              <circle cx="95" cy="200" r="3.5" fill="#8F6834" />
            </g>

            {/* 03: Primary Ink Ring */}
            <g className="transition-all duration-700" opacity={step >= 3 ? 1 : 0}>
              <circle
                cx="200"
                cy="200"
                r="105"
                fill="none"
                stroke="#694C24"
                strokeWidth="2"
                strokeDasharray="660"
                strokeDashoffset={step >= 3 ? 0 : 660}
                className="transition-all duration-700"
              />
            </g>

            {/* 04: North Pointer & Letter */}
            <g className="transition-opacity duration-500" opacity={step >= 4 ? 1 : 0}>
              <text x="200" y="58" textAnchor="middle" fill="#523918" fontFamily="Cinzel, Georgia, serif" fontWeight="bold" fontSize="22">
                N
              </text>
              <g transform="translate(200, 95)">
                <polygon points="0,-36 -7,-4 0,0" fill="#8F6834" />
                <polygon points="0,-36 7,-4 0,0" fill="#B8860B" />
                <circle cx="0" cy="0" r="5" fill="#523918" />
              </g>
            </g>

            {/* 05: Cardinal Tick Pointers */}
            <g className="transition-opacity duration-500" opacity={step >= 5 ? 1 : 0} fill="#8F6834" stroke="#8F6834">
              <g transform="translate(305, 200)">
                <line x1="-10" y1="0" x2="18" y2="0" strokeWidth="1.5" />
                <polygon points="18,0 12,-3 14,0 12,3" />
              </g>
              <g transform="translate(200, 305) rotate(90)">
                <line x1="-10" y1="0" x2="18" y2="0" strokeWidth="1.5" />
                <polygon points="18,0 12,-3 14,0 12,3" />
              </g>
              <g transform="translate(95, 200) rotate(180)">
                <line x1="-10" y1="0" x2="18" y2="0" strokeWidth="1.5" />
                <polygon points="18,0 12,-3 14,0 12,3" />
              </g>
            </g>

            {/* 06: Inner Geometry Circles */}
            <g className="transition-opacity duration-500" opacity={step >= 6 ? 0.8 : 0}>
              <circle cx="200" cy="200" r="68" fill="none" stroke="#A67C1E" strokeWidth="1" strokeDasharray="3 3" />
              <circle cx="200" cy="200" r="32" fill="none" stroke="#A67C1E" strokeWidth="1" strokeDasharray="3 3" />
            </g>

            {/* 07: Central Astrolabe Devanagari / Vastu Glyph */}
            <g className="transition-all duration-500" opacity={step >= 7 ? 1 : 0}>
              <text
                x="200"
                y="206"
                textAnchor="middle"
                fill="#422E15"
                fontFamily="Cinzel, 'Cormorant Garamond', serif"
                fontWeight="bold"
                fontSize="18"
                letterSpacing="3"
              >
                वास्तु
              </text>
            </g>

            {/* 08: Micro Calibration Radians */}
            <g className="transition-opacity duration-500" opacity={step >= 8 ? 0.6 : 0}>
              {[30, 60, 120, 150, 210, 240, 300, 330].map((deg) => (
                <circle
                  key={deg}
                  cx={200 + 105 * Math.cos((deg * Math.PI) / 180)}
                  cy={200 + 105 * Math.sin((deg * Math.PI) / 180)}
                  r="1.8"
                  fill="#8F6834"
                />
              ))}
            </g>

            {/* 09: Dynamic Scan Needle Pulse */}
            <line
              x1="200"
              y1="200"
              x2={200 + 105 * Math.cos((step * 40 * Math.PI) / 180)}
              y2={200 + 105 * Math.sin((step * 40 * Math.PI) / 180)}
              stroke="#B8860B"
              strokeWidth="1.5"
              opacity="0.75"
            />
          </svg>
        </div>

        {/* Required Message Line */}
        <div className="mt-6 space-y-2">
          <h2 className="text-xl sm:text-2xl font-bold font-serif-brand text-[#2B2219] tracking-wide">
            {message}
          </h2>
          <p className="text-xs sm:text-sm text-[#695541] max-w-sm mx-auto font-medium">
            {submessage}
          </p>
        </div>

        {/* Progress Step Indicators */}
        <div className="flex items-center justify-center space-x-2 mt-6">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                i === step
                  ? 'w-8 bg-[#8F6834] shadow-sm shadow-[#8F6834]/50'
                  : i < step
                  ? 'w-3 bg-[#B8860B]/70'
                  : 'w-2 bg-[#A68659]/30'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
};
