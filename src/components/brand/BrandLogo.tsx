import React from 'react';

interface BrandLogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showTagline?: boolean;
  showText?: boolean;
  theme?: 'light' | 'dark';
  className?: string;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({
  size = 'md',
  showTagline = false,
  showText = true,
  theme = 'dark',
  className = '',
}) => {
  const iconDimensions = {
    sm: 'w-7 h-7',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
    xl: 'w-24 h-24',
  }[size];

  const titleSizes = {
    sm: 'text-sm tracking-[0.15em]',
    md: 'text-base tracking-[0.18em]',
    lg: 'text-2xl tracking-[0.2em]',
    xl: 'text-4xl tracking-[0.25em]',
  }[size];

  const titleColor = theme === 'light' ? 'text-[#2B2219]' : 'text-[#E8C982]';
  const taglineColor = theme === 'light' ? 'text-[#695541]' : 'text-[#A6998A]';
  const badgeColor = theme === 'light' ? 'text-[#8F6834]' : 'text-[#C5A059]/90';

  return (
    <div className={`inline-flex items-center space-x-3.5 ${className}`}>
      {/* VĀSTU Astrolabe / Compass Architectural Icon (Transparent Background) */}
      <div className={`relative ${iconDimensions} flex items-center justify-center shrink-0`}>
        <img
          src="/vastu-brand.png"
          alt="VĀSTU Compass"
          className="w-full h-full object-contain filter drop-shadow-[0_2px_10px_rgba(197,160,89,0.35)]"
        />
      </div>

      {showText && (
        <div className="flex flex-col text-left">
          <div className="flex items-center space-x-2">
            <span
              className={`font-serif-brand font-bold uppercase ${titleColor} ${titleSizes}`}
              style={{ letterSpacing: '0.18em' }}
            >
              VĀSTU
            </span>
          </div>
          {showTagline ? (
            <span className={`text-[10px] ${taglineColor} font-medium tracking-wide`}>
              Mapping Spaces. Building Digital Twins.
            </span>
          ) : (
            <span className={`text-[9px] uppercase font-bold tracking-[0.18em] ${badgeColor}`}>
              Spatial Cloud
            </span>
          )}
        </div>
      )}
    </div>
  );
};
