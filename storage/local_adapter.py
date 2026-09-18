"""
VĀSTU Local Storage Adapter
Local filesystem implementation of StorageAdapter for testing and offline execution.
"""

import os
import shutil
from typing import Optional
from storage.base import StorageAdapter

class LocalStorageAdapter(StorageAdapter):
    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, remote_key: str, bucket: Optional[str] = None) -> str:
        clean_key = remote_key.lstrip("/")
        if bucket:
            target = os.path.join(self.base_dir, bucket, clean_key)
        else:
            target = os.path.join(self.base_dir, clean_key)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        return target

    def upload_file(self, local_path: str, remote_key: str, bucket: Optional[str] = None) -> str:
        dest = self._resolve_path(remote_key, bucket)
        shutil.copy2(local_path, dest)
        return f"file://{dest}"

    def download_file(self, remote_key: str, local_path: str, bucket: Optional[str] = None) -> str:
        src = self._resolve_path(remote_key, bucket)
        if not os.path.exists(src):
            raise FileNotFoundError(f"Storage object not found: {src}")
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        shutil.copy2(src, local_path)
        return local_path

    def upload_bytes(self, data: bytes, remote_key: str, content_type: str = "application/octet-stream", bucket: Optional[str] = None) -> str:
        dest = self._resolve_path(remote_key, bucket)
        with open(dest, "wb") as f:
            f.write(data)
        return f"file://{dest}"

    def download_bytes(self, remote_key: str, bucket: Optional[str] = None) -> bytes:
        src = self._resolve_path(remote_key, bucket)
        if not os.path.exists(src):
            raise FileNotFoundError(f"Storage object not found: {src}")
        with open(src, "rb") as f:
            return f.read()

    def generate_presigned_upload_url(self, remote_key: str, expires_in_sec: int = 3600, bucket: Optional[str] = None) -> str:
        dest = self._resolve_path(remote_key, bucket)
        return f"/api/v1/uploads/direct/{bucket or 'default'}/{remote_key.lstrip('/')}"

    def generate_presigned_download_url(self, remote_key: str, expires_in_sec: int = 3600, bucket: Optional[str] = None) -> str:
        return f"/api/v1/uploads/download/{bucket or 'default'}/{remote_key.lstrip('/')}"

    def exists(self, remote_key: str, bucket: Optional[str] = None) -> bool:
        src = self._resolve_path(remote_key, bucket)
        return os.path.exists(src)

    def delete(self, remote_key: str, bucket: Optional[str] = None) -> bool:
        src = self._resolve_path(remote_key, bucket)
        if os.path.exists(src):
            os.remove(src)
            return True
        return False

    def create_multipart_upload(self, remote_key: str, bucket: Optional[str] = None) -> str:
        import uuid
        upload_id = str(uuid.uuid4())
        parts_dir = self._resolve_path(f".parts_{upload_id}", bucket)
        os.makedirs(parts_dir, exist_ok=True)
        return upload_id

    def generate_presigned_part_url(
        self,
        remote_key: str,
        upload_id: str,
        part_number: int,
        expires_in_sec: int = 3600,
        bucket: Optional[str] = None
    ) -> str:
        parts_dir = self._resolve_path(f".parts_{upload_id}", bucket)
        part_file = os.path.join(parts_dir, f"part_{part_number}")
        return f"file://{part_file}"

    def complete_multipart_upload(
        self,
        remote_key: str,
        upload_id: str,
        parts: Optional[list] = None,
        bucket: Optional[str] = None
    ) -> str:
        parts_dir = self._resolve_path(f".parts_{upload_id}", bucket)
        target_file = self._resolve_path(remote_key, bucket)
        os.makedirs(os.path.dirname(target_file), exist_ok=True)

        # Concatenate parts in numerical order
        part_files = sorted(
            [f for f in os.listdir(parts_dir) if f.startswith("part_")],
            key=lambda x: int(x.split("_")[1])
        )

        with open(target_file, "wb") as outfile:
            for pf in part_files:
                p_path = os.path.join(parts_dir, pf)
                with open(p_path, "rb") as infile:
                    shutil.copyfileobj(infile, outfile)

        shutil.rmtree(parts_dir, ignore_errors=True)
        return f"file://{target_file}"

    def abort_multipart_upload(self, remote_key: str, upload_id: str, bucket: Optional[str] = None) -> bool:
        parts_dir = self._resolve_path(f".parts_{upload_id}", bucket)
        if os.path.exists(parts_dir):
            shutil.rmtree(parts_dir, ignore_errors=True)
            return True
        return False

    def list_uploaded_parts(self, remote_key: str, upload_id: str, bucket: Optional[str] = None) -> list:
        parts_dir = self._resolve_path(f".parts_{upload_id}", bucket)
        if not os.path.exists(parts_dir):
            return []
        part_files = [f for f in os.listdir(parts_dir) if f.startswith("part_")]
        return [
            {
                "part_number": int(f.split("_")[1]),
                "etag": f"part_{f.split('_')[1]}_etag",
                "size_bytes": os.path.getsize(os.path.join(parts_dir, f))
            }
            for f in sorted(part_files, key=lambda x: int(x.split("_")[1]))
        ]

