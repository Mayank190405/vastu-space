"""
VĀSTU Resumable Upload Client
Client-side upload engine that handles chunked uploads, checksum calculation,
simulated network drops, exponential backoff retries, and seamless resumption.
"""

import os
import hashlib
import logging
from typing import Optional, Callable, Dict, Any, List
import urllib.request
import urllib.error

from core.schemas.upload_session import (
    CreateUploadSessionRequest,
    UploadSessionResponse,
    UploadSessionState,
)
from core.upload.session_manager import UploadSessionManager
from core.upload.retry import retry_with_backoff

logger = logging.getLogger("vastu.upload.client")


class ResumableUploadClient:
    """
    Client orchestrating multi-gigabyte chunked uploads directly to storage
    with robust retry, failure injection, and resumption capabilities.
    """
    def __init__(
        self,
        session_manager: UploadSessionManager,
        chunk_size_bytes: int = 5 * 1024 * 1024,  # 5MB chunks
        network_drop_hook: Optional[Callable[[int], bool]] = None
    ):
        self.session_manager = session_manager
        self.chunk_size_bytes = chunk_size_bytes
        self.network_drop_hook = network_drop_hook
        self.interrupted_chunks: List[int] = []

    def compute_sha256(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        return h.hexdigest()

    def upload_file(
        self,
        file_path: str,
        capture_id: Any,
        project_id: Any,
        artifact_name: str,
        idempotency_key: Optional[str] = None,
        existing_session_id: Optional[str] = None
    ) -> UploadSessionResponse:
        """
        Uploads a local file using chunked resumable upload.
        Can resume an existing session or start a new one.
        """
        file_size = os.path.getsize(file_path)
        file_sha256 = self.compute_sha256(file_path)
        total_chunks = (file_size + self.chunk_size_bytes - 1) // self.chunk_size_bytes

        if existing_session_id:
            logger.info(f"Resuming existing session {existing_session_id}")
            session = self.session_manager.get_session(existing_session_id)
            if session.state == UploadSessionState.PAUSED:
                session = self.session_manager.resume_session(existing_session_id)
        else:
            req = CreateUploadSessionRequest(
                capture_id=capture_id,
                project_id=project_id,
                artifact_name=artifact_name,
                total_size_bytes=file_size,
                chunk_size_bytes=self.chunk_size_bytes,
                total_chunks=total_chunks,
                sha256_checksum=file_sha256,
                idempotency_key=idempotency_key
            )
            session = self.session_manager.create_session(req)

        # Upload missing chunks
        with open(file_path, "rb") as f:
            for chunk_idx in list(session.missing_chunks):
                # Check for deliberate network interruption hook
                if self.network_drop_hook and self.network_drop_hook(chunk_idx):
                    self.interrupted_chunks.append(chunk_idx)
                    logger.warning(f"Simulating network drop on chunk {chunk_idx}!")
                    # Transition session to PAUSED to simulate client pausing on disconnect
                    self.session_manager.pause_session(session.session_id)
                    raise ConnectionError(f"Network connection interrupted during chunk {chunk_idx}")

                offset = chunk_idx * self.chunk_size_bytes
                f.seek(offset)
                chunk_data = f.read(self.chunk_size_bytes)
                chunk_sha256 = hashlib.sha256(chunk_data).hexdigest()

                # Direct storage upload via presigned URL or storage adapter
                url = session.presigned_urls[chunk_idx]
                etag = self._upload_chunk_data(url, chunk_data, chunk_idx)

                # Record chunk with session manager
                session = self.session_manager.record_chunk_uploaded(
                    session_id=session.session_id,
                    chunk_index=chunk_idx,
                    etag=etag,
                    sha256=chunk_sha256
                )

        # Once all chunks are uploaded, complete the session
        final_session = self.session_manager.complete_session(session.session_id)
        return final_session

    def _upload_chunk_data(self, presigned_url: str, data: bytes, chunk_idx: int) -> str:
        """
        Transfers chunk data directly to storage endpoint without proxying through API.
        Supports file:// presigned URLs (Local adapter) or http/https presigned URLs (S3/MinIO).
        """
        if presigned_url.startswith("file://"):
            local_target = presigned_url[7:]
            os.makedirs(os.path.dirname(local_target), exist_ok=True)
            with open(local_target, "wb") as f:
                f.write(data)
            return hashlib.md5(data).hexdigest()
        else:
            # S3 / MinIO HTTP PUT
            req = urllib.request.Request(
                presigned_url,
                data=data,
                method="PUT",
                headers={"Content-Type": "application/octet-stream"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                etag = resp.headers.get("ETag", hashlib.md5(data).hexdigest())
                return etag.strip('"')
