"""
VĀSTU API: Uploads Router
Zero-proxy direct-to-storage resumable multipart upload management.
Tracks 7 explicit states: CREATED, UPLOADING, PAUSED, RESUMING, UPLOADED, VALIDATED, FAILED.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Optional
from pydantic import BaseModel

from core.schemas.upload_session import (
    CreateUploadSessionRequest,
    UploadSessionResponse,
    CompleteUploadSessionRequest
)
from core.upload.session_manager import UploadSessionManager

router = APIRouter(prefix="/uploads", tags=["Uploads"])

# Global upload session manager instance (backed by configured storage adapter)
_session_manager = UploadSessionManager()


def get_upload_session_manager() -> UploadSessionManager:
    return _session_manager


class RecordPartRequest(BaseModel):
    etag: str
    sha256: Optional[str] = None


@router.post("/", response_model=UploadSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_upload_session(req: CreateUploadSessionRequest):
    """
    Creates a new resumable chunked upload session or returns existing session
    if matching idempotency key or active artifact capture session is found.
    Directs the client to upload parts directly to presigned storage URLs.
    """
    try:
        session = _session_manager.create_session(req)
        return session
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}", response_model=UploadSessionResponse)
async def get_upload_session(session_id: str):
    """
    Retrieves the current status, state, missing chunks, and presigned URLs of an upload session.
    """
    try:
        return _session_manager.get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Upload session '{session_id}' not found")


@router.post("/{session_id}/pause", response_model=UploadSessionResponse)
async def pause_upload_session(session_id: str):
    """
    Pauses an active upload session.
    """
    try:
        return _session_manager.pause_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Upload session '{session_id}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/resume", response_model=UploadSessionResponse)
async def resume_upload_session(session_id: str):
    """
    Resumes a paused upload session, refreshing presigned URLs for all pending/missing chunks.
    """
    try:
        return _session_manager.resume_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Upload session '{session_id}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/parts/{chunk_index}", response_model=UploadSessionResponse)
async def record_uploaded_part(session_id: str, chunk_index: int, req: RecordPartRequest):
    """
    Notifies the control plane that a chunk was successfully uploaded directly to storage.
    """
    try:
        return _session_manager.record_chunk_uploaded(
            session_id=session_id,
            chunk_index=chunk_index,
            etag=req.etag,
            sha256=req.sha256
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Upload session '{session_id}' not found")
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/complete", response_model=UploadSessionResponse)
async def complete_upload_session(session_id: str, req: Optional[CompleteUploadSessionRequest] = None):
    """
    Finalizes the multipart upload, stitches chunks in storage, and verifies
    the whole-file SHA-256 integrity checksum. Transitions session to VALIDATED.
    """
    try:
        parts = req.parts if req else None
        return _session_manager.complete_session(session_id, parts=parts)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Upload session '{session_id}' not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/abort", response_model=UploadSessionResponse)
async def abort_upload_session(session_id: str):
    """
    Aborts the multipart upload session and cleans up temporary parts in storage.
    """
    try:
        return _session_manager.abort_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Upload session '{session_id}' not found")
