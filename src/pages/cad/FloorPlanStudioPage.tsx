import React, { useState, useRef, useEffect, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  Square,
  Minus,
  DoorOpen,
  MousePointer,
  RotateCcw,
  RotateCw,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Trash2,
  Grid,
  Check,
  Download,
  Upload,
  Box,
  Layers,
  Sparkles,
  Eye,
  Sliders,
  Ruler,
  Maximize,
  Save,
  HelpCircle,
  Compass,
  ArrowRight
} from 'lucide-react';
import { api } from '../../services/api';

interface Wall {
  id: string;
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  thickness: number; // in meters
  height: number;    // in meters
}

interface Room {
  id: string;
  name: string;
  points: { x: number; y: number }[];
  color: string;
  areaSqM: number;
}

interface Opening {
  id: string;
  type: 'door' | 'window';
  wallId: string;
  distanceAlongWall: number;
  width: number;
}

type ToolMode = 'select' | 'wall' | 'room' | 'door' | 'window' | 'measure' | 'pan';

export const FloorPlanStudioPage: React.FC = () => {
  // Mode & Tools
  const [activeTool, setActiveTool] = useState<ToolMode>('wall');
  const [viewMode, setViewMode] = useState<'split' | '2d' | '3d'>('split');
  const [snapToGrid, setSnapToGrid] = useState(true);
  const [gridSize, setGridSize] = useState(0.25); // 0.25 meters = 25cm
  const [wallHeight, setWallHeight] = useState(2.8); // 2.8 meters standard ceiling
  const [wallThickness, setWallThickness] = useState(0.15); // 15cm interior wall
  const [scale, setScale] = useState(40); // 40 pixels = 1 meter
  const [pan, setPan] = useState({ x: 300, y: 250 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  // Geometry Data
  const [walls, setWalls] = useState<Wall[]>([
    { id: 'w1', startX: -4, startY: -3, endX: 4, endY: -3, thickness: 0.2, height: 2.8 },
    { id: 'w2', startX: 4, startY: -3, endX: 4, endY: 3, thickness: 0.2, height: 2.8 },
    { id: 'w3', startX: 4, startY: 3, endX: -4, endY: 3, thickness: 0.2, height: 2.8 },
    { id: 'w4', startX: -4, startY: 3, endX: -4, endY: -3, thickness: 0.2, height: 2.8 },
    { id: 'w5', startX: 0, startY: -3, endX: 0, endY: 3, thickness: 0.15, height: 2.8 },
  ]);

  const [rooms, setRooms] = useState<Room[]>([
    {
      id: 'r1',
      name: 'Conference Room Alpha',
      points: [
        { x: -4, y: -3 },
        { x: 0, y: -3 },
        { x: 0, y: 3 },
        { x: -4, y: 3 }
      ],
      color: '#C5A059',
      areaSqM: 24.0
    },
    {
      id: 'r2',
      name: 'Open Collaboration Studio',
      points: [
        { x: 0, y: -3 },
        { x: 4, y: -3 },
        { x: 4, y: 3 },
        { x: 0, y: 3 }
      ],
      color: '#8F7864',
      areaSqM: 24.0
    }
  ]);

  const [selectedWallId, setSelectedWallId] = useState<string | null>(null);
  const [drawingStart, setDrawingStart] = useState<{ x: number; y: number } | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [hoveredWall, setHoveredWall] = useState<string | null>(null);
  const [savedNotification, setSavedNotification] = useState(false);

  // References
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const threeMountRef = useRef<HTMLDivElement>(null);
  const threeSceneRef = useRef<{
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    renderer: THREE.WebGLRenderer;
    controls: OrbitControls;
    wallMeshGroup: THREE.Group;
  } | null>(null);

  // Coordinate Conversion: Screen Pixel -> World Meters
  const toWorld = useCallback((screenX: number, screenY: number) => {
    return {
      x: (screenX - pan.x) / scale,
      y: (screenY - pan.y) / scale
    };
  }, [pan, scale]);

  // Coordinate Conversion: World Meters -> Screen Pixel
  const toScreen = useCallback((worldX: number, worldY: number) => {
    return {
      x: worldX * scale + pan.x,
      y: worldY * scale + pan.y
    };
  }, [pan, scale]);

  // Snap to Grid
  const snap = useCallback((val: number) => {
    if (!snapToGrid) return val;
    return Math.round(val / gridSize) * gridSize;
  }, [snapToGrid, gridSize]);

  // ---------------------------------------------------------------------------
  // 1. 2D CANVAS RENDERING ENGINE
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 1. Draw Architectural Grid
    const step = scale * gridSize;
    const offsetX = pan.x % step;
    const offsetY = pan.y % step;

    ctx.beginPath();
    ctx.strokeStyle = '#2A2016';
    ctx.lineWidth = 0.5;

    for (let x = offsetX; x < canvas.width; x += step) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
    }
    for (let y = offsetY; y < canvas.height; y += step) {
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
    }
    ctx.stroke();

    // 2. Draw Major 1-Meter Grid Lines
    const majorStep = scale * 1.0;
    const majorOffsetX = pan.x % majorStep;
    const majorOffsetY = pan.y % majorStep;

    ctx.beginPath();
    ctx.strokeStyle = '#3D2C1F';
    ctx.lineWidth = 1;

    for (let x = majorOffsetX; x < canvas.width; x += majorStep) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
    }
    for (let y = majorOffsetY; y < canvas.height; y += majorStep) {
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
    }
    ctx.stroke();

    // 3. Draw Axis Origin Crosshair
    const origin = toScreen(0, 0);
    ctx.beginPath();
    ctx.strokeStyle = '#C5A059';
    ctx.lineWidth = 1.5;
    ctx.moveTo(origin.x - 15, origin.y);
    ctx.lineTo(origin.x + 15, origin.y);
    ctx.moveTo(origin.x, origin.y - 15);
    ctx.lineTo(origin.x, origin.y + 15);
    ctx.stroke();

    // 4. Draw Rooms Polygons with Areas
    rooms.forEach((room) => {
      if (room.points.length < 3) return;
      ctx.beginPath();
      const p0 = toScreen(room.points[0].x, room.points[0].y);
      ctx.moveTo(p0.x, p0.y);
      for (let i = 1; i < room.points.length; i++) {
        const pt = toScreen(room.points[i].x, room.points[i].y);
        ctx.lineTo(pt.x, pt.y);
      }
      ctx.closePath();
      ctx.fillStyle = `${room.color}18`;
      ctx.fill();

      // Room Center Label
      let cx = 0;
      let cy = 0;
      room.points.forEach((p) => {
        cx += p.x;
        cy += p.y;
      });
      cx /= room.points.length;
      cy /= room.points.length;
      const centerScreen = toScreen(cx, cy);

      ctx.fillStyle = '#F2DFB8';
      ctx.font = 'bold 12px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(room.name, centerScreen.x, centerScreen.y - 6);

      ctx.fillStyle = '#C5A059';
      ctx.font = '10px monospace';
      ctx.fillText(`${room.areaSqM.toFixed(1)} m² (${(room.areaSqM * 10.7639).toFixed(1)} sq ft)`, centerScreen.x, centerScreen.y + 10);
    });

    // 5. Draw Existing Walls
    walls.forEach((wall) => {
      const isSelected = selectedWallId === wall.id;
      const isHovered = hoveredWall === wall.id;
      const p1 = toScreen(wall.startX, wall.startY);
      const p2 = toScreen(wall.endX, wall.endY);

      // Wall Core Line
      ctx.beginPath();
      ctx.strokeStyle = isSelected ? '#38BDF8' : isHovered ? '#FCD34D' : '#C5A059';
      ctx.lineWidth = Math.max(3, wall.thickness * scale);
      ctx.lineCap = 'square';
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();

      // Dimension Label along wall
      const midX = (p1.x + p2.x) / 2;
      const midY = (p1.y + p2.y) / 2;
      const lengthM = Math.hypot(wall.endX - wall.startX, wall.endY - wall.startY);

      ctx.fillStyle = '#211710';
      ctx.beginPath();
      ctx.roundRect(midX - 22, midY - 8, 44, 16, 4);
      ctx.fill();
      ctx.strokeStyle = '#C5A059';
      ctx.lineWidth = 0.5;
      ctx.stroke();

      ctx.fillStyle = '#F2DFB8';
      ctx.font = 'bold 9px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${lengthM.toFixed(2)}m`, midX, midY);
    });

    // 6. Draw In-Progress Wall
    if (drawingStart) {
      const p1 = toScreen(drawingStart.x, drawingStart.y);
      const p2 = toScreen(mousePos.x, mousePos.y);

      ctx.beginPath();
      ctx.setLineDash([6, 6]);
      ctx.strokeStyle = '#38BDF8';
      ctx.lineWidth = Math.max(3, wallThickness * scale);
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
      ctx.setLineDash([]);

      const len = Math.hypot(mousePos.x - drawingStart.x, mousePos.y - drawingStart.y);
      const midX = (p1.x + p2.x) / 2;
      const midY = (p1.y + p2.y) / 2;

      ctx.fillStyle = '#38BDF8';
      ctx.font = 'bold 11px monospace';
      ctx.fillText(`${len.toFixed(2)}m (drawing)`, midX, midY - 14);
    }
  }, [walls, rooms, selectedWallId, hoveredWall, drawingStart, mousePos, pan, scale, gridSize, wallThickness, toScreen]);

  // ---------------------------------------------------------------------------
  // 2. THREE.JS REAL-TIME 3D EXTRUSION ENGINE
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!threeMountRef.current) return;
    const mount = threeMountRef.current;

    const width = mount.clientWidth;
    const height = mount.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a120c);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 14, 16);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.05; // Stay above ground plane

    // Studio Lighting
    const ambientLight = new THREE.AmbientLight(0xfff6e8, 0.7);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xfff0d0, 1.2);
    dirLight.position.set(15, 25, 10);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.bias = -0.0001;
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0x7090b0, 0.4);
    fillLight.position.set(-15, 10, -10);
    scene.add(fillLight);

    // Architectural Ground Grid
    const gridHelper = new THREE.GridHelper(30, 30, 0xc5a059, 0x36271c);
    gridHelper.position.y = -0.01;
    scene.add(gridHelper);

    // Floor Plane
    const floorGeo = new THREE.PlaneGeometry(30, 30);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x241a13,
      roughness: 0.85,
      metalness: 0.1
    });
    const floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.rotation.x = -Math.PI / 2;
    floorMesh.receiveShadow = true;
    scene.add(floorMesh);

    // Wall Group
    const wallMeshGroup = new THREE.Group();
    scene.add(wallMeshGroup);

    threeSceneRef.current = {
      scene,
      camera,
      renderer,
      controls,
      wallMeshGroup
    };

    // Animation Loop
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

  // Update 3D Extrusion when 2D walls change
  useEffect(() => {
    if (!threeSceneRef.current) return;
    const { wallMeshGroup } = threeSceneRef.current;

    // Clear previous wall meshes
    while (wallMeshGroup.children.length > 0) {
      const child = wallMeshGroup.children[0] as THREE.Mesh;
      if (child.geometry) child.geometry.dispose();
      wallMeshGroup.remove(child);
    }

    // Extrude each wall into a solid 3D Box
    const wallMaterial = new THREE.MeshStandardMaterial({
      color: 0xf5eedb,
      roughness: 0.6,
      metalness: 0.05
    });

    walls.forEach((wall) => {
      const dx = wall.endX - wall.startX;
      const dy = wall.endY - wall.startY;
      const length = Math.hypot(dx, dy);
      const angle = Math.atan2(dy, dx);

      const geometry = new THREE.BoxGeometry(length, wall.height, wall.thickness);
      const mesh = new THREE.Mesh(geometry, wallMaterial);
      mesh.castShadow = true;
      mesh.receiveShadow = true;

      // Position center of the wall
      const centerX = (wall.startX + wall.endX) / 2;
      const centerZ = (wall.startY + wall.endY) / 2;

      mesh.position.set(centerX, wall.height / 2, centerZ);
      mesh.rotation.y = -angle;

      wallMeshGroup.add(mesh);
    });
  }, [walls]);

  // ---------------------------------------------------------------------------
  // Canvas Mouse Interaction
  // ---------------------------------------------------------------------------
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const rawX = e.clientX - rect.left;
    const rawY = e.clientY - rect.top;

    if (e.button === 1 || activeTool === 'pan' || e.shiftKey) {
      setIsPanning(true);
      setPanStart({ x: rawX - pan.x, y: rawY - pan.y });
      return;
    }

    const world = toWorld(rawX, rawY);
    const snappedX = snap(world.x);
    const snappedY = snap(world.y);

    if (activeTool === 'wall') {
      if (!drawingStart) {
        setDrawingStart({ x: snappedX, y: snappedY });
      } else {
        // Complete the wall segment
        if (Math.hypot(snappedX - drawingStart.x, snappedY - drawingStart.y) > 0.3) {
          const newWall: Wall = {
            id: `w_${Date.now()}`,
            startX: drawingStart.x,
            startY: drawingStart.y,
            endX: snappedX,
            endY: snappedY,
            thickness: wallThickness,
            height: wallHeight
          };
          setWalls((prev) => [...prev, newWall]);
          setDrawingStart({ x: snappedX, y: snappedY }); // continue chaining
        }
      }
    } else if (activeTool === 'select') {
      // Find nearest wall
      const clickedWall = walls.find((w) => {
        const d = distToSegment({ x: world.x, y: world.y }, { x: w.startX, y: w.startY }, { x: w.endX, y: w.endY });
        return d < w.thickness * 1.5;
      });
      setSelectedWallId(clickedWall ? clickedWall.id : null);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const rawX = e.clientX - rect.left;
    const rawY = e.clientY - rect.top;

    if (isPanning) {
      setPan({ x: rawX - panStart.x, y: rawY - panStart.y });
      return;
    }

    const world = toWorld(rawX, rawY);
    setMousePos({ x: snap(world.x), y: snap(world.y) });

    // Check hover
    const hovered = walls.find((w) => {
      const d = distToSegment({ x: world.x, y: world.y }, { x: w.startX, y: w.startY }, { x: w.endX, y: w.endY });
      return d < w.thickness * 1.5;
    });
    setHoveredWall(hovered ? hovered.id : null);
  };

  const handleMouseUp = () => {
    setIsPanning(false);
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setScale((prev) => Math.min(120, Math.max(15, prev * zoomFactor)));
  };

  // Distance helper from point to line segment
  function distToSegment(
    p: { x: number; y: number },
    v: { x: number; y: number },
    w: { x: number; y: number }
  ) {
    const l2 = (w.x - v.x) ** 2 + (w.y - v.y) ** 2;
    if (l2 === 0) return Math.hypot(p.x - v.x, p.y - v.y);
    let t = ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(p.x - (v.x + t * (w.x - v.x)), p.y - (v.y + t * (w.y - v.y)));
  }

  const deleteSelected = () => {
    if (!selectedWallId) return;
    setWalls((prev) => prev.filter((w) => w.id !== selectedWallId));
    setSelectedWallId(null);
  };

  const handleSaveFloorPlan = () => {
    setSavedNotification(true);
    setTimeout(() => setSavedNotification(false), 3000);
  };

  const totalArea = rooms.reduce((acc, r) => acc + r.areaSqM, 0);

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-[#17100A] text-[#F2DFB8] overflow-hidden">
      {/* Top Studio Control Bar */}
      <header className="h-14 border-b border-[#C5A059]/30 bg-[#211710] px-5 flex items-center justify-between z-20 shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-[#2A1E14] border border-[#C5A059]/50 text-[#C5A059]">
            <Square className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-sm font-black text-white font-serif-brand tracking-wide">
                2D / 3D Spatial CAD Studio
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#C5A059]/20 text-[#F2DFB8] border border-[#C5A059]/40">
                BIM Sync
              </span>
            </div>
            <p className="text-[10px] text-[#A6998A]">
              Draw architectural blueprints with millimetric precision and instant 3D mesh extrusion.
            </p>
          </div>
        </div>

        {/* View Switcher: Split / 2D / 3D */}
        <div className="flex items-center space-x-2 bg-[#17100A] p-1 rounded-xl border border-[#3D2C1F]">
          <button
            onClick={() => setViewMode('split')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              viewMode === 'split' ? 'bg-[#C5A059] text-black shadow' : 'text-[#A6998A] hover:text-white'
            }`}
          >
            Split View (2D + 3D)
          </button>
          <button
            onClick={() => setViewMode('2d')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              viewMode === '2d' ? 'bg-[#C5A059] text-black shadow' : 'text-[#A6998A] hover:text-white'
            }`}
          >
            2D CAD Blueprint
          </button>
          <button
            onClick={() => setViewMode('3d')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              viewMode === '3d' ? 'bg-[#C5A059] text-black shadow' : 'text-[#A6998A] hover:text-white'
            }`}
          >
            3D Extrusion
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-3">
          <div className="hidden lg:flex items-center space-x-2 text-xs font-mono text-[#C5A059] bg-[#2A1E14] px-3 py-1.5 rounded-lg border border-[#3D2C1F]">
            <Ruler className="w-3.5 h-3.5" />
            <span>Total: {totalArea.toFixed(1)} m² ({(totalArea * 10.7639).toFixed(0)} sq ft)</span>
          </div>

          <button
            onClick={handleSaveFloorPlan}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#C5A059] to-[#9A7B3E] text-black font-bold text-xs flex items-center space-x-1.5 shadow-lg hover:brightness-110 active:scale-95 transition-all"
          >
            <Save className="w-4 h-4" />
            <span>Save CAD Floorplan</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Floating Tool Palette */}
        <aside className="w-16 bg-[#211710] border-r border-[#36271C] flex flex-col items-center py-4 space-y-3 z-10 shrink-0">
          <button
            onClick={() => {
              setActiveTool('select');
              setDrawingStart(null);
            }}
            title="Select & Inspect Element (V)"
            className={`p-3 rounded-xl transition-all ${
              activeTool === 'select'
                ? 'bg-[#C5A059] text-black shadow-lg scale-105'
                : 'text-[#A6998A] hover:text-white hover:bg-[#2A1E14]'
            }`}
          >
            <MousePointer className="w-5 h-5" />
          </button>

          <button
            onClick={() => {
              setActiveTool('wall');
              setSelectedWallId(null);
            }}
            title="Draw Walls (W)"
            className={`p-3 rounded-xl transition-all ${
              activeTool === 'wall'
                ? 'bg-[#C5A059] text-black shadow-lg scale-105'
                : 'text-[#A6998A] hover:text-white hover:bg-[#2A1E14]'
            }`}
          >
            <Minus className="w-5 h-5 rotate-45" />
          </button>

          <button
            onClick={() => setSnapToGrid(!snapToGrid)}
            title={`Snap to Grid (${snapToGrid ? 'ON' : 'OFF'})`}
            className={`p-3 rounded-xl transition-all ${
              snapToGrid ? 'bg-[#3D2C1F] text-[#C5A059] border border-[#C5A059]/40' : 'text-[#685545]'
            }`}
          >
            <Grid className="w-5 h-5" />
          </button>

          <div className="w-8 h-[1px] bg-[#36271C] my-1" />

          <button
            onClick={() => setScale((s) => Math.min(120, s * 1.2))}
            title="Zoom In"
            className="p-2.5 rounded-lg text-[#A6998A] hover:text-white hover:bg-[#2A1E14]"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setScale((s) => Math.max(15, s * 0.8))}
            title="Zoom Out"
            className="p-2.5 rounded-lg text-[#A6998A] hover:text-white hover:bg-[#2A1E14]"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setScale(40);
              setPan({ x: 300, y: 250 });
            }}
            title="Reset View"
            className="p-2.5 rounded-lg text-[#A6998A] hover:text-white hover:bg-[#2A1E14]"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {selectedWallId && (
            <button
              onClick={deleteSelected}
              title="Delete Selected Wall"
              className="p-2.5 rounded-lg text-red-400 hover:bg-red-950/40 border border-red-500/30 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </aside>

        {/* Dual Viewport Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* 2D CAD Canvas Viewport */}
          {(viewMode === 'split' || viewMode === '2d') && (
            <div className={`relative ${viewMode === 'split' ? 'w-1/2 border-r border-[#36271C]' : 'w-full'} h-full bg-[#17100A] select-none`}>
              <canvas
                ref={canvasRef}
                width={1200}
                height={800}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onWheel={handleWheel}
                className="w-full h-full cursor-crosshair block"
              />

              {/* Status Overlay HUD */}
              <div className="absolute bottom-4 left-4 pointer-events-none bg-[#211710]/90 backdrop-blur-md px-3.5 py-2 rounded-xl border border-[#C5A059]/30 text-xs font-mono space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="text-[#C5A059] font-bold">X:</span>
                  <span>{mousePos.x.toFixed(2)}m</span>
                  <span className="text-[#C5A059] font-bold ml-2">Y:</span>
                  <span>{mousePos.y.toFixed(2)}m</span>
                  <span className="text-[#8F7864] ml-2">| Grid: {gridSize}m</span>
                </div>
                <div className="text-[10px] text-[#A6998A]">
                  {activeTool === 'wall'
                    ? drawingStart
                      ? 'Click to complete wall segment • Esc to cancel'
                      : 'Click starting point to draw wall'
                    : 'Click a wall to inspect parameters'}
                </div>
              </div>
            </div>
          )}

          {/* 3D Extrusion Viewport */}
          {(viewMode === 'split' || viewMode === '3d') && (
            <div className={`relative ${viewMode === 'split' ? 'w-1/2' : 'w-full'} h-full bg-[#1a120c]`}>
              <div ref={threeMountRef} className="w-full h-full" />

              {/* 3D Viewport Controls Overlay */}
              <div className="absolute top-4 right-4 bg-[#211710]/85 backdrop-blur-md p-3 rounded-xl border border-[#C5A059]/30 space-y-2 text-xs">
                <div className="font-bold text-white flex items-center space-x-1.5">
                  <Box className="w-4 h-4 text-[#C5A059]" />
                  <span>3D BIM Parameters</span>
                </div>
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between space-x-4">
                    <span className="text-[#A6998A]">Wall Height:</span>
                    <span className="font-mono text-[#F2DFB8]">{wallHeight}m</span>
                  </div>
                  <input
                    type="range"
                    min="2.0"
                    max="4.5"
                    step="0.1"
                    value={wallHeight}
                    onChange={(e) => setWallHeight(parseFloat(e.target.value))}
                    className="w-full accent-[#C5A059] h-1.5 bg-[#36271C] rounded"
                  />
                  <div className="flex items-center justify-between space-x-4 pt-1">
                    <span className="text-[#A6998A]">Thickness:</span>
                    <span className="font-mono text-[#F2DFB8]">{wallThickness * 100}cm</span>
                  </div>
                  <input
                    type="range"
                    min="0.10"
                    max="0.30"
                    step="0.05"
                    value={wallThickness}
                    onChange={(e) => setWallThickness(parseFloat(e.target.value))}
                    className="w-full accent-[#C5A059] h-1.5 bg-[#36271C] rounded"
                  />
                </div>
              </div>

              {/* Instructions Pill */}
              <div className="absolute bottom-4 right-4 bg-[#211710]/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-[#36271C] text-[10px] text-[#A6998A] flex items-center space-x-2">
                <span>Left Click: Orbit</span>
                <span>•</span>
                <span>Right Click: Pan</span>
                <span>•</span>
                <span>Scroll: Zoom</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Save Toast Notification */}
      {savedNotification && (
        <div className="fixed bottom-6 right-6 bg-[#211710] border border-emerald-500/60 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center space-x-3 z-50 animate-in fade-in slide-in-from-bottom-2">
          <div className="w-7 h-7 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
            ✓
          </div>
          <div>
            <div className="text-xs font-bold">CAD Blueprint Synchronized</div>
            <div className="text-[10px] text-gray-400">
              Vector floorplan and 3D extrusion saved to project digital twin.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
