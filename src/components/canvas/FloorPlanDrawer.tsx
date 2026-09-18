import React, { useRef, useState, useEffect, useCallback } from 'react';
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
  Type,
  LayoutGrid
} from 'lucide-react';
import { DrawingObject, FloorPlanDrawingData } from '../../types';

interface FloorPlanDrawerProps {
  initialData?: FloorPlanDrawingData;
  onSave: (data: {
    drawing_data: FloorPlanDrawingData;
    canvas_width: number;
    canvas_height: number;
    scale_ratio: number;
    preview_base64: string;
  }) => void;
  onCancel?: () => void;
}

type ToolType = 'select' | 'wall' | 'room' | 'door' | 'window' | 'line' | 'rect';

export const FloorPlanDrawer: React.FC<FloorPlanDrawerProps> = ({
  initialData,
  onSave,
  onCancel,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [activeTool, setActiveTool] = useState<ToolType>('wall');
  const [objects, setObjects] = useState<DrawingObject[]>(initialData?.objects || []);
  const [history, setHistory] = useState<DrawingObject[][]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);
  const [snapToGrid, setSnapToGrid] = useState<boolean>(true);
  const [scaleRatio, setScaleRatio] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Drawing state
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [currentStart, setCurrentStart] = useState<{ x: number; y: number } | null>(null);
  const [currentEnd, setCurrentEnd] = useState<{ x: number; y: number } | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const gridSize = 20;
  const canvasWidth = 1200;
  const canvasHeight = 800;

  // Push history on change
  const pushHistory = useCallback(
    (newObjects: DrawingObject[]) => {
      const updated = history.slice(0, historyIndex + 1);
      updated.push(newObjects);
      setHistory(updated);
      setHistoryIndex(updated.length - 1);
      setObjects(newObjects);
    },
    [history, historyIndex]
  );

  // Initialize history
  useEffect(() => {
    if (history.length === 0) {
      const initial = initialData?.objects || [];
      setHistory([initial]);
      setHistoryIndex(0);
    }
  }, [initialData, history.length]);

  const snap = useCallback(
    (val: number) => {
      if (!snapToGrid) return val;
      return Math.round(val / gridSize) * gridSize;
    },
    [snapToGrid]
  );

  const getCanvasCoords = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - pan.x) / scaleRatio;
    const y = (e.clientY - rect.top - pan.y) / scaleRatio;
    return { x: snap(x), y: snap(y) };
  };

  // Render loop
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(scaleRatio, scaleRatio);

    // 1. Draw Architectural Grid
    if (snapToGrid) {
      ctx.strokeStyle = '#E2D8C6';
      ctx.lineWidth = 0.5;
      for (let x = 0; x <= canvasWidth; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvasHeight);
        ctx.stroke();
      }
      for (let y = 0; y <= canvasHeight; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvasWidth, y);
        ctx.stroke();
      }
    }

    // 2. Draw Objects
    objects.forEach((obj) => {
      ctx.save();
      const isSelected = obj.id === selectedId;

      if (isSelected) {
        ctx.shadowColor = '#8F6834';
        ctx.shadowBlur = 8;
      }

      switch (obj.type) {
        case 'wall':
        case 'line': {
          ctx.strokeStyle = isSelected ? '#8F6834' : obj.strokeColor || '#1F150D';
          ctx.lineWidth = obj.lineWidth || (obj.type === 'wall' ? 8 : 3);
          ctx.lineCap = 'round';
          if (obj.points && obj.points.length >= 2) {
            ctx.beginPath();
            ctx.moveTo(obj.points[0].x, obj.points[0].y);
            ctx.lineTo(obj.points[1].x, obj.points[1].y);
            ctx.stroke();

            // Dimension label
            const dx = obj.points[1].x - obj.points[0].x;
            const dy = obj.points[1].y - obj.points[0].y;
            const distFt = (Math.hypot(dx, dy) / gridSize).toFixed(1);
            const midX = (obj.points[0].x + obj.points[1].x) / 2;
            const midY = (obj.points[0].y + obj.points[1].y) / 2;

            ctx.fillStyle = '#8F6834';
            ctx.font = '10px sans-serif';
            ctx.fillText(`${distFt} ft`, midX + 6, midY - 6);
          }
          break;
        }

        case 'room':
        case 'rect': {
          ctx.fillStyle = isSelected ? 'rgba(143, 104, 52, 0.15)' : obj.fillColor || 'rgba(235, 226, 212, 0.5)';
          ctx.strokeStyle = isSelected ? '#8F6834' : obj.strokeColor || '#5C4D3E';
          ctx.lineWidth = obj.lineWidth || 2;
          const rx = obj.x || 0;
          const ry = obj.y || 0;
          const rw = obj.width || 0;
          const rh = obj.height || 0;

          ctx.fillRect(rx, ry, rw, rh);
          ctx.strokeRect(rx, ry, rw, rh);

          // Room label
          if (obj.label || obj.type === 'room') {
            const wFt = (Math.abs(rw) / gridSize).toFixed(0);
            const hFt = (Math.abs(rh) / gridSize).toFixed(0);
            const area = (Number(wFt) * Number(hFt)).toFixed(0);

            ctx.fillStyle = '#1F150D';
            ctx.font = 'bold 12px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(obj.label || 'Zone / Room', rx + rw / 2, ry + rh / 2 - 6);
            ctx.font = '10px sans-serif';
            ctx.fillStyle = '#7C6652';
            ctx.fillText(`${wFt}' × ${hFt}' (${area} sqft)`, rx + rw / 2, ry + rh / 2 + 10);
            ctx.textAlign = 'left';
          }
          break;
        }

        case 'door': {
          // Door opening with radial swing arc
          ctx.strokeStyle = isSelected ? '#8F6834' : '#8F6834';
          ctx.lineWidth = 3;
          if (obj.points && obj.points.length >= 2) {
            const p1 = obj.points[0];
            const p2 = obj.points[1];
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();

            // Swing arc
            const r = Math.hypot(p2.x - p1.x, p2.y - p1.y);
            ctx.beginPath();
            ctx.setLineDash([3, 3]);
            ctx.arc(p1.x, p1.y, r, 0, Math.PI / 2);
            ctx.stroke();
            ctx.setLineDash([]);
          }
          break;
        }

        case 'window': {
          ctx.strokeStyle = '#3B82F6';
          ctx.lineWidth = 5;
          if (obj.points && obj.points.length >= 2) {
            ctx.beginPath();
            ctx.moveTo(obj.points[0].x, obj.points[0].y);
            ctx.lineTo(obj.points[1].x, obj.points[1].y);
            ctx.stroke();
          }
          break;
        }
      }
      ctx.restore();
    });

    // 3. Draw in-progress preview
    if (isDrawing && currentStart && currentEnd) {
      ctx.save();
      ctx.strokeStyle = '#8F6834';
      ctx.setLineDash([4, 4]);

      if (activeTool === 'wall' || activeTool === 'line') {
        ctx.lineWidth = activeTool === 'wall' ? 8 : 3;
        ctx.beginPath();
        ctx.moveTo(currentStart.x, currentStart.y);
        ctx.lineTo(currentEnd.x, currentEnd.y);
        ctx.stroke();
      } else if (activeTool === 'room' || activeTool === 'rect') {
        ctx.lineWidth = 2;
        ctx.fillStyle = 'rgba(143, 104, 52, 0.1)';
        const rw = currentEnd.x - currentStart.x;
        const rh = currentEnd.y - currentStart.y;
        ctx.fillRect(currentStart.x, currentStart.y, rw, rh);
        ctx.strokeRect(currentStart.x, currentStart.y, rw, rh);
      } else if (activeTool === 'door' || activeTool === 'window') {
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(currentStart.x, currentStart.y);
        ctx.lineTo(currentEnd.x, currentEnd.y);
        ctx.stroke();
      }
      ctx.restore();
    }

    ctx.restore();
  }, [
    objects,
    isDrawing,
    currentStart,
    currentEnd,
    activeTool,
    selectedId,
    snapToGrid,
    scaleRatio,
    pan,
  ]);

  useEffect(() => {
    draw();
  }, [draw]);

  // Mouse handlers
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      // Pan mode
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      return;
    }

    const coords = getCanvasCoords(e);

    if (activeTool === 'select') {
      // Find clicked object
      const found = objects.slice().reverse().find((obj) => {
        if (obj.type === 'rect' || obj.type === 'room') {
          const x = obj.x || 0;
          const y = obj.y || 0;
          const w = obj.width || 0;
          const h = obj.height || 0;
          return (
            coords.x >= Math.min(x, x + w) &&
            coords.x <= Math.max(x, x + w) &&
            coords.y >= Math.min(y, y + h) &&
            coords.y <= Math.max(y, y + h)
          );
        }
        if (obj.points && obj.points.length >= 2) {
          const p1 = obj.points[0];
          const p2 = obj.points[1];
          const dist =
            Math.abs((p2.y - p1.y) * coords.x - (p2.x - p1.x) * coords.y + p2.x * p1.y - p2.y * p1.x) /
            Math.hypot(p2.y - p1.y, p2.x - p1.x);
          return dist < 15;
        }
        return false;
      });

      setSelectedId(found ? found.id : null);
      return;
    }

    setIsDrawing(true);
    setCurrentStart(coords);
    setCurrentEnd(coords);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isPanning) {
      setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
      return;
    }

    if (!isDrawing) return;
    const coords = getCanvasCoords(e);
    setCurrentEnd(coords);
  };

  const handleMouseUp = () => {
    if (isPanning) {
      setIsPanning(false);
      return;
    }

    if (!isDrawing || !currentStart || !currentEnd) {
      setIsDrawing(false);
      return;
    }

    const dx = currentEnd.x - currentStart.x;
    const dy = currentEnd.y - currentStart.y;
    if (Math.hypot(dx, dy) < 5) {
      setIsDrawing(false);
      return;
    }

    const newId = 'obj_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6);
    let newObj: DrawingObject | null = null;

    if (activeTool === 'wall' || activeTool === 'line') {
      newObj = {
        id: newId,
        type: activeTool === 'wall' ? 'wall' : 'line',
        points: [currentStart, currentEnd],
        strokeColor: '#1F150D',
        lineWidth: activeTool === 'wall' ? 8 : 3,
      };
    } else if (activeTool === 'room' || activeTool === 'rect') {
      newObj = {
        id: newId,
        type: activeTool === 'room' ? 'room' : 'rect',
        x: Math.min(currentStart.x, currentEnd.x),
        y: Math.min(currentStart.y, currentEnd.y),
        width: Math.abs(dx),
        height: Math.abs(dy),
        fillColor: 'rgba(235, 226, 212, 0.6)',
        strokeColor: '#5C4D3E',
        lineWidth: 2,
        label: activeTool === 'room' ? 'Zone ' + (objects.filter((o) => o.type === 'room').length + 1) : '',
      };
    } else if (activeTool === 'door') {
      newObj = {
        id: newId,
        type: 'door',
        points: [currentStart, currentEnd],
        strokeColor: '#8F6834',
        lineWidth: 3,
      };
    } else if (activeTool === 'window') {
      newObj = {
        id: newId,
        type: 'window',
        points: [currentStart, currentEnd],
        strokeColor: '#3B82F6',
        lineWidth: 5,
      };
    }

    if (newObj) {
      pushHistory([...objects, newObj]);
    }

    setIsDrawing(false);
    setCurrentStart(null);
    setCurrentEnd(null);
  };

  // Actions
  const handleUndo = () => {
    if (historyIndex > 0) {
      const nextIdx = historyIndex - 1;
      setHistoryIndex(nextIdx);
      setObjects(history[nextIdx]);
      setSelectedId(null);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const nextIdx = historyIndex + 1;
      setHistoryIndex(nextIdx);
      setObjects(history[nextIdx]);
      setSelectedId(null);
    }
  };

  const handleDeleteSelected = () => {
    if (!selectedId) return;
    pushHistory(objects.filter((o) => o.id !== selectedId));
    setSelectedId(null);
  };

  const handleClear = () => {
    if (objects.length === 0) return;
    if (confirm('Are you sure you want to clear this entire floor plan drawing?')) {
      pushHistory([]);
      setSelectedId(null);
    }
  };

  const handleSave = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Generate preview data URL
    const previewBase64 = canvas.toDataURL('image/png');

    onSave({
      drawing_data: { objects, scale_unit: 'FT' },
      canvas_width: canvasWidth,
      canvas_height: canvasHeight,
      scale_ratio: scaleRatio,
      preview_base64: previewBase64,
    });
  };

  return (
    <div className="flex flex-col h-full bg-[#EBE5D8] rounded-2xl border border-[#D1C2A5] overflow-hidden shadow-xl">
      {/* Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 bg-[#FAF7F2] border-b border-[#D1C2A5]">
        {/* Drawing Tools */}
        <div className="flex items-center gap-1.5 p-1 bg-[#EAE2D3] rounded-xl">
          <button
            type="button"
            onClick={() => setActiveTool('select')}
            className={`p-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
              activeTool === 'select'
                ? 'bg-[#FAF7F2] text-[#8F6834] shadow-xs'
                : 'text-[#5C4D3E] hover:text-[#1F150D]'
            }`}
            title="Select & Move (V)"
          >
            <MousePointer className="w-4 h-4" />
            <span>Select</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTool('wall')}
            className={`p-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
              activeTool === 'wall'
                ? 'bg-[#FAF7F2] text-[#8F6834] shadow-xs'
                : 'text-[#5C4D3E] hover:text-[#1F150D]'
            }`}
            title="Wall (W)"
          >
            <Minus className="w-4 h-4 rotate-45" />
            <span>Wall</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTool('room')}
            className={`p-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
              activeTool === 'room'
                ? 'bg-[#FAF7F2] text-[#8F6834] shadow-xs'
                : 'text-[#5C4D3E] hover:text-[#1F150D]'
            }`}
            title="Room / Zone (R)"
          >
            <LayoutGrid className="w-4 h-4" />
            <span>Room / Zone</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTool('door')}
            className={`p-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
              activeTool === 'door'
                ? 'bg-[#FAF7F2] text-[#8F6834] shadow-xs'
                : 'text-[#5C4D3E] hover:text-[#1F150D]'
            }`}
            title="Door (D)"
          >
            <DoorOpen className="w-4 h-4" />
            <span>Door</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTool('rect')}
            className={`p-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
              activeTool === 'rect'
                ? 'bg-[#FAF7F2] text-[#8F6834] shadow-xs'
                : 'text-[#5C4D3E] hover:text-[#1F150D]'
            }`}
            title="Rectangle"
          >
            <Square className="w-4 h-4" />
            <span>Rect</span>
          </button>
        </div>

        {/* History & Zoom Controls */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-[#EAE2D3] p-1 rounded-xl">
            <button
              type="button"
              onClick={handleUndo}
              disabled={historyIndex <= 0}
              className="p-1.5 rounded-lg text-[#5C4D3E] hover:text-[#1F150D] disabled:opacity-30"
              title="Undo"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={handleRedo}
              disabled={historyIndex >= history.length - 1}
              className="p-1.5 rounded-lg text-[#5C4D3E] hover:text-[#1F150D] disabled:opacity-30"
              title="Redo"
            >
              <RotateCw className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-1 bg-[#EAE2D3] p-1 rounded-xl">
            <button
              type="button"
              onClick={() => setScaleRatio((s) => Math.max(0.5, s - 0.15))}
              className="p-1.5 rounded-lg text-[#5C4D3E] hover:text-[#1F150D]"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-xs font-mono px-1.5 text-[#5C4D3E]">
              {Math.round(scaleRatio * 100)}%
            </span>
            <button
              type="button"
              onClick={() => setScaleRatio((s) => Math.min(2.5, s + 0.15))}
              className="p-1.5 rounded-lg text-[#5C4D3E] hover:text-[#1F150D]"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => {
                setScaleRatio(1.0);
                setPan({ x: 0, y: 0 });
              }}
              className="p-1.5 rounded-lg text-[#5C4D3E] hover:text-[#1F150D]"
              title="Reset View"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          <button
            type="button"
            onClick={() => setSnapToGrid(!snapToGrid)}
            className={`p-2 rounded-xl border text-xs font-medium flex items-center gap-1.5 transition-colors ${
              snapToGrid
                ? 'bg-[#FAF3E0] border-[#D9C4A1] text-[#8F6834]'
                : 'bg-[#FAF7F2] border-[#D1C2A5] text-[#5C4D3E]'
            }`}
            title="Snap to 20px (1ft) Grid"
          >
            <Grid className="w-4 h-4" />
            <span>Grid</span>
          </button>

          {selectedId && (
            <button
              type="button"
              onClick={handleDeleteSelected}
              className="p-2 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 rounded-xl text-xs font-medium flex items-center gap-1"
              title="Delete Selected Item"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

          <button
            type="button"
            onClick={handleClear}
            className="p-2 hover:bg-[#EAE2D3] text-[#7C6652] rounded-xl text-xs font-medium"
            title="Clear Canvas"
          >
            Clear
          </button>
        </div>

        {/* Primary Action Buttons */}
        <div className="flex items-center gap-2">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-3 py-2 bg-[#FAF7F2] border border-[#D1C2A5] hover:bg-[#EFE7D8] text-[#5C4D3E] text-xs font-medium rounded-xl transition-colors"
            >
              Cancel
            </button>
          )}
          <button
            type="button"
            onClick={handleSave}
            className="px-4 py-2 bg-[#8F6834] hover:bg-[#755427] text-[#FAF7F2] text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-sm transition-all"
          >
            <Check className="w-4 h-4" />
            <span>Apply Floor Plan</span>
          </button>
        </div>
      </div>

      {/* Interactive Vector Canvas Area */}
      <div className="relative flex-1 overflow-hidden bg-[#FAF7F2] flex items-center justify-center">
        <canvas
          ref={canvasRef}
          width={canvasWidth}
          height={canvasHeight}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          className="border border-[#D9CEBC] shadow-sm cursor-crosshair bg-white"
          style={{
            maxWidth: '100%',
            maxHeight: '100%',
            objectFit: 'contain',
          }}
        />

        {/* Canvas Status & Legend Overlay */}
        <div className="absolute bottom-3 left-3 bg-[#FAF7F2]/90 backdrop-blur-xs border border-[#D1C2A5] rounded-xl px-3 py-1.5 text-[11px] text-[#5C4D3E] flex items-center gap-3 shadow-xs">
          <span>Grid: 1 block = 1 ft (20px)</span>
          <span className="text-[#D1C2A5]">|</span>
          <span>Objects: {objects.length}</span>
          <span className="text-[#D1C2A5]">|</span>
          <span>Alt+Drag to Pan</span>
        </div>
      </div>
    </div>
  );
};
