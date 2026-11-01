"""
VĀSTU GLB Exporter
==================
Zero-dependency, high-performance Binary glTF 2.0 (.glb) exporter.
Exports clean architectural structural meshes and collision geometry with standard PBR materials,
per-vertex normals, face indices, and metric world coordinates.
Strictly adheres to glTF 2.0 specification.
"""

import os
import json
import struct
from typing import List, Optional, Tuple, Dict, Any
import numpy as np


class GLBExporter:
    """Exports triangular meshes to valid Binary glTF 2.0 (.glb) files."""

    @staticmethod
    def export(
        vertices: np.ndarray,
        faces: np.ndarray,
        normals: Optional[np.ndarray] = None,
        output_path: str = "model.glb",
        mesh_name: str = "Mesh",
        base_color_rgba: Tuple[float, float, float, float] = (0.85, 0.85, 0.85, 1.0),
        double_sided: bool = True,
        colors: Optional[np.ndarray] = None
    ) -> str:
        """
        Exports vertices and triangular faces to a standalone .glb file.

        Args:
            vertices: [N, 3] float32 array of vertex positions in metric coordinates.
            faces: [M, 3] uint32 or int32 array of triangular indices.
            normals: Optional [N, 3] float32 array of per-vertex normals.
            output_path: Target .glb file path.
            mesh_name: Name of the mesh node in the glTF hierarchy.
            base_color_rgba: Base PBR color RGBA (values in [0.0, 1.0]).
            double_sided: Whether the material is visible from both sides.

        Returns:
            The absolute path of the generated .glb file.
        """
        verts = np.asarray(vertices, dtype=np.float32).reshape(-1, 3)
        tris = np.asarray(faces, dtype=np.uint32).reshape(-1, 3)

        if len(verts) == 0 or len(tris) == 0:
            raise ValueError("Cannot export empty mesh to GLB.")

        # Compute normals if not provided
        if normals is None or len(normals) != len(verts):
            v0 = verts[tris[:, 0]]
            v1 = verts[tris[:, 1]]
            v2 = verts[tris[:, 2]]
            face_normals = np.cross(v1 - v0, v2 - v0)
            norm_mag = np.linalg.norm(face_normals, axis=1, keepdims=True)
            face_normals = face_normals / np.maximum(norm_mag, 1e-8)

            vert_normals = np.zeros_like(verts)
            for i in range(3):
                np.add.at(vert_normals, tris[:, i], face_normals)
            vert_mag = np.linalg.norm(vert_normals, axis=1, keepdims=True)
            normals = (vert_normals / np.maximum(vert_mag, 1e-8)).astype(np.float32)
        else:
            normals = np.asarray(normals, dtype=np.float32).reshape(-1, 3)

        # Flatten buffers
        pos_bytes = verts.tobytes()
        norm_bytes = normals.tobytes()
        idx_bytes = tris.tobytes()

        has_colors = False
        color_bytes = b""
        if colors is not None and len(colors) == len(verts):
            c_arr = np.asarray(colors, dtype=np.float32).reshape(-1, 3)
            if c_arr.max() > 1.0:
                c_arr = c_arr / 255.0
            color_bytes = c_arr.tobytes()
            has_colors = True

        # Align each buffer to 4 bytes
        def pad4(data: bytes, pad_byte: bytes = b"\x00") -> bytes:
            rem = len(data) % 4
            return data + (pad_byte * (4 - rem)) if rem != 0 else data

        pos_offset = 0
        pos_len = len(pos_bytes)
        norm_offset = len(pad4(pos_bytes))
        norm_len = len(norm_bytes)
        idx_offset = norm_offset + len(pad4(norm_bytes))
        idx_len = len(idx_bytes)

        bin_buffer = pad4(pos_bytes) + pad4(norm_bytes) + pad4(idx_bytes)
        col_offset = len(bin_buffer)
        col_len = len(color_bytes)
        if has_colors:
            bin_buffer += pad4(color_bytes)
        total_bin_len = len(bin_buffer)

        min_pos = verts.min(axis=0).tolist()
        max_pos = verts.max(axis=0).tolist()

        prim_attrs = {
            "POSITION": 0,
            "NORMAL": 1
        }
        if has_colors:
            prim_attrs["COLOR_0"] = 3

        accessors = [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": 5126,  # FLOAT
                "count": len(verts),
                "type": "VEC3",
                "min": min_pos,
                "max": max_pos
            },
            {
                "bufferView": 1,
                "byteOffset": 0,
                "componentType": 5126,  # FLOAT
                "count": len(normals),
                "type": "VEC3"
            },
            {
                "bufferView": 2,
                "byteOffset": 0,
                "componentType": 5125,  # UNSIGNED_INT
                "count": len(tris) * 3,
                "type": "SCALAR"
            }
        ]

        buffer_views = [
            {
                "buffer": 0,
                "byteOffset": pos_offset,
                "byteLength": pos_len,
                "target": 34962  # ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": norm_offset,
                "byteLength": norm_len,
                "target": 34962  # ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": idx_offset,
                "byteLength": idx_len,
                "target": 34963  # ELEMENT_ARRAY_BUFFER
            }
        ]

        if has_colors:
            accessors.append({
                "bufferView": 3,
                "byteOffset": 0,
                "componentType": 5126,  # FLOAT
                "count": len(verts),
                "type": "VEC3"
            })
            buffer_views.append({
                "buffer": 0,
                "byteOffset": col_offset,
                "byteLength": col_len,
                "target": 34962  # ARRAY_BUFFER
            })

        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "VASTU Metric Architectural Pipeline"
            },
            "scene": 0,
            "scenes": [
                {
                    "nodes": [0]
                }
            ],
            "nodes": [
                {
                    "name": mesh_name,
                    "mesh": 0
                }
            ],
            "meshes": [
                {
                    "name": mesh_name,
                    "primitives": [
                        {
                            "attributes": prim_attrs,
                            "indices": 2,
                            "material": 0
                        }
                    ]
                }
            ],
            "materials": [
                {
                    "name": f"{mesh_name}_Material",
                    "pbrMetallicRoughness": {
                        "baseColorFactor": list(base_color_rgba),
                        "metallicFactor": 0.05,
                        "roughnessFactor": 0.85
                    },
                    "doubleSided": bool(double_sided)
                }
            ],
            "accessors": accessors,
            "bufferViews": buffer_views,
            "buffers": [
                {
                    "byteLength": total_bin_len
                }
            ]
        }

        json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        json_padded = pad4(json_bytes, b" ")

        # GLB Header: magic (4B), version (4B), total_length (4B)
        # Chunk 0: length (4B), type "JSON" (4B), json_padded
        # Chunk 1: length (4B), type "BIN\0" (4B), bin_buffer
        total_glb_len = 12 + 8 + len(json_padded) + 8 + len(bin_buffer)

        header = struct.pack("<4sII", b"glTF", 2, total_glb_len)
        chunk0_header = struct.pack("<I4s", len(json_padded), b"JSON")
        chunk1_header = struct.pack("<I4s", len(bin_buffer), b"BIN\0")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(header)
            f.write(chunk0_header)
            f.write(json_padded)
            f.write(chunk1_header)
            f.write(bin_buffer)

        return os.path.abspath(output_path)

