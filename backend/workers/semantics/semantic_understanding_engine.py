#!/usr/bin/env python3
"""
VĀSTU — Point 24: Semantic Understanding Engine
PyTorch-powered 3D indoor spatial semantic segmentation and object extraction pipeline.

Development sequence:
1. Run semantic model (PyTorch neural network forward pass)
2. Generate 2D segmentation masks and confidence maps
3. Associate image regions with 3D geometry (depth unprojection)
4. Project semantic information into 3D spatial representation
5. Merge observations (multi-view Bayesian probability accumulation)
6. Calculate confidence and evaluation metrics (Precision, Recall, F1, IoU)
7. Store semantic objects (3D oriented bounding boxes, centroids, semantic JSON & point cloud)

Classes:
0: Other / Background
1: Floor
2: Wall
3: Ceiling
4: Door
5: Window
6: Table
7: Chair
8: Sofa
9: Cabinet
"""

import os
import sys
import json
import logging
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VastuSemanticEngine")

SEMANTIC_CLASSES = [
    "Other",    # 0
    "Floor",    # 1
    "Wall",     # 2
    "Ceiling",  # 3
    "Door",     # 4
    "Window",   # 5
    "Table",    # 6
    "Chair",    # 7
    "Sofa",     # 8
    "Cabinet"   # 9
]

CLASS_TO_ID = {name: i for i, name in enumerate(SEMANTIC_CLASSES)}

# Color palette for 3D visualization (RGB 0..255)
CLASS_COLORS = {
    0: [128, 128, 128], # Other: Gray
    1: [140, 200, 140], # Floor: Soft Green
    2: [220, 220, 230], # Wall: Off White
    3: [240, 235, 210], # Ceiling: Warm White
    4: [180, 100,  50], # Door: Wood Brown
    5: [ 80, 170, 230], # Window: Sky Blue
    6: [200, 140,  80], # Table: Amber Oak
    7: [220,  60,  60], # Chair: Crimson Red
    8: [130,  80, 160], # Sofa: Royal Purple
    9: [210, 170,  90], # Cabinet: Golden Birch
}


class VastuIndoorSegmenter(nn.Module):
    """
    Modular PyTorch multi-scale semantic segmentation model for indoor architectural spaces.
    Uses dilated convolutions for large spatial receptive field without losing resolution.
    """
    def __init__(self, num_classes: int = len(SEMANTIC_CLASSES)):
        super().__init__()
        # Backbone: Multi-scale convolutional feature extractor
        self.conv1 = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 32, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2) # 1/2
        )

        self.conv2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2) # 1/4
        )

        # Atrous Spatial Pyramid Pooling (ASPP) for multi-scale context
        self.aspp_branch1 = nn.Conv2d(64, 32, kernel_size=1, bias=False)
        self.aspp_branch2 = nn.Conv2d(64, 32, kernel_size=3, padding=2, dilation=2, bias=False)
        self.aspp_branch3 = nn.Conv2d(64, 32, kernel_size=3, padding=4, dilation=4, bias=False)

        self.aspp_fuse = nn.Sequential(
            nn.Conv2d(96, 64, kernel_size=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )

        # Decoder / Upsampling
        self.upsample = nn.Upsample(scale_factor=4, mode="bilinear", align_corners=False)
        self.classifier = nn.Conv2d(64, num_classes, kernel_size=1)

        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat1 = self.conv1(x)
        feat2 = self.conv2(feat1)

        b1 = self.aspp_branch1(feat2)
        b2 = self.aspp_branch2(feat2)
        b3 = self.aspp_branch3(feat2)

        fused = self.aspp_fuse(torch.cat([b1, b2, b3], dim=1))
        up = self.upsample(fused)
        logits = self.classifier(up)
        return logits


class SemanticUnderstandingEngine:
    def __init__(
        self,
        device: str = None,
        confidence_threshold: float = 0.40,
        min_cluster_points: int = 15,
        cluster_eps_m: float = 0.25
    ):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.confidence_threshold = confidence_threshold
        self.min_cluster_points = min_cluster_points
        self.cluster_eps_m = cluster_eps_m

        self.model = VastuIndoorSegmenter(num_classes=len(SEMANTIC_CLASSES)).to(self.device)
        self.model.eval()
        logger.info(f"Initialized SemanticUnderstandingEngine on device: {self.device}")

    # -------------------------------------------------------------------------
    # Step 1 & 2: Run Semantic Model & Generate 2D Segmentation
    # -------------------------------------------------------------------------
    def run_inference_2d(self, frame_bgr: np.ndarray) -> tuple:
        """
        Runs PyTorch forward pass on a single RGB frame.
        Returns:
            pred_mask: (H, W) int64 class indices
            confidence_map: (H, W) float32 confidence scores [0.0, 1.0]
            prob_tensor: (num_classes, H, W) float32 probability distribution
        """
        img_rgb = frame_bgr[:, :, ::-1].copy() # BGR to RGB
        h, w = img_rgb.shape[:2]

        # Normalize to [0, 1] tensor (B, C, H, W)
        img_norm = img_rgb.astype(np.float32) / 255.0
        # Standard ImageNet-like normalization
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img_norm = (img_norm - mean) / std

        tensor = torch.from_numpy(img_norm.transpose(2, 0, 1)).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            # Ensure spatial dimension matches input
            if logits.shape[2:] != (h, w):
                logits = F.interpolate(logits, size=(h, w), mode="bilinear", align_corners=False)

            probs = F.softmax(logits, dim=1).squeeze(0) # (num_classes, H, W)
            conf_map, pred_mask = torch.max(probs, dim=0)

        return (
            pred_mask.cpu().numpy().astype(np.int64),
            conf_map.cpu().numpy().astype(np.float32),
            probs.cpu().numpy().astype(np.float32)
        )

    # -------------------------------------------------------------------------
    # Step 3: Associate Image Regions with 3D Geometry
    # -------------------------------------------------------------------------
    def associate_image_regions_with_3d(
        self,
        points_3d: np.ndarray,
        camera_pose: dict,
        intrinsics_k: np.ndarray,
        depth_map: np.ndarray,
        img_w: int,
        img_h: int
    ) -> tuple:
        """
        Projects 3D points into camera view, performs Z-depth association,
        and retrieves visible corresponding pixel coordinates.
        Returns:
            pixel_coords: (N, 2) int array [u, v]
            valid_indices: (M,) 1D index array of points that project cleanly onto surface
        """
        r_mat = camera_pose["R"]
        t_vec = camera_pose["t"].reshape(1, 3)

        # p_cam = R * p_world + t
        p_cam = (r_mat @ points_3d.T).T + t_vec
        zc = p_cam[:, 2]

        in_front = zc > 0.1
        inv_z = np.zeros_like(zc)
        inv_z[in_front] = 1.0 / zc[in_front]

        u = intrinsics_k[0, 0] * (p_cam[:, 0] * inv_z) + intrinsics_k[0, 2]
        v = intrinsics_k[1, 1] * (p_cam[:, 1] * inv_z) + intrinsics_k[1, 2]

        inside_bounds = (
            in_front &
            (u >= 0.0) & (u < float(img_w)) &
            (v >= 0.0) & (v < float(img_h))
        )

        cand_indices = np.where(inside_bounds)[0]
        u_int = np.clip(np.round(u[cand_indices]).astype(np.int32), 0, img_w - 1)
        v_int = np.clip(np.round(v[cand_indices]).astype(np.int32), 0, img_h - 1)

        # Depth buffer consistency check if depth map is provided
        if depth_map is not None:
            observed_depths = depth_map[v_int, u_int]
            depth_consistent = (observed_depths > 0.05) & (np.abs(zc[cand_indices] - observed_depths) < 0.15)
            final_indices = cand_indices[depth_consistent]
            final_pixels = np.column_stack([u_int[depth_consistent], v_int[depth_consistent]])
        else:
            final_indices = cand_indices
            final_pixels = np.column_stack([u_int, v_int])

        return final_pixels, final_indices

    # -------------------------------------------------------------------------
    # Step 4 & 5: Project & Merge Multi-View Semantic Observations
    # -------------------------------------------------------------------------
    def fuse_multiview_semantics(
        self,
        points_3d: np.ndarray,
        camera_poses: list,
        frames: list,
        depth_maps: list,
        intrinsics_k: np.ndarray
    ) -> tuple:
        """
        Accumulates 2D semantic probabilities across all camera viewpoints
        using Bayesian log-odds pooling.
        Returns:
            fused_class_ids: (N,) int array of majority predicted class per 3D point
            fused_confidences: (N,) float array of fused confidence scores
            class_prob_matrix: (N, num_classes) float array of probability distributions
        """
        num_points = len(points_3d)
        num_classes = len(SEMANTIC_CLASSES)
        img_h, img_w = frames[0].shape[:2]

        # Log-odds probability accumulator initialized to uniform neutral prior (log(1/K))
        log_odds = np.zeros((num_points, num_classes), dtype=np.float32)
        observation_counts = np.zeros(num_points, dtype=np.int32)

        for i, (pose, frame) in enumerate(zip(camera_poses, frames)):
            depth_map = depth_maps[i] if depth_maps is not None and i < len(depth_maps) else None

            # Step 1 & 2: 2D Inference
            _, _, probs_2d = self.run_inference_2d(frame) # (num_classes, H, W)

            # Step 3: Associate with 3D points
            pixels, pt_indices = self.associate_image_regions_with_3d(
                points_3d, pose, intrinsics_k, depth_map, img_w, img_h
            )

            if len(pt_indices) == 0:
                continue

            u_coords = pixels[:, 0]
            v_coords = pixels[:, 1]

            # Sample class probabilities for observed points
            sampled_probs = probs_2d[:, v_coords, u_coords].T # (M, num_classes)
            sampled_probs = np.clip(sampled_probs, 1e-4, 1.0 - 1e-4)

            # Bayesian update: log_odds += log(P / (1 - P))
            log_ratio = np.log(sampled_probs / (1.0 - sampled_probs))
            log_odds[pt_indices] += log_ratio
            observation_counts[pt_indices] += 1

        # Convert back from log-odds to normalized probabilities via Softmax
        # Subtract max for numerical stability
        max_logs = np.max(log_odds, axis=1, keepdims=True)
        exp_logs = np.exp(log_odds - max_logs)
        prob_matrix = exp_logs / np.sum(exp_logs, axis=1, keepdims=True)

        fused_class_ids = np.argmax(prob_matrix, axis=1)
        fused_confidences = np.max(prob_matrix, axis=1)

        # Filter out points with 0 observations (set to Other / Background)
        unobserved = observation_counts == 0
        fused_class_ids[unobserved] = 0
        fused_confidences[unobserved] = 0.0

        return fused_class_ids, fused_confidences, prob_matrix

    # -------------------------------------------------------------------------
    # Step 6: Calculate Confidence & Evaluation Metrics (Precision, Recall, F1, IoU)
    # -------------------------------------------------------------------------
    @staticmethod
    def calculate_evaluation_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        target_classes: list = None
    ) -> dict:
        """
        Computes Precision, Recall, F1, and IoU per class, along with macro-averaged mIoU.
        """
        if target_classes is None:
            target_classes = range(len(SEMANTIC_CLASSES))

        metrics_per_class = {}
        ious = []
        f1s = []
        precisions = []
        recalls = []

        for c in target_classes:
            name = SEMANTIC_CLASSES[c] if c < len(SEMANTIC_CLASSES) else f"Class_{c}"

            true_mask = (y_true == c)
            pred_mask = (y_pred == c)

            tp = int(np.sum(true_mask & pred_mask))
            fp = int(np.sum((~true_mask) & pred_mask))
            fn = int(np.sum(true_mask & (~pred_mask)))

            precision = float(tp) / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = float(tp) / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2.0 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            iou = float(tp) / (tp + fp + fn) if (tp + fp + fn) > 0 else 1.0 if np.sum(true_mask) == 0 else 0.0

            metrics_per_class[name] = {
                "class_id": c,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "iou": round(iou, 4),
                "support": int(np.sum(true_mask))
            }

            if np.sum(true_mask) > 0:
                ious.append(iou)
                f1s.append(f1)
                precisions.append(precision)
                recalls.append(recall)

        macro_iou = float(np.mean(ious)) if ious else 0.0
        macro_f1 = float(np.mean(f1s)) if f1s else 0.0
        macro_prec = float(np.mean(precisions)) if precisions else 0.0
        macro_rec = float(np.mean(recalls)) if recalls else 0.0

        summary = {
            "mean_iou": round(macro_iou, 4),
            "macro_f1": round(macro_f1, 4),
            "macro_precision": round(macro_prec, 4),
            "macro_recall": round(macro_rec, 4),
            "classes": metrics_per_class
        }

        logger.info(
            f"[Metrics] mIoU: {macro_iou:.4f} | Macro F1: {macro_f1:.4f} | "
            f"Precision: {macro_prec:.4f} | Recall: {macro_rec:.4f}"
        )
        return summary

    # -------------------------------------------------------------------------
    # Step 7: Store Semantic Objects (3D Bounding Boxes, Centroids, JSON)
    # -------------------------------------------------------------------------
    def extract_semantic_objects(
        self,
        points_3d: np.ndarray,
        class_ids: np.ndarray,
        confidences: np.ndarray
    ) -> list:
        """
        Clusters points of identical semantic classes into individual 3D objects
        and calculates oriented/axis-aligned 3D bounding boxes, centroids, and volumes.
        """
        semantic_objects = []
        obj_id = 1

        for c in range(1, len(SEMANTIC_CLASSES)):
            c_mask = (class_ids == c) & (confidences >= self.confidence_threshold)
            c_points = points_3d[c_mask]

            if len(c_points) < self.min_cluster_points:
                continue

            # Spatial voxel clustering to separate individual instances
            cell_size = self.cluster_eps_m
            bins = np.floor(c_points / cell_size).astype(np.int64)

            from collections import defaultdict
            bin_to_pts = defaultdict(list)
            for idx in range(len(c_points)):
                b_key = (int(bins[idx, 0]), int(bins[idx, 1]), int(bins[idx, 2]))
                bin_to_pts[b_key].append(c_points[idx])

            unique_bins_set = set(bin_to_pts.keys())
            visited_bins = set()
            clusters = []

            for b_tuple in list(unique_bins_set):
                if b_tuple in visited_bins:
                    continue

                cluster_pts = []
                queue = [b_tuple]
                visited_bins.add(b_tuple)

                while queue:
                    cur = queue.pop(0)
                    cluster_pts.extend(bin_to_pts[cur])

                    # Check 26-neighborhood
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            for dz in [-1, 0, 1]:
                                if dx == 0 and dy == 0 and dz == 0:
                                    continue
                                nbr = (cur[0] + dx, cur[1] + dy, cur[2] + dz)
                                if nbr in unique_bins_set and nbr not in visited_bins:
                                    visited_bins.add(nbr)
                                    queue.append(nbr)

                if cluster_pts:
                    merged = np.vstack(cluster_pts)
                    if len(merged) >= self.min_cluster_points:
                        clusters.append(merged)

            # For each cluster, calculate 3D bounding box
            for cluster in clusters:
                min_pt = np.min(cluster, axis=0)
                max_pt = np.max(cluster, axis=0)
                dims = max_pt - min_pt
                dims = np.maximum(dims, 0.05) # Minimum 5cm dimension
                centroid = np.mean(cluster, axis=0)
                volume_m3 = float(dims[0] * dims[1] * dims[2])

                class_name = SEMANTIC_CLASSES[c]
                entity = {
                    "object_id": f"{class_name.lower()}_{obj_id:03d}",
                    "class_name": class_name,
                    "class_id": c,
                    "point_count": int(len(cluster)),
                    "centroid": [round(float(v), 3) for v in centroid],
                    "bounding_box": {
                        "min_xyz": [round(float(v), 3) for v in min_pt],
                        "max_xyz": [round(float(v), 3) for v in max_pt],
                        "dimensions_xyz": [round(float(v), 3) for v in dims],
                        "volume_m3": round(volume_m3, 4)
                    }
                }
                semantic_objects.append(entity)
                obj_id += 1

        return semantic_objects

    def store_semantic_assets(
        self,
        output_dir: str,
        points_3d: np.ndarray,
        class_ids: np.ndarray,
        confidences: np.ndarray,
        semantic_objects: list,
        evaluation_metrics: dict = None
    ) -> dict:
        """
        Stores semantic metadata JSON and colored PLY point cloud representation.
        """
        os.makedirs(output_dir, exist_ok=True)

        # 1. Save semantic objects JSON
        objects_json_path = os.path.join(output_dir, "semantic_objects.json")
        output_payload = {
            "status": "success",
            "pipeline_point": 24,
            "engine": "VastuSemanticUnderstandingEngine",
            "total_objects_detected": len(semantic_objects),
            "objects": semantic_objects,
            "metrics": evaluation_metrics or {}
        }
        with open(objects_json_path, "w") as f:
            json.dump(output_payload, f, indent=2)

        # 2. Save colored semantic point cloud (PLY)
        ply_path = os.path.join(output_dir, "semantic_pointcloud.ply")
        with open(ply_path, "w") as f:
            f.write("ply\nformat ascii 1.0\n")
            f.write(f"element vertex {len(points_3d)}\n")
            f.write("property float x\nproperty float y\nproperty float z\n")
            f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
            f.write("property uchar class_id\n")
            f.write("end_header\n")

            for i in range(len(points_3d)):
                cid = int(class_ids[i])
                color = CLASS_COLORS.get(cid, [128, 128, 128])
                p = points_3d[i]
                f.write(f"{p[0]:.4f} {p[1]:.4f} {p[2]:.4f} {color[0]} {color[1]} {color[2]} {cid}\n")

        logger.info(f"Saved {len(semantic_objects)} semantic objects to {objects_json_path}")
        return output_payload

    # -------------------------------------------------------------------------
    # Full End-to-End Orchestrator Pipeline
    # -------------------------------------------------------------------------
    def run_pipeline(
        self,
        points_3d: np.ndarray,
        camera_poses: list,
        frames: list,
        depth_maps: list,
        intrinsics_k: np.ndarray,
        output_dir: str,
        ground_truth_labels: np.ndarray = None
    ) -> dict:
        """Executes full 7-step semantic understanding sequence."""
        logger.info("[Step 1-5] Running 2D PyTorch inference and fusing multi-view 3D semantics...")
        fused_classes, fused_confs, _ = self.fuse_multiview_semantics(
            points_3d, camera_poses, frames, depth_maps, intrinsics_k
        )

        metrics = {}
        if ground_truth_labels is not None:
            logger.info("[Step 6] Calculating Precision, Recall, F1, and IoU metrics...")
            metrics = self.calculate_evaluation_metrics(ground_truth_labels, fused_classes)

        logger.info("[Step 7] Extracting individual 3D semantic objects and bounding boxes...")
        objects = self.extract_semantic_objects(points_3d, fused_classes, fused_confs)

        metadata = self.store_semantic_assets(
            output_dir, points_3d, fused_classes, fused_confs, objects, metrics
        )
        return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VĀSTU Point 24 Semantic Understanding Engine")
    parser.add_argument("--mesh", type=str, required=True, help="Input mesh/pointcloud file")
    parser.add_argument("--frames-dir", type=str, required=True, help="Directory containing RGB keyframes")
    parser.add_argument("--poses-file", type=str, required=True, help="Camera poses and intrinsics file")
    parser.add_argument("--output-dir", type=str, required=True, help="Output directory for semantic assets")
    args = parser.parse_args()

    print(f"Launching VĀSTU Semantic Understanding Engine on {args.mesh}")
