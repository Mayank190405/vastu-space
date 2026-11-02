# VĀSTU / NAMMA SPACE — Demonstration Video Script & Storyboard
**Target Duration:** 3 Minutes 45 Seconds (Fits 3 to 5-Minute Competition Requirement)  
**Deliverable:** Demonstration Video for Techfest IIT Bombay 2026 (Round 1)  
**File Output Format:** `VĀSTU_Demo_Video_Round1.mp4` (1080p / 60fps)  

---

## 🎬 Video Structure Overview

| Scene | Timestamp | Segment Title | Visual On-Screen Action | Audio Voiceover Narration |
| :---: | :---: | :--- | :--- | :--- |
| **1** | **0:00 – 0:45** | **Introduction & Problem Scope** | Title card, Dadar Studio survey photos, tape measuring fatigue | Introduces VĀSTU, the Create Fo'em industrial pilot, and why conventional tape surveying fails with a 4.8% error rate. |
| **2** | **0:45 – 1:45** | **Smartphone Capture SOP** | Split-screen: Person walking laterally along wall + Mobile HUD | Explains why rotating in one spot causes homography failure, and demonstrates the Lateral Trucking standard ($B \ge 0.8\text{m}$, speed $0.2\text{ m/s}$, corner anchor dwell). |
| **3** | **1:45 – 3:15** | **3D Web Walkthrough & Roaming** | Screen capture of `https://vastu.krads.co.in/viewer` | Demonstrates 60 FPS first-person WASD roaming, floor clamping at 1.6m, collision against walls, double-click 3D ruler, and 3D NavMesh. |
| **4** | **3:15 – 3:45** | **Metrology Benchmarks & Conclusion** | Leica Disto D2 comparison table ($\pm 1.11\text{ cm}$) + GitHub repo | Highlights our ground-truth laser accuracy, automated DXF CAD export, and final closing remarks. |

---

## 🎙️ Second-by-Second Narration Script

### Scene 1: Introduction & Problem Scope (0:00 – 0:45)
* **Visual:** Fade in on VĀSTU logo and title: *"VĀSTU: Autonomous Smartphone-to-3D Spatial Computing & Metric Digital Twin Engine"*. Show quick footage or photos of traditional tape measuring in an apartment.
* **Voiceover:**
  > *"Welcome to VĀSTU. In modern architecture and interior design, as-built spatial surveying is broken. At Create Fo'em Studio in Dadar West, Mumbai, measuring a typical residential flat takes two architects 4 to 6 hours with measuring tapes, averaging a 4.8% error discrepancy that leads to expensive rework during cabinetry installation. Terrestrial laser scanners cost upwards of $20,000, while casual smartphone videos consistently fail due to motion blur and lack of depth triangulation.*  
  > *VĀSTU solves this completely. By pairing an edge Standard Operating Procedure with an autonomous multi-stage volumetric reconstruction pipeline, VĀSTU converts casual handheld smartphone video into millimeter-accurate 3D watertight twins, CAD floor plans, and collision-aware navigation meshes in under 20 minutes."*

---

### Scene 2: Smartphone Capture SOP (0:45 – 1:45)
* **Visual:** Show a person holding a smartphone at chest level walking laterally along a room wall. On the right, show the mobile phone screen displaying the VĀSTU Capture HUD with live speedometer, distance radar, and corner anchor locked animation.
* **Voiceover:**
  > *"The secret to survey-grade photogrammetry is physical translation. When an operator stands in one spot and pivots like a lighthouse, camera rays intersect at near-zero angles, causing flat walls to bow into curves.*  
  > *Our mobile Standard Operating Procedure enforces the Lateral Trucking Standard: the surveyor holds the phone at chest level, maintaining a 1.5 to 2.0-meter standoff while walking smoothly sideways at 0.2 meters per second. This guarantees an epipolar baseline greater than 0.8 meters.*  
  > *The mobile engine continuously evaluates the discrete Laplacian blur operator: if the user pans too fast, real-time voice feedback warns them to slow down. At every room corner, the operator holds for 1.5 seconds, locking metric scale against the gravity vector before chunked 5MB upload."*

---

### Scene 3: Interactive 3D Web Walkthrough & Roaming (1:45 – 3:15)
* **Visual:** Clean full-screen capture of `https://vastu.krads.co.in/viewer`. Show the mouse locking, roaming around the room using WASD, bumping into a wall (collision pushback), double-clicking to measure distance between walls, and toggling the CAD floor plan view.
* **Voiceover:**
  > *"Now let's open the VĀSTU Web Viewer live at vastu.krads.co.in. Notice that this requires zero software installation—it runs natively inside any browser at a silky smooth 60 FPS using WebGL 2.0 and Three.js.*  
  > *Here, we are roaming inside the reconstructed digital twin of the Dadar flat. Notice three critical features:*  
  > *First, Floor Height Clamping: the camera is constrained to natural human eye level—1.60 meters above the floor datum—even over uneven scans.*  
  > *Second, Physical Collision Boundaries: as we approach this partition wall or the conference table, our collision cylinder prevents the camera from clipping through geometry.*  
  > *Third, Real-time 3D Metrology: by double-clicking two vertices, we can measure physical wall spans with ±0.01-meter precision.*  
  > *We can also toggle our extracted Manhattan-world CAD floor plan and export directly to AutoCAD DXF or SVG, alongside our 3D NavMesh which enforces ADA wheelchair slope limits under 4.76 degrees."*

---

### Scene 4: Metrology Benchmarks & Conclusion (3:15 – 3:45)
* **Visual:** Show the Leica Disto D2 ground truth comparison table, then cut to the GitHub repository page (`Mayank190405/vastu-space`).
* **Voiceover:**
  > *"To verify accuracy, every site was benchmarked against a calibrated Leica Disto D2 Laser Distance Meter across 36 landmark points. VĀSTU achieved a mean absolute error of just 1.11 centimeters across 10-meter spans—well within standard construction tolerances.*  
  > *Our entire system—including the FastAPI backend, Go microservices, and Three.js frontend—is open and deployed on AWS EC2.*  
  > *Thank you for watching VĀSTU: Mapping spaces, building digital twins."*

