"""
VĀSTU Storage Layer Abstraction
Abstract Base Interface for Object Storage
"""

from abc import ABC, abstractmethod
from typing import Optional, BinaryIO

class StorageAdapter(ABC):
    @abstractmethod
    def upload_file(self, local_path: str, remote_key: str, bucket: Optional[str] = None) -> str:
        """Uploads a local file to remote storage. Returns the remote key/URI."""
        pass

    @abstractmethod
    def download_file(self, remote_key: str, local_path: str, bucket: Optional[str] = None) -> str:
        """Downloads a remote object to local path. Returns the local path."""
        pass

    @abstractmethod
    def upload_bytes(self, data: bytes, remote_key: str, content_type: str = "application/octet-stream", bucket: Optional[str] = None) -> str:
        """Uploads raw bytes to remote storage."""
        pass

    @abstractmethod
    def download_bytes(self, remote_key: str, bucket: Optional[str] = None) -> bytes:
        """Downloads remote object as raw bytes."""
        pass

    @abstractmethod
    def generate_presigned_upload_url(self, remote_key: str, expires_in_sec: int = 3600, bucket: Optional[str] = None) -> str:
        """Generates a presigned PUT URL for client uploads."""
        pass

    @abstractmethod
    def generate_presigned_download_url(self, remote_key: str, expires_in_sec: int = 3600, bucket: Optional[str] = None) -> str:
        """Generates a presigned GET URL for client downloads."""
        pass

    @abstractmethod
    def exists(self, remote_key: str, bucket: Optional[str] = None) -> bool:
        """Checks if remote key exists."""
        pass

    @abstractmethod
    def delete(self, remote_key: str, bucket: Optional[str] = None) -> bool:
        """Deletes remote object."""
        pass

    @abstractmethod
    def create_multipart_upload(self, remote_key: str, bucket: Optional[str] = None) -> str:
        """Initializes a multi-part upload and returns an upload ID."""
        pass

    @abstractmethod
    def generate_presigned_part_url(
        self,
        remote_key: str,
        upload_id: str,
        part_number: int,
        expires_in_sec: int = 3600,
        bucket: Optional[str] = None
    ) -> str:
        """Generates a presigned PUT URL for a specific multi-part chunk."""
        pass

    @abstractmethod
    def complete_multipart_upload(
        self,
        remote_key: str,
        upload_id: str,
        parts: Optional[list] = None,
        bucket: Optional[str] = None
    ) -> str:
        """Completes and assembles a multi-part upload."""
        pass

    @abstractmethod
    def abort_multipart_upload(self, remote_key: str, upload_id: str, bucket: Optional[str] = None) -> bool:
        """Aborts a pending multi-part upload."""
        pass

    @abstractmethod
    def list_uploaded_parts(self, remote_key: str, upload_id: str, bucket: Optional[str] = None) -> list:
        """Lists chunk indices/numbers that have been uploaded."""
        pass

