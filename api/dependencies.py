"""
VĀSTU API Dependencies
Provides dependency injection for Storage, Database, and Security.
"""

from typing import Generator
from storage.base import StorageAdapter
from storage import get_storage_adapter

def get_storage() -> StorageAdapter:
    """Dependency provider for storage adapter."""
    return get_storage_adapter()
