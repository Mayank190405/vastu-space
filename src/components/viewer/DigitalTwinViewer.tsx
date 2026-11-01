import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import {
  Maximize2,
  Minimize2,
  RotateCcw,
  Footprints,
  Box,
  Compass,
  AlertTriangle,
  Info,
  CheckCircle2
} from 'lucide-react';
import { SpatialAssetLoader, SceneManifest } from './services/SpatialAssetLoader';
import { CollisionSystem, RoomCollisionData } from './services/CollisionSystem';
import { NavigationSystem } from './services/NavigationSystem';
import { RoomVisibilityManager } from './services/RoomVisibilityManager';
import { FirstPersonController, FirstPersonState } from './controllers/FirstPersonController';
import { IsometricCameraController } from './controllers/IsometricCameraController';
import { ViewerModeSwitcher } from './components/ViewerModeSwitcher';
import { RoomSelector } from './components/RoomSelector';
import { FloorSelector } from './components/FloorSelector';
import { NavigationHUD } from './components/NavigationHUD';

export interface DigitalTwinViewerProps {
  projectId?: string;
  baseAssetPath?: string;
  initialMode?: 'walk' | 'isometric';
  onRoomChange?: (roomId: string) => void;
}

export const DigitalTwinViewer: React.FC<DigitalTwinViewerProps> = ({
  projectId,
  baseAssetPath,
  initialMode = 'walk',
  onRoomChange,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Core Services Refs
  const assetLoaderRef = useRef<SpatialAssetLoader>(new SpatialAssetLoader());
  const collisionSystemRef = useRef<CollisionSystem>(new CollisionSystem(0.35, 1.60));
  const navSystemRef = useRef<NavigationSystem>(new NavigationSystem());
  const visibilityMgrRef = useRef<RoomVisibilityManager>(new RoomVisibilityManager());

  // Controllers Refs
  const fpControllerRef = useRef<FirstPersonController | null>(null);
  const isoControllerRef = useRef<IsometricCameraController | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const roomPolygonsGroupRef = useRef<THREE.Group>(new THREE.Group());
  const userPinMarkerRef = useRef<THREE.Group | null>(null);

  // State
  const [mode, setMode] = useState<'walk' | 'isometric'>(initialMode);
  const [manifest, setManifest] = useState<SceneManifest | null>(null);
  const [selectedRoomId, setSelectedRoomId] = useState<string>('');
  const [selectedFloor, setSelectedFloor] = useState<number>(1);
  const [isCeilingVisible, setIsCeilingVisible] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingProgress, setLoadingProgress] = useState<number>(10);
  const [loadingStatus, setLoadingStatus] = useState<string>('Initializing 3D Spatial Engine...');
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [fpState, setFpState] = useState<FirstPersonState | null>(null);

  // Resolve base path for models
  const basePath = baseAssetPath || (projectId ? `/renders/${projectId}` : '/models');

  // Mode switcher handler
  const handleModeToggle = useCallback(() => {
    setMode((prev) => (prev === 'walk' ? 'isometric' : 'walk'));
  }, []);

  // Initialize Three.js Scene
  useEffect(() => {
    if (!mountRef.current) return;
    const width = mountRef.current.clientWidth || 800;
    const height = mountRef.current.clientHeight || 600;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a); // Slate-900
    sceneRef.current = scene;

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(65, width / height, 0.1, 200);
    camera.position.set(0, 0, 1.60);
    cameraRef.current = camera;

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xfff7ed, 1.2);
    dirLight.position.set(12, 16, 20);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0xdbeafe, 0.5);
    fillLight.position.set(-12, -16, 10);
    scene.add(fillLight);

    // 5. Grid helper at floor
    const gridHelper = new THREE.GridHelper(50, 50, 0xC5A059, 0x334155);
    gridHelper.rotation.x = Math.PI / 2; // Lie flat in XY ground
    scene.add(gridHelper);

    // 6. Controllers
    const collisionSys = collisionSystemRef.current;
    const fpController = new FirstPersonController(
      camera,
      renderer.domElement,
      collisionSys,
      (state) => {
        setFpState(state);
        if (state.activeRoomId && state.activeRoomId !== selectedRoomId) {
          setSelectedRoomId(state.activeRoomId);
          onRoomChange?.(state.activeRoomId);
          visibilityMgrRef.current.updateActiveRoom(state.activeRoomId);
        }
      },
      handleModeToggle
    );
    fpControllerRef.current = fpController;

    const isoController = new IsometricCameraController(camera, renderer.domElement);
    isoControllerRef.current = isoController;

    // Room boundaries outline group
    scene.add(roomPolygonsGroupRef.current);

    // User pin marker in isometric mode
    const pinGroup = new THREE.Group();
    const pinGeo = new THREE.ConeGeometry(0.3, 0.8, 16);
    pinGeo.rotateX(Math.PI);
    const pinMat = new THREE.MeshStandardMaterial({
      color: 0xef4444, // Red pin
      emissive: 0xb91c1c,
      roughness: 0.3
    });
    const pinMesh = new THREE.Mesh(pinGeo, pinMat);
    pinMesh.position.set(0, 0, 0.8);
    pinGroup.add(pinMesh);

    // Pulsing base ring
    const ringGeo = new THREE.RingGeometry(0.2, 0.6, 24);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0xef4444, side: THREE.DoubleSide });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    pinGroup.add(ringMesh);

    scene.add(pinGroup);
    userPinMarkerRef.current = pinGroup;
    pinGroup.visible = false;

    // 7. Render Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      if (mode === 'walk') {
        fpController.update();
      } else {
        isoController.update();
        if (userPinMarkerRef.current) {
          const walkPos = isoController.getSavedWalkingPosition();
          userPinMarkerRef.current.position.set(walkPos.x, walkPos.y, 0.1);
          // Animate pin bobbing
          userPinMarkerRef.current.position.z = 0.1 + Math.sin(performance.now() * 0.004) * 0.15;
        }
      }

      renderer.render(scene, camera);
    };
    animate();

    // 8. Resize Handler
    const handleResize = () => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      fpController.dispose();
      isoController.dispose();
      renderer.dispose();
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
    };
  }, [handleModeToggle, mode]);

  // Load Assets and Initialize Collision/Navmesh
  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setLoadingProgress(20);
    setLoadingStatus('Fetching Facility Spatial Manifest...');

    const loader = assetLoaderRef.current;

    loader
      .loadManifest(basePath)
      .then(async (m) => {
        if (!isMounted) return;
        setManifest(m);
        setSelectedRoomId(m.default_spawn?.room_id || m.rooms[0]?.room_id || '');
        setLoadingProgress(45);
        setLoadingStatus('Configuring Architectural Collision Surfaces...');

        // Load Collision
        const collisionData = await loader.loadCollisionGeometry(basePath, m);
        collisionSystemRef.current.setCollisionData(collisionData);
        setLoadingProgress(65);
        setLoadingStatus('Synthesizing Walkable Navigation Mesh...');

        // Set initial spawn position
        const spawnPos = new THREE.Vector3(
          m.default_spawn.position_3d[0],
          m.default_spawn.position_3d[1],
          m.default_spawn.position_3d[2]
        );
        fpControllerRef.current?.setPosition(spawnPos);

        // Draw Room Polygons & Floating Badges
        drawRoomBoundaries(m.rooms);

        // Load Architectural 3D Mesh
        setLoadingProgress(80);
        setLoadingStatus('Streaming Photorealistic 3D Architecture...');
        const meshGroup = await loader.loadArchitecturalMesh(basePath, (p) => {
          if (isMounted) setLoadingProgress(80 + Math.round(p * 0.18));
        });

        if (sceneRef.current && meshGroup.children.length > 0) {
          sceneRef.current.add(meshGroup);
        }

        setLoadingProgress(100);
        setLoadingStatus('Ready');
      })
      .catch((err) => {
        console.error('Failed to load spatial digital twin:', err);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [basePath]);

  // Draw 2D Room Boundaries & 3D Text Badges in Isometric View
  const drawRoomBoundaries = (rooms: SceneManifest['rooms']) => {
    const group = roomPolygonsGroupRef.current;
    group.clear();

    const colors = [0x38bdf8, 0xa855f7, 0x10b981, 0xf59e0b, 0xec4899];

    rooms.forEach((room, idx) => {
      const poly = room.boundary_polygon_world;
      if (!poly || poly.length < 3) return;

      const color = colors[idx % colors.length];

      // Draw boundary line loop
      const points: THREE.Vector3[] = poly.map(
        (p) => new THREE.Vector3(p[0], p[1], 0.08)
      );
      points.push(points[0]); // close loop

      const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
      const lineMat = new THREE.LineBasicMaterial({
        color: color,
        linewidth: 3,
        transparent: true,
        opacity: 0.95
      });
      const line = new THREE.Line(lineGeo, lineMat);
      line.userData = { roomId: room.room_id };
      group.add(line);

      // Floor polygon plane with subtle tint
      const shape = new THREE.Shape();
      shape.moveTo(poly[0][0], poly[0][1]);
      for (let i = 1; i < poly.length; i++) {
        shape.lineTo(poly[i][0], poly[i][1]);
      }
      shape.closePath();

      const floorGeo = new THREE.ShapeGeometry(shape);
      const floorMat = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.12,
        side: THREE.DoubleSide
      });
      const floorMesh = new THREE.Mesh(floorGeo, floorMat);
      floorMesh.position.z = 0.02;
      group.add(floorMesh);
    });
  };

  // Switch Mode Handler (Walk vs Isometric)
  useEffect(() => {
    if (!fpControllerRef.current || !isoControllerRef.current) return;

    if (mode === 'isometric') {
      fpControllerRef.current.unlock();
      const lastWalkPos = fpControllerRef.current.getPosition();
      isoControllerRef.current.activateIsometricView(new THREE.Vector3(0, 0, 0), lastWalkPos);
      if (userPinMarkerRef.current) userPinMarkerRef.current.visible = true;
      roomPolygonsGroupRef.current.visible = true;
      visibilityMgrRef.current.setMode('isometric');
    } else {
      isoControllerRef.current.deactivate();
      const savedPos = isoControllerRef.current.getSavedWalkingPosition();
      fpControllerRef.current.setPosition(savedPos);
      if (userPinMarkerRef.current) userPinMarkerRef.current.visible = false;
      visibilityMgrRef.current.setMode('walk');
    }
  }, [mode]);

  // Handle Room Selection
  const handleSelectRoom = (roomId: string) => {
    setSelectedRoomId(roomId);
    onRoomChange?.(roomId);

    const room = manifest?.rooms.find((r) => r.room_id === roomId);
    if (!room) return;

    if (mode === 'isometric') {
      const poly = room.boundary_polygon_world;
      const cx = poly.reduce((acc, p) => acc + p[0], 0) / poly.length;
      const cy = poly.reduce((acc, p) => acc + p[1], 0) / poly.length;
      isoControllerRef.current?.focusOnRoom(new THREE.Vector3(cx, cy, 0));
    }
  };

  // Enter Walk Mode at specific Room
  const handleEnterWalkModeAtRoom = (roomId: string) => {
    const spawn = collisionSystemRef.current.getSpawnPositionForRoom(roomId);
    fpControllerRef.current?.setPosition(spawn);
    setSelectedRoomId(roomId);
    setMode('walk');
    setTimeout(() => {
      fpControllerRef.current?.lock();
    }, 150);
  };

  // Toggle Fullscreen
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  };

  const activeRoom = manifest?.rooms.find((r) => r.room_id === selectedRoomId);

  return (
    <div
      ref={containerRef}
      className="relative w-full h-[680px] bg-slate-950 rounded-2xl overflow-hidden shadow-2xl border border-slate-800 select-none"
    >
      {/* 3D Canvas Mount */}
      <div ref={mountRef} className="w-full h-full cursor-crosshair" />

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-md flex flex-col items-center justify-center gap-4 z-50">
          <div className="w-16 h-16 rounded-full border-4 border-[#C5A059]/20 border-t-[#C5A059] animate-spin" />
          <div className="text-center space-y-1.5">
            <div className="text-sm font-bold text-white tracking-wide">{loadingStatus}</div>
            <div className="text-xs text-slate-400">Loading VĀSTU calibrated spatial twin</div>
          </div>
          <div className="w-64 h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#C5A059] transition-all duration-300"
              style={{ width: `${loadingProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Top Floating Controls Bar */}
      <div className="absolute top-4 inset-x-4 flex flex-wrap items-center justify-between gap-3 pointer-events-none z-40">
        <div className="flex flex-wrap items-center gap-2.5 pointer-events-auto">
          {/* Walk / Isometric View Mode Switcher */}
          <ViewerModeSwitcher currentMode={mode} onModeChange={setMode} />

          {/* Room Selector */}
          {manifest && (
            <RoomSelector
              rooms={manifest.rooms}
              selectedRoomId={selectedRoomId}
              onSelectRoom={handleSelectRoom}
              onEnterWalkMode={handleEnterWalkModeAtRoom}
            />
          )}

          {/* Floor & Ceiling Selector */}
          {manifest && (
            <FloorSelector
              floors={manifest.floors}
              selectedFloor={selectedFloor}
              onSelectFloor={setSelectedFloor}
              isCeilingVisible={isCeilingVisible}
              onToggleCeiling={() => {
                const next = visibilityMgrRef.current.toggleCeilingVisibility();
                setIsCeilingVisible(next);
              }}
            />
          )}
        </div>

        {/* Right Action Buttons */}
        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            onClick={() => {
              if (mode === 'walk') {
                const spawn = collisionSystemRef.current.getSpawnPositionForRoom(selectedRoomId);
                fpControllerRef.current?.setPosition(spawn);
              } else {
                isoControllerRef.current?.activateIsometricView(new THREE.Vector3(0, 0, 0));
              }
            }}
            className="p-2.5 rounded-xl bg-slate-900/80 backdrop-blur-md border border-slate-700/80 text-slate-300 hover:text-white transition shadow-lg"
            title="Reset Camera Position"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <button
            onClick={toggleFullscreen}
            className="p-2.5 rounded-xl bg-slate-900/80 backdrop-blur-md border border-slate-700/80 text-slate-300 hover:text-white transition shadow-lg"
            title="Toggle Fullscreen"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* First-Person HUD */}
      <NavigationHUD
        mode={mode}
        state={fpState}
        activeRoomName={activeRoom?.room_name || 'Living Space'}
        onUnlockPointer={() => fpControllerRef.current?.unlock()}
      />

      {/* Isometric Mode Overlay Banner */}
      {mode === 'isometric' && (
        <div className="pointer-events-none absolute bottom-6 inset-x-0 flex justify-center z-30">
          <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700 px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-4 pointer-events-auto">
            <div className="text-xs text-slate-300">
              <span className="font-bold text-white">Isometric Space Overview</span> •{' '}
              {manifest ? `${manifest.room_count} connected rooms • ${manifest.total_area_sqm.toFixed(1)} m² total` : ''}
            </div>
            <button
              onClick={() => handleEnterWalkModeAtRoom(selectedRoomId)}
              className="flex items-center gap-2 px-3.5 py-1.5 bg-[#C5A059] hover:bg-[#b08b47] text-slate-950 font-bold rounded-xl transition text-xs shadow-md"
            >
              <Footprints className="w-3.5 h-3.5" />
              <span>Walk Here</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

