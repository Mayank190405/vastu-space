# VĀSTU — Smartphone Video Capture Standard Operating Procedure (SOP)
**Document ID:** `SOP-VASTU-CAP-001`  
**Version:** 1.0.0  
**Target Audience:** Mobile Operators, Field Technicians, Surveyors  
**Scope:** Smartphone Video Capture to 3D Digital Twin Pipeline  
**Compliance Target:** Techfest IIT Bombay 2026

---

## 1. Executive Summary & Geometric Directive

The VĀSTU 3D digital twin engine constructs volumetric geometry using multi-view epipolar geometry, neural metric depth estimation, and TSDF Marching Cubes integration.

**The Golden Rule of Spatial Capture:**
> **3D depth cannot be triangulated from a stationary pivot.**
> Rotating or panning the smartphone while standing in one spot produces 2D homography flow ($H \approx K R K^{-1}$), not 3D parallax. Without camera translation across the room floor, rays intersect at near-zero angles, forcing flat walls to bow into curved arcs.

This document defines the exact physical capture procedure required to produce architecturally accurate, sub-5cm 3D reconstructions.

---

## 2. Mathematical Foundation: Parallax vs. Rotational Degeneracy

When two camera frames observe a 3D point $P$, the triangulation error $\sigma_Z$ is inversely proportional to the camera baseline distance $B$:
$$\sigma_Z \approx \frac{Z^2}{f \cdot B} \cdot \sigma_{\text{pixel}}$$

- **Pivoting in place:** Baseline $B \approx 0.03\text{ m} \implies$ Triangulation uncertainty $\sigma_Z > 0.50\text{ m}$. Monocular depth estimation cannot be refined by stereo consensus, resulting in 36 cm wall curvature.
- **Translating laterally:** Baseline $B \ge 0.80\text{ m} \implies$ Triangulation uncertainty $\sigma_Z < 0.03\text{ m}$. Geometric consensus eliminates depth ambiguity, producing flat planar walls and sharp $90^\circ$ corners.

---

## 3. Smartphone Recording Configuration

| Parameter | Recommended Specification | Acceptable Range | Notes |
| :--- | :--- | :--- | :--- |
| **Resolution** | 4K UHD ($3840 \times 2160$ or $2160 \times 3840$) | Minimum 1080p ($1920 \times 1080$) | Higher resolution provides denser feature matches. |
| **Frame Rate** | 30 fps or 60 fps | 24–60 fps | 60 fps reduces motion blur during movement. |
| **Camera Lens** | $1\times$ Primary Wide-Angle ($\approx 24\text{–}26\text{mm}$) | $1\times$ Wide only | **DO NOT USE $0.5\times$ Ultra-Wide** (severe optical distortion) or $3\times/5\times$ Telephoto. |
| **Orientation** | Portrait or Landscape (Consistent) | Do not switch orientation mid-recording | Keep phone orientation locked throughout scan. |
| **Exposure / Focus** | Auto-Exposure / Auto-Focus (Stable) | Locked AE/AF preferred in constant light | Avoid rapid exposure hunting or flickering. |
| **Duration** | 15 to 45 seconds per room | 10 to 90 seconds | Ensures 16–32 keyframes with $> 70\%$ overlap. |

---

## 4. Physical Movement Protocol: The Lateral Truck & Dolly Standard

### Step 1: Room Preparation
1. **Lighting:** Turn on all ceiling lights and interior lamps. Open curtains to provide even, diffuse daylight. Avoid strong direct glare pointed straight into the camera lens.
2. **Doorways:** Prop all doors open or closed consistently. Do not move furniture or open doors during the recording.
3. **Clutter:** Clear loose cables, clothes, or movable floor obstacles that obscure wall-floor baseboards.

### Step 2: The Walking Motion (Translational Trucking)
- **DO NOT stand in the center and rotate like a lighthouse.**
- **DO walk laterally across the room floor:**
  - Hold the phone firmly with two hands at chest level ($Y \approx 1.3\text{m} - 1.5\text{m}$).
  - Walk slowly and smoothly at approximately **$0.3\text{ m/s}$ (one slow step per two seconds)**.
  - Move sideways along the length of each wall (trucking/strafing motion) while facing the wall and adjacent corner.
  - Minimum translation distance along any wall segment is **$0.80\text{ meters}$**.

### Step 3: Vertical Trajectory Coverage
To capture complete room surfaces without open boundary gaps:
1. **Lower Pass (Floor & Baseboards):** Tilt the phone slightly down ($\sim -15^\circ$) while translating sideways to capture the floor-to-wall contact line.
2. **Middle Pass (Walls & Openings):** Maintain level horizontal orientation ($\sim 0^\circ$) to record door frames, windows, light switches, and wall art.
3. **Upper Pass (Ceiling & Cornice):** Tilt the phone slightly up ($\sim +15^\circ$) while moving laterally to capture the ceiling plane and top corners.

### Step 4: Corner & Wall Traversal Loop
- **The "Perimeter Box" Path:** Start at the entrance door, translate along Wall 1 toward Corner 1, pivot smoothly while taking 2 lateral steps into Wall 2, translate along Wall 2 toward Corner 2, and continue around the room perimeter.
- Maintain continuous visual overlap: at least **70% of the previous camera frame must remain visible in the next frame**.

---

## 5. What to Avoid (Defect Prevention Checklist)

| Defect Pattern | Visual Symptom in 3D Output | Root Cause | Operator Correction |
| :--- | :--- | :--- | :--- |
| **Stationary Pivot** | Severely bowed/curved walls (36cm RMS error) | Standing in one spot and turning the phone. | Walk across the floor sideways ($B \ge 0.8\text{m}$). |
| **Rapid Whip-Pan** | Dropped keyframes, lost tracking, fragmented point cloud | Rotating the phone faster than $30^\circ/\text{s}$. | Turn smoothly and slowly ($< 15^\circ/\text{s}$). |
| **Ultra-Wide $0.5\times$ Lens** | Upward ceiling flaring, stretched corner geometry | Using the wide-angle camera lens. | Use the standard $1\times$ wide-angle lens only. |
| **Reflective Glare** | Floating noise artifacts, holes in mirror surfaces | Filming large mirrors or glass windows directly. | Film reflective surfaces at an oblique $45^\circ$ angle. |
| **Moving Humans/Pets** | Ghosting, smeared textures across room surfaces | Moving objects in frame during recording. | Keep the room clear of people and pets during capture. |

---

## 6. Preflight Acceptance Criteria

When a video is submitted, VĀSTU's automated preflight validator (`core/preflight/validator.py`) inspects the raw stream before executing heavy 3D reconstruction:

```text
[PREFLIGHT AUDIT GATES]
1. Image Sharpness:         Laplacian variance >= 80.0
2. Keyframe Overlap:        Visual feature overlap >= 65%
3. Motion Flow Homography:  Homography inliers < 60% (Rejects stationary pivot)
4. Physical Baseline:       Camera translation >= 0.80 meters
5. Exposure Stability:      Histogram drift < 25%
```

If the video violates Gate 3 or Gate 4, the preflight engine issues an immediate recapture prompt:
> **"CAPTURE GUIDANCE: Insufficient camera translation detected ($< 0.10\text{ m}$). Please re-record using a lateral walking motion along the room floor rather than pivoting from a single spot."**

---

## 7. Clarification on Physical Measurements

- **Standard User Workflow:** Normal VĀSTU users and clients **DO NOT** need to measure rooms with a tape measure or place AR calibration markers on walls. The pipeline automatically recovers scale using Depth Anything V2 Metric neural inference and visual-inertial trajectory integration.
- **Engineering Quality Verification:** For internal accuracy certification and competition benchmarking, engineering teams perform physical tape measurements (laser meter) of room length, width, ceiling height, and door widths to calculate millimeter residual errors against ground truth.
