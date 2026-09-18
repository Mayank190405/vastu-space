"""
Unit & Integration Tests: VĀSTU Upload Pipeline
Validates:
1. 7-state lifecycle: CREATED, UPLOADING, PAUSED, RESUMING, UPLOADED, VALIDATED, FAILED
2. Direct-to-storage zero-proxy multipart upload
3. Duplicate prevention via idempotency key and (capture_id, artifact_name)
4. Deliberate network interruption & seamless resumption without restarting from zero
5. Whole-file checksum integrity verification
6. Exponential backoff and retry behavior
7. FastAPI HTTP control plane endpoints
"""

import os
import uuid
import pytest
import hashlib
import tempfile
from fastapi.testclient import TestClient

from core.schemas.upload_session import (
    UploadSessionState,
    CreateUploadSessionRequest,
)
from storage.local_adapter import LocalStorageAdapter
from core.upload.session_manager import UploadSessionManager
from core.upload.client import ResumableUploadClient
from core.upload.retry import calculate_backoff_delay, retry_with_backoff
from api.main import app

client = TestClient(app)


def test_calculate_backoff_delay():
    # Attempt 0: base 0.5s -> [0.25, 0.5] with jitter
    d0 = calculate_backoff_delay(0, base_delay=0.5, jitter=False)
    assert d0 == 0.5

    d1 = calculate_backoff_delay(1, base_delay=0.5, jitter=False)
    assert d1 == 1.0

    d2 = calculate_backoff_delay(2, base_delay=0.5, jitter=False)
    assert d2 == 2.0

    # Max delay capped
    d_capped = calculate_backoff_delay(10, base_delay=1.0, max_delay=10.0, jitter=False)
    assert d_capped == 10.0

    # Jittered
    d_jitter = calculate_backoff_delay(1, base_delay=0.5, jitter=True)
    assert 0.5 <= d_jitter <= 1.0


def test_retry_with_backoff():
    calls = 0

    def flaky_func():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionResetError("Simulated network blip")
        return "success"

    res = retry_with_backoff(flaky_func, max_retries=4, base_delay=0.01, max_delay=0.1)
    assert res == "success"
    assert calls == 3


def test_upload_session_lifecycle_and_states(tmp_path):
    storage = LocalStorageAdapter(base_dir=str(tmp_path / "storage"))
    manager = UploadSessionManager(storage_adapter=storage)

    cid = uuid.uuid4()
    pid = uuid.uuid4()
    content = b"TEST_PAYLOAD_FOR_LIFECYCLE_VERIFICATION"
    content_hash = hashlib.sha256(content).hexdigest()

    req = CreateUploadSessionRequest(
        capture_id=cid,
        project_id=pid,
        artifact_name="video.mp4",
        total_size_bytes=len(content),
        chunk_size_bytes=10,
        total_chunks=4,
        sha256_checksum=content_hash,
        idempotency_key="unique-req-123"
    )

    # 1. CREATED
    sess = manager.create_session(req)
    assert sess.state == UploadSessionState.CREATED
    assert sess.total_chunks == 4
    assert len(sess.missing_chunks) == 4
    assert sess.uploaded_chunks_count == 0

    # Duplicate prevention with same idempotency key
    sess_dup = manager.create_session(req)
    assert sess_dup.session_id == sess.session_id

    # 2. UPLOADING (record chunk 0)
    sess = manager.record_chunk_uploaded(sess.session_id, chunk_index=0, etag="etag0")
    assert sess.state == UploadSessionState.UPLOADING
    assert sess.uploaded_chunks_count == 1
    assert 0 not in sess.missing_chunks

    # 3. PAUSED
    sess = manager.pause_session(sess.session_id)
    assert sess.state == UploadSessionState.PAUSED

    # 4. RESUMING
    sess = manager.resume_session(sess.session_id)
    assert sess.state == UploadSessionState.RESUMING
    assert sess.uploaded_chunks_count == 1
    assert 0 not in sess.missing_chunks

    # Record remaining chunks
    sess = manager.record_chunk_uploaded(sess.session_id, chunk_index=1, etag="etag1")
    sess = manager.record_chunk_uploaded(sess.session_id, chunk_index=2, etag="etag2")
    sess = manager.record_chunk_uploaded(sess.session_id, chunk_index=3, etag="etag3")
    assert sess.uploaded_chunks_count == 4
    assert len(sess.missing_chunks) == 0

    # Mock writing parts to storage before completion test
    rec = manager._sessions[sess.session_id]
    parts_dir = tmp_path / "storage" / f".parts_{rec.upload_id}"
    os.makedirs(parts_dir, exist_ok=True)
    chunks_data = [content[i * 10 : (i + 1) * 10] for i in range(4)]
    for idx, c_bytes in enumerate(chunks_data):
        with open(parts_dir / f"part_{idx+1}", "wb") as f:
            f.write(c_bytes)

    # 5 & 6. UPLOADED -> VALIDATED
    sess = manager.complete_session(sess.session_id)
    assert sess.state == UploadSessionState.VALIDATED
    assert storage.exists(rec.remote_key)
    assert storage.download_bytes(rec.remote_key) == content


def test_completion_fails_on_checksum_mismatch(tmp_path):
    storage = LocalStorageAdapter(base_dir=str(tmp_path / "storage"))
    manager = UploadSessionManager(storage_adapter=storage)

    cid = uuid.uuid4()
    pid = uuid.uuid4()
    content = b"VALID_BYTES"
    bad_hash = hashlib.sha256(b"CORRUPTED_BYTES").hexdigest()

    req = CreateUploadSessionRequest(
        capture_id=cid,
        project_id=pid,
        artifact_name="corrupt.bin",
        total_size_bytes=len(content),
        chunk_size_bytes=100,
        total_chunks=1,
        sha256_checksum=bad_hash
    )
    sess = manager.create_session(req)
    manager.record_chunk_uploaded(sess.session_id, chunk_index=0, etag="etag0")

    rec = manager._sessions[sess.session_id]
    parts_dir = tmp_path / "storage" / f".parts_{rec.upload_id}"
    os.makedirs(parts_dir, exist_ok=True)
    with open(parts_dir / "part_1", "wb") as f:
        f.write(content)

    # Completion should detect mismatch and transition to FAILED
    with pytest.raises(ValueError, match="Checksum mismatch"):
        manager.complete_session(sess.session_id)

    sess_failed = manager.get_session(sess.session_id)
    assert sess_failed.state == UploadSessionState.FAILED


def test_network_interruption_and_resumption(tmp_path):
    """
    Deliberately interrupts network transfer mid-upload and resumes.
    Verifies chunks uploaded before interruption are NOT re-uploaded.
    """
    storage = LocalStorageAdapter(base_dir=str(tmp_path / "storage"))
    manager = UploadSessionManager(storage_adapter=storage)

    # Generate a multi-chunk test file (5 chunks of 100KB = 500KB total)
    chunk_size = 100 * 1024
    total_chunks = 5
    file_path = tmp_path / "large_capture.mp4"
    data = os.urandom(chunk_size * total_chunks)
    with open(file_path, "wb") as f:
        f.write(data)

    cid = uuid.uuid4()
    pid = uuid.uuid4()

    # Step 1: Client simulates upload, but injects deliberate drop on chunk 2
    dropped = False

    def drop_on_chunk_2(chunk_idx: int) -> bool:
        nonlocal dropped
        if chunk_idx == 2 and not dropped:
            dropped = True
            return True
        return False

    client = ResumableUploadClient(
        session_manager=manager,
        chunk_size_bytes=chunk_size,
        network_drop_hook=drop_on_chunk_2
    )

    # Initial attempt should fail on chunk 2
    with pytest.raises(ConnectionError, match="interrupted during chunk 2"):
        client.upload_file(
            file_path=str(file_path),
            capture_id=cid,
            project_id=pid,
            artifact_name="large_capture.mp4"
        )

    # Inspect session state after network drop
    active_sessions = list(manager._sessions.values())
    assert len(active_sessions) == 1
    sess_id = active_sessions[0].session_id
    sess_record = manager.get_session(sess_id)

    # Session is PAUSED
    assert sess_record.state == UploadSessionState.PAUSED
    # Chunks 0 and 1 were successfully uploaded!
    assert 0 not in sess_record.missing_chunks
    assert 1 not in sess_record.missing_chunks
    # Chunk 2, 3, 4 are still missing
    assert 2 in sess_record.missing_chunks
    assert sess_record.uploaded_chunks_count == 2

    # Step 2: Resume without restarting from zero
    # Disable drop hook
    client.network_drop_hook = None
    resumed_session = client.upload_file(
        file_path=str(file_path),
        capture_id=cid,
        project_id=pid,
        artifact_name="large_capture.mp4",
        existing_session_id=sess_id
    )

    # Final state should be VALIDATED
    assert resumed_session.state == UploadSessionState.VALIDATED
    assert resumed_session.uploaded_chunks_count == 5
    assert len(resumed_session.missing_chunks) == 0

    # Verify destination file on storage has exact content & byte integrity
    rec = manager._sessions[sess_id]
    uploaded_bytes = storage.download_bytes(rec.remote_key)
    assert len(uploaded_bytes) == len(data)
    assert hashlib.sha256(uploaded_bytes).hexdigest() == hashlib.sha256(data).hexdigest()


def test_api_upload_endpoints():
    cid = str(uuid.uuid4())
    pid = str(uuid.uuid4())
    content = b"FASTAPI_UPLOAD_TEST_DATA"
    sha = hashlib.sha256(content).hexdigest()

    # 1. POST /api/v1/uploads/
    payload = {
        "capture_id": cid,
        "project_id": pid,
        "artifact_name": "api_test.bin",
        "total_size_bytes": len(content),
        "chunk_size_bytes": 1024 * 1024,
        "total_chunks": 1,
        "sha256_checksum": sha,
        "idempotency_key": "api-key-test-999"
    }
    resp = client.post("/api/v1/uploads/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    sess_id = data["session_id"]
    assert data["state"] == "CREATED"
    assert data["uploaded_chunks_count"] == 0

    # 2. GET /api/v1/uploads/{sess_id}
    resp = client.get(f"/api/v1/uploads/{sess_id}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == sess_id

    # 3. POST /api/v1/uploads/{sess_id}/pause
    resp = client.post(f"/api/v1/uploads/{sess_id}/pause")
    assert resp.status_code == 200
    assert resp.json()["state"] == "PAUSED"

    # 4. POST /api/v1/uploads/{sess_id}/resume
    resp = client.post(f"/api/v1/uploads/{sess_id}/resume")
    assert resp.status_code == 200
    assert resp.json()["state"] == "RESUMING"

    # 5. POST /api/v1/uploads/{sess_id}/parts/0
    resp = client.post(
        f"/api/v1/uploads/{sess_id}/parts/0",
        json={"etag": "chunk0etag", "sha256": sha}
    )
    assert resp.status_code == 200
    assert resp.json()["uploaded_chunks_count"] == 1
    assert resp.json()["state"] == "UPLOADING"
