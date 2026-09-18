"""
VĀSTU Upload Pipeline: Upload Session Schemas
Defines the explicit 7 states and request/response models for resumable chunked uploads.
"""

from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import uuid

class UploadSessionState(str, Enum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    PAUSED = "PAUSED"
    RESUMING = "RESUMING"
    UPLOADED = "UPLOADED"
    VALIDATED = "VALIDATED"
    FAILED = "FAILED"


class CreateUploadSessionRequest(BaseModel):
    capture_id: uuid.UUID
    project_id: uuid.UUID
    artifact_name: str
    total_size_bytes: int = Field(gt=0)
    chunk_size_bytes: int = Field(default=5 * 1024 * 1024, gt=0)  # 5MB default
    total_chunks: int = Field(gt=0)
    sha256_checksum: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    idempotency_key: Optional[str] = None


class UploadChunkMeta(BaseModel):
    chunk_index: int
    offset_bytes: int
    length_bytes: int
    presigned_url: str
    is_uploaded: bool = False
    sha256: Optional[str] = None
    etag: Optional[str] = None


class UploadSessionResponse(BaseModel):
    session_id: str
    state: UploadSessionState
    capture_id: str
    project_id: str
    artifact_name: str
    total_size_bytes: int
    chunk_size_bytes: int
    total_chunks: int
    uploaded_chunks_count: int
    missing_chunks: List[int]
    presigned_urls: Dict[int, str]
    sha256_checksum: str
    created_at: str
    updated_at: str


class CompleteUploadSessionRequest(BaseModel):
    parts: Optional[List[Dict[str, Any]]] = None
