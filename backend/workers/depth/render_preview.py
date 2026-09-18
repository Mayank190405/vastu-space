#!/usr/bin/env python3
import os
import json
import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from depth_estimator import DepthEstimator

out_dir = '/workers/depth/output/demo'
os.makedirs(f'{out_dir}/keyframes', exist_ok=True)
os.makedirs(f'{out_dir}/depth_maps', exist_ok=True)

h, w = 360, 480
img = np.full((h, w, 3), 195, dtype=np.uint8)
for y in range(int(h * 0.55), h):
    img[y, :] = [int(120 + (y - h * 0.55) * 0.3), int(90 + (y - h * 0.55) * 0.25), int(70 + (y - h * 0.55) * 0.2)]

cv2.rectangle(img, (80, 160), (280, 300), (60, 75, 110), -1)
cv2.rectangle(img, (140, 240), (220, 320), (40, 45, 55), -1)
cv2.circle(img, (380, 120), 30, (230, 210, 140), -1)
cv2.rectangle(img, (378, 150), (382, 320), (40, 40, 40), -1)

img_path = f'{out_dir}/keyframes/keyframe_0001.jpg'
cv2.imwrite(img_path, img)

K = np.array([[450.0, 0, 240.0], [0, 450.0, 180.0], [0, 0, 1.0]], dtype=np.float64)
sparse_pts = [
    {'point_id': 1, 'position': [-1.0, 0.5, 4.2], 'color': [195, 195, 195]},
    {'point_id': 2, 'position': [-0.4, -0.2, 2.1], 'color': [60, 75, 110]},
    {'point_id': 3, 'position': [0.0, -0.4, 1.5], 'color': [40, 45, 55]},
    {'point_id': 4, 'position': [0.8, 0.2, 2.8], 'color': [230, 210, 140]}
]

estimator = DepthEstimator(device='cpu')
res = estimator.process_keyframe(img_path, K, np.eye(3), np.zeros((3, 1)), sparse_pts, f'{out_dir}/depth_maps', 1)

depth_npy_name = res['depth_npy']
conf_png_name = res['confidence_png']
depth = np.load(f'{out_dir}/depth_maps/{depth_npy_name}')
conf_img = cv2.imread(f'{out_dir}/depth_maps/{conf_png_name}', cv2.IMREAD_GRAYSCALE)

fig, axes = plt.subplots(1, 3, figsize=(16, 5), facecolor='#150F0B')

axes[0].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
axes[0].set_title('1. Input RGB Keyframe', color='#DFB873', fontsize=12, fontweight='bold', pad=10)
axes[0].axis('off')

im2 = axes[1].imshow(depth, cmap='inferno', vmin=res['min_depth_m'], vmax=res['max_depth_m'])
axes[1].set_title(f"2. Dense Metric Depth ({res['min_depth_m']}m - {res['max_depth_m']}m)", color='#DFB873', fontsize=12, fontweight='bold', pad=10)
axes[1].axis('off')
cbar = fig.colorbar(im2, ax=axes[1], fraction=0.046, pad=0.04)
cbar.ax.yaxis.set_tick_params(color='#DFB873', labelcolor='#DFB873')

im3 = axes[2].imshow(conf_img, cmap='viridis', vmin=0, vmax=255)
axes[2].set_title(f"3. Per-Pixel Confidence (Mean: {res['mean_confidence']})", color='#DFB873', fontsize=12, fontweight='bold', pad=10)
axes[2].axis('off')
cbar2 = fig.colorbar(im3, ax=axes[2], fraction=0.046, pad=0.04)
cbar2.ax.yaxis.set_tick_params(color='#DFB873', labelcolor='#DFB873')

plt.tight_layout()
preview_png = '/workers/depth/output/depth_estimation_preview.png'
plt.savefig(preview_png, dpi=160, facecolor=fig.get_facecolor(), edgecolor='none')
print('SUCCESS_DEPTH_RENDERED:', preview_png)
