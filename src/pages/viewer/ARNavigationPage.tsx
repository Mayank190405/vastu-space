import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  Compass,
  Navigation,
  Sparkles,
  AlertTriangle,
  RotateCw,
  MapPin,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';
import { MobileARNavigationController, ARNavigationState } from '../../components/viewer/arController';
import { POI } from '../../components/viewer/navigationEngine';
import { api } from '../../services/api';

export const ARNavigationPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get('projectId') || '';
  const arContainerRef = useRef<HTMLDivElement>(null);
  const controllerRef = useRef<MobileARNavigationController | null>(null);

  const [pois, setPOIs] = useState<POI[]>([]);
  const [selectedPOI, setSelectedPOI] = useState<POI | null>(null);
  const [arState, setARState] = useState<ARNavigationState>({
    hasCamera: false,
    compassHeading: 0,
    bearingToTarget: 0,
    distanceToTarget: 0,
    turnDirection: 'straight'
  });

  const [showPOIList, setShowPOIList] = useState(false);

  useEffect(() => {
    if (!arContainerRef.current) return;

    const controller = new MobileARNavigationController(
      arContainerRef.current,
      (state) => {
        setARState(state);
      }
    );
    controllerRef.current = controller;

    return () => {
      controller.dispose();
    };
  }, []);

  const handleSelectPOI = (poi: POI) => {
    setSelectedPOI(poi);
    setShowPOIList(false);
    if (controllerRef.current) {
      // Calculate a target bearing based on real POI coordinates
      const angle = Math.atan2(poi.position[0], -poi.position[2]) * (180 / Math.PI);
      const normalizedBearing = (angle + 360) % 360;
      const dist = Math.hypot(poi.position[0], poi.position[2]) * 2.2;
      controllerRef.current.setTargetLocation(Math.round(normalizedBearing), parseFloat(dist.toFixed(1)));
    }
  };

  useEffect(() => {
    if (projectId) {
      api.listPOIs(projectId)
        .then((data) => {
          if (Array.isArray(data) && data.length > 0) {
            const loaded: POI[] = data.map((p: any) => ({
              id: p.id,
              name: p.name,
              category: p.category || 'Custom',
              position: [p.x ?? p.position?.[0] ?? 0, p.y ?? p.position?.[1] ?? 0, p.z ?? p.position?.[2] ?? 0],
              color: p.color || '#3b82f6',
              description: p.description
            }));
            setPOIs(loaded);
            handleSelectPOI(loaded[0]);
          }
        })
        .catch((err) => {
          console.warn('Failed to fetch project POIs:', err);
        });
    }
  }, [projectId]);

  return (
    <div className="relative w-full h-screen bg-black overflow-hidden font-sans select-none">
      {/* 1. AR Camera Video and Three.js 3D Arrow Canvas Container */}
      <div ref={arContainerRef} className="absolute inset-0 w-full h-full" />

      {/* 2. Top Header Overlay */}
      <div className="absolute top-4 left-4 right-4 z-30 flex items-center justify-between pointer-events-none">
        <button
          onClick={() => navigate('/viewer')}
          className="p-2.5 bg-black/60 hover:bg-black/80 backdrop-blur-xl border border-white/20 text-white rounded-xl shadow-xl pointer-events-auto transition active:scale-95"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 bg-black/60 backdrop-blur-xl border border-[#DFB873]/30 px-3.5 py-1.5 rounded-full pointer-events-auto shadow-xl">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-[11px] font-bold text-[#dfb873] tracking-wide uppercase">
            Live AR Guidance
          </span>
          <span className="text-[10px] text-slate-400 font-mono">
            {arState.compassHeading}°
          </span>
        </div>

        <button
          onClick={() => setShowPOIList(!showPOIList)}
          className="p-2.5 bg-[#dfb873] hover:bg-[#c9a25b] text-black font-bold rounded-xl shadow-xl pointer-events-auto transition active:scale-95"
          title="Select Destination"
        >
          <MapPin className="w-5 h-5" />
        </button>
      </div>

      {/* 3. Turn-by-Turn Guidance Banner */}
      <div className="absolute top-20 left-4 right-4 z-30 pointer-events-none">
        <div className="bg-[#0d1118]/90 backdrop-blur-2xl border border-[#DFB873]/40 rounded-2xl p-4 shadow-2xl pointer-events-auto">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
              <Navigation className="w-3.5 h-3.5" /> Next Maneuver
            </span>
            <span className="text-xs font-mono font-bold text-[#dfb873] bg-[#dfb873]/15 px-2 py-0.5 rounded-md border border-[#dfb873]/30">
              {arState.distanceToTarget} m away
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#dfb873] to-[#a8823b] flex items-center justify-center text-black font-bold shadow-md shrink-0">
              {arState.turnDirection === 'straight' && '↑'}
              {arState.turnDirection === 'slight-right' && '↗'}
              {arState.turnDirection === 'sharp-right' && '→'}
              {arState.turnDirection === 'slight-left' && '↖'}
              {arState.turnDirection === 'sharp-left' && '←'}
              {arState.turnDirection === 'behind' && '↓'}
            </div>
            <div>
              <h3 className="text-sm font-bold text-white leading-tight">
                {arState.turnDirection === 'straight' && 'Follow arrow straight ahead'}
                {arState.turnDirection === 'slight-right' && 'Bear slight right toward aisle'}
                {arState.turnDirection === 'sharp-right' && 'Turn right toward corridor'}
                {arState.turnDirection === 'slight-left' && 'Bear slight left toward door'}
                {arState.turnDirection === 'sharp-left' && 'Turn sharp left'}
                {arState.turnDirection === 'behind' && 'Turn around'}
              </h3>
              <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
                <span>Destination:</span>
                <span className="text-[#dfb873] font-semibold">{selectedPOI ? selectedPOI.name : 'No waypoint selected'}</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 4. POI Selection Drawer */}
      {showPOIList && (
        <div className="absolute inset-x-4 top-20 bottom-24 z-40 bg-[#0d1118]/95 backdrop-blur-2xl border border-[#DFB873]/40 rounded-2xl p-4 shadow-2xl flex flex-col animate-in fade-in zoom-in-95 duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-white/10">
            <span className="text-xs font-bold text-[#dfb873] uppercase tracking-wider flex items-center gap-1.5">
              <MapPin className="w-4 h-4" /> Select AR Waypoint
            </span>
            <button
              onClick={() => setShowPOIList(false)}
              className="p-1 text-slate-400 hover:text-white"
            >
              ✕
            </button>
          </div>

          <div className="flex-1 overflow-y-auto py-3 space-y-2">
            {pois.length > 0 ? (
              pois.map((poi) => (
                <button
                  key={poi.id}
                  onClick={() => handleSelectPOI(poi)}
                  className={`w-full p-3 rounded-xl border text-left transition-all flex items-center justify-between ${
                    selectedPOI?.id === poi.id
                      ? 'bg-[#dfb873]/20 border-[#dfb873] text-white shadow-lg'
                      : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: poi.color }}
                      />
                      <span className="font-bold text-xs text-white">{poi.name}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-0.5 block">
                      {poi.description}
                    </span>
                  </div>
                  {selectedPOI?.id === poi.id && (
                    <CheckCircle2 className="w-4 h-4 text-[#dfb873]" />
                  )}
                </button>
              ))
            ) : (
              <div className="p-8 text-center text-slate-400 text-xs">
                No POIs recorded for this project yet.
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. Center Reticle & Compass Heading HUD */}
      <div className="absolute inset-0 z-20 flex flex-col items-center justify-center pointer-events-none">
        <div className="w-48 h-48 rounded-full border border-white/10 flex items-center justify-center relative">
          <div className="absolute top-1 text-[10px] font-mono text-slate-400">N (0°)</div>
          <div className="absolute right-1 text-[10px] font-mono text-slate-400">E (90°)</div>
          <div className="absolute bottom-1 text-[10px] font-mono text-slate-400">S (180°)</div>
          <div className="absolute left-1 text-[10px] font-mono text-slate-400">W (270°)</div>

          {/* Compass Needle */}
          <div
            className="w-1 h-32 bg-gradient-to-t from-transparent via-[#dfb873] to-red-500 rounded-full transition-transform duration-300"
            style={{ transform: `rotate(${arState.compassHeading}deg)` }}
          />

          <div className="w-3 h-3 rounded-full bg-white/40 backdrop-blur-md z-10" />
        </div>
      </div>

      {/* 6. Bottom Status HUD */}
      <div className="absolute bottom-6 left-4 right-4 z-30 flex items-center justify-between bg-black/75 backdrop-blur-xl border border-white/15 px-4 py-3 rounded-2xl shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-white/10 text-[#dfb873]">
            <Compass className="w-4 h-4" />
          </div>
          <div>
            <div className="text-[10px] text-slate-400 uppercase font-mono">Bearing to Target</div>
            <div className="text-xs font-mono font-bold text-white">
              {arState.bearingToTarget}° &bull; Range: {arState.distanceToTarget}m
            </div>
          </div>
        </div>

        <button
          onClick={() => navigate('/viewer')}
          className="px-3.5 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-semibold text-slate-200 transition"
        >
          Exit AR
        </button>
      </div>

      {/* Camera permission alert if unavailable */}
      {!arState.hasCamera && arState.cameraError && (
        <div className="absolute bottom-20 left-4 right-4 z-40 p-3 bg-amber-950/80 border border-amber-500/40 rounded-xl text-xs text-amber-200 flex items-center gap-2.5 shadow-xl">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>Camera feed unavailable on this device. Displaying 3D synthetic spatial simulation mode.</span>
        </div>
      )}
    </div>
  );
};
