"""
VĀSTU Storage Layer Factory
"""

import os
from storage.base import StorageAdapter
from storage.local_adapter import LocalStorageAdapter
from storage.s3_adapter import S3StorageAdapter, HAS_BOTO3

def get_storage_adapter() -> StorageAdapter:
    """Returns S3StorageAdapter if configured and boto3 available, else LocalStorageAdapter."""
    storage_type = os.getenv("STORAGE_BACKEND", "auto").lower()
    
    if storage_type == "s3" or (storage_type == "auto" and HAS_BOTO3 and os.getenv("AWS_ACCESS_KEY_ID")):
        return S3StorageAdapter()
    
    base_upload_dir = os.getenv("UPLOAD_DIR", "uploads")
    return LocalStorageAdapter(base_dir=base_upload_dir)

__all__ = ["StorageAdapter", "LocalStorageAdapter", "S3StorageAdapter", "get_storage_adapter"]
