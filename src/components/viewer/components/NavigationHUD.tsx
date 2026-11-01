import React from 'react';
import { Crosshair, ShieldAlert, DoorOpen, Compass } from 'lucide-react';
import { FirstPersonState } from '../controllers/FirstPersonController';

interface NavigationHUDProps {
  mode: 'walk' | 'isometric';
  state: FirstPersonState | null;
  activeRoomName: string;
  onUnlockPointer?: () => void;
}

export const NavigationHUD: React.FC<NavigationHUDProps> = ({
  mode,
  state,
  activeRoomName,
}) => {
  if (mode !== 'walk') return null;

  const isLocked = state?.isLocked ?? false;
  const isColliding = state?.isColliding ?? false;
  const collidedWith = state?.collidedWith;
  const isInDoorway = state?.isInDoorway ?? false;
  const coords = state?.playerCoords ?? { x: 0, y: 0, z: 1.6 };

  return (
    <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-6 select-none z-30">
      {/* Center Crosshair */}
      <div className="absolute inset-0 flex items-center justify-center">
        {isLocked ? (
          <div className="relative">
            <div
              className={`w-2.5 h-2.5 rounded-full border-2 transition-colors duration-150 ${
                isColliding
                  ? 'border-red-500 bg-red-500/50 scale-125'
                  : 'border-white/80 bg-white/30'
              }`}
            />
            {isColliding && (
              <div className="absolute -top-7 left-1/2 -translate-x-1/2 whitespace-nowrap bg-red-600/90 text-white text-[10px] font-bold px-2 py-0.5 rounded shadow-lg uppercase tracking-wider">
                {collidedWith === 'WALL' && 'Wall Collision'}
                {collidedWith === 'FURNITURE' && 'Furniture Collision'}
                {collidedWith === 'BOUNDARY' && 'Room Perimeter'}
              </div>
            )}
          </div>
        ) : (
          <div className="bg-slate-950/85 backdrop-blur-md text-white px-5 py-3.5 rounded-2xl border border-slate-700 shadow-2xl flex flex-col items-center gap-2 pointer-events-auto cursor-pointer text-center">
            <div className="text-sm font-bold text-[#C5A059]">Click Canvas to Enter Walk Mode</div>
            <div className="text-xs text-slate-300">
              Use <span className="font-bold text-white">W, A, S, D</span> to walk,{' '}
              <span className="font-bold text-white">Mouse</span> to look around
            </div>
          </div>
        )}
      </div>

      {/* Top Banner Notifications */}
      <div className="flex items-center justify-between w-full">
        {/* Active Room Indicator */}
        <div className="flex items-center gap-2.5 px-3.5 py-1.5 bg-slate-900/80 backdrop-blur-md rounded-xl border border-slate-700/80 text-white text-xs shadow-lg">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-bold">{activeRoomName || 'Active Room'}</span>
          {isInDoorway && (
            <span className="flex items-center gap-1 text-[11px] font-semibold text-amber-300 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-500/30">
              <DoorOpen className="w-3.5 h-3.5" /> Doorway Transit
            </span>
          )}
        </div>

        {/* Real Metric Coordinates */}
        <div className="px-3 py-1.5 bg-slate-900/80 backdrop-blur-md rounded-xl border border-slate-700/80 text-slate-300 font-mono text-[11px] shadow-lg">
          X: <span className="text-white font-bold">{coords.x.toFixed(2)}m</span> | Y:{' '}
          <span className="text-white font-bold">{coords.y.toFixed(2)}m</span> | Z:{' '}
          <span className="text-white font-bold">{coords.z.toFixed(2)}m</span>
        </div>
      </div>

      {/* Bottom Controls Reminder */}
      <div className="flex items-end justify-between w-full">
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300 bg-slate-900/85 backdrop-blur-md px-4 py-2.5 rounded-2xl border border-slate-700/80 shadow-lg">
          <span className="flex items-center gap-1 font-semibold text-white">
            <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-600 rounded font-mono text-[10px]">
              W
            </kbd>
            <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-600 rounded font-mono text-[10px]">
              A
            </kbd>
            <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-600 rounded font-mono text-[10px]">
              S
            </kbd>
            <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-600 rounded font-mono text-[10px]">
              D
            </kbd>{' '}
            Walk
          </span>
          <span className="text-slate-600">•</span>
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-600 rounded font-mono text-[10px]">
              Shift
            </kbd>{' '}
            Sprint
          </span>
          <span className="text-slate-600">•</span>
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-600 rounded font-mono text-[10px]">
              V
            </kbd>{' '}
            Isometric View
          </span>
          <span className="text-slate-600">•</span>
          <span className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-600 rounded font-mono text-[10px]">
              Esc
            </kbd>{' '}
            Release Mouse
          </span>
        </div>
      </div>
    </div>
  );
};

