"""
VĀSTU Upload Session Manager
Orchestrates the lifecycle of chunked, resumable multipart uploads across the 7 explicit states:
CREATED -> UPLOADING -> PAUSED -> RESUMING -> UPLOADED -> VALIDATED -> FAILED.
Direct-to-storage architecture (zero API proxying).
"""

import time
import uuid
import hashlib
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from core.schemas.upload_session import (
    UploadSessionState,
    CreateUploadSessionRequest,
    UploadSessionResponse,
    UploadChunkMeta,
)
from storage.base import StorageAdapter
from storage.local_adapter import LocalStorageAdapter

logger = logging.getLogger("vastu.upload.session")


class UploadSessionRecord:
    """Internal session tracking record."""
    def __init__(
        self,
        session_id: str,
        capture_id: str,
        project_id: str,
        artifact_name: str,
        remote_key: str,
        upload_id: str,
        total_size_bytes: int,
        chunk_size_bytes: int,
        total_chunks: int,
        sha256_checksum: str,
        idempotency_key: Optional[str] = None
    ):
        self.session_id = session_id
        self.capture_id = capture_id
        self.project_id = project_id
        self.artifact_name = artifact_name
        self.remote_key = remote_key
        self.upload_id = upload_id
        self.total_size_bytes = total_size_bytes
        self.chunk_size_bytes = chunk_size_bytes
        self.total_chunks = total_chunks
        self.sha256_checksum = sha256_checksum
        self.idempotency_key = idempotency_key

        self.state = UploadSessionState.CREATED
        self.chunks: Dict[int, UploadChunkMeta] = {}
        self.presigned_urls: Dict[int, str] = {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
        self.final_uri: Optional[str] = None
        self.error_message: Optional[str] = None


class UploadSessionManager:
    """
    Manages multipart upload sessions with state tracking, resumption,
    duplicate prevention, and whole-file checksum verification.
    """
    def __init__(self, storage_adapter: Optional[StorageAdapter] = None):
        self.storage: StorageAdapter = storage_adapter or LocalStorageAdapter()
        self._sessions: Dict[str, UploadSessionRecord] = {}
        self._idempotency_map: Dict[str, str] = {}  # idempotency_key -> session_id
        self._artifact_map: Dict[str, str] = {}     # f"{capture_id}:{artifact_name}" -> session_id
        self._lock = threading.Lock()

    def _format_response(self, record: UploadSessionRecord) -> UploadSessionResponse:
        uploaded_count = sum(1 for c in record.chunks.values() if c.is_uploaded)
        missing_chunks = [
            i for i in range(record.total_chunks)
            if i not in record.chunks or not record.chunks[i].is_uploaded
        ]
        return UploadSessionResponse(
            session_id=record.session_id,
            state=record.state,
            capture_id=record.capture_id,
            project_id=record.project_id,
            artifact_name=record.artifact_name,
            total_size_bytes=record.total_size_bytes,
            chunk_size_bytes=record.chunk_size_bytes,
            total_chunks=record.total_chunks,
            uploaded_chunks_count=uploaded_count,
            missing_chunks=missing_chunks,
            presigned_urls=dict(record.presigned_urls),
            sha256_checksum=record.sha256_checksum,
            created_at=record.created_at,
            updated_at=record.updated_at
        )

    def create_session(self, req: CreateUploadSessionRequest) -> UploadSessionResponse:
        with self._lock:
            # Duplicate prevention 1: Idempotency Key
            if req.idempotency_key and req.idempotency_key in self._idempotency_map:
                existing_id = self._idempotency_map[req.idempotency_key]
                record = self._sessions[existing_id]
                if record.state != UploadSessionState.FAILED:
                    logger.info(f"Returning existing upload session {existing_id} for idempotency key {req.idempotency_key}")
                    return self._format_response(record)

            # Duplicate prevention 2: (capture_id, artifact_name) pair
            artifact_key = f"{str(req.capture_id)}:{req.artifact_name}"
            if artifact_key in self._artifact_map:
                existing_id = self._artifact_map[artifact_key]
                record = self._sessions[existing_id]
                if record.state in (UploadSessionState.CREATED, UploadSessionState.UPLOADING,
                                    UploadSessionState.PAUSED, UploadSessionState.RESUMING,
                                    UploadSessionState.VALIDATED):
                    logger.info(f"Returning active upload session {existing_id} for {artifact_key}")
                    return self._format_response(record)

            session_id = f"upsess_{uuid.uuid4().hex[:12]}"
            clean_artifact = req.artifact_name.lstrip("/")
            remote_key = f"captures/{str(req.capture_id)}/raw/{clean_artifact}"

            # Initialize multi-part upload directly with storage adapter
            upload_id = self.storage.create_multipart_upload(remote_key)

            record = UploadSessionRecord(
                session_id=session_id,
                capture_id=str(req.capture_id),
                project_id=str(req.project_id),
                artifact_name=req.artifact_name,
                remote_key=remote_key,
                upload_id=upload_id,
                total_size_bytes=req.total_size_bytes,
                chunk_size_bytes=req.chunk_size_bytes,
                total_chunks=req.total_chunks,
                sha256_checksum=req.sha256_checksum,
                idempotency_key=req.idempotency_key
            )

            # Generate direct presigned URLs for each chunk (part_number = chunk_index + 1)
            for chunk_idx in range(req.total_chunks):
                part_number = chunk_idx + 1
                offset = chunk_idx * req.chunk_size_bytes
                length = min(req.chunk_size_bytes, req.total_size_bytes - offset)
                url = self.storage.generate_presigned_part_url(
                    remote_key=remote_key,
                    upload_id=upload_id,
                    part_number=part_number
                )
                record.presigned_urls[chunk_idx] = url
                record.chunks[chunk_idx] = UploadChunkMeta(
                    chunk_index=chunk_idx,
                    offset_bytes=offset,
                    length_bytes=length,
                    presigned_url=url,
                    is_uploaded=False
                )

            self._sessions[session_id] = record
            if req.idempotency_key:
                self._idempotency_map[req.idempotency_key] = session_id
            self._artifact_map[artifact_key] = session_id

            logger.info(f"Created upload session {session_id} for {remote_key} with {req.total_chunks} chunks")
            return self._format_response(record)

    def get_session(self, session_id: str) -> UploadSessionResponse:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Upload session '{session_id}' not found")
            return self._format_response(self._sessions[session_id])

    def pause_session(self, session_id: str) -> UploadSessionResponse:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Upload session '{session_id}' not found")
            record = self._sessions[session_id]
            if record.state in (UploadSessionState.UPLOADED, UploadSessionState.VALIDATED, UploadSessionState.FAILED):
                raise ValueError(f"Cannot pause session in terminal state '{record.state.value}'")

            record.state = UploadSessionState.PAUSED
            record.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Upload session {session_id} transitioned to PAUSED")
            return self._format_response(record)

    def resume_session(self, session_id: str) -> UploadSessionResponse:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Upload session '{session_id}' not found")
            record = self._sessions[session_id]
            if record.state in (UploadSessionState.UPLOADED, UploadSessionState.VALIDATED, UploadSessionState.FAILED):
                raise ValueError(f"Cannot resume session in terminal state '{record.state.value}'")

            # Check existing parts already received in storage
            uploaded_parts = self.storage.list_uploaded_parts(record.remote_key, record.upload_id)
            for part in uploaded_parts:
                part_no = part["part_number"]
                chunk_idx = part_no - 1
                if chunk_idx in record.chunks:
                    record.chunks[chunk_idx].is_uploaded = True
                    record.chunks[chunk_idx].etag = part["etag"]

            # Refresh presigned URLs for missing chunks
            for chunk_idx, chunk_meta in record.chunks.items():
                if not chunk_meta.is_uploaded:
                    part_number = chunk_idx + 1
                    fresh_url = self.storage.generate_presigned_part_url(
                        remote_key=record.remote_key,
                        upload_id=record.upload_id,
                        part_number=part_number
                    )
                    chunk_meta.presigned_url = fresh_url
                    record.presigned_urls[chunk_idx] = fresh_url

            record.state = UploadSessionState.RESUMING
            record.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Upload session {session_id} transitioned to RESUMING")
            return self._format_response(record)

    def record_chunk_uploaded(
        self,
        session_id: str,
        chunk_index: int,
        etag: str,
        sha256: Optional[str] = None
    ) -> UploadSessionResponse:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Upload session '{session_id}' not found")
            record = self._sessions[session_id]

            if record.state in (UploadSessionState.UPLOADED, UploadSessionState.VALIDATED, UploadSessionState.FAILED):
                raise ValueError(f"Cannot record chunk in terminal state '{record.state.value}'")

            if chunk_index not in record.chunks:
                raise IndexError(f"Invalid chunk_index {chunk_index}; session total is {record.total_chunks}")

            meta = record.chunks[chunk_index]
            meta.is_uploaded = True
            meta.etag = etag.strip('"')
            if sha256:
                meta.sha256 = sha256

            # Transition state to UPLOADING if currently CREATED or RESUMING
            if record.state in (UploadSessionState.CREATED, UploadSessionState.RESUMING):
                record.state = UploadSessionState.UPLOADING

            record.updated_at = datetime.now(timezone.utc).isoformat()
            return self._format_response(record)

    def complete_session(
        self,
        session_id: str,
        parts: Optional[List[Dict[str, Any]]] = None
    ) -> UploadSessionResponse:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Upload session '{session_id}' not found")
            record = self._sessions[session_id]

            if record.state == UploadSessionState.VALIDATED:
                return self._format_response(record)
            if record.state == UploadSessionState.FAILED:
                raise ValueError(f"Cannot complete failed upload session: {record.error_message}")

            # Verify all chunks are accounted for
            missing = [
                i for i in range(record.total_chunks)
                if i not in record.chunks or not record.chunks[i].is_uploaded
            ]
            if missing:
                raise ValueError(f"Cannot complete session {session_id}; missing chunks: {missing}")

            record.state = UploadSessionState.UPLOADED
            record.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Upload session {session_id} transitioned to UPLOADED")

            # Format parts for storage adapter completion
            parts_payload = []
            if parts:
                parts_payload = parts
            else:
                for idx in sorted(record.chunks.keys()):
                    c = record.chunks[idx]
                    parts_payload.append({
                        "part_number": idx + 1,
                        "etag": c.etag or f"part_{idx+1}_etag"
                    })

            try:
                # Complete multipart upload in storage adapter
                final_uri = self.storage.complete_multipart_upload(
                    remote_key=record.remote_key,
                    upload_id=record.upload_id,
                    parts=parts_payload
                )
                record.final_uri = final_uri

                # Validate whole-file checksum
                if not self.storage.exists(record.remote_key):
                    raise FileNotFoundError(f"Completed object {record.remote_key} not found in storage")

                # Perform integrity verification
                file_bytes = self.storage.download_bytes(record.remote_key)
                actual_sha256 = hashlib.sha256(file_bytes).hexdigest()
                if actual_sha256.lower() != record.sha256_checksum.lower():
                    error_msg = f"Checksum mismatch: expected {record.sha256_checksum}, got {actual_sha256}"
                    logger.error(error_msg)
                    record.state = UploadSessionState.FAILED
                    record.error_message = error_msg
                    raise ValueError(error_msg)

                # Validation succeeded!
                record.state = UploadSessionState.VALIDATED
                record.updated_at = datetime.now(timezone.utc).isoformat()
                logger.info(f"Upload session {session_id} successfully VALIDATED (SHA-256: {actual_sha256})")
                return self._format_response(record)

            except Exception as e:
                record.state = UploadSessionState.FAILED
                record.error_message = str(e)
                record.updated_at = datetime.now(timezone.utc).isoformat()
                logger.error(f"Upload session {session_id} failed completion validation: {e}")
                raise e

    def abort_session(self, session_id: str) -> UploadSessionResponse:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(f"Upload session '{session_id}' not found")
            record = self._sessions[session_id]

            self.storage.abort_multipart_upload(record.remote_key, record.upload_id)
            record.state = UploadSessionState.FAILED
            record.error_message = "Session explicitly aborted"
            record.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Upload session {session_id} aborted")
            return self._format_response(record)
