import React from 'react';
import { Layers, Eye, EyeOff } from 'lucide-react';

interface FloorSelectorProps {
  floors: number[];
  selectedFloor: number;
  onSelectFloor: (floor: number) => void;
  isCeilingVisible: boolean;
  onToggleCeiling: () => void;
}

export const FloorSelector: React.FC<FloorSelectorProps> = ({
  floors,
  selectedFloor,
  onSelectFloor,
  isCeilingVisible,
  onToggleCeiling,
}) => {
  return (
    <div className="flex items-center gap-2 p-1.5 bg-slate-900/85 backdrop-blur-md rounded-2xl border border-slate-700/80 shadow-xl text-xs text-white">
      <div className="flex items-center gap-1 pl-2 pr-1 text-slate-400">
        <Layers className="w-3.5 h-3.5" />
        <span className="font-semibold text-[11px]">Floor</span>
      </div>

      <div className="flex items-center gap-1">
        {floors.map((floor) => (
          <button
            key={floor}
            onClick={() => onSelectFloor(floor)}
            className={`px-2.5 py-1 rounded-lg font-bold transition ${
              selectedFloor === floor
                ? 'bg-[#C5A059] text-slate-950'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
          >
            {floor}
          </button>
        ))}
      </div>

      <div className="h-4 w-px bg-slate-700 mx-1" />

      {/* Ceiling toggle */}
      <button
        onClick={onToggleCeiling}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-medium transition ${
          isCeilingVisible
            ? 'bg-slate-800 text-white'
            : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
        }`}
        title={isCeilingVisible ? 'Hide Ceiling for Top-Down View' : 'Show Ceiling'}
      >
        {isCeilingVisible ? (
          <>
            <Eye className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-[11px]">Ceiling On</span>
          </>
        ) : (
          <>
            <EyeOff className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-[11px]">Ceiling Off</span>
          </>
        )}
      </button>
    </div>
  );
};

