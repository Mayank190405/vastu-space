"""
VĀSTU Mobile Capture: Upload Queue Preparation
Chunks finalized captures into atomic 5MB upload parts with SHA-256 checksums.
"""

import os
import hashlib
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class UploadChunk(BaseModel):
    chunk_index: int
    offset_bytes: int
    length_bytes: int
    sha256: str


class UploadQueueItem(BaseModel):
    capture_id: str
    project_id: str
    artifact_name: str
    local_file_path: str
    total_size_bytes: int
    total_chunks: int
    chunks: List[UploadChunk]
    status: str = "PENDING"  # PENDING, UPLOADING, COMPLETED, FAILED


class UploadQueueManager:
    DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB

    @classmethod
    def prepare_file_chunks(
        cls,
        file_path: str,
        capture_id: str,
        project_id: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE
    ) -> UploadQueueItem:
        """
        Splits a physical asset into deterministic upload chunks with per-chunk checksums.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Cannot prepare upload: file missing {file_path}")

        total_size = os.path.getsize(file_path)
        chunks: List[UploadChunk] = []

        chunk_idx = 0
        offset = 0

        with open(file_path, "rb") as f:
            while offset < total_size:
                data = f.read(chunk_size)
                if not data:
                    break
                c_sha = hashlib.sha256(data).hexdigest()
                c_len = len(data)

                chunks.append(
                    UploadChunk(
                        chunk_index=chunk_idx,
                        offset_bytes=offset,
                        length_bytes=c_len,
                        sha256=c_sha
                    )
                )

                offset += c_len
                chunk_idx += 1

        return UploadQueueItem(
            capture_id=str(capture_id),
            project_id=str(project_id),
            artifact_name=os.path.basename(file_path),
            local_file_path=file_path,
            total_size_bytes=total_size,
            total_chunks=len(chunks),
            chunks=chunks
        )
