import React, { useRef, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import * as THREE from 'three';
import {
  Box,
  Layers,
  Compass,
  Maximize2,
  Eye,
  RotateCcw,
  Sparkles,
  CheckCircle2,
  Sliders,
  Move
} from 'lucide-react';

export const Showcase3DViewer: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [wireframe, setWireframe] = useState<boolean>(false);
  const [showWalls, setShowWalls] = useState<boolean>(true);
  const [showFurniture, setShowFurniture] = useState<boolean>(true);
  const [showPath, setShowPath] = useState<boolean>(true);
  const [showPois, setShowPois] = useState<boolean>(true);
  const [cameraView, setCameraView] = useState<'iso' | 'top' | 'eye'>('iso');

  // Three.js instances ref
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const wallsGroupRef = useRef<THREE.Group | null>(null);
  const furnitureGroupRef = useRef<THREE.Group | null>(null);
  const pathGroupRef = useRef<THREE.Group | null>(null);
  const poiGroupRef = useRef<THREE.Group | null>(null);
  const materialsRef = useRef<THREE.Material[]>([]);

  // Mouse orbit state
  const isDragging = useRef<boolean>(false);
  const prevMouse = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const spherical = useRef<{ radius: number; theta: number; phi: number }>({
    radius: 12,
    theta: Math.PI / 4,
    phi: Math.PI / 3,
  });

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight || 500;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0e0c0a);
    sceneRef.current = scene;

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    cameraRef.current = camera;
    updateCameraPosition();

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Lights
    const ambientLight = new THREE.AmbientLight(0xfff5e6, 0.7);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xe8c982, 1.2);
    dirLight.position.set(8, 14, 6);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0x736a5e, 0.5);
    fillLight.position.set(-8, 6, -6);
    scene.add(fillLight);

    // 5. Floor with Architectural Grid
    const floorGeo = new THREE.PlaneGeometry(10, 8);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x1a1714,
      roughness: 0.8,
      metalness: 0.2,
    });
    materialsRef.current.push(floorMat);
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    // Architectural Grid Lines
    const grid = new THREE.GridHelper(10, 20, 0xc5a059, 0x3a342d);
    grid.position.y = 0.01;
    scene.add(grid);

    // 6. Walls Group
    const wallsGroup = new THREE.Group();
    wallsGroupRef.current = wallsGroup;
    scene.add(wallsGroup);

    const wallMat = new THREE.MeshStandardMaterial({
      color: 0x2b2219,
      roughness: 0.9,
      metalness: 0.1,
      wireframe: false,
    });
    materialsRef.current.push(wallMat);

    // North Wall with Window opening
    const northWallLeft = new THREE.Mesh(new THREE.BoxGeometry(3.5, 2.8, 0.2), wallMat);
    northWallLeft.position.set(-3.25, 1.4, -4);
    northWallLeft.castShadow = true;
    northWallLeft.receiveShadow = true;
    wallsGroup.add(northWallLeft);

    const northWallRight = new THREE.Mesh(new THREE.BoxGeometry(3.5, 2.8, 0.2), wallMat);
    northWallRight.position.set(3.25, 1.4, -4);
    northWallRight.castShadow = true;
    northWallRight.receiveShadow = true;
    wallsGroup.add(northWallRight);

    const northWallTop = new THREE.Mesh(new THREE.BoxGeometry(3, 0.8, 0.2), wallMat);
    northWallTop.position.set(0, 2.4, -4);
    wallsGroup.add(northWallTop);

    // Window Glass Frame
    const windowMat = new THREE.MeshStandardMaterial({
      color: 0x5a9bc8,
      transparent: true,
      opacity: 0.35,
      metalness: 0.8,
      roughness: 0.1,
    });
    const windowMesh = new THREE.Mesh(new THREE.BoxGeometry(2.9, 1.6, 0.05), windowMat);
    windowMesh.position.set(0, 1.2, -4);
    wallsGroup.add(windowMesh);

    // South Wall with Door cutout
    const southWallLeft = new THREE.Mesh(new THREE.BoxGeometry(4.0, 2.8, 0.2), wallMat);
    southWallLeft.position.set(-3, 1.4, 4);
    wallsGroup.add(southWallLeft);

    const southWallRight = new THREE.Mesh(new THREE.BoxGeometry(4.5, 2.8, 0.2), wallMat);
    southWallRight.position.set(2.75, 1.4, 4);
    wallsGroup.add(southWallRight);

    // West Wall
    const westWall = new THREE.Mesh(new THREE.BoxGeometry(0.2, 2.8, 8), wallMat);
    westWall.position.set(-5, 1.4, 0);
    wallsGroup.add(westWall);

    // East Wall
    const eastWall = new THREE.Mesh(new THREE.BoxGeometry(0.2, 2.8, 8), wallMat);
    eastWall.position.set(5, 1.4, 0);
    wallsGroup.add(eastWall);

    // Interior Partition Wall
    const partition = new THREE.Mesh(new THREE.BoxGeometry(0.15, 2.8, 3.5), wallMat);
    partition.position.set(1.5, 1.4, 0.5);
    wallsGroup.add(partition);

    // 7. Furniture Bounding Boxes Group
    const furnitureGroup = new THREE.Group();
    furnitureGroupRef.current = furnitureGroup;
    scene.add(furnitureGroup);

    const tableMat = new THREE.MeshStandardMaterial({
      color: 0x4a3515,
      roughness: 0.6,
      metalness: 0.3,
    });
    materialsRef.current.push(tableMat);

    // Conference Table
    const tableTop = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.1, 1.2), tableMat);
    tableTop.position.set(-2, 0.75, -1);
    tableTop.castShadow = true;
    furnitureGroup.add(tableTop);

    // Table Bounding Box Wireframe
    const tableBBoxGeo = new THREE.BoxGeometry(2.6, 0.9, 1.4);
    const tableBBoxMat = new THREE.MeshBasicMaterial({
      color: 0xc5a059,
      wireframe: true,
      transparent: true,
      opacity: 0.6,
    });
    materialsRef.current.push(tableBBoxMat);
    const tableBBox = new THREE.Mesh(tableBBoxGeo, tableBBoxMat);
    tableBBox.position.set(-2, 0.45, -1);
    furnitureGroup.add(tableBBox);

    // Reception Desk
    const deskMat = new THREE.MeshStandardMaterial({ color: 0x3a342d, roughness: 0.5 });
    materialsRef.current.push(deskMat);
    const desk = new THREE.Mesh(new THREE.BoxGeometry(1.8, 1.0, 0.8), deskMat);
    desk.position.set(3.2, 0.5, 2.0);
    desk.castShadow = true;
    furnitureGroup.add(desk);

    // Planter
    const plantMat = new THREE.MeshStandardMaterial({ color: 0x2d4a22 });
    materialsRef.current.push(plantMat);
    const plant = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.25, 0.8, 16), plantMat);
    plant.position.set(-4.2, 0.4, 3.2);
    furnitureGroup.add(plant);

    // 8. 3D Navigation Path Line (Glowing Tube & Waypoints)
    const pathGroup = new THREE.Group();
    pathGroupRef.current = pathGroup;
    scene.add(pathGroup);

    // Waypoint curve from door entrance to conference table
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.5, 0.08, 3.8), // Door entry
      new THREE.Vector3(-0.5, 0.08, 1.8),
      new THREE.Vector3(0.5, 0.08, 0.5),
      new THREE.Vector3(-0.5, 0.08, -0.5),
      new THREE.Vector3(-2.0, 0.08, -0.5), // Destination
    ]);

    const tubeGeo = new THREE.TubeGeometry(curve, 32, 0.04, 8, false);
    const tubeMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
    materialsRef.current.push(tubeMat);
    const pathTube = new THREE.Mesh(tubeGeo, tubeMat);
    pathGroup.add(pathTube);

    // Pulsing waypoint rings at waypoints
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x34d399,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.8,
    });
    materialsRef.current.push(ringMat);

    const points = curve.getPoints(4);
    points.forEach((pt) => {
      const ring = new THREE.Mesh(new THREE.RingGeometry(0.12, 0.2, 16), ringMat);
      ring.position.set(pt.x, 0.09, pt.z);
      ring.rotation.x = -Math.PI / 2;
      pathGroup.add(ring);
    });

    // 9. Vāstu Directional POI Markers
    const poiGroup = new THREE.Group();
    poiGroupRef.current = poiGroup;
    scene.add(poiGroup);

    const createPoiPin = (x: number, z: number, labelColor: number) => {
      const pinMat = new THREE.MeshBasicMaterial({ color: labelColor });
      materialsRef.current.push(pinMat);
      const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.15, 16, 16), pinMat);
      sphere.position.set(x, 1.8, z);
      const stemMat = new THREE.MeshBasicMaterial({ color: 0xc5a059, transparent: true, opacity: 0.5 });
      materialsRef.current.push(stemMat);
      const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 1.8), stemMat);
      stem.position.set(x, 0.9, z);
      poiGroup.add(sphere);
      poiGroup.add(stem);
    };

    createPoiPin(-4.0, -3.2, 0x38bdf8); // Ishanya (NE)
    createPoiPin(4.0, -3.2, 0xf97316);  // Agni (SE)
    createPoiPin(4.0, 3.2, 0xa855f7);   // Nairutya (SW)
    createPoiPin(-4.0, 3.2, 0x10b981);  // Vayu (NW)

    // Animation Loop
    let animId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Subtle pulse on waypoints
      ringMat.opacity = 0.5 + Math.sin(elapsedTime * 4) * 0.3;

      renderer.render(scene, camera);
    };
    animate();

    // Mouse Drag Controls
    const handleMouseDown = (e: MouseEvent) => {
      isDragging.current = true;
      prevMouse.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const dx = e.clientX - prevMouse.current.x;
      const dy = e.clientY - prevMouse.current.y;
      prevMouse.current = { x: e.clientX, y: e.clientY };

      spherical.current.theta -= dx * 0.008;
      spherical.current.phi = Math.max(
        0.1,
        Math.min(Math.PI / 2 - 0.05, spherical.current.phi - dy * 0.008)
      );
      updateCameraPosition();
    };

    const handleMouseUp = () => {
      isDragging.current = false;
    };

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      spherical.current.radius = Math.max(
        5,
        Math.min(22, spherical.current.radius + e.deltaY * 0.01)
      );
      updateCameraPosition();
    };

    const domElement = renderer.domElement;
    domElement.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    domElement.addEventListener('wheel', handleWheel, { passive: false });

    // Window Resize
    const handleResize = () => {
      if (!container) return;
      const newW = container.clientWidth;
      const newH = container.clientHeight || 500;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animId);
      domElement.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      domElement.removeEventListener('wheel', handleWheel);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      materialsRef.current.forEach((m) => m.dispose());
    };
  }, []);

  const updateCameraPosition = () => {
    if (!cameraRef.current) return;
    const { radius, theta, phi } = spherical.current;
    cameraRef.current.position.x = radius * Math.sin(phi) * Math.sin(theta);
    cameraRef.current.position.y = radius * Math.cos(phi);
    cameraRef.current.position.z = radius * Math.sin(phi) * Math.cos(theta);
    cameraRef.current.lookAt(0, 1.0, 0);
  };

  const setViewPreset = (view: 'iso' | 'top' | 'eye') => {
    setCameraView(view);
    if (view === 'iso') {
      spherical.current = { radius: 12, theta: Math.PI / 4, phi: Math.PI / 3 };
    } else if (view === 'top') {
      spherical.current = { radius: 13, theta: 0, phi: 0.05 };
    } else if (view === 'eye') {
      spherical.current = { radius: 7, theta: 0.1, phi: Math.PI / 2.2 };
    }
    updateCameraPosition();
  };

  // Wireframe toggle effect
  useEffect(() => {
    materialsRef.current.forEach((m: any) => {
      if (m.wireframe !== undefined && m !== materialsRef.current[3]) {
        // don't toggle bboxes
        m.wireframe = wireframe;
      }
    });
  }, [wireframe]);

  // Visibility toggles
  useEffect(() => {
    if (wallsGroupRef.current) wallsGroupRef.current.visible = showWalls;
  }, [showWalls]);

  useEffect(() => {
    if (furnitureGroupRef.current) furnitureGroupRef.current.visible = showFurniture;
  }, [showFurniture]);

  useEffect(() => {
    if (pathGroupRef.current) pathGroupRef.current.visible = showPath;
  }, [showPath]);

  useEffect(() => {
    if (poiGroupRef.current) poiGroupRef.current.visible = showPois;
  }, [showPois]);

  return (
    <section id="3d-showcase" className="py-24 bg-[#0E0C0A] relative border-t border-[#C5A059]/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-[#1A1714] border border-[#C5A059]/40 text-[#E8C982] text-xs font-mono uppercase tracking-wider">
            <Box className="w-3.5 h-3.5 text-[#C5A059]" />
            <span>Interactive WebGL Three.js Engine</span>
          </div>

          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold text-[#FAF7F0] tracking-tight">
            Live 3D Digital Twin{' '}
            <span className="text-[#E8C982]">Showcase</span>
          </h2>

          <p className="text-[#C4B9AC] text-sm sm:text-base font-light leading-relaxed">
            Test the zero-install 3D spatial viewer directly in your browser. Drag to orbit, scroll to zoom, toggle geometric layers, and inspect the automated barrier-aware 3D navigation path.
          </p>
        </div>

        {/* 3D Canvas Box */}
        <div className="mt-12 rounded-2xl bg-[#141210] border border-[#C5A059]/40 shadow-2xl overflow-hidden relative">
          {/* Top Control Bar */}
          <div className="px-4 py-3 bg-[#0E0C0A] border-b border-[#C5A059]/20 flex flex-wrap items-center justify-between gap-3 text-xs">
            {/* View Presets */}
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-mono uppercase text-[#A6998A] hidden sm:inline">Camera View:</span>
              <button
                onClick={() => setViewPreset('iso')}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
                  cameraView === 'iso'
                    ? 'bg-[#C5A059] text-black font-bold'
                    : 'bg-[#1A1714] text-[#C4B9AC] hover:text-white'
                }`}
              >
                Isometric
              </button>
              <button
                onClick={() => setViewPreset('top')}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
                  cameraView === 'top'
                    ? 'bg-[#C5A059] text-black font-bold'
                    : 'bg-[#1A1714] text-[#C4B9AC] hover:text-white'
                }`}
              >
                Top-Down
              </button>
              <button
                onClick={() => setViewPreset('eye')}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
                  cameraView === 'eye'
                    ? 'bg-[#C5A059] text-black font-bold'
                    : 'bg-[#1A1714] text-[#C4B9AC] hover:text-white'
                }`}
              >
                Eye-Level
              </button>
            </div>

            {/* Layer Toggles */}
            <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
              <button
                onClick={() => setShowWalls(!showWalls)}
                className={`px-2 py-1 rounded border transition-colors ${
                  showWalls
                    ? 'bg-[#1A1714] border-[#C5A059]/60 text-[#E8C982]'
                    : 'bg-transparent border-white/10 text-[#6D5020]'
                }`}
              >
                Walls {showWalls ? '✓' : '✗'}
              </button>

              <button
                onClick={() => setShowFurniture(!showFurniture)}
                className={`px-2 py-1 rounded border transition-colors ${
                  showFurniture
                    ? 'bg-[#1A1714] border-[#C5A059]/60 text-[#E8C982]'
                    : 'bg-transparent border-white/10 text-[#6D5020]'
                }`}
              >
                Obstacles {showFurniture ? '✓' : '✗'}
              </button>

              <button
                onClick={() => setShowPath(!showPath)}
                className={`px-2 py-1 rounded border transition-colors ${
                  showPath
                    ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-400'
                    : 'bg-transparent border-white/10 text-[#6D5020]'
                }`}
              >
                A* NavMesh {showPath ? '✓' : '✗'}
              </button>

              <button
                onClick={() => setShowPois(!showPois)}
                className={`px-2 py-1 rounded border transition-colors ${
                  showPois
                    ? 'bg-[#1A1714] border-[#C5A059]/60 text-[#E8C982]'
                    : 'bg-transparent border-white/10 text-[#6D5020]'
                }`}
              >
                Vāstu POIs {showPois ? '✓' : '✗'}
              </button>

              <button
                onClick={() => setWireframe(!wireframe)}
                className={`px-2 py-1 rounded border transition-colors ${
                  wireframe
                    ? 'bg-[#C5A059] text-black font-bold border-[#C5A059]'
                    : 'bg-transparent border-white/10 text-[#9C9183]'
                }`}
              >
                Wireframe
              </button>
            </div>

            {/* Direct Studio Link */}
            <Link
              to="/viewer"
              className="px-3 py-1 rounded-lg bg-gradient-to-r from-[#C5A059] to-[#9A7B3E] text-black font-bold text-xs flex items-center space-x-1.5 shadow"
            >
              <Maximize2 className="w-3.5 h-3.5" />
              <span>Full Studio</span>
            </Link>
          </div>

          {/* WebGL Rendering Viewport */}
          <div
            ref={containerRef}
            className="w-full h-[500px] cursor-grab active:cursor-grabbing relative select-none"
          />

          {/* Floating Instruction Overlay (Bottom-Left) */}
          <div className="absolute bottom-4 left-4 pointer-events-none p-3 rounded-xl bg-[#0E0C0A]/85 backdrop-blur-md border border-[#C5A059]/30 text-[11px] font-mono text-[#C4B9AC] space-y-1">
            <div className="flex items-center space-x-1.5 text-[#E8C982] font-semibold">
              <Move className="w-3.5 h-3.5 text-[#C5A059]" />
              <span>INTERACTIVE VIEWPORT CONTROLS</span>
            </div>
            <div>• Drag mouse to orbit around the room</div>
            <div>• Scroll wheel to zoom in / out</div>
            <div className="text-emerald-400">• Glowing green spline represents obstacle-free A* route</div>
          </div>

          {/* Floating Vāstu Key (Bottom-Right) */}
          <div className="absolute bottom-4 right-4 pointer-events-none p-3 rounded-xl bg-[#0E0C0A]/85 backdrop-blur-md border border-[#C5A059]/30 text-[11px] font-mono text-[#C4B9AC] space-y-1 hidden sm:block">
            <div className="text-[#E8C982] font-semibold">VĀSTU CARDINAL ANCHORS:</div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-sky-400" />
              <span>NE (Ishanya): Meditation / Light Load</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-orange-500" />
              <span>SE (Agni): Electrical & Fire</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-purple-500" />
              <span>SW (Nairutya): Master Cabin / Heavy Base</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>NW (Vayu): Guest & Dynamic Airflow</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

