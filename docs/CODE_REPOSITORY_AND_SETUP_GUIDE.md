# VĀSTU / NAMMA SPACE
## Code Repository & Reconstruction Setup Guide
**Competition:** Techfest IIT Bombay 2026 — Round 1: 3D Reconstruction & Roaming  
**Submission Category:** Online 3D Reconstruction & Free-Roaming  
**Team / Project:** VĀSTU / Namma Space Technologies  
**Document Type:** Deliverable 4 — Code Repository & Setup Instructions Document  
**Date:** November 2026  

---

### 📦 1. Repository Links & Architecture

* **Official GitHub Code Repository:**  
  👉 **`https://github.com/Mayank190405/vastu-space.git`**
* **Active Production Branch:**  
  `codex/p0-capture-video-recovery`
* **Test Dataset Directory:**  
  `test_data/` (contains pre-validated indoor smartphone capture: `sample_indoor_scan.mp4`)
* **Live Web Viewer Demonstration:**  
  `https://vastu.krads.co.in/output`

---

### 💻 2. System Prerequisites

The reconstruction pipeline is written in Python (PyTorch + OpenCV + Open3D), and the viewer is built with TypeScript (React + Three.js + Vite).

* **Operating System:** Linux (Ubuntu 20.04+), macOS (Apple Silicon / Intel), or Windows (WSL2)
* **Python Runtime:** Python 3.9, 3.10, or 3.11
* **Node.js (Optional for Frontend):** Node.js v18+ with `npm`
* **Hardware:** Any modern CPU (GPU optional; Depth Anything V2 Small runs efficiently on CPU)

---

### 🚀 3. Step-by-Step Setup & Model Reconstruction

#### Step 1: Clone the Repository
```bash
git clone -b codex/p0-capture-video-recovery https://github.com/Mayank190405/vastu-space.git
cd vastu-space
```

#### Step 2: Create Virtual Environment & Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install computer vision & reconstruction requirements
pip install -r backend/workers/requirements.txt
```

#### Step 3: Run 3D Model Reconstruction on Sample Data
Run the official VĀSTU reconstruction CLI on the sample video located inside `test_data/`:

```bash
python scripts/reconstruct.py --video test_data/sample_indoor_scan.mp4 --output digital_twin_output --deploy
```

**Pipeline Stages Automatically Executed:**
1. **Signal Quality Audit:** Analyzes sharpness (Laplacian variance), exposure histograms, and duplicates.
2. **Keyframe Selection:** Filters redundant frames by optical flow displacement.
3. **PnP Camera Trajectory:** Solves 3D-2D camera poses using SIFT/ORB with RANSAC.
4. **Depth Anything V2 Metric Inference:** Predicts true metric depth (meters) and confidence maps.
5. **TSDF Volume Integration:** Fuses multi-view RGB-D into a truncated signed distance voxel grid.
6. **Marching Cubes Meshing:** Extracts topological manifold surface mesh (`mesh.ply`).
7. **Photographic Texture Atlas Projection:** Projects camera frames onto UV coordinates to produce `textured_mesh.obj`, `textured_mesh.mtl`, and `texture_atlas.jpg`.
8. **WebGL Asset Packaging:** Generates `model.glb` and standalone `index.html`.

---

### 🌐 4. Viewing the Reconstructed Model Locally

#### Option A: Instant Zero-Install WebGL Viewer
Simply double-click or open `digital_twin_output/index.html` in Chrome, Safari, or Edge.

#### Option B: Launch Full React Spatial Studio
```bash
npm install
npm run dev
# Browse to: http://localhost:5173/output
```

---

### 📂 5. Repository Directory Structure Overview

```
vastu-space/
├── test_data/                      # Required Sample Data Directory
│   ├── sample_indoor_scan.mp4      # 720p 30fps indoor test sequence
│   └── README.md                   # Dataset documentation
├── scripts/
│   ├── reconstruct.py              # Official CLI reconstruction entrypoint
│   └── generate_video_twin.py      # 25-stage TSDF & texture projection engine
├── public/
│   └── output/                     # Production 3D digital twin models & WebGL assets
│       ├── model.glb               # Binary GLTF for WebGL / AR Quick Look
│       ├── textured_mesh.obj       # Wavefront OBJ mesh
│       ├── textured_mesh.mtl       # Material definitions
│       ├── texture_atlas.jpg       # 2048x2048 photographic texture
│       ├── dense_pointcloud.ply    # 437k Stanford PLY point cloud
│       └── index.html              # Standalone Three.js roaming viewer
├── src/
│   ├── pages/website/              # Dedicated Project Website & documentation
│   └── pages/viewer/               # Live Digital Twin viewer & Spatial Studio
├── backend/
│   └── workers/                    # Reconstruction worker orchestrator & ML models
└── docker-compose.prod.yml         # Cloud deployment orchestrator
```

