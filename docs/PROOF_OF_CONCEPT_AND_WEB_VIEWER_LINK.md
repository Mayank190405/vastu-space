# VĀSTU / NAMMA SPACE
## Proof of Concept & Interactive 3D Web Viewer Link
**Competition:** Techfest IIT Bombay 2026 — Round 1: 3D Reconstruction & Roaming  
**Submission Category:** Online 3D Reconstruction & Free-Roaming  
**Team / Project:** VĀSTU / Namma Space Technologies  
**Document Type:** Deliverable 2 — Proof of Concept & Working Web Viewer Access Document  
**Date:** November 2026  

---

### 🌐 1. Live Public Working Links

The VĀSTU spatial computing platform has been deployed to production cloud infrastructure and is accessible 24/7 without software installation:

* **Primary Free-Roaming 3D Digital Twin Viewer:**  
  👉 **`https://vastu.krads.co.in/output`**  
  *(Embedded WebGL roaming viewer pre-loaded with the reconstructed bedroom digital twin, real-time FPS counter, HUD, and fullscreen roaming).*

* **Direct Standalone WebGL Viewer (Zero-Overhead):**  
  👉 **`https://vastu.krads.co.in/output/index.html`**  
  *(Instant Three.js canvas with textured mesh, wireframe toggle, point cloud splats, and WASD free-walk).*

* **Interactive 3D Spatial Studio (Floor Plans & Analytics):**  
  👉 **`https://vastu.krads.co.in/viewer`**  
  *(Metric measurements, architectural cross-sections, compass orientation, and lighting simulation).*

* **Official Project Overview Portal:**  
  👉 **`https://vastu.krads.co.in/`**  
  *(Dedicated academic & industrial project presentation, SOP simulator, and live 3D showcases).*

* **Download Reconstructed 3D Assets (For Blender / MeshLab verification):**  
  - Complete 3D Model (GLB): **`https://vastu.krads.co.in/output/model.glb`**  
  - Photographic Mesh (OBJ): **`https://vastu.krads.co.in/output/textured_mesh.obj`**  
  - Dense Point Cloud (PLY): **`https://vastu.krads.co.in/output/dense_pointcloud.ply`**  
  - Photographic Texture Atlas: **`https://vastu.krads.co.in/output/texture_atlas.jpg`**

---

### 💻 2. System & Browser Requirements

The VĀSTU Web Viewer runs directly inside any modern web browser using standard WebGL 2.0 without requiring plugins, extensions, or third-party client software.

| Requirement | Recommended Specification | Minimum Compatible |
| :--- | :--- | :--- |
| **Supported Browsers** | Google Chrome (v100+), Apple Safari (v15+), Microsoft Edge (v100+), Firefox (v100+) | Any WebGL 2.0 compliant browser |
| **Operating System** | macOS, Windows 10/11, Linux (Ubuntu), iOS 15+, Android 10+ | Any modern desktop or mobile OS |
| **Graphics Hardware** | Dedicated GPU (NVIDIA/AMD) or Apple Silicon (M1/M2/M3) | Integrated Intel UHD / Iris Graphics |
| **Internet Connection** | Broadband (≥ 5 Mbps for initial 3D mesh loading) | 4G / 5G Mobile Data |
| **Client Installation** | **ZERO INSTALL** (Runs 100% in browser) | None |

---

### 🔑 3. Authentication & Access Credentials

* **Public Zero-Barrier Access:** The 3D Viewer (`/viewer`), Project Website (`/`), and Mobile AR (`/ar`) require **NO login or password**. Evaluators can click the link and begin roaming immediately.
* **Optional Enterprise Console Access:** If evaluators wish to inspect the multi-tenant organization dashboard, upload tracking, and pipeline commands at `https://vastu.krads.co.in/dashboard`:
  * **Test Demo Organization Code:** `ORG-VASTU-2026`
  * **Evaluation Role:** Lead Architectural Reviewer (Full Read/Write Access)

---

### 🎮 4. Free-Roaming Navigation & Control Guide

The web viewer features a dual-mode interaction engine supporting both first-person architectural walkthroughs and bird's-eye orbital inspection.

#### A. Desktop Keyboard & Mouse Controls (First-Person Roaming):
* **`W` / `↑`**: Move Forward along current camera gaze.
* **`S` / `↓`**: Move Backward.
* **`A` / `←`**: Strafe / Walk Left.
* **`D` / `→`**: Strafe / Walk Right.
* **`Mouse Movement`**: 360° Free look (Pitch & Yaw). Click the canvas to activate Pointer Lock.
* **`Shift` (Hold)**: Sprint / Accelerate movement speed ($2.5\times$).
* **`Esc`**: Release mouse cursor from canvas.
* **`Double Click on 3D Surface`**: Activate the 3D Euclidean measurement ruler. Click any two points to measure real-world distances in meters ($\pm 0.01\text{m}$ accuracy).

#### B. Mobile & Tablet Touch Controls:
* **Left Screen Area**: Virtual floating joystick for omnidirectional planar walking.
* **Right Screen Area**: Touch drag to rotate viewing angle.
* **Pinch Gesture**: Zoom camera in / out in Orbit inspection mode.

#### C. Built-in Geometric Constraints & Physics:
1. **Floor Clamping:** Camera elevation is clamped at a fixed human eye-level ($Y = 1.60\text{ m}$ to $1.65\text{ m}$) above the detected horizontal floor datum ($Y = 0.00\text{ m}$).
2. **Obstacle Collision Detection:** An elliptical collider ($r = 0.35\text{ m}$) prevents the viewer camera from penetrating solid walls, doors, or furniture bounding boxes.
3. **Layer Toggles:** Top toolbar buttons allow toggling **Walls**, **Obstacle Colliders**, **Walkable 3D NavMesh**, **Vāstu Directional POI Anchors**, and **Wireframe Mesh**.

---

### 📦 5. Available Digital Twin Models for Evaluation

When opening `https://vastu.krads.co.in/viewer`, evaluators can switch between pre-processed digital twin spaces using the top project dropdown:

1. **Model 1: Dadar Studio Residential Suite (`dadar-cfm-04963`)**  
   * Full residential flat captured via SOP lateral trucking with verified Leica Disto D2 laser ground truth ($\pm 1.11\text{ cm}$ absolute error).
   * Features: Hardwood floor, primary partition walls, furniture bounding boxes, and glowing 3D A* navigation path.

2. **Model 2: Executive Architectural Office & Conference Suite (`img-3966-tsdf`)**  
   * Volumetric TSDF Marching Cubes reconstruction with 2048×2048 photometric texture atlas and $90^\circ$ Manhattan corner alignment.

---

### 📞 6. Technical Support & Verification
* **GitHub Repository:** `https://github.com/Mayank190405/vastu-space.git` (Branch: `codex/p0-capture-video-recovery`)
* **Live System Status:** Verified operational on AWS EC2 Cloud Infrastructure with Nginx SSL gateway.

