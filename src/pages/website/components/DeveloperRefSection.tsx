import React, { useState } from 'react';
import {
  Code2,
  Copy,
  Check,
  Terminal,
  Server,
  Database,
  Container,
  Layers,
  ArrowRight,
  ExternalLink
} from 'lucide-react';

export const DeveloperRefSection: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'cli' | 'api' | 'sql' | 'docker'>('cli');
  const [copied, setCopied] = useState<boolean>(false);

  const snippets = {
    cli: `# 1. Install pure algorithmic engine dependencies
pip install -r requirements-api.txt

# 2. Run automated end-to-end 9-stage photogrammetric reconstruction
python scripts/reconstruct.py \\
    --video /captures/dadar_flat_sweep.mp4 \\
    --output digital_twin_output \\
    --tolerance-cm 2.5 \\
    --deploy

# Output:
# [✓] Keyframes extracted: 284 sharp frames (Laplacian var: 184.2 ≥ 120.0)
# [✓] PyCOLMAP Sparse Reconstruction: Reprojection error: 0.84 px
# [✓] Screened Poisson Meshing: Watertight mesh with 342,100 faces
# [✓] Visibility Texture Baked: 4K atlas generated (model.glb)
# [✓] Manhattan CAD Plan: Exported dadar_flat_sweep.dxf
# [✓] Deployed to Three.js viewer: http://localhost:5173/viewer`,

    api: `# 1. Resumable Chunk Ingestion Gateway (FastAPI :8000)
curl -X POST "http://localhost:8000/api/v1/captures/upload/chunk" \\
    -H "Authorization: Bearer \${VASTU_JWT_TOKEN}" \\
    -F "chunk_index=0" \\
    -F "total_chunks=14" \\
    -F "sha256_checksum=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" \\
    -F "file=@capture_chunk_00.bin"

# 2. Query 3D Obstacle-Aware NavMesh Route (PostGIS SRID:0)
curl -X GET "http://localhost:8000/api/v1/navigation/route?\\
start_x=-0.5&start_y=0.0&start_z=3.8&\\
goal_x=-2.0&goal_y=0.0&goal_z=-0.5&\\
require_ada_compliance=true" \\
    -H "Accept: application/json"

# Response:
# {
#   "distance_meters": 5.42,
#   "ada_compliant": true,
#   "max_slope_degrees": 2.10,
#   "waypoints": [[-0.5, 0.08, 3.8], [0.5, 0.08, 0.5], [-2.0, 0.08, -0.5]],
#   "instructions": ["Walk straight 3.2m", "Turn slightly left around conference table"]
# }`,

    sql: `-- PostgreSQL 16 + PostGIS 3.4 Spatial Indexing
-- Coordinates stored in local metric Cartesian space (SRID 0, 1 unit = 1.000 meter)

-- Query: Find all architectural POIs within 5.0m wheelchair reach of coordinates (1.2, 0.0, -3.8)
SELECT 
    p.id,
    p.name,
    p.category,
    ROUND(ST_3DDistance(p.geom_pointz, ST_SetSRID(ST_MakePoint(1.2, 0.0, -3.8), 0))::numeric, 2) AS distance_meters,
    ST_AsGeoJSON(p.geom_pointz) AS geojson
FROM spatial_pois p
WHERE p.model_id = '5425ee6c-460a-4508-8e84-918cbcc57f42'
  AND ST_3DDWithin(p.geom_pointz, ST_SetSRID(ST_MakePoint(1.2, 0.0, -3.8), 0), 5.0)
ORDER BY p.geom_pointz <-> ST_SetSRID(ST_MakePoint(1.2, 0.0, -3.8), 0);`,

    docker: `# Spin up complete production microservices cluster:
# - PostgreSQL 16 + PostGIS 3.4 (Port 5432)
# - Redis 7.2 Message Broker (Port 6379)
# - MinIO S3 Object Storage (Port 9000 / 9001)
# - FastAPI Python Control Plane (Port 8000)
# - Go High-Throughput REST Engine (Port 8080)
# - Celery Distributed GPU Worker Nodes
# - Nginx WebGL Frontend Gateway (Port 80 / 443)

docker-compose -f docker-compose.prod.yml up -d --build

# Verify cluster health status
docker-compose -f docker-compose.prod.yml ps`,
  };

  const copySnippet = () => {
    navigator.clipboard.writeText(snippets[activeTab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="developer" className="py-24 bg-[#0E0C0A] relative border-t border-[#C5A059]/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-[#1A1714] border border-[#C5A059]/40 text-[#E8C982] text-xs font-mono uppercase tracking-wider">
            <Code2 className="w-3.5 h-3.5 text-[#C5A059]" />
            <span>Developer & Engineering Specifications</span>
          </div>

          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold text-[#FAF7F0] tracking-tight">
            Microservice Topology &{' '}
            <span className="text-[#E8C982]">Developer APIs</span>
          </h2>

          <p className="text-[#C4B9AC] text-sm sm:text-base font-light leading-relaxed">
            VĀSTU is designed for seamless headless integration into architectural CAD packages, facility management systems, and enterprise cloud infrastructure.
          </p>
        </div>

        {/* Microservice Architecture Diagram Grid */}
        <div className="mt-14 p-6 sm:p-8 rounded-2xl bg-[#141210] border border-[#C5A059]/30 shadow-2xl space-y-6">
          <div className="flex items-center justify-between border-b border-[#C5A059]/20 pb-4">
            <div className="flex items-center space-x-2">
              <Server className="w-5 h-5 text-[#C5A059]" />
              <h3 className="font-serif font-bold text-lg text-[#FAF7F0]">
                Distributed System Architecture
              </h3>
            </div>
            <span className="font-mono text-xs text-[#E8C982]">DECOUPLED SERVICE TOPOLOGY</span>
          </div>

          {/* Architecture Flowchart Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-mono">
            {/* Box 1: Edge Capture */}
            <div className="p-4 rounded-xl bg-[#0E0C0A] border border-[#C5A059]/20 space-y-2">
              <div className="text-[10px] text-[#A6998A] uppercase font-bold">1. Edge Mobile Client</div>
              <div className="text-white font-bold">iOS Swift / Android AR</div>
              <p className="text-[11px] text-[#9C9183] font-sans">
                Real-time Laplacian blur filter (≥120), visual-inertial odometry, 5MB chunked resumable upload.
              </p>
            </div>

            {/* Box 2: API Gateway */}
            <div className="p-4 rounded-xl bg-[#0E0C0A] border border-[#C5A059]/20 space-y-2">
              <div className="text-[10px] text-[#A6998A] uppercase font-bold">2. Ingestion & Control</div>
              <div className="text-[#E8C982] font-bold">FastAPI + Go Gateway</div>
              <p className="text-[11px] text-[#9C9183] font-sans">
                SHA-256 stream integrity, JWT auth, Celery task dispatching, MinIO S3 object storage.
              </p>
            </div>

            {/* Box 3: Distributed Workers */}
            <div className="p-4 rounded-xl bg-[#0E0C0A] border border-[#C5A059]/20 space-y-2">
              <div className="text-[10px] text-[#A6998A] uppercase font-bold">3. 9-Stage Workers</div>
              <div className="text-emerald-400 font-bold">PyCOLMAP / Open3D / CUDA</div>
              <p className="text-[11px] text-[#9C9183] font-sans">
                Structure-from-Motion, PatchMatch MVS, Screened Poisson meshing, 4K photometric UV atlas.
              </p>
            </div>

            {/* Box 4: Storage & Delivery */}
            <div className="p-4 rounded-xl bg-[#0E0C0A] border border-[#C5A059]/20 space-y-2">
              <div className="text-[10px] text-[#A6998A] uppercase font-bold">4. Spatial Database & Web</div>
              <div className="text-sky-400 font-bold">PostGIS 3.4 + Three.js</div>
              <p className="text-[11px] text-[#9C9183] font-sans">
                Cartesian SRID:0 indexing, 3D A* obstacle router, zero-install 60 FPS WebGL viewer & WebAR.
              </p>
            </div>
          </div>
        </div>

        {/* Code Snippets Section */}
        <div className="mt-8 rounded-2xl bg-[#141210] border border-[#C5A059]/40 overflow-hidden shadow-2xl">
          {/* Tabs */}
          <div className="px-4 py-3 bg-[#0E0C0A] border-b border-[#C5A059]/20 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => setActiveTab('cli')}
                className={`px-3 py-1.5 rounded-lg font-mono font-medium transition-colors ${
                  activeTab === 'cli'
                    ? 'bg-[#C5A059] text-black font-bold'
                    : 'bg-[#1A1714] text-[#C4B9AC] hover:text-white'
                }`}
              >
                Python CLI Script
              </button>

              <button
                onClick={() => setActiveTab('api')}
                className={`px-3 py-1.5 rounded-lg font-mono font-medium transition-colors ${
                  activeTab === 'api'
                    ? 'bg-[#C5A059] text-black font-bold'
                    : 'bg-[#1A1714] text-[#C4B9AC] hover:text-white'
                }`}
              >
                FastAPI REST API
              </button>

              <button
                onClick={() => setActiveTab('sql')}
                className={`px-3 py-1.5 rounded-lg font-mono font-medium transition-colors ${
                  activeTab === 'sql'
                    ? 'bg-[#C5A059] text-black font-bold'
                    : 'bg-[#1A1714] text-[#C4B9AC] hover:text-white'
                }`}
              >
                PostGIS 3.4 Spatial SQL
              </button>

              <button
                onClick={() => setActiveTab('docker')}
                className={`px-3 py-1.5 rounded-lg font-mono font-medium transition-colors ${
                  activeTab === 'docker'
                    ? 'bg-[#C5A059] text-black font-bold'
                    : 'bg-[#1A1714] text-[#C4B9AC] hover:text-white'
                }`}
              >
                Docker Compose Cluster
              </button>
            </div>

            <button
              onClick={copySnippet}
              className="px-3 py-1.5 rounded-lg border border-[#C5A059]/30 bg-[#1A1714] hover:bg-[#26221D] text-[#E8C982] text-xs font-mono font-semibold flex items-center space-x-1.5 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied to Clipboard' : 'Copy Snippet'}</span>
            </button>
          </div>

          {/* Pre Code Box */}
          <div className="p-6 bg-[#080706] overflow-x-auto">
            <pre className="font-mono text-xs text-[#C4B9AC] leading-relaxed">
              <code>{snippets[activeTab]}</code>
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
};

