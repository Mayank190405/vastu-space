import React, { useState } from 'react';
import {
  Compass,
  Flame,
  Droplets,
  Wind,
  Mountain,
  Sun,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Info
} from 'lucide-react';

interface VastuZone {
  id: string;
  name: string;
  sanskrit: string;
  direction: string;
  degrees: string;
  element: string;
  deity: string;
  optimalRooms: string[];
  restrictedRooms: string[];
  spatialScoreWeight: number;
  principle: string;
  color: string;
}

export const VastuShastraSection: React.FC = () => {
  const [selectedZoneId, setSelectedZoneId] = useState<string>('ne');

  const zones: VastuZone[] = [
    {
      id: 'ne',
      name: 'North-East',
      sanskrit: 'Īśānya (ईशान्य)',
      direction: 'NE',
      degrees: '22.5° – 67.5°',
      element: 'Water (Jala) & Ether',
      deity: 'Ishana (Lord of Purity)',
      optimalRooms: ['Puja / Meditation Room', 'Entrance Foyer', 'Study & Library', 'Open Balcony'],
      restrictedRooms: ['Heavy Master Bedroom', 'Kitchen (Agni clashes with Jala)', 'Toilets / Waste Shafts'],
      spatialScoreWeight: 95,
      principle: 'Represents mental clarity and spiritual wisdom. The structural weight here must be minimized; floor height should be lowest or level, with maximum fenestration for morning solar irradiance.',
      color: 'from-sky-500 to-cyan-400',
    },
    {
      id: 'e',
      name: 'East',
      sanskrit: 'Pūrva (पूर्व)',
      direction: 'E',
      degrees: '67.5° – 112.5°',
      element: 'Solar Light & Air',
      deity: 'Indra / Surya (Illumination)',
      optimalRooms: ['Main Entrance', 'Living Lounge', 'Verandah', 'Child Study Desk'],
      restrictedRooms: ['Heavy Storage', 'Master Bedhead against East'],
      spatialScoreWeight: 88,
      principle: 'Source of early morning ultraviolet and visible spectrum rays. Ideal for daily family gathering spaces and prominent entrance thresholds.',
      color: 'from-amber-400 to-yellow-300',
    },
    {
      id: 'se',
      name: 'South-East',
      sanskrit: 'Āgneya (आग्नेय)',
      direction: 'SE',
      degrees: '112.5° – 157.5°',
      element: 'Fire (Agni)',
      deity: 'Agni Deva (Energy & Metabolism)',
      optimalRooms: ['Modular Kitchen (Cooktop facing East)', 'Electrical Conduits & Inverters', 'Boiler / Water Heater'],
      restrictedRooms: ['Master Bedroom', 'Puja Room', 'Underground Water Tank'],
      spatialScoreWeight: 92,
      principle: 'Governs metabolic and thermal energy. High-wattage culinary equipment and electrical distribution boxes belong strictly in this quadrant to prevent energetic discord.',
      color: 'from-orange-500 to-amber-600',
    },
    {
      id: 's',
      name: 'South',
      sanskrit: 'Dakṣiṇa (दक्षिण)',
      direction: 'S',
      degrees: '157.5° – 202.5°',
      element: 'Earth & Stability',
      deity: 'Yama (Discipline & Rest)',
      optimalRooms: ['Bedroom Suites', 'Administrative Office', 'Heavy Wardrobes'],
      restrictedRooms: ['Main Building Entrance', 'Pond / Water Fountain'],
      spatialScoreWeight: 82,
      principle: 'Governs rest and vitality. Requires moderate structural mass, thicker partition walls, and restricted window apertures.',
      color: 'from-red-600 to-orange-500',
    },
    {
      id: 'sw',
      name: 'South-West',
      sanskrit: 'Nairṛtya (नैऋत्य)',
      direction: 'SW',
      degrees: '202.5° – 247.5°',
      element: 'Earth (Prithvi)',
      deity: 'Nirriti (Anchor & Grounding)',
      optimalRooms: ['Master Bedroom Suite', 'Principal Architect Cabin', 'Heavy Safe & Storage', 'Overhead Water Tank'],
      restrictedRooms: ['Main Entry Door', 'Kitchen', 'Puja Sanctum', 'Open Void / Basement'],
      spatialScoreWeight: 96,
      principle: 'The foundational anchor of the entire architectural structure. Must carry the maximum structural mass, thickest load-bearing columns, and highest floor datum.',
      color: 'from-stone-600 to-amber-800',
    },
    {
      id: 'w',
      name: 'West',
      sanskrit: 'Paścima (पश्चिम)',
      direction: 'W',
      degrees: '247.5° – 292.5°',
      element: 'Water & Metal',
      deity: 'Varuna (Overseer of Prosperity)',
      optimalRooms: ['Dining Hall', 'Children Bedroom', 'Study Cabin', 'Overhead Water Storage'],
      restrictedRooms: ['Main Entrance Foyer', 'Pantry Cooktop'],
      spatialScoreWeight: 84,
      principle: 'Governs abundance and intellectual focus. Excellent for family dining and children bedrooms, shielded from harsh western sunset thermal heat.',
      color: 'from-teal-600 to-cyan-700',
    },
    {
      id: 'nw',
      name: 'North-West',
      sanskrit: 'Vāyavya (वायव्य)',
      direction: 'NW',
      degrees: '292.5° – 337.5°',
      element: 'Air (Vayu)',
      deity: 'Vayu Deva (Movement & Circulation)',
      optimalRooms: ['Guest Bedroom', 'Client Meeting Room', 'Pantry / Cold Storage', 'Vehicle Parking'],
      restrictedRooms: ['Master Bedroom (Causes restless movement)', 'Heavy Concrete Safe'],
      spatialScoreWeight: 86,
      principle: 'Governs dynamic spatial circulation and social engagement. Ideal for transient functional zones like visitor lounges and ventilation breezeways.',
      color: 'from-emerald-500 to-teal-400',
    },
    {
      id: 'n',
      name: 'North',
      sanskrit: 'Uttara (उत्तर)',
      direction: 'N',
      degrees: '337.5° – 22.5°',
      element: 'Water & Magnetism',
      deity: 'Kubera (Lord of Wealth)',
      optimalRooms: ['Living Room Foyer', 'Cash / Accounts Desk', 'Open Balconies', 'Water Fountain'],
      restrictedRooms: ['Heavy Machinery', 'Master Bedhead against North', 'Toilets'],
      spatialScoreWeight: 90,
      principle: 'Governs northern geomagnetic flux and prosperity. Architectural openings should be expansive and unobstructed to draw natural light.',
      color: 'from-blue-500 to-indigo-400',
    },
    {
      id: 'center',
      name: 'Center Sanctum',
      sanskrit: 'Brahmasthāna (ब्रह्मस्थान)',
      direction: 'Center',
      degrees: 'Omni-Directional Core',
      element: 'Space / Ether (Ākāśa)',
      deity: 'Brahma (Universal Architect)',
      optimalRooms: ['Open Courtyard (Atrium)', 'Central Circulation Spine', 'Lobby'],
      restrictedRooms: ['Structural Columns', 'Load-bearing Pillars', 'Kitchen', 'Toilets', 'Beams'],
      spatialScoreWeight: 98,
      principle: 'The heart and umbilical energy core of the digital twin. VĀSTU enforces an automated check to verify zero structural columns penetrate this central quadrant.',
      color: 'from-[#C5A059] to-[#E8C982]',
    },
  ];

  const selected = zones.find((z) => z.id === selectedZoneId) || zones[0];

  return (
    <section id="vastu-shastra" className="py-24 bg-[#0E0C0A] relative border-t border-[#C5A059]/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-[#1A1714] border border-[#C5A059]/40 text-[#E8C982] text-xs font-mono uppercase tracking-wider">
            <Compass className="w-3.5 h-3.5 text-[#C5A059]" />
            <span>Vedic Geometry Meets 3D Spatial Computing</span>
          </div>

          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold text-[#FAF7F0] tracking-tight">
            Vāstu Shastra &{' '}
            <span className="text-[#E8C982]">Directional Energy Grids</span>
          </h2>

          <p className="text-[#C4B9AC] text-sm sm:text-base font-light leading-relaxed">
            In collaboration with <strong>Create Fo'em Studio</strong>, VĀSTU integrates India's millennia-old architectural orientation guidelines directly into our spatial classification engine. Click on any cardinal sector below to view its algorithmic rules.
          </p>
        </div>

        {/* Interactive Vāstu Compass Grid */}
        <div className="mt-14 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: 9 Sector Selector Grid (5 cols) */}
          <div className="lg:col-span-5 rounded-2xl bg-[#141210] border border-[#C5A059]/40 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#C5A059]/20 pb-3">
              <span className="text-xs font-mono uppercase tracking-wider text-[#E8C982] font-semibold">
                Select Cardinal Direction:
              </span>
              <span className="text-[10px] font-mono text-[#9C9183]">360° GEODETIC GRID</span>
            </div>

            <div className="grid grid-cols-3 gap-2.5">
              {zones.map((zone) => {
                const isSelected = selectedZoneId === zone.id;
                return (
                  <button
                    key={zone.id}
                    onClick={() => setSelectedZoneId(zone.id)}
                    className={`p-3 rounded-xl border text-center transition-all flex flex-col items-center justify-center min-h-[85px] ${
                      isSelected
                        ? 'bg-gradient-to-b from-[#C5A059]/30 to-[#1A1714] border-[#C5A059] shadow-lg shadow-[#C5A059]/20 ring-1 ring-[#C5A059]'
                        : 'bg-[#0E0C0A] border-[#C5A059]/20 hover:border-[#C5A059]/50 hover:bg-[#1A1714]'
                    }`}
                  >
                    <span
                      className={`text-sm font-bold font-mono ${
                        isSelected ? 'text-[#E8C982]' : 'text-white'
                      }`}
                    >
                      {zone.direction}
                    </span>
                    <span className="text-[10px] text-[#A6998A] font-serif font-medium mt-0.5 line-clamp-1">
                      {zone.name}
                    </span>
                    <span className="text-[9px] font-mono text-[#C5A059] mt-1">
                      {zone.sanskrit.split(' ')[0]}
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="p-3 rounded-xl bg-[#0E0C0A] border border-[#C5A059]/20 flex items-center space-x-2 text-xs font-mono text-[#A6998A]">
              <Info className="w-4 h-4 text-[#C5A059] shrink-0" />
              <span>Compass heading calibrated automatically via phone magnetometer during capture.</span>
            </div>
          </div>

          {/* Right Column: Detailed Vāstu Algorithmic Card (7 cols) */}
          <div className="lg:col-span-7 rounded-2xl bg-[#141210] border border-[#C5A059]/40 p-6 sm:p-8 shadow-2xl space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#C5A059]/20 pb-4">
              <div>
                <span className="text-xs font-mono text-[#C5A059] uppercase tracking-widest font-semibold">
                  ZONE DEGREES: {selected.degrees}
                </span>
                <h3 className="font-serif text-2xl font-bold text-[#FAF7F0] mt-0.5">
                  {selected.name} · {selected.sanskrit}
                </h3>
              </div>
              <div className="flex items-center space-x-2 font-mono text-xs">
                <span className="px-3 py-1 rounded bg-[#0E0C0A] border border-[#C5A059]/30 text-[#E8C982]">
                  {selected.element}
                </span>
              </div>
            </div>

            {/* Principle Description */}
            <p className="text-sm text-[#C4B9AC] font-light leading-relaxed">
              {selected.principle}
            </p>

            {/* Optimal vs Restricted Rooms */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 space-y-2">
                <div className="flex items-center space-x-1.5 text-xs font-mono font-bold text-emerald-400 uppercase">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Optimal Space Allocations:</span>
                </div>
                <ul className="space-y-1.5 text-xs text-[#E3DDD5]">
                  {selected.optimalRooms.map((room, idx) => (
                    <li key={idx} className="flex items-start space-x-1.5">
                      <span className="text-emerald-400">•</span>
                      <span>{room}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="p-4 rounded-xl bg-red-950/20 border border-red-500/30 space-y-2">
                <div className="flex items-center space-x-1.5 text-xs font-mono font-bold text-red-400 uppercase">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Restricted / Adverse Allocations:</span>
                </div>
                <ul className="space-y-1.5 text-xs text-[#E3DDD5]">
                  {selected.restrictedRooms.map((room, idx) => (
                    <li key={idx} className="flex items-start space-x-1.5">
                      <span className="text-red-400">•</span>
                      <span>{room}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* VĀSTU PostGIS Spatial Scoring Rule */}
            <div className="p-4 rounded-xl bg-[#0E0C0A] border border-[#C5A059]/20 space-y-2 font-mono text-xs">
              <div className="flex items-center justify-between text-[#E8C982] text-[11px] font-bold">
                <span>VĀSTU ENGINE SPATIAL AUDIT RULE:</span>
                <span className="text-emerald-400">WEIGHT: {selected.spatialScoreWeight}/100</span>
              </div>
              <p className="text-[11px] text-[#9C9183]">
                Evaluated in PostGIS via <code>ST_Azimuth(center_geom, poi_geom)</code>. When a kitchen cooktop or prayer altar is placed in this zone, the audit score automatically factors in directional angular deviation.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

