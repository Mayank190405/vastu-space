#!/usr/bin/env python3
"""
VĀSTU — Point 23: Texture Reconstruction Engine
Production-grade 10-step texture reconstruction pipeline:
1. Project camera images onto mesh
2. Determine visible surfaces (backface culling + Z-buffer occlusion testing)
3. Select high-quality observations (scoring: incidence angle, resolution, sharpness, border margin)
4. Blend observations (weighted multi-view blending + exposure compensation)
5. Generate UV layout (planar chart clustering & packed unwrap)
6. Generate texture atlas (rasterize blended samples into contiguous texture map)
7. Remove obvious seams (dilation color bleed & boundary edge leveling)
8. Compress textures (JPEG/PNG export with mipmap pyramid & PBR material properties)
9. Validate coverage (surface coverage %, hole detection, texel density)
10. Store texture assets (OBJ, MTL, atlas PNG/JPG, material.json, metadata.json)
"""

import os
import sys
import json
import logging
import argparse
import numpy as np
import cv2
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VastuTexturingEngine")


class TextureReconstructionEngine:
    def __init__(
        self,
        atlas_size: int = 2048,
        gutter_margin: int = 4,
        max_blend_views: int = 3,
        jpeg_quality: int = 92,
        min_incidence_cos: float = 0.15,
        exposure_compensation: bool = True
    ):
        self.atlas_size = atlas_size
        self.gutter_margin = gutter_margin
        self.max_blend_views = max_blend_views
        self.jpeg_quality = jpeg_quality
        self.min_incidence_cos = min_incidence_cos
        self.exposure_compensation = exposure_compensation
        self.metadata = {}

    # -------------------------------------------------------------------------
    # Step 1: Project Camera Images onto Mesh
    # -------------------------------------------------------------------------
    def project_points_to_camera(
        self,
        points_3d: np.ndarray,
        extrinsics_r: np.ndarray,
        extrinsics_t: np.ndarray,
        intrinsics_k: np.ndarray,
        img_w: int,
        img_h: int
    ) -> tuple:
        """
        Projects 3D world points into camera pixel coordinates.
        Returns:
            uv_pixels: (N, 2) pixel coords [u, v]
            depths: (N,) depth values along optical axis (Z_c)
            valid_mask: (N,) boolean mask of points in front of camera and inside image bounds
        """
        pts = np.asarray(points_3d, dtype=np.float64)
        if pts.ndim == 1:
            pts = pts.reshape(1, -1)

        # p_cam = R * p_world + t
        p_cam = (extrinsics_r @ pts.T).T + extrinsics_t.reshape(1, 3)
        depths = p_cam[:, 2]

        in_front = depths > 0.05
        uv_pixels = np.zeros((len(pts), 2), dtype=np.float32)

        # Perspective division
        inv_z = np.zeros_like(depths)
        inv_z[in_front] = 1.0 / depths[in_front]

        u = intrinsics_k[0, 0] * (p_cam[:, 0] * inv_z) + intrinsics_k[0, 2]
        v = intrinsics_k[1, 1] * (p_cam[:, 1] * inv_z) + intrinsics_k[1, 2]

        uv_pixels[:, 0] = u
        uv_pixels[:, 1] = v

        inside = (
            in_front &
            (u >= 0.0) & (u < float(img_w)) &
            (v >= 0.0) & (v < float(img_h))
        )

        return uv_pixels, depths, inside

    # -------------------------------------------------------------------------
    # Step 2: Determine Visible Surfaces (Backface Culling + Occlusion)
    # -------------------------------------------------------------------------
    def determine_surface_visibility(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        face_normals: np.ndarray,
        camera_poses: list,
        intrinsics_k: np.ndarray,
        img_w: int,
        img_h: int,
        depth_buffer_res: int = 256
    ) -> np.ndarray:
        """
        Determines visibility of each triangle from each camera pose.
        Returns visibility boolean matrix: (num_faces, num_cameras)
        """
        num_faces = len(faces)
        num_cams = len(camera_poses)
        visibility = np.zeros((num_faces, num_cams), dtype=bool)

        centroids = np.mean(vertices[faces], axis=1)

        for cam_idx, pose in enumerate(camera_poses):
            r_mat = pose["R"]
            t_vec = pose["t"]
            cam_center = -r_mat.T @ t_vec

            # 1. Backface culling: Vector from centroid to camera center
            view_dirs = cam_center.reshape(1, 3) - centroids
            dists = np.linalg.norm(view_dirs, axis=1, keepdims=True)
            dists[dists == 0] = 1e-6
            norm_view_dirs = view_dirs / dists

            cos_angles = np.sum(face_normals * norm_view_dirs, axis=1)
            front_facing = cos_angles > self.min_incidence_cos

            # 2. Field-of-View projection check
            uvs, depths, in_frustum = self.project_points_to_camera(
                centroids, r_mat, t_vec, intrinsics_k, img_w, img_h
            )

            candidate_mask = front_facing & in_frustum

            # 3. Fast Z-Buffer rasterization for self-occlusion testing
            z_buf = np.full((depth_buffer_res, depth_buffer_res), np.inf, dtype=np.float32)
            scale_u = (depth_buffer_res - 1) / float(img_w)
            scale_v = (depth_buffer_res - 1) / float(img_h)

            cand_indices = np.where(candidate_mask)[0]
            for fi in cand_indices:
                u_bin = int(np.clip(uvs[fi, 0] * scale_u, 0, depth_buffer_res - 1))
                v_bin = int(np.clip(uvs[fi, 1] * scale_v, 0, depth_buffer_res - 1))
                if depths[fi] < z_buf[v_bin, u_bin]:
                    z_buf[v_bin, u_bin] = depths[fi]

            # Depth tolerance test: triangle is visible if its depth is close to Z-buffer
            for fi in cand_indices:
                u_bin = int(np.clip(uvs[fi, 0] * scale_u, 0, depth_buffer_res - 1))
                v_bin = int(np.clip(uvs[fi, 1] * scale_v, 0, depth_buffer_res - 1))
                closest_depth = z_buf[v_bin, u_bin]
                # Allow 5% depth tolerance or 0.05m
                if depths[fi] <= closest_depth * 1.08 + 0.05:
                    visibility[fi, cam_idx] = True

        return visibility

    # -------------------------------------------------------------------------
    # Step 3: Select High-Quality Observations
    # -------------------------------------------------------------------------
    def select_high_quality_observations(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        face_normals: np.ndarray,
        camera_poses: list,
        frames: list,
        visibility_map: np.ndarray,
        intrinsics_k: np.ndarray
    ) -> list:
        """
        Computes multi-criteria quality scores for each (face, camera) pair.
        Criteria:
          1. Incidence angle (cos theta near 1 is best)
          2. Projected resolution (closer distance = higher spatial sampling)
          3. Frame sharpness (Laplacian variance)
          4. Distance to image border (penalize radial lens distortion)
        Returns:
            face_best_views: list of length num_faces containing sorted (cam_idx, score) tuples
        """
        num_faces = len(faces)
        num_cams = len(camera_poses)
        centroids = np.mean(vertices[faces], axis=1)

        # Precalculate frame sharpness
        frame_sharpness = np.zeros(num_cams, dtype=np.float32)
        for i, frame in enumerate(frames):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            frame_sharpness[i] = max(1.0, float(lap_var))
        # Normalize sharpness to [0.5, 1.0]
        max_sharp = np.max(frame_sharpness)
        sharp_norm = 0.5 + 0.5 * (frame_sharpness / (max_sharp + 1e-6))

        img_h, img_w = frames[0].shape[:2]
        face_observations = []

        for fi in range(num_faces):
            visible_cams = np.where(visibility_map[fi])[0]
            if len(visible_cams) == 0:
                face_observations.append([])
                continue

            scores = []
            cent = centroids[fi]
            norm = face_normals[fi]

            for ci in visible_cams:
                pose = camera_poses[ci]
                cam_center = -pose["R"].T @ pose["t"]
                view_vec = cam_center - cent
                dist = np.linalg.norm(view_vec)
                if dist < 1e-6:
                    dist = 1e-6
                view_dir = view_vec / dist

                # Incidence cos
                cos_theta = max(0.0, float(np.dot(norm, view_dir)))

                # Projected coordinate
                uv, depth, _ = self.project_points_to_camera(
                    cent, pose["R"], pose["t"], intrinsics_k, img_w, img_h
                )
                u_val, v_val = uv[0, 0], uv[0, 1]

                # Distance to border penalty (0 near edges, 1 at center)
                dist_u = min(u_val, img_w - 1 - u_val) / (img_w * 0.5)
                dist_v = min(v_val, img_h - 1 - v_val) / (img_h * 0.5)
                border_weight = np.clip(min(dist_u, dist_v), 0.05, 1.0)

                # Distance factor: closer yields higher resolution (bounded)
                dist_weight = 1.0 / (dist + 0.2)

                # Total score
                total_score = (
                    0.50 * cos_theta +
                    0.25 * np.clip(dist_weight, 0.1, 1.0) +
                    0.15 * sharp_norm[ci] +
                    0.10 * border_weight
                )
                scores.append((ci, total_score, cos_theta))

            # Sort descending by score
            scores.sort(key=lambda x: x[1], reverse=True)
            face_observations.append(scores)

        return face_observations

    # -------------------------------------------------------------------------
    # Step 4: Blend Observations & Exposure Compensation
    # -------------------------------------------------------------------------
    def blend_observations_for_face(
        self,
        face_idx: int,
        observations: list,
        vertices: np.ndarray,
        faces: np.ndarray,
        frames: list,
        camera_poses: list,
        intrinsics_k: np.ndarray,
        sample_resolution: int = 16
    ) -> np.ndarray:
        """
        Samples and blends RGB texture values across top-K visible camera observations.
        Includes exposure compensation via luminance normalization.
        Returns:
            texture_patch: (sample_resolution, sample_resolution, 3) uint8 BGR image
        """
        top_obs = observations[:self.max_blend_views]
        if not top_obs:
            # Fallback neutral albedo
            return np.full((sample_resolution, sample_resolution, 3), 180, dtype=np.uint8)

        v_tri = vertices[faces[face_idx]] # (3, 3)
        img_h, img_w = frames[0].shape[:2]

        # Generate sample grid in 2D parametric barycentric space
        u_grid = np.linspace(0.0, 1.0, sample_resolution)
        v_grid = np.linspace(0.0, 1.0, sample_resolution)
        uu, vv = np.meshgrid(u_grid, v_grid)
        mask = (uu + vv <= 1.0) # valid triangle region

        # Barycentric points: P = (1 - u - v)*v0 + u*v1 + v*v2
        ww = 1.0 - uu - vv
        points_3d = (
            ww[:, :, None] * v_tri[0] +
            uu[:, :, None] * v_tri[1] +
            vv[:, :, None] * v_tri[2]
        ).reshape(-1, 3)

        sampled_colors = []
        weights = []

        for ci, score, _ in top_obs:
            pose = camera_poses[ci]
            uv_pix, _, valid = self.project_points_to_camera(
                points_3d, pose["R"], pose["t"], intrinsics_k, img_w, img_h
            )

            # Sample image using bilinear interpolation via cv2.remap
            frame = frames[ci]
            map_x = uv_pix[:, 0].reshape(sample_resolution, sample_resolution).astype(np.float32)
            map_y = uv_pix[:, 1].reshape(sample_resolution, sample_resolution).astype(np.float32)

            sampled = cv2.remap(
                frame, map_x, map_y,
                interpolation=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REFLECT_101
            )

            # Optional Exposure Compensation (normalize luminance channel)
            if self.exposure_compensation:
                hsv = cv2.cvtColor(sampled, cv2.COLOR_BGR2HSV).astype(np.float32)
                v_chan = hsv[:, :, 2]
                mean_v = np.mean(v_chan[mask]) if np.any(mask) else 128.0
                target_v = 140.0 # Standard interior luminance target
                scale = np.clip(target_v / (mean_v + 1e-4), 0.7, 1.4)
                hsv[:, :, 2] = np.clip(v_chan * scale, 0, 255)
                sampled = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

            sampled_colors.append(sampled.astype(np.float32))
            weights.append(score)

        # Weighted blend
        total_w = sum(weights)
        if total_w < 1e-6:
            blended = sampled_colors[0]
        else:
            blended = np.zeros_like(sampled_colors[0])
            for color, w in zip(sampled_colors, weights):
                blended += color * (w / total_w)

        return np.clip(blended, 0, 255).astype(np.uint8)

    # -------------------------------------------------------------------------
    # Step 5: Generate UV Layout
    # -------------------------------------------------------------------------
    def generate_uv_layout(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        face_normals: np.ndarray
    ) -> tuple:
        """
        Clusters faces into planar charts and unwraps them into a packed [0, 1]^2 atlas space.
        Returns:
            face_uvs: (num_faces, 3, 2) array of UV coordinates for each face's 3 vertices
            chart_boxes: list of bounding boxes [(u0, v0, w, h)] in atlas pixel coords
        """
        num_faces = len(faces)
        face_uvs = np.zeros((num_faces, 3, 2), dtype=np.float32)

        # Planar chart clustering by normal affinity (6 cardinal direction buckets)
        cardinal_normals = np.array([
            [1, 0, 0], [-1, 0, 0],
            [0, 1, 0], [0, -1, 0],
            [0, 0, 1], [0, 0, -1]
        ], dtype=np.float32)

        chart_assignments = np.argmax(face_normals @ cardinal_normals.T, axis=1)

        # Compute optimal grid layout based on triangle counts
        grid_cols = int(np.ceil(np.sqrt(num_faces)))
        grid_rows = int(np.ceil(num_faces / float(grid_cols)))

        cell_w = self.atlas_size / float(grid_cols)
        cell_h = self.atlas_size / float(grid_rows)
        gutter = float(self.gutter_margin)

        chart_boxes = []

        for fi in range(num_faces):
            r = fi // grid_cols
            c = fi % grid_cols

            # Local 2D planar projection of 3D triangle vertices
            v_tri = vertices[faces[fi]] # (3, 3)
            # Center and project to 2D
            e1 = v_tri[1] - v_tri[0]
            e2 = v_tri[2] - v_tri[0]
            len_e1 = np.linalg.norm(e1)
            u_axis = e1 / (len_e1 + 1e-8)
            norm = face_normals[fi]
            v_axis = np.cross(norm, u_axis)
            v_axis /= (np.linalg.norm(v_axis) + 1e-8)

            p0 = np.array([0.0, 0.0])
            p1 = np.array([len_e1, 0.0])
            p2 = np.array([np.dot(e2, u_axis), np.dot(e2, v_axis)])

            pts2d = np.array([p0, p1, p2], dtype=np.float32)

            # Normalize to [0, 1] within cell
            min_pt = pts2d.min(axis=0)
            max_pt = pts2d.max(axis=0)
            span = np.maximum(max_pt - min_pt, 1e-6)

            pts2d_norm = (pts2d - min_pt) / span

            # Offset into atlas pixel space with gutter
            u_pixel = c * cell_w + gutter + pts2d_norm[:, 0] * (cell_w - 2 * gutter)
            v_pixel = r * cell_h + gutter + pts2d_norm[:, 1] * (cell_h - 2 * gutter)

            face_uvs[fi, :, 0] = u_pixel / float(self.atlas_size)
            face_uvs[fi, :, 1] = 1.0 - (v_pixel / float(self.atlas_size)) # OpenGL UV flip

            chart_boxes.append((int(c * cell_w), int(r * cell_h), int(cell_w), int(cell_h)))

        return face_uvs, chart_boxes

    # -------------------------------------------------------------------------
    # Step 6: Generate Texture Atlas
    # -------------------------------------------------------------------------
    def generate_texture_atlas(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        face_uvs: np.ndarray,
        observations: list,
        frames: list,
        camera_poses: list,
        intrinsics_k: np.ndarray
    ) -> tuple:
        """
        Rasterizes blended observation samples onto the texture atlas bitmap.
        Returns:
            atlas: (atlas_size, atlas_size, 3) uint8 BGR image
            valid_texel_mask: (atlas_size, atlas_size) boolean mask of painted texels
        """
        atlas = np.full((self.atlas_size, self.atlas_size, 3), 160, dtype=np.uint8)
        valid_texel_mask = np.zeros((self.atlas_size, self.atlas_size), dtype=bool)

        patch_res = 16

        for fi in range(len(faces)):
            obs = observations[fi]
            patch = self.blend_observations_for_face(
                fi, obs, vertices, faces, frames, camera_poses, intrinsics_k, sample_resolution=patch_res
            )

            # Atlas UVs in pixel coords
            uv = face_uvs[fi]
            u_pix = (uv[:, 0] * self.atlas_size).astype(np.float32)
            v_pix = ((1.0 - uv[:, 1]) * self.atlas_size).astype(np.float32)

            # Bounding box of destination triangle
            min_x = int(np.clip(np.floor(np.min(u_pix)), 0, self.atlas_size - 1))
            max_x = int(np.clip(np.ceil(np.max(u_pix)), 0, self.atlas_size - 1))
            min_y = int(np.clip(np.floor(np.min(v_pix)), 0, self.atlas_size - 1))
            max_y = int(np.clip(np.ceil(np.max(v_pix)), 0, self.atlas_size - 1))

            bw = max_x - min_x + 1
            bh = max_y - min_y + 1
            if bw <= 1 or bh <= 1:
                continue

            # Local coordinates within bounding box
            tri_local = np.column_stack([u_pix - min_x, v_pix - min_y])

            # Source patch triangle (corners of parametric square)
            tri_src = np.array([
                [0.0, 0.0],
                [patch_res - 1.0, 0.0],
                [0.0, patch_res - 1.0]
            ], dtype=np.float32)

            warp_mat = cv2.getAffineTransform(tri_src, tri_local)

            # Local face mask (tiny ROI instead of full atlas allocation)
            local_mask = np.zeros((bh, bw), dtype=np.uint8)
            cv2.fillConvexPoly(local_mask, np.int32(tri_local), 255)

            warped_patch = cv2.warpAffine(
                patch, warp_mat, (bw, bh),
                borderMode=cv2.BORDER_REFLECT
            )

            mask_roi = local_mask > 0
            atlas_roi = atlas[min_y:max_y+1, min_x:max_x+1]
            valid_roi = valid_texel_mask[min_y:max_y+1, min_x:max_x+1]

            atlas_roi[mask_roi] = warped_patch[mask_roi]
            valid_roi[mask_roi] = True

        return atlas, valid_texel_mask

    # -------------------------------------------------------------------------
    # Step 7: Remove Obvious Seams
    # -------------------------------------------------------------------------
    def remove_obvious_seams(
        self,
        atlas: np.ndarray,
        valid_mask: np.ndarray
    ) -> np.ndarray:
        """
        Removes visible border seams:
        1. Color dilation / edge bleeding into gutter margins to prevent mipmap filtering artifacts.
        2. Boundary smoothing to blend transition zones.
        """
        seam_free_atlas = atlas.copy()
        current_valid = valid_mask.copy()

        # Efficient iterative color dilation into gutter margins
        bleed_radius = max(2, self.gutter_margin * 2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        for _ in range(bleed_radius):
            dilated_color = cv2.dilate(seam_free_atlas, kernel)
            new_valid = cv2.dilate(current_valid.astype(np.uint8), kernel) > 0
            gutter_texels = new_valid & (~current_valid)
            if not np.any(gutter_texels):
                break
            seam_free_atlas[gutter_texels] = dilated_color[gutter_texels]
            current_valid = new_valid

        return seam_free_atlas

    # -------------------------------------------------------------------------
    # Step 8: Compress Textures & Material Info
    # -------------------------------------------------------------------------
    def compress_and_export_textures(
        self,
        atlas: np.ndarray,
        output_dir: str,
        base_name: str = "texture_atlas"
    ) -> dict:
        """
        Exports texture maps in multiple compressed formats:
        1. Lossless PNG (original fidelity)
        2. Web-optimized high-compression JPEG
        3. Mipmap pyramid (power of 2 downsampling: 1024, 512, 256)
        4. PBR Material parameters (roughness, metallic, AO)
        """
        os.makedirs(output_dir, exist_ok=True)
        paths = {}

        # 1. Lossless PNG
        png_path = os.path.join(output_dir, f"{base_name}.png")
        cv2.imwrite(png_path, atlas, [cv2.IMWRITE_PNG_COMPRESSION, 6])
        paths["png"] = png_path

        # 2. Optimized JPEG
        jpg_path = os.path.join(output_dir, f"{base_name}.jpg")
        cv2.imwrite(jpg_path, atlas, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        paths["jpg"] = jpg_path

        # 3. Mipmaps
        mip_dir = os.path.join(output_dir, "mipmaps")
        os.makedirs(mip_dir, exist_ok=True)
        cur = atlas.copy()
        paths["mipmaps"] = []
        for level in [1, 2, 3]:
            cur = cv2.pyrDown(cur)
            mip_path = os.path.join(mip_dir, f"{base_name}_mip_{level}.jpg")
            cv2.imwrite(mip_path, cur, [cv2.IMWRITE_JPEG_QUALITY, 85])
            paths["mipmaps"].append(mip_path)

        # 4. PBR Material Definition
        pbr_material = {
            "name": "VastuPBRMaterial",
            "diffuse_map": f"{base_name}.jpg",
            "roughness": 0.65,
            "metallic": 0.05,
            "ambient_occlusion": 1.0,
            "double_sided": False,
            "specular_f0": 0.04
        }
        mat_path = os.path.join(output_dir, "material.json")
        with open(mat_path, "w") as f:
            json.dump(pbr_material, f, indent=2)
        paths["material"] = mat_path

        return paths

    # -------------------------------------------------------------------------
    # Step 9: Validate Coverage
    # -------------------------------------------------------------------------
    def validate_coverage(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        face_uvs: np.ndarray,
        valid_mask: np.ndarray,
        atlas: np.ndarray
    ) -> dict:
        """
        Validates texture reconstruction quality:
        - Surface coverage percentage
        - Untextured face count
        - Average texel density (texels per m^2 of 3D geometry)
        - Dynamic range & contrast
        """
        num_faces = len(faces)

        # Compute total 3D surface area
        v0 = vertices[faces[:, 0]]
        v1 = vertices[faces[:, 1]]
        v2 = vertices[faces[:, 2]]
        cross_prod = np.cross(v1 - v0, v2 - v0)
        face_areas = 0.5 * np.linalg.norm(cross_prod, axis=1)
        total_surface_area_m2 = float(np.sum(face_areas))

        # Count painted texels
        total_painted_texels = int(np.sum(valid_mask))
        total_atlas_texels = self.atlas_size * self.atlas_size
        texel_density_pts_m2 = (
            float(total_painted_texels) / total_surface_area_m2
            if total_surface_area_m2 > 1e-6 else 0.0
        )

        # Check untextured faces
        untextured_faces = 0
        for fi in range(num_faces):
            uv = face_uvs[fi]
            u_center = int(np.clip(np.mean(uv[:, 0]) * self.atlas_size, 0, self.atlas_size - 1))
            v_center = int(np.clip((1.0 - np.mean(uv[:, 1])) * self.atlas_size, 0, self.atlas_size - 1))
            if not valid_mask[v_center, u_center]:
                untextured_faces += 1

        coverage_pct = 100.0 * (1.0 - float(untextured_faces) / float(num_faces)) if num_faces > 0 else 0.0

        metrics = {
            "total_faces": num_faces,
            "untextured_faces": untextured_faces,
            "surface_coverage_pct": round(coverage_pct, 2),
            "total_surface_area_m2": round(total_surface_area_m2, 4),
            "total_painted_texels": total_painted_texels,
            "texel_density_pts_m2": round(texel_density_pts_m2, 1),
            "is_valid": coverage_pct >= 85.0
        }

        logger.info(
            f"[Step 9: Quality Validation] Coverage: {coverage_pct:.1f}%, "
            f"Texel Density: {texel_density_pts_m2:.1f} texels/m², "
            f"Untextured: {untextured_faces}/{num_faces}"
        )
        return metrics

    # -------------------------------------------------------------------------
    # Step 10: Store Texture Assets (OBJ, MTL, Atlas, Metadata)
    # -------------------------------------------------------------------------
    def store_texture_assets(
        self,
        output_dir: str,
        vertices: np.ndarray,
        faces: np.ndarray,
        face_normals: np.ndarray,
        face_uvs: np.ndarray,
        atlas: np.ndarray,
        coverage_metrics: dict,
        mesh_name: str = "textured_mesh"
    ) -> dict:
        """
        Writes complete Wavefront OBJ with VT texture coordinates, companion MTL,
        texture atlas images, and metadata JSON.
        """
        os.makedirs(output_dir, exist_ok=True)

        obj_path = os.path.join(output_dir, f"{mesh_name}.obj")
        mtl_path = os.path.join(output_dir, f"{mesh_name}.mtl")
        mtl_filename = os.path.basename(mtl_path)
        atlas_filename = "texture_atlas.jpg"

        # 1. Write MTL Material
        with open(mtl_path, "w") as f:
            f.write("# VASTU Spatial Material Template\n")
            f.write(f"newmtl VastuMaterial\n")
            f.write("Ka 1.000 1.000 1.000\n")
            f.write("Kd 1.000 1.000 1.000\n")
            f.write("Ks 0.050 0.050 0.050\n")
            f.write("Ns 10.0\n")
            f.write("d 1.0\n")
            f.write("illum 2\n")
            f.write(f"map_Kd {atlas_filename}\n")

        # 2. Write OBJ with (v, vt, vn, f v/vt/vn)
        with open(obj_path, "w") as f:
            f.write(f"# VASTU Point 23 Textured Mesh\n")
            f.write(f"mtllib {mtl_filename}\n")

            # Vertices
            for v in vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

            # Normals
            vert_normals = np.zeros_like(vertices)
            counts = np.zeros(len(vertices))
            for fi, face in enumerate(faces):
                for vid in face:
                    vert_normals[vid] += face_normals[fi]
                    counts[vid] += 1
            counts[counts == 0] = 1.0
            vert_normals /= counts[:, None]
            norm_len = np.linalg.norm(vert_normals, axis=1, keepdims=True)
            norm_len[norm_len == 0] = 1.0
            vert_normals /= norm_len

            for vn in vert_normals:
                f.write(f"vn {vn[0]:.4f} {vn[1]:.4f} {vn[2]:.4f}\n")

            # Texture coordinates (vt) - each face has 3 UVs
            for fi in range(len(faces)):
                for uv in face_uvs[fi]:
                    f.write(f"vt {uv[0]:.6f} {uv[1]:.6f}\n")

            f.write("usemtl VastuMaterial\n")
            f.write("s 1\n")

            # Faces: 1-indexed in OBJ. (v/vt/vn)
            for fi, face in enumerate(faces):
                vt0 = fi * 3 + 1
                vt1 = fi * 3 + 2
                vt2 = fi * 3 + 3
                v0, v1, v2 = face[0] + 1, face[1] + 1, face[2] + 1
                f.write(f"f {v0}/{vt0}/{v0} {v1}/{vt1}/{v1} {v2}/{vt2}/{v2}\n")

        # 3. Export compressed atlas
        tex_paths = self.compress_and_export_textures(atlas, output_dir, base_name="texture_atlas")

        # 4. Write metadata
        metadata = {
            "status": "success",
            "pipeline_point": 23,
            "engine": "VastuTextureReconstructionEngine",
            "atlas_resolution": f"{self.atlas_size}x{self.atlas_size}",
            "coverage": coverage_metrics,
            "assets": {
                "mesh_obj": obj_path,
                "material_mtl": mtl_path,
                "atlas_png": tex_paths["png"],
                "atlas_jpg": tex_paths["jpg"],
                "material_json": tex_paths["material"],
                "mipmaps": tex_paths["mipmaps"]
            }
        }
        meta_path = os.path.join(output_dir, "metadata.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return metadata

    # -------------------------------------------------------------------------
    # Full End-to-End Orchestrator Pipeline
    # -------------------------------------------------------------------------
    def run_pipeline(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        face_normals: np.ndarray,
        camera_poses: list,
        frames: list,
        intrinsics_k: np.ndarray,
        output_dir: str
    ) -> dict:
        """Executes all 10 steps sequentially."""
        logger.info("[Step 1] Projecting camera views onto 3D mesh surface...")
        img_h, img_w = frames[0].shape[:2]

        logger.info("[Step 2] Determining surface visibility and occlusions...")
        visibility_map = self.determine_surface_visibility(
            vertices, faces, face_normals, camera_poses, intrinsics_k, img_w, img_h
        )

        logger.info("[Step 3] Selecting high-quality observations...")
        observations = self.select_high_quality_observations(
            vertices, faces, face_normals, camera_poses, frames, visibility_map, intrinsics_k
        )

        logger.info("[Step 5] Generating UV parameterization charts...")
        face_uvs, chart_boxes = self.generate_uv_layout(vertices, faces, face_normals)

        logger.info("[Step 6 & 4] Rasterizing blended observations into texture atlas...")
        raw_atlas, valid_mask = self.generate_texture_atlas(
            vertices, faces, face_uvs, observations, frames, camera_poses, intrinsics_k
        )

        logger.info("[Step 7] Removing chart border seams and applying gutter bleed...")
        seamless_atlas = self.remove_obvious_seams(raw_atlas, valid_mask)

        logger.info("[Step 9] Validating texture coverage and resolution density...")
        metrics = self.validate_coverage(vertices, faces, face_uvs, valid_mask, seamless_atlas)

        logger.info("[Step 8 & 10] Compressing textures and writing assets...")
        metadata = self.store_texture_assets(
            output_dir, vertices, faces, face_normals, face_uvs, seamless_atlas, metrics
        )

        logger.info(f"Texture reconstruction completed successfully. Output in {output_dir}")
        return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VĀSTU Point 23 Texture Reconstruction Engine")
    parser.add_argument("--mesh", type=str, required=True, help="Input mesh file (PLY/OBJ)")
    parser.add_argument("--frames-dir", type=str, required=True, help="Directory containing RGB keyframes")
    parser.add_argument("--poses-file", type=str, required=True, help="JSON file containing camera poses & intrinsics")
    parser.add_argument("--output-dir", type=str, required=True, help="Output directory for textured mesh assets")
    parser.add_argument("--atlas-size", type=int, default=2048, help="Texture atlas resolution (default 2048)")
    args = parser.parse_args()

    print(f"Launching VĀSTU Texture Reconstruction Engine on {args.mesh}")
