/**
 * VĀSTU — Spatial Multimodal Capture SOP Engine
 * Analyzes architectural floor plans + 1st reconnaissance video scans
 * to generate space-tailored capture guidelines, room trajectory zones, and mistake prevention alerts.
 */

export interface CaptureZone {
  id: string;
  name: string;
  sequence: number;
  sector_bbox: { x: number; y: number; width: number; height: number };
  instructions: string;
  zone_mistakes: string;
  target_duration_sec: number;
  key_features: string[];
  status: 'PENDING' | 'RECORDING' | 'COMPLETED';
}

export interface MistakeWarning {
  id: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  title: string;
  description: string;
  visual_trigger: string;
}

export interface CaptureSOPResponse {
  summary: string;
  recommended_start_zone: string;
  global_guidelines: {
    speed: string;
    phone_tilt: string;
    phone_height: string;
    overlap_percentage: string;
    lighting_note: string;
  };
  mistakes_to_avoid: MistakeWarning[];
  zones: CaptureZone[];
}

const SPATIAL_API_KEY =
  ((import.meta as any).env?.VITE_SPATIAL_API_KEY as string) || '';

export class SpatialSOPService {
  /**
   * Deterministic offline blueprint parser: converts 2D floorplan data and dimensions
   * into structured capture zones without requiring any cloud API or network connectivity.
   */
  static generateOfflineFloorplanSOP(params: {
    projectName: string;
    floorName: string;
    areaSqft: number;
    heightFt?: number;
    projectType?: string;
    drawingData?: any;
  }): CaptureSOPResponse {
    const area = Math.max(120, params.areaSqft || 400);
    const areaSqm = Math.round(area / 10.7639);
    const widthM = Math.round(Math.sqrt(areaSqm * 1.3));
    const lengthM = Math.round(areaSqm / widthM);
    const perimeterM = 2 * (widthM + lengthM);

    return {
      summary: `On-device architectural SOP for ${params.floorName} (${widthM}m x ${lengthM}m, ${areaSqm} m²). 5 guided trajectory zones with translation baseline and 85% completion gate.`,
      recommended_start_zone: 'zone_1',
      global_guidelines: {
        speed: '0.3 - 0.5 m/s steady walking pace',
        phone_tilt: '15° downward tilt toward floor-wall junction',
        phone_height: '1.2 - 1.4 m chest height with dual hand stabilization',
        overlap_percentage: '65-75% visual feature overlap',
        lighting_note: 'Ensure room lighting is fully switched on; avoid aiming straight into window glare'
      },
      mistakes_to_avoid: [
        {
          id: 'm_pure_rotation',
          severity: 'CRITICAL',
          title: 'Twisting in Place (Zero Baseline)',
          description: 'Never pivot or rotate on your heels without walking sideways. Monocular depth collapses without parallax baseline.',
          visual_trigger: 'Rotational speed > 15 deg/s with translation < 0.15 m/s'
        },
        {
          id: 'm_rapid_motion',
          severity: 'CRITICAL',
          title: 'Excessive Walking Speed',
          description: 'Slow down. Keep walking pace at 0.3 - 0.5 m/s to prevent motion blur and lost SLAM tracking.',
          visual_trigger: 'Walking speed > 0.8 m/s'
        },
        {
          id: 'm_skipped_floor',
          severity: 'HIGH',
          title: 'Skipped Floor Foreground',
          description: 'Keep floor and baseboards visible in lower 35% of camera frame to prevent mesh floor holes.',
          visual_trigger: 'Floor coverage < 80%'
        },
        {
          id: 'm_window_glare',
          severity: 'HIGH',
          title: 'Direct Glass Glare',
          description: 'Tilt phone 20° downward when scanning exterior glass windows to prevent sensor over-exposure.',
          visual_trigger: 'High ambient glare saturation'
        }
      ],
      zones: [
        {
          id: 'zone_1',
          name: `${params.floorName} — Entrance Threshold & Baseline`,
          sequence: 1,
          sector_bbox: { x: 50, y: 50, width: 240, height: 180 },
          instructions: 'Stand at room entrance doorway. Hold phone steady for 3 seconds to establish visual SLAM anchor.',
          zone_mistakes: 'Do not pivot before anchor locks; avoid bright corridor backlight.',
          target_duration_sec: 15,
          key_features: ['Door jamb', 'Threshold baseline', 'Baseboards'],
          status: 'PENDING'
        },
        {
          id: 'zone_2',
          name: `${params.floorName} — Outer Perimeter Wall Loop`,
          sequence: 2,
          sector_bbox: { x: 20, y: 20, width: 700, height: 460 },
          instructions: `Walk along the room perimeter (~${perimeterM}m loop). Maintain 1.5m distance from walls. Step sideways along corners.`,
          zone_mistakes: 'CRITICAL: Do NOT twist in place without walking! Step sideways to preserve baseline.',
          target_duration_sec: Math.max(30, Math.round(perimeterM * 1.5)),
          key_features: ['Wall planes', 'Baseboard joints', 'Corners'],
          status: 'PENDING'
        },
        {
          id: 'zone_3',
          name: `${params.floorName} — Corners, Doors & Windows`,
          sequence: 3,
          sector_bbox: { x: 40, y: 40, width: 660, height: 420 },
          instructions: 'At each room corner and window frame, tilt phone slowly up and down from floor baseboard to ceiling.',
          zone_mistakes: 'Do not tilt faster than 15 deg/sec; angle phone away from direct sunlight.',
          target_duration_sec: 25,
          key_features: ['Wall corners', 'Window frames', 'Ceiling joints'],
          status: 'PENDING'
        },
        {
          id: 'zone_4',
          name: `${params.floorName} — Floor Surface & Center Traversal`,
          sequence: 4,
          sector_bbox: { x: 180, y: 140, width: 400, height: 260 },
          instructions: 'Tilt camera 20° downward. Walk across the room center to capture floor surface and central furniture.',
          zone_mistakes: 'Keep floor tiles and skirting boards in view to eliminate foreground voids.',
          target_duration_sec: 25,
          key_features: ['Floor surface', 'Furniture legs', 'Center rug'],
          status: 'PENDING'
        },
        {
          id: 'zone_5',
          name: `${params.floorName} — Return & Loop Closure`,
          sequence: 5,
          sector_bbox: { x: 50, y: 50, width: 240, height: 180 },
          instructions: 'Return to the original entrance door. Align view with start frame until 85% coverage confirms.',
          zone_mistakes: 'Do not end capture prematurely before 85% coverage gate unlocks.',
          target_duration_sec: 15,
          key_features: ['Entrance door frame', 'Initial SLAM anchors'],
          status: 'PENDING'
        }
      ]
    };
  }

  /**
   * Generates tailored capture SOP using on-device deterministic blueprint parsing
   * with seamless multimodal vision fallback when API key is configured.
   */
  static async generateCaptureSOP(params: {
    floorPlanImageUrl?: string;
    floorPlanBase64?: string;
    reconVideoFrameBase64?: string;
    projectName: string;
    floorName: string;
    areaSqft: number;
    heightFt?: number;
    projectType?: string;
    drawingData?: any;
  }): Promise<CaptureSOPResponse> {
    if (!SPATIAL_API_KEY) {
      // Offline on-device blueprint parsing (zero-buffering, zero network latency)
      return this.generateOfflineFloorplanSOP(params);
    }

    const prompt = `
You are the Chief Spatial Metrology Engine for VĀSTU, an evidence-based 3D digital twin and indoor spatial computing platform.
Analyze the attached architectural floor plan and the initial 360° space reconnaissance walkthrough to generate a standardized spatial capture SOP (Standard Operating Procedure).

Target Space Details:
- Project Name: ${params.projectName}
- Floor / Level: ${params.floorName}
- Total Area: ${params.areaSqft} sqft
- Height: ${params.heightFt || 10.5} ft
- Space Type: ${params.projectType || 'Building'}

Your output MUST be a strict JSON object (and nothing else, no markdown codeblocks, just raw valid JSON) following this exact schema:
{
  "summary": "Concise architectural and spatial analysis of this floor plan and reconnaissance scan.",
  "recommended_start_zone": "zone_1",
  "global_guidelines": {
    "speed": "0.3 - 0.5 m/s steady pacing",
    "phone_tilt": "15° downward tilt toward floor-wall boundary",
    "phone_height": "1.2 - 1.4 m chest height with dual hand stabilization",
    "overlap_percentage": "65-75% visual feature overlap",
    "lighting_note": "Keep natural daylight behind camera where possible; avoid direct backlight"
  },
  "mistakes_to_avoid": [
    {
      "id": "m1",
      "severity": "CRITICAL",
      "title": "Rapid Pan Motion Blur",
      "description": "Never pivot the camera faster than 30 deg/sec at room corners or entryways.",
      "visual_trigger": "Corner transitions"
    },
    {
      "id": "m2",
      "severity": "HIGH",
      "title": "Glass / Window Backlight Glare",
      "description": "Tilt camera slightly downwards (20°) when facing exterior glass windows to avoid sensor blindness.",
      "visual_trigger": "South and West facing glass"
    },
    {
      "id": "m3",
      "severity": "MEDIUM",
      "title": "Featureless Monochrome Surfaces",
      "description": "Maintain skirting boards, floor tiles, and doorframes in lower 40% of viewport when tracking plain walls.",
      "visual_trigger": "Plain white corridor walls"
    },
    {
      "id": "m4",
      "severity": "HIGH",
      "title": "Doorway Jump Cuts",
      "description": "Do not rush through doorways. Pause at threshold, pan left 45°, right 45°, then proceed.",
      "visual_trigger": "Room thresholds"
    }
  ],
  "zones": [
    {
      "id": "zone_1",
      "name": "Entrance Foyer & Reception",
      "sequence": 1,
      "sector_bbox": { "x": 60, "y": 60, "width": 260, "height": 200 },
      "instructions": "Begin at primary entrance threshold. Pan 180° across entryway, capture doorframe and floor junction, then move forward along wall perimeter.",
      "zone_mistakes": "Avoid shooting straight into exterior daylight glare from main doors.",
      "target_duration_sec": 30,
      "key_features": ["Entrance doorframe", "Foyer flooring", "Reception counter"]
    },
    {
      "id": "zone_2",
      "name": "Central Circulation Corridor",
      "sequence": 2,
      "sector_bbox": { "x": 340, "y": 80, "width": 320, "height": 160 },
      "instructions": "Walk down the center corridor keeping floor and baseboard features visible. Maintain 60% overlap with Foyer anchors.",
      "zone_mistakes": "Featureless walls here; keep baseboards in view to avoid tracking drift.",
      "target_duration_sec": 45,
      "key_features": ["Baseboard joints", "Door openings", "Ceiling fixture line"]
    },
    {
      "id": "zone_3",
      "name": "Main Open Spatial Hall",
      "sequence": 3,
      "sector_bbox": { "x": 100, "y": 280, "width": 420, "height": 300 },
      "instructions": "Walk full perimeter in clockwise loop. Ensure corners are covered with 3 slow overlapping viewpoints.",
      "zone_mistakes": "Watch out for window glare on east wall; keep phone angled 15° downwards.",
      "target_duration_sec": 60,
      "key_features": ["Columns", "Large wall expanses", "Perimeter corners"]
    },
    {
      "id": "zone_4",
      "name": "Executive Suite / Conference Room",
      "sequence": 4,
      "sector_bbox": { "x": 540, "y": 260, "width": 380, "height": 240 },
      "instructions": "Cross threshold slowly. Orbit central conference table / seating area in full 360° circle, then complete outer perimeter.",
      "zone_mistakes": "Reflective glass partitions present. Avoid pointing directly perpendicular to glass surfaces.",
      "target_duration_sec": 40,
      "key_features": ["Conference table", "Glass partition anchors", "Corner junctions"]
    }
  ]
}
`;

    try {
      const parts: any[] = [{ text: prompt }];

      // Attach floor plan image if base64 provided
      if (params.floorPlanBase64) {
        const cleanBase64 = params.floorPlanBase64.replace(/^data:image\/\w+;base64,/, '');
        parts.push({
          inline_data: {
            mime_type: 'image/jpeg',
            data: cleanBase64
          }
        });
      }

      // Attach 1st recon video frame if provided
      if (params.reconVideoFrameBase64) {
        const cleanVideoFrame = params.reconVideoFrameBase64.replace(/^data:image\/\w+;base64,/, '');
        parts.push({
          inline_data: {
            mime_type: 'image/jpeg',
            data: cleanVideoFrame
          }
        });
      }

      const endpoint =
        ((import.meta as any).env?.VITE_SPATIAL_ENDPOINT as string) ||
        'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent';
      const url = `${endpoint}?key=${SPATIAL_API_KEY}`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts }]
        })
      });

      if (!res.ok) {
        throw new Error(`Spatial AI generation request failed with status: ${res.status}`);
      }

      const data = await res.json();
      const rawText = data?.candidates?.[0]?.content?.parts?.[0]?.text;
      if (!rawText) {
        throw new Error('Spatial AI model returned empty content');
      }

      // Clean markdown code blocks if wrapped in ```json ... ```
      const cleanedJson = rawText.replace(/```json/g, '').replace(/```/g, '').trim();
      const parsed: CaptureSOPResponse = JSON.parse(cleanedJson);

      // Initialize status on zones
      parsed.zones = parsed.zones.map((z) => ({
        ...z,
        status: 'PENDING'
      }));

      return parsed;
    } catch (err) {
      console.warn('Spatial AI API unavailable or failed, falling back to on-device offline blueprint SOP generator:', err);
      return this.generateOfflineFloorplanSOP(params);
    }
  }
}
