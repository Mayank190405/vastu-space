# VĀSTU / NAMMA SPACE
## Round 1 Submission Companion Document
**Competition:** Techfest IIT Bombay 2026 — Round 1: 3D Reconstruction & Roaming  
**Submission Category:** Online 3D Reconstruction & Free-Roaming  
**Team / Project:** VĀSTU / Namma Space Technologies  
**Deliverables Covered:** Deliverable 2 (Web Viewer Link & Controls) & Deliverable 4 (Code Repository & Setup)  
**Date:** November 2026  

---

### 🌐 1. Public Working Links (Zero-Install 3D Web Viewer)

The VĀSTU Web Viewer has been deployed to cloud infrastructure and is accessible 24/7 without login or software installation:

* **Primary 3D Free-Roaming Viewer:**  
  👉 **`https://vastu.krads.co.in/output`**  
  *(Interactive 3D digital twin of a real bedroom. Fullscreen roaming, real-time FPS HUD, and visual layer controls).*

* **Standalone Pure WebGL Canvas (Zero-Overhead):**  
  👉 **`https://vastu.krads.co.in/output/index.html`**  
  *(Ultra-fast Three.js canvas pre-loaded with metric mesh, wireframe cage, and 437k point cloud splats).*

* **Interactive 3D Spatial Studio (Floor Plans & Analytics):**  
  👉 **`https://vastu.krads.co.in/viewer`**  
  *(Metric measurements, architectural cross-sections, compass orientation, and lighting simulation).*

* **Official Project Overview Portal:**  
  👉 **`https://vastu.krads.co.in/`**  
  *(Mathematical architecture, interactive SOP simulator, and Dadar West studio pilot benchmarks).*

---

### 💻 2. System Compatibility & Access Credentials

| Requirement | Specification | Access Credentials |
| :--- | :--- | :--- |
| **Supported Browsers** | Google Chrome (v100+), Apple Safari (v15+), Microsoft Edge (v100+), Firefox (v100+) | **ZERO LOGIN REQUIRED** |
| **Operating Systems** | Windows 10/11, macOS, Linux, iOS 15+, Android 10+ | Evaluators can freely click and inspect |
| **Graphics Hardware** | WebGL 2.0 compliant GPU (Apple Silicon, NVIDIA, AMD, or Intel Iris) | No account or credentials required |
| **Client Installation** | **ZERO INSTALL** (Runs 100% in browser) | Pure web delivery |

---

### 🎮 3. Free-Roaming Navigation & Control Guide

| Platform | Control / Input | Function |
| :--- | :--- | :--- |
| **Desktop** | `W` `A` `S` `D` or Arrow Keys | Move forward, left, backward, right (walk mode) |
| **Desktop** | **Left Mouse Click + Drag** | Look around (first-person 360° camera orientation) |
| **Desktop** | **Right Mouse Drag / Scroll Wheel** | Pan camera position / Zoom in and out |
| **Desktop** | `Space` / `Shift` | Ascend / Descend camera height |
| **Mobile / Touch** | **Single Finger Drag** | Orbit / Look around scene |
| **Mobile / Touch** | **Two-Finger Pinch / Drag** | Zoom camera in/out / Pan translation |
| **Display Modes** | HUD Buttons (`Mesh`, `Wireframe`, `Points`) | Toggle between textured surface, wireframe, or splats |

---

### 📦 4. Code Repository Information

* **Official GitHub Code Repository:**  
  👉 **`https://github.com/Mayank190405/vastu-space.git`**
* **Active Production Branch:**  
  `codex/p0-capture-video-recovery`
* **Test Dataset Directory:**  
  `test_data/` (contains pre-validated indoor smartphone capture: `sample_indoor_scan.mp4`)

---

### 🚀 5. Quick Setup & Local Model Reconstruction

Follow these 3 steps to set up the environment and reconstruct the 3D model using the sample data:

#### Step 1: Clone the Repository
```bash
git clone -b codex/p0-capture-video-recovery https://github.com/Mayank190405/vastu-space.git
cd vastu-space
```

#### Step 2: Set up Python Environment & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r backend/workers/requirements.txt
```

#### Step 3: Run Reconstruction on Sample Data
```bash
python scripts/reconstruct.py --video test_data/sample_indoor_scan.mp4 --output digital_twin_output --deploy
```

**Viewing the Local Output:**
* **Direct Standalone WebGL:** Double-click `digital_twin_output/index.html` in any browser.
* **Full Local Studio:** Run `npm install && npm run dev` and navigate to `http://localhost:5173/output`.

---

### 📁 6. Sample Data in Test Directory (`test_data/`)

The repository includes `test_data/sample_indoor_scan.mp4` (2.8 MB), a pre-validated 720p 30fps indoor spatial scan captured according to the VĀSTU standard operating procedure (smooth dolly translation, >75% visual overlap, zero motion blur, verified lighting). Running the CLI generates the complete 3D textured mesh, point cloud, and standalone WebGL viewer in `digital_twin_output/`.

---

### 📥 7. Direct 3D Model Asset Downloads (For External CAD / Blender Verification)

* **Complete 3D Digital Twin (GLB):** [`https://vastu.krads.co.in/output/model.glb`](https://vastu.krads.co.in/output/model.glb) (3.16 MB)
* **Photographic OBJ Mesh:** [`https://vastu.krads.co.in/output/textured_mesh.obj`](https://vastu.krads.co.in/output/textured_mesh.obj) (7.6 MB, 256k triangles)
* **High-Res Texture Atlas:** [`https://vastu.krads.co.in/output/texture_atlas.jpg`](https://vastu.krads.co.in/output/texture_atlas.jpg) (2048x2048)
* **Dense Point Cloud (PLY):** [`https://vastu.krads.co.in/output/dense_pointcloud.ply`](https://vastu.krads.co.in/output/dense_pointcloud.ply) (24 MB, 437k points)
* **Quality Summary:** [`https://vastu.krads.co.in/output/digital_twin_summary.json`](https://vastu.krads.co.in/output/digital_twin_summary.json)

