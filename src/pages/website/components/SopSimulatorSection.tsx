import React, { useState, useEffect } from 'react';
import {
  Sliders,
  Volume2,
  VolumeX,
  Gauge,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Sparkles,
  Compass,
  Eye,
  RefreshCw
} from 'lucide-react';

export const SopSimulatorSection: React.FC = () => {
  // Simulator State
  const [speed, setSpeed] = useState<number>(0.22); // m/s
  const [distance, setDistance] = useState<number>(1.8); // meters
  const [overlap, setOverlap] = useState<number>(75); // percent
  const [cornerDwell, setCornerDwell] = useState<number>(1.6); // seconds
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(false);
  const [lastSpoken, setLastSpoken] = useState<string>('');

  // Derived Metrics
  const speedOptimal = speed >= 0.15 && speed <= 0.28;
  const speedWarning = speed > 0.28 && speed <= 0.40;
  const speedViolated = speed > 0.40 || speed < 0.10;

  const distanceOptimal = distance >= 1.4 && distance <= 2.2;
  const distanceWarning = (distance >= 1.0 && distance < 1.4) || (distance > 2.2 && distance <= 2.8);
  const distanceViolated = distance < 1.0 || distance > 2.8;

  const overlapOptimal = overlap >= 70 && overlap <= 85;
  const overlapWarning = (overlap >= 60 && overlap < 70) || (overlap > 85 && overlap <= 90);
  const overlapViolated = overlap < 60;

  const cornerOptimal = cornerDwell >= 1.5;

  // Laplacian Blur Variance estimation formula
  const estimatedLaplacian = Math.max(35, Math.round(230 - speed * 260 + (Math.random() * 4 - 2)));
  const blurPassed = estimatedLaplacian >= 120;

  // Composite Score
  let score = 100;
  if (!speedOptimal) score -= speedWarning ? 12 : 30;
  if (!distanceOptimal) score -= distanceWarning ? 10 : 25;
  if (!overlapOptimal) score -= overlapWarning ? 10 : 25;
  if (!cornerOptimal) score -= 15;
  if (!blurPassed) score -= 20;
  score = Math.max(10, Math.min(100, score));

  // Voice synthesis trigger
  const speakInstruction = (text: string) => {
    if (!voiceEnabled || !window.speechSynthesis) return;
    if (text === lastSpoken) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
    setLastSpoken(text);
  };

  useEffect(() => {
    if (!voiceEnabled) return;
    if (speed > 0.40) {
      speakInstruction('Please slow down. High motion blur detected.');
    } else if (distance > 2.8) {
      speakInstruction('Step closer to the wall. Recommended distance is 1.5 meters.');
    } else if (overlap < 60) {
      speakInstruction('Insufficient overlap. Sweep slower for feature matching.');
    } else if (cornerDwell >= 1.5) {
      speakInstruction('Corner anchor locked. Scale calibration active.');
    } else if (score >= 90) {
      speakInstruction('Sweep speed and distance optimal. Keyframe quality excellent.');
    }
  }, [speed, distance, overlap, cornerDwell, voiceEnabled, score]);

  const resetDefaults = () => {
    setSpeed(0.22);
    setDistance(1.8);
    setOverlap(75);
    setCornerDwell(1.6);
  };

  return (
    <section id="sop-simulator" className="py-24 bg-[#141210] relative border-t border-[#C5A059]/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-[#1A1714] border border-[#C5A059]/40 text-[#E8C982] text-xs font-mono uppercase tracking-wider">
            <Sliders className="w-3.5 h-3.5 text-[#C5A059]" />
            <span>Interactive Mobile Edge Simulator</span>
          </div>

          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold text-[#FAF7F0] tracking-tight">
            Standard Operating Procedure (SOP){' '}
            <span className="text-[#E8C982]">Capture Simulator</span>
          </h2>

          <p className="text-[#C4B9AC] text-sm sm:text-base font-light leading-relaxed">
            Experience the real-time telemetry algorithms running on the surveyor's mobile device during an on-site scan. Adjust the parameters below to see how our edge engine enforces sub-centimeter photogrammetric quality gates.
          </p>
        </div>

        {/* Interactive Simulator Grid */}
        <div className="mt-14 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Interactive Telemetry Controls (7 cols) */}
          <div className="lg:col-span-7 rounded-2xl bg-[#0E0C0A] border border-[#C5A059]/40 p-6 sm:p-8 shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-[#C5A059]/20 pb-4">
              <div className="flex items-center space-x-2">
                <Gauge className="w-5 h-5 text-[#C5A059]" />
                <h3 className="font-serif font-bold text-lg text-[#FAF7F0]">
                  Surveyor Capture Parameters
                </h3>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={() => setVoiceEnabled(!voiceEnabled)}
                  className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center space-x-1.5 transition-all ${
                    voiceEnabled
                      ? 'bg-emerald-950/60 border-emerald-500/50 text-emerald-400 shadow-md'
                      : 'bg-[#1A1714] border-[#C5A059]/30 text-[#A6998A] hover:text-white'
                  }`}
                  title="Enable realistic voice speech guidance"
                >
                  {voiceEnabled ? <Volume2 className="w-3.5 h-3.5 text-emerald-400" /> : <VolumeX className="w-3.5 h-3.5 text-[#A6998A]" />}
                  <span>{voiceEnabled ? 'Audio HUD Active' : 'Enable Audio Guidance'}</span>
                </button>

                <button
                  onClick={resetDefaults}
                  className="p-1.5 rounded-lg border border-[#C5A059]/30 bg-[#1A1714] text-[#A6998A] hover:text-[#E8C982] transition-colors"
                  title="Reset to default optimal parameters"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Slider 1: Sweep Speed */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-[#FAF7F0] font-semibold flex items-center space-x-2">
                  <span>1. Panning & Sweep Speed:</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      speedOptimal
                        ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/40'
                        : speedWarning
                        ? 'bg-amber-950/80 text-amber-400 border border-amber-500/40'
                        : 'bg-red-950/80 text-red-400 border border-red-500/40'
                    }`}
                  >
                    {speedOptimal ? 'OPTIMAL (0.15 - 0.28 m/s)' : speedWarning ? 'CAUTION (Fast)' : 'CRITICAL (Blur Risk)'}
                  </span>
                </span>
                <span className="text-[#E8C982] font-bold text-sm">{speed.toFixed(2)} m/s</span>
              </div>
              <input
                type="range"
                min="0.08"
                max="0.80"
                step="0.02"
                value={speed}
                onChange={(e) => setSpeed(parseFloat(e.target.value))}
                className="w-full h-2 bg-[#1A1714] rounded-lg appearance-none cursor-pointer accent-[#C5A059]"
              />
              <div className="flex justify-between text-[10px] font-mono text-[#6D5020]">
                <span>0.10 m/s (Slow)</span>
                <span>0.22 m/s (Recommended)</span>
                <span>0.80 m/s (Fast)</span>
              </div>
            </div>

            {/* Slider 2: Wall Distance */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-[#FAF7F0] font-semibold flex items-center space-x-2">
                  <span>2. Wall Standoff Distance:</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      distanceOptimal
                        ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/40'
                        : distanceWarning
                        ? 'bg-amber-950/80 text-amber-400 border border-amber-500/40'
                        : 'bg-red-950/80 text-red-400 border border-red-500/40'
                    }`}
                  >
                    {distanceOptimal ? 'OPTIMAL (1.5 - 2.0 m)' : distanceWarning ? 'ACCEPTABLE' : 'OUT OF BOUNDS'}
                  </span>
                </span>
                <span className="text-[#E8C982] font-bold text-sm">{distance.toFixed(2)} m</span>
              </div>
              <input
                type="range"
                min="0.6"
                max="3.5"
                step="0.1"
                value={distance}
                onChange={(e) => setDistance(parseFloat(e.target.value))}
                className="w-full h-2 bg-[#1A1714] rounded-lg appearance-none cursor-pointer accent-[#C5A059]"
              />
              <div className="flex justify-between text-[10px] font-mono text-[#6D5020]">
                <span>0.6 m (Too Close)</span>
                <span>1.8 m (Standard)</span>
                <span>3.5 m (Too Far)</span>
              </div>
            </div>

            {/* Slider 3: Frame Overlap */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-[#FAF7F0] font-semibold flex items-center space-x-2">
                  <span>3. Inter-Frame Keyframe Overlap:</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      overlapOptimal
                        ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/40'
                        : overlapWarning
                        ? 'bg-amber-950/80 text-amber-400 border border-amber-500/40'
                        : 'bg-red-950/80 text-red-400 border border-red-500/40'
                    }`}
                  >
                    {overlapOptimal ? 'OPTIMAL (70% - 80%)' : overlapWarning ? 'ACCEPTABLE' : 'INSUFFICIENT'}
                  </span>
                </span>
                <span className="text-[#E8C982] font-bold text-sm">{overlap}%</span>
              </div>
              <input
                type="range"
                min="40"
                max="90"
                step="1"
                value={overlap}
                onChange={(e) => setOverlap(parseInt(e.target.value))}
                className="w-full h-2 bg-[#1A1714] rounded-lg appearance-none cursor-pointer accent-[#C5A059]"
              />
              <div className="flex justify-between text-[10px] font-mono text-[#6D5020]">
                <span>40% (Triangulation Failure)</span>
                <span>75% (Target)</span>
                <span>90% (Redundant Data)</span>
              </div>
            </div>

            {/* Slider 4: Corner Dwell */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-[#FAF7F0] font-semibold flex items-center space-x-2">
                  <span>4. Room Corner Anchor Dwell Time:</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      cornerOptimal
                        ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/40'
                        : 'bg-amber-950/80 text-amber-400 border border-amber-500/40'
                    }`}
                  >
                    {cornerOptimal ? 'SCALE ANCHOR LOCKED (≥ 1.5s)' : 'INSUFFICIENT DWELL'}
                  </span>
                </span>
                <span className="text-[#E8C982] font-bold text-sm">{cornerDwell.toFixed(1)} s</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="3.0"
                step="0.1"
                value={cornerDwell}
                onChange={(e) => setCornerDwell(parseFloat(e.target.value))}
                className="w-full h-2 bg-[#1A1714] rounded-lg appearance-none cursor-pointer accent-[#C5A059]"
              />
              <div className="flex justify-between text-[10px] font-mono text-[#6D5020]">
                <span>0.0 s (No Anchor)</span>
                <span>1.5 s (Required)</span>
                <span>3.0 s (Maximum)</span>
              </div>
            </div>
          </div>

          {/* Right Column: Live Mobile Edge HUD Output (5 cols) */}
          <div className="lg:col-span-5 rounded-2xl bg-[#0E0C0A] border border-[#C5A059]/40 p-6 sm:p-8 shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-[#C5A059]/20 pb-4">
              <div className="flex items-center space-x-2">
                <Eye className="w-5 h-5 text-emerald-400" />
                <h3 className="font-serif font-bold text-lg text-[#FAF7F0]">
                  Live Mobile HUD Telemetry
                </h3>
              </div>
              <span className="font-mono text-[10px] text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2 py-0.5 rounded">
                SIMULATOR
              </span>
            </div>

            {/* Composite Score Meter */}
            <div className="p-5 rounded-xl bg-[#141210] border border-[#C5A059]/30 text-center space-y-3">
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#A6998A]">
                Composite SOP Quality Score
              </span>
              <div className="flex items-center justify-center space-x-3">
                <span
                  className={`text-5xl font-mono font-bold ${
                    score >= 85
                      ? 'text-emerald-400'
                      : score >= 65
                      ? 'text-amber-400'
                      : 'text-red-400'
                  }`}
                >
                  {score}%
                </span>
              </div>
              <div className="w-full h-2 bg-[#0E0C0A] rounded-full overflow-hidden border border-[#C5A059]/20">
                <div
                  className={`h-full transition-all duration-300 ${
                    score >= 85
                      ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
                      : score >= 65
                      ? 'bg-gradient-to-r from-amber-500 to-yellow-400'
                      : 'bg-gradient-to-r from-red-500 to-rose-400'
                  }`}
                  style={{ width: `${score}%` }}
                />
              </div>
              <span className="text-xs font-sans text-[#C4B9AC] block">
                {score >= 85
                  ? '✓ Ready for Production Cloud Ingestion'
                  : score >= 65
                  ? '⚠ Acceptable with minor reprojection variance'
                  : '✖ Rejection Risk: High motion blur or drift'}
              </span>
            </div>

            {/* Quality Gate Status Table */}
            <div className="space-y-2.5 font-mono text-xs">
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-[#141210] border border-[#C5A059]/20">
                <span className="text-[#A6998A]">Laplacian Sharpness σ²:</span>
                <span
                  className={`font-bold flex items-center space-x-1 ${
                    blurPassed ? 'text-emerald-400' : 'text-red-400'
                  }`}
                >
                  {blurPassed ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                  <span>{estimatedLaplacian} (≥ 120.0)</span>
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg bg-[#141210] border border-[#C5A059]/20">
                <span className="text-[#A6998A]">Overlap Consensus:</span>
                <span
                  className={`font-bold flex items-center space-x-1 ${
                    overlapOptimal ? 'text-emerald-400' : overlapWarning ? 'text-amber-400' : 'text-red-400'
                  }`}
                >
                  {overlapOptimal ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                  <span>{overlap}% (≥ 70%)</span>
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg bg-[#141210] border border-[#C5A059]/20">
                <span className="text-[#A6998A]">Metric Anchor Lock:</span>
                <span
                  className={`font-bold flex items-center space-x-1 ${
                    cornerOptimal ? 'text-emerald-400' : 'text-amber-400'
                  }`}
                >
                  {cornerOptimal ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                  <span>{cornerDwell.toFixed(1)}s (≥ 1.5s)</span>
                </span>
              </div>
            </div>

            {/* Audio Cue Transcript Box */}
            <div className="p-3.5 rounded-xl bg-[#141210] border border-[#C5A059]/30 text-xs">
              <span className="text-[10px] font-mono uppercase tracking-wider text-[#C5A059] block mb-1">
                Active Speech Synthesis Cue:
              </span>
              <p className="italic text-[#FAF7F0] font-sans">
                "{voiceEnabled ? lastSpoken || 'Monitoring capture telemetry in real time...' : 'Toggle "Audio HUD Active" above to hear realistic surveyor voice alerts.'}"
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

