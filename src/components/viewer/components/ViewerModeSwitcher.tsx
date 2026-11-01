import React from 'react';
import { Footprints, Box, Eye } from 'lucide-react';

interface ViewerModeSwitcherProps {
  currentMode: 'walk' | 'isometric';
  onModeChange: (mode: 'walk' | 'isometric') => void;
}

export const ViewerModeSwitcher: React.FC<ViewerModeSwitcherProps> = ({
  currentMode,
  onModeChange,
}) => {
  return (
    <div className="inline-flex items-center p-1.5 bg-slate-900/85 backdrop-blur-md rounded-2xl border border-slate-700/80 shadow-2xl text-xs font-semibold text-white">
      <button
        onClick={() => onModeChange('walk')}
        className={`flex items-center gap-2 px-3.5 py-2 rounded-xl transition ${
          currentMode === 'walk'
            ? 'bg-[#C5A059] text-slate-950 shadow-md font-bold'
            : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
        }`}
        title="First-Person Walking Navigation (WASD + Mouse)"
      >
        <Footprints className="w-4 h-4" />
        <span>Walk Mode</span>
        <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] bg-black/20 rounded font-mono">
          V
        </kbd>
      </button>

      <button
        onClick={() => onModeChange('isometric')}
        className={`flex items-center gap-2 px-3.5 py-2 rounded-xl transition ${
          currentMode === 'isometric'
            ? 'bg-[#C5A059] text-slate-950 shadow-md font-bold'
            : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
        }`}
        title="Elevated Orthographic Space Overview (Pan/Zoom)"
      >
        <Box className="w-4 h-4" />
        <span>Isometric View</span>
        <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] bg-black/20 rounded font-mono">
          V
        </kbd>
      </button>
    </div>
  );
};

