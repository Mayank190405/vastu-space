import os
import sys
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import core.reconstruction.o3d_shim as o3d
sys.modules["open3d"] = o3d
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
import cv2

twin_dir = sys.argv[1] if len(sys.argv) > 1 else "digital_twin_output_img4972"
out_dir = sys.argv[2] if len(sys.argv) > 2 else twin_dir

os.makedirs(out_dir, exist_ok=True)

# Determine video label
video_title = "VĀSTU 3D DIGITAL TWIN — RECONSTRUCTION VIEWS"
cap_path = os.path.join(twin_dir, "00_capture", "capture_report.json")
if not os.path.exists(cap_path):
    cap_path = os.path.join(twin_dir, "capture_report.json")
if os.path.exists(cap_path):
    try:
        import json
        with open(cap_path) as f:
            v_name = os.path.basename(json.load(f).get("video_path", ""))
            if v_name:
                video_title = f"VĀSTU 3D DIGITAL TWIN — RECONSTRUCTION VIEWS ({v_name})"
    except Exception:
        pass

# 1. Load Point Cloud
pcd_path = os.path.join(twin_dir, "dense_pointcloud_clean.ply")
pcd = o3d.io.read_point_cloud(pcd_path)
pts = np.asarray(pcd.points)
cols = np.asarray(pcd.colors)

if len(cols) == 0 or cols.shape[0] != pts.shape[0]:
    cols = np.ones((len(pts), 3)) * 0.7

# Downsample for matplotlib scatter if very dense
max_pts = 60000
if len(pts) > max_pts:
    idx = np.random.choice(len(pts), max_pts, replace=False)
    pts_sub = pts[idx]
    cols_sub = cols[idx]
else:
    pts_sub = pts
    cols_sub = cols

if HAS_MATPLOTLIB:
    # Set dark theme styling
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(20, 14), facecolor='#080a0f')

    # Title banner
    fig.suptitle(video_title, 
                 fontsize=18, fontweight='bold', color='#dfb873', y=0.97)

    # Panel 1: 3D Perspective Isometric View
    ax1 = fig.add_subplot(2, 2, 1, projection='3d', facecolor='#0b0f17')
    ax1.scatter(pts_sub[:, 0], pts_sub[:, 2], pts_sub[:, 1], c=cols_sub, s=0.8, alpha=0.85)
    ax1.set_title('3D Perspective View (Isocline)', fontsize=14, color='#38bdf8', pad=12)
    ax1.set_xlabel('X (Width, m)', color='#94a3b8', labelpad=8)
    ax1.set_ylabel('Z (Depth, m)', color='#94a3b8', labelpad=8)
    ax1.set_zlabel('Y (Height, m)', color='#94a3b8', labelpad=8)
    ax1.view_init(elev=28, azim=-55)
    ax1.grid(True, color='#1e293b', linestyle='--', alpha=0.5)

    # Panel 2: Top-Down Architectural Plan View (X-Z)
    ax2 = fig.add_subplot(2, 2, 2, facecolor='#0b0f17')
    sc2 = ax2.scatter(pts_sub[:, 0], pts_sub[:, 2], c=cols_sub, s=0.9, alpha=0.8)
    ax2.set_title('Top-Down Floor Plan (X-Z Projection)', fontsize=14, color='#38bdf8', pad=12)
    ax2.set_xlabel('X (Width, m)', color='#94a3b8')
    ax2.set_ylabel('Z (Depth, m)', color='#94a3b8')
    ax2.set_aspect('equal')
    ax2.grid(True, color='#1e293b', linestyle='--', alpha=0.5)
    ax2.axhline(0, color='#dfb873', linestyle=':', alpha=0.3)
    ax2.axvline(0, color='#dfb873', linestyle=':', alpha=0.3)

    # Panel 3: Front Elevation View (X-Y)
    ax3 = fig.add_subplot(2, 2, 3, facecolor='#0b0f17')
    sc3 = ax3.scatter(pts_sub[:, 0], pts_sub[:, 1], c=cols_sub, s=0.9, alpha=0.8)
    ax3.set_title('Front Elevation (X-Y Projection)', fontsize=14, color='#38bdf8', pad=12)
    ax3.set_xlabel('X (Width, m)', color='#94a3b8')
    ax3.set_ylabel('Y (Height / Floor Up, m)', color='#94a3b8')
    ax3.set_aspect('equal')
    ax3.grid(True, color='#1e293b', linestyle='--', alpha=0.5)
    ax3.axhline(0, color='#10b981', linewidth=1.5, label='Floor Datum (Y=0.00m)')
    ax3.legend(loc='upper right', facecolor='#0d1118', edgecolor='#dfb873')

    # Panel 4: Side Elevation View (Z-Y)
    ax4 = fig.add_subplot(2, 2, 4, facecolor='#0b0f17')
    sc4 = ax4.scatter(pts_sub[:, 2], pts_sub[:, 1], c=cols_sub, s=0.9, alpha=0.8)
    ax4.set_title('Side Profile Elevation (Z-Y Projection)', fontsize=14, color='#38bdf8', pad=12)
    ax4.set_xlabel('Z (Depth, m)', color='#94a3b8')
    ax4.set_ylabel('Y (Height / Floor Up, m)', color='#94a3b8')
    ax4.set_aspect('equal')
    ax4.grid(True, color='#1e293b', linestyle='--', alpha=0.5)
    ax4.axhline(0, color='#10b981', linewidth=1.5, label='Floor Datum (Y=0.00m)')
    ax4.legend(loc='upper right', facecolor='#0d1118', edgecolor='#dfb873')

    plt.tight_layout(rect=[0.02, 0.03, 0.98, 0.94])
    ortho_output_path = os.path.join(out_dir, "twin_orthogonal_views.png")
    plt.savefig(ortho_output_path, dpi=180, facecolor='#080a0f')
    plt.close()
    print(f"Saved: {ortho_output_path}")

    # 1b. Render Solid Mesh Views if mesh.ply exists
    mesh_path = os.path.join(twin_dir, "mesh.ply")
    if os.path.exists(mesh_path):
        try:
            m = o3d.io.read_triangle_mesh(mesh_path)
            m_verts = np.asarray(m.vertices)
            m_tris = np.asarray(m.triangles)
            if len(m_verts) > 0 and len(m_tris) > 0:
                fig_m = plt.figure(figsize=(20, 14), facecolor='#080a0f')
                fig_m.suptitle(video_title + " — SOLID 3D MESH GEOMETRY", fontsize=18, fontweight='bold', color='#dfb873', y=0.97)

                ax1 = fig_m.add_subplot(2, 2, 1, projection='3d', facecolor='#0b0f17')
                sub_tris = m_tris[::max(1, len(m_tris)//10000)]
                ax1.plot_trisurf(m_verts[:, 0], m_verts[:, 2], sub_tris, m_verts[:, 1], color='#dfb873', alpha=0.85, edgecolor='#1e293b', linewidth=0.1)
                ax1.set_title('Solid 3D Reconstructed Mesh (Isometric)', fontsize=14, color='#38bdf8', pad=12)
                ax1.view_init(elev=28, azim=-55)

                ax2 = fig_m.add_subplot(2, 2, 2, facecolor='#0b0f17')
                ax2.scatter(m_verts[:, 0], m_verts[:, 2], c='#dfb873', s=0.5, alpha=0.6)
                ax2.set_title('Top-Down Structural Plan (X-Z Projection)', fontsize=14, color='#38bdf8', pad=12)
                ax2.set_aspect('equal')
                ax2.grid(True, color='#1e293b', linestyle='--', alpha=0.5)

                ax3 = fig_m.add_subplot(2, 2, 3, facecolor='#0b0f17')
                ax3.scatter(m_verts[:, 0], m_verts[:, 1], c='#38bdf8', s=0.5, alpha=0.6)
                ax3.axhline(0, color='#10b981', linewidth=1.5, label='Floor Datum (Y=0.00m)')
                ax3.set_title('Front Architectural Elevation (X-Y Projection)', fontsize=14, color='#38bdf8', pad=12)
                ax3.set_aspect('equal')
                ax3.grid(True, color='#1e293b', linestyle='--', alpha=0.5)
                ax3.legend(loc='upper right', facecolor='#0d1118', edgecolor='#dfb873')

                ax4 = fig_m.add_subplot(2, 2, 4, facecolor='#0b0f17')
                ax4.scatter(m_verts[:, 2], m_verts[:, 1], c='#38bdf8', s=0.5, alpha=0.6)
                ax4.axhline(0, color='#10b981', linewidth=1.5, label='Floor Datum (Y=0.00m)')
                ax4.set_title('Side Profile Elevation (Z-Y Projection)', fontsize=14, color='#38bdf8', pad=12)
                ax4.set_aspect('equal')
                ax4.grid(True, color='#1e293b', linestyle='--', alpha=0.5)
                ax4.legend(loc='upper right', facecolor='#0d1118', edgecolor='#dfb873')

                plt.tight_layout(rect=[0.02, 0.03, 0.98, 0.94])
                mesh_out = os.path.join(out_dir, "mesh_orthogonal_views.png")
                plt.savefig(mesh_out, dpi=180, facecolor='#080a0f')
                plt.close()
                print(f"Saved: {mesh_out}")
        except Exception as e:
            print(f"Mesh render notice: {e}")

    # 2. Pipeline Evidence Collage: Keyframes + Depth Maps + Texture Atlas
    fig2, axes = plt.subplots(2, 4, figsize=(18, 9), facecolor='#080a0f')
    fig2.suptitle('STAGE EVIDENCE: MONOCULAR KEYFRAMES VS METRIC DEPTH MAPS', 
                  fontsize=16, fontweight='bold', color='#dfb873', y=0.98)

    sample_indices = [0, 4, 8, 12]
    for col_idx, f_idx in enumerate(sample_indices):
        rgb_p = os.path.join(twin_dir, "01_keyframes", f"frame_{f_idx:02d}.png")
        depth_p = os.path.join(twin_dir, "05_depth", f"depth_frame_{f_idx:02d}.png")
        
        if os.path.exists(rgb_p):
            rgb = cv2.imread(rgb_p)
            rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
            axes[0, col_idx].imshow(rgb)
            axes[0, col_idx].set_title(f'Keyframe {f_idx:02d} (RGB)', color='#38bdf8', fontsize=12)
        axes[0, col_idx].axis('off')

        if os.path.exists(depth_p):
            depth = cv2.imread(depth_p)
            depth = cv2.cvtColor(depth, cv2.COLOR_BGR2RGB)
            axes[1, col_idx].imshow(depth)
            axes[1, col_idx].set_title(f'Depth Metric {f_idx:02d}', color='#10b981', fontsize=12)
        axes[1, col_idx].axis('off')

    plt.tight_layout(rect=[0.01, 0.02, 0.99, 0.94])
    depth_output_path = os.path.join(out_dir, "twin_depth_evidence.png")
    plt.savefig(depth_output_path, dpi=180, facecolor='#080a0f')
    plt.close()
    print(f"Saved: {depth_output_path}")
else:
    # Pure OpenCV orthogonal multi-panel renderer
    canvas = np.full((1200, 1600, 3), 15, dtype=np.uint8)
    cv2.putText(canvas, video_title, (50, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (115, 184, 223), 2, cv2.LINE_AA)

    # Render Top-Down (X-Z)
    sub_top = canvas[120:620, 50:780]
    min_x, max_x = pts_sub[:, 0].min(), pts_sub[:, 0].max()
    min_z, max_z = pts_sub[:, 2].min(), pts_sub[:, 2].max()
    span_x = max(max_x - min_x, 1e-3)
    span_z = max(max_z - min_z, 1e-3)

    px = np.clip(((pts_sub[:, 0] - min_x) / span_x * 700 + 15).astype(int), 0, 729)
    pz = np.clip(((pts_sub[:, 2] - min_z) / span_z * 470 + 15).astype(int), 0, 499)
    bgr_cols = (cols_sub[:, [2, 1, 0]] * 255).astype(np.uint8) if cols_sub.max() <= 1.0 else cols_sub[:, [2, 1, 0]].astype(np.uint8)

    for i in range(len(px)):
        cv2.circle(sub_top, (px[i], pz[i]), 1, (int(bgr_cols[i, 0]), int(bgr_cols[i, 1]), int(bgr_cols[i, 2])), -1)
    cv2.rectangle(canvas, (50, 120), (780, 620), (50, 70, 90), 1)
    cv2.putText(canvas, "Top-Down Floor Plan (X-Z Projection)", (60, 150),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (248, 189, 56), 2, cv2.LINE_AA)

    # Render Front Elevation (X-Y)
    sub_front = canvas[120:620, 820:1550]
    min_y, max_y = pts_sub[:, 1].min(), pts_sub[:, 1].max()
    span_y = max(max_y - min_y, 1e-3)
    py = np.clip(((max_y - pts_sub[:, 1]) / span_y * 470 + 15).astype(int), 0, 499)
    for i in range(len(px)):
        cv2.circle(sub_front, (px[i], py[i]), 1, (int(bgr_cols[i, 0]), int(bgr_cols[i, 1]), int(bgr_cols[i, 2])), -1)
    cv2.rectangle(canvas, (820, 120), (1550, 620), (50, 70, 90), 1)
    cv2.putText(canvas, "Front Elevation (X-Y Projection)", (830, 150),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (248, 189, 56), 2, cv2.LINE_AA)

    # Render Side Elevation (Z-Y)
    sub_side = canvas[660:1160, 50:780]
    for i in range(len(pz)):
        cv2.circle(sub_side, (pz[i], py[i]), 1, (int(bgr_cols[i, 0]), int(bgr_cols[i, 1]), int(bgr_cols[i, 2])), -1)
    cv2.rectangle(canvas, (50, 660), (780, 1160), (50, 70, 90), 1)
    cv2.putText(canvas, "Side Profile Elevation (Z-Y Projection)", (60, 690),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (248, 189, 56), 2, cv2.LINE_AA)

    # Perspective Isocline (Composite)
    sub_iso = canvas[660:1160, 820:1550]
    iso_x = (pts_sub[:, 0] - pts_sub[:, 2]) * 0.707
    iso_y = (pts_sub[:, 0] + pts_sub[:, 2]) * 0.408 + pts_sub[:, 1] * 0.816
    min_ix, max_ix = iso_x.min(), iso_x.max()
    min_iy, max_iy = iso_y.min(), iso_y.max()
    pix = np.clip(((iso_x - min_ix) / max(max_ix - min_ix, 1e-3) * 700 + 15).astype(int), 0, 729)
    piy = np.clip(((max_iy - iso_y) / max(max_iy - min_iy, 1e-3) * 470 + 15).astype(int), 0, 499)
    for i in range(len(pix)):
        cv2.circle(sub_iso, (pix[i], piy[i]), 1, (int(bgr_cols[i, 0]), int(bgr_cols[i, 1]), int(bgr_cols[i, 2])), -1)
    cv2.rectangle(canvas, (820, 660), (1550, 1160), (50, 70, 90), 1)
    cv2.putText(canvas, "3D Perspective View (Isocline)", (830, 690),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (248, 189, 56), 2, cv2.LINE_AA)

    ortho_output_path = os.path.join(out_dir, "twin_orthogonal_views.png")
    cv2.imwrite(ortho_output_path, canvas)
    print(f"Saved: {ortho_output_path}")

    # Generate twin_depth_evidence.png using OpenCV
    sample_indices = [0, 4, 8, 12]
    tile_w, tile_h = 360, 480
    depth_canvas = np.full((tile_h * 2 + 100, tile_w * 4 + 50, 3), 15, dtype=np.uint8)
    cv2.putText(depth_canvas, "STAGE EVIDENCE: MONOCULAR KEYFRAMES VS METRIC DEPTH MAPS", (30, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (115, 184, 223), 2, cv2.LINE_AA)

    for col_idx, f_idx in enumerate(sample_indices):
        rgb_p = os.path.join(twin_dir, "01_keyframes", f"frame_{f_idx:02d}.png")
        depth_p = os.path.join(twin_dir, "05_depth", f"depth_frame_{f_idx:02d}.png")
        x_off = 25 + col_idx * tile_w
        if os.path.exists(rgb_p):
            rgb = cv2.imread(rgb_p)
            rgb_thumb = cv2.resize(rgb, (tile_w - 10, tile_h - 40))
            depth_canvas[70 : 70 + tile_h - 40, x_off : x_off + tile_w - 10] = rgb_thumb
            cv2.putText(depth_canvas, f"Keyframe {f_idx:02d} (RGB)", (x_off + 10, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (248, 189, 56), 1, cv2.LINE_AA)

        if os.path.exists(depth_p):
            depth_img = cv2.imread(depth_p)
            depth_thumb = cv2.resize(depth_img, (tile_w - 10, tile_h - 40))
            y_off = 70 + tile_h - 20
            depth_canvas[y_off : y_off + tile_h - 40, x_off : x_off + tile_w - 10] = depth_thumb
            cv2.putText(depth_canvas, f"Depth Metric {f_idx:02d}", (x_off + 10, y_off - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (129, 185, 16), 1, cv2.LINE_AA)

    depth_output_path = os.path.join(out_dir, "twin_depth_evidence.png")
    cv2.imwrite(depth_output_path, depth_canvas)
    print(f"Saved: {depth_output_path}")

# 3. Texture Atlas Preview
atlas_src = os.path.join(twin_dir, "texture_atlas.png")
if os.path.exists(atlas_src):
    atlas_img = cv2.imread(atlas_src)
    atlas_dst = os.path.join(out_dir, "twin_texture_atlas_preview.png")
    cv2.imwrite(atlas_dst, atlas_img)
    print(f"Saved: {atlas_dst}")

