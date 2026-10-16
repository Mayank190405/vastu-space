import React, { useState, useRef, useEffect } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  Camera,
  Play,
  Pause,
  RotateCcw,
  Plus,
  Trash2,
  Share2,
  Download,
  Eye,
  Film,
  Sparkles,
  Volume2,
  Maximize2,
  Clock,
  Compass,
  Sliders,
  Check,
  ChevronRight,
  Presentation
} from 'lucide-react';

interface TourWaypoint {
  id: string;
  name: string;
  position: { x: number; y: number; z: number };
  target: { x: number; y: number; z: number };
  durationSec: number;
  audioNote?: string;
  description: string;
}

export const VirtualTourStudioPage: React.FC = () => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentWaypointIndex, setCurrentWaypointIndex] = useState(0);
  const [tourSpeed, setTourSpeed] = useState<number>(1.0);
  const [playbackProgress, setPlaybackProgress] = useState<number>(0);
  const [presentationMode, setPresentationMode] = useState<boolean>(false);
  const [copiedLink, setCopiedLink] = useState(false);

  // Pre-configured cinematic tour waypoints
  const [waypoints, setWaypoints] = useState<TourWaypoint[]>([
    {
      id: 'wp_1',
      name: 'Grand Entrance & Vestibule',
      position: { x: 0, y: 1.8, z: 12 },
      target: { x: 0, y: 1.5, z: 0 },
      durationSec: 4,
      audioNote: 'Welcome to the executive digital twin showcase.',
      description: 'Main double-height entrance with acoustic ceiling baffles.'
    },
    {
      id: 'wp_2',
      name: 'Central Atrium & Skylight',
      position: { x: -4, y: 3.5, z: 4 },
      target: { x: 0, y: 1.0, z: 0 },
      durationSec: 5,
      audioNote: 'Natural daylight penetration reaches 85% of interior work areas.',
      description: 'Full-spectrum sunlight study area.'
    },
    {
      id: 'wp_3',
      name: 'Collaboration Studio Alpha',
      position: { x: -5, y: 1.7, z: -3 },
      target: { x: -2, y: 1.2, z: -4 },
      durationSec: 4,
      audioNote: 'Modular seating with integrated power raceways.',
      description: 'Acoustic pods configured for 8-person agile scrums.'
    },
    {
      id: 'wp_4',
      name: 'Executive Boardroom Overlook',
      position: { x: 5, y: 2.2, z: -2 },
      target: { x: 2, y: 1.4, z: -1 },
      durationSec: 5,
      audioNote: 'Triple-glazed sound isolation envelope.',
      description: 'Seamless 4K telepresence setup with spatial audio.'
    }
  ]);

  const sceneRef = useRef<{
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    renderer: THREE.WebGLRenderer;
    controls: OrbitControls;
    cameraSpline?: THREE.CatmullRomCurve3;
  } | null>(null);

  // ---------------------------------------------------------------------------
  // Three.js Interactive Tour Scene
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!mountRef.current) return;
    const mount = mountRef.current;
    const width = mount.clientWidth;
    const height = mount.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x17100a);
    scene.fog = new THREE.FogExp2(0x17100a, 0.025);

    const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 1000);
    camera.position.set(waypoints[0].position.x, waypoints[0].position.y, waypoints[0].position.z);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(waypoints[0].target.x, waypoints[0].target.y, waypoints[0].target.z);

    // Warm Architectural Lighting
    const ambientLight = new THREE.AmbientLight(0xffeedd, 0.6);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfff5e0, 1.4);
    sunLight.position.set(12, 20, 15);
    sunLight.castShadow = true;
    scene.add(sunLight);

    // Architectural Ground Grid
    const grid = new THREE.GridHelper(40, 40, 0xc5a059, 0x36271c);
    grid.position.y = -0.01;
    scene.add(grid);

    // Demonstration Architectural Room Geometry
    const roomGroup = new THREE.Group();

    // Floor
    const floorGeo = new THREE.PlaneGeometry(24, 20);
    const floorMat = new THREE.MeshStandardMaterial({ color: 0x241a13, roughness: 0.8 });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    roomGroup.add(floor);

    // Stylized Architectural Walls & Columns
    const wallMat = new THREE.MeshStandardMaterial({ color: 0xe8dfcc, roughness: 0.6 });
    const createWall = (w: number, h: number, d: number, x: number, y: number, z: number) => {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), wallMat);
      mesh.position.set(x, y, z);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      roomGroup.add(mesh);
    };

    createWall(24, 3.5, 0.3, 0, 1.75, -10); // Back wall
    createWall(0.3, 3.5, 20, -12, 1.75, 0); // Left wall
    createWall(0.3, 3.5, 20, 12, 1.75, 0);  // Right wall
    createWall(0.3, 3.5, 8, 0, 1.75, -6);   // Interior partition

    // Visual Columns with gold base
    for (let x = -8; x <= 8; x += 8) {
      for (let z = -6; z <= 6; z += 6) {
        const col = new THREE.Mesh(
          new THREE.CylinderGeometry(0.3, 0.3, 3.5, 16),
          new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.4 })
        );
        col.position.set(x, 1.75, z);
        col.castShadow = true;
        roomGroup.add(col);
      }
    }

    scene.add(roomGroup);

    sceneRef.current = {
      scene,
      camera,
      renderer,
      controls
    };

    let animId: number;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!mount) return;
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  // Jump to selected waypoint
  const jumpToWaypoint = (index: number) => {
    setCurrentWaypointIndex(index);
    if (!sceneRef.current) return;
    const wp = waypoints[index];
    const { camera, controls } = sceneRef.current;

    // Smooth transition
    const startPos = camera.position.clone();
    const endPos = new THREE.Vector3(wp.position.x, wp.position.y, wp.position.z);
    const startTarget = controls.target.clone();
    const endTarget = new THREE.Vector3(wp.target.x, wp.target.y, wp.target.z);

    let progress = 0;
    const duration = 60; // frames
    const step = () => {
      progress += 1;
      const t = progress / duration;
      const ease = t * (2 - t); // ease-out
      camera.position.lerpVectors(startPos, endPos, ease);
      controls.target.lerpVectors(startTarget, endTarget, ease);
      controls.update();

      if (progress < duration) {
        requestAnimationFrame(step);
      }
    };
    step();
  };

  const handleCaptureCurrentView = () => {
    if (!sceneRef.current) return;
    const { camera, controls } = sceneRef.current;

    const newWp: TourWaypoint = {
      id: `wp_${Date.now()}`,
      name: `Waypoint ${waypoints.length + 1}`,
      position: {
        x: parseFloat(camera.position.x.toFixed(2)),
        y: parseFloat(camera.position.y.toFixed(2)),
        z: parseFloat(camera.position.z.toFixed(2))
      },
      target: {
        x: parseFloat(controls.target.x.toFixed(2)),
        y: parseFloat(controls.target.y.toFixed(2)),
        z: parseFloat(controls.target.z.toFixed(2))
      },
      durationSec: 4,
      description: 'Captured custom vantage point.'
    };
    setWaypoints((prev) => [...prev, newWp]);
  };

  const handleCopyTourLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return (
    <div className={`h-[calc(100vh-4rem)] flex flex-col bg-[#17100A] text-[#F2DFB8] overflow-hidden ${
      presentationMode ? 'fixed inset-0 z-50 h-screen' : ''
    }`}>
      {/* Top Header */}
      <header className="h-14 border-b border-[#36271C] bg-[#211710] px-5 flex items-center justify-between z-20 shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-[#2A1E14] border border-[#C5A059]/50 text-[#C5A059]">
            <Film className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-sm font-black text-white font-serif-brand tracking-wide">
                Cinematic Virtual Tour & Guided Presentation Suite
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#C5A059]/20 text-[#F2DFB8] border border-[#C5A059]/40">
                Spline Camera
              </span>
            </div>
            <p className="text-[10px] text-[#A6998A]">
              Record fluid camera flythroughs, attach audio hotspots, and launch client pitch walkthroughs.
            </p>
          </div>
        </div>

        {/* Presentation & Sharing */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setPresentationMode(!presentationMode)}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center space-x-1.5 transition-all ${
              presentationMode
                ? 'bg-amber-400 text-black shadow-lg'
                : 'bg-[#2A1E14] text-[#F2DFB8] border border-[#3D2C1F] hover:border-[#C5A059]'
            }`}
          >
            <Presentation className="w-4 h-4" />
            <span>{presentationMode ? 'Exit Presenter' : 'Presenter Mode'}</span>
          </button>

          <button
            onClick={handleCopyTourLink}
            className="px-3 py-1.5 rounded-xl bg-[#2A1E14] border border-[#3D2C1F] text-[#F2DFB8] hover:border-[#C5A059] text-xs font-bold flex items-center space-x-1.5 transition-colors"
          >
            {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5 text-[#C5A059]" />}
            <span>{copiedLink ? 'Link Copied' : 'Share Tour'}</span>
          </button>
        </div>
      </header>

      {/* Main Studio Viewport */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* 3D Scene Viewport */}
        <div className="flex-1 relative bg-[#17100A]">
          <div ref={mountRef} className="w-full h-full" />

          {/* Active Waypoint HUD Banner */}
          <div className="absolute top-5 left-6 max-w-md bg-[#211710]/90 backdrop-blur-md p-4 rounded-2xl border border-[#C5A059]/40 shadow-2xl space-y-1.5 animate-in fade-in slide-in-from-top-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-[#C5A059] uppercase tracking-wider font-bold">
                WAYPOINT {currentWaypointIndex + 1} OF {waypoints.length}
              </span>
              <Volume2 className="w-4 h-4 text-[#C5A059]" />
            </div>
            <h2 className="text-base font-black text-white font-serif-brand">
              {waypoints[currentWaypointIndex].name}
            </h2>
            <p className="text-xs text-[#E3DACA] leading-relaxed">
              {waypoints[currentWaypointIndex].description}
            </p>
            {waypoints[currentWaypointIndex].audioNote && (
              <div className="pt-1 text-[11px] text-[#C5A059] flex items-center space-x-1.5 font-medium italic">
                <span>"{waypoints[currentWaypointIndex].audioNote}"</span>
              </div>
            )}
          </div>

          {/* Bottom Scrub Bar & Flight Controls */}
          <div className="absolute bottom-6 inset-x-6 max-w-2xl mx-auto bg-[#211710]/90 backdrop-blur-md p-3.5 rounded-2xl border border-[#C5A059]/40 shadow-2xl flex items-center justify-between space-x-4">
            <button
              onClick={() => {
                const nextIdx = (currentWaypointIndex + 1) % waypoints.length;
                jumpToWaypoint(nextIdx);
              }}
              className="p-3 rounded-xl bg-gradient-to-r from-[#C5A059] to-[#9A7B3E] text-black shadow-lg hover:brightness-110 active:scale-95 transition-all shrink-0"
            >
              <Play className="w-4 h-4 fill-current" />
            </button>

            {/* Waypoint Pills */}
            <div className="flex-1 flex items-center space-x-2 overflow-x-auto py-1">
              {waypoints.map((wp, idx) => (
                <button
                  key={wp.id}
                  onClick={() => jumpToWaypoint(idx)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                    idx === currentWaypointIndex
                      ? 'bg-[#C5A059] text-black shadow'
                      : 'bg-[#17100A] text-[#A6998A] hover:text-white border border-[#36271C]'
                  }`}
                >
                  {idx + 1}. {wp.name.split(' ')[0]}
                </button>
              ))}
            </div>

            {/* Speed Multiplier */}
            <div className="flex items-center space-x-1 bg-[#17100A] px-2 py-1 rounded-lg border border-[#36271C] text-[10px] font-bold text-[#C5A059] shrink-0">
              <button
                onClick={() => setTourSpeed((s) => (s === 1.0 ? 1.5 : s === 1.5 ? 2.0 : 1.0))}
                className="hover:text-white transition-colors"
              >
                {tourSpeed}x Speed
              </button>
            </div>
          </div>
        </div>

        {/* Right Waypoints Inspector Sidebar (Hidden in Presenter Mode) */}
        {!presentationMode && (
          <aside className="w-80 bg-[#211710] border-l border-[#36271C] flex flex-col p-4 space-y-4 z-10 shrink-0 overflow-y-auto">
            <div className="flex items-center justify-between border-b border-[#36271C] pb-3">
              <span className="text-xs font-black uppercase text-[#8F7864] tracking-wider">
                Tour Timeline ({waypoints.length} Waypoints)
              </span>
              <button
                onClick={handleCaptureCurrentView}
                title="Capture Current Camera Angle"
                className="px-2.5 py-1 rounded-lg bg-[#2A1E14] border border-[#C5A059]/50 text-[#F2DFB8] text-xs font-bold flex items-center space-x-1 hover:bg-[#3D2C1F] transition-colors"
              >
                <Plus className="w-3.5 h-3.5 text-[#C5A059]" />
                <span>Add Angle</span>
              </button>
            </div>

            {/* Waypoints List */}
            <div className="space-y-2.5">
              {waypoints.map((wp, idx) => {
                const isCurrent = idx === currentWaypointIndex;
                return (
                  <div
                    key={wp.id}
                    onClick={() => jumpToWaypoint(idx)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all ${
                      isCurrent
                        ? 'bg-[#2A1E14] border-[#C5A059] shadow-lg shadow-[#C5A059]/10'
                        : 'bg-[#17100A] border-[#36271C] hover:border-[#C5A059]/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">
                        {idx + 1}. {wp.name}
                      </span>
                      <span className="text-[10px] font-mono text-[#C5A059]">{wp.durationSec}s</span>
                    </div>
                    <p className="text-[10px] text-[#A6998A] mt-1 line-clamp-2">
                      {wp.description}
                    </p>
                    <div className="mt-2 text-[9px] font-mono text-[#8F7864] flex items-center justify-between border-t border-[#261B11] pt-1">
                      <span>XYZ: {wp.position.x}, {wp.position.y}, {wp.position.z}</span>
                      {waypoints.length > 2 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setWaypoints((prev) => prev.filter((w) => w.id !== wp.id));
                          }}
                          className="text-red-400 hover:text-red-300"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
};
