import os
import tempfile
import pytest
from storage.local_adapter import LocalStorageAdapter

def test_local_storage_upload_and_download_file():
    with tempfile.TemporaryDirectory() as temp_dir:
        adapter = LocalStorageAdapter(base_dir=temp_dir)
        
        # Create a sample local file
        src_file = os.path.join(temp_dir, "test_input.txt")
        with open(src_file, "w") as f:
            f.write("Hello VASTU Storage")
            
        # Upload
        uri = adapter.upload_file(src_file, "models/test.txt", bucket="captures")
        assert uri.startswith("file://")
        assert adapter.exists("models/test.txt", bucket="captures")
        
        # Download
        dest_file = os.path.join(temp_dir, "test_output.txt")
        downloaded_path = adapter.download_file("models/test.txt", dest_file, bucket="captures")
        assert os.path.exists(downloaded_path)
        with open(downloaded_path, "r") as f:
            assert f.read() == "Hello VASTU Storage"

def test_local_storage_bytes_and_presigned_urls():
    with tempfile.TemporaryDirectory() as temp_dir:
        adapter = LocalStorageAdapter(base_dir=temp_dir)
        
        raw_data = b"raw binary pointcloud data"
        adapter.upload_bytes(raw_data, "points.bin", bucket="models")
        assert adapter.exists("points.bin", bucket="models")
        
        read_back = adapter.download_bytes("points.bin", bucket="models")
        assert read_back == raw_data
        
        upload_url = adapter.generate_presigned_upload_url("new.ply", bucket="models")
        assert "/api/v1/uploads/direct/models/new.ply" in upload_url
        
        download_url = adapter.generate_presigned_download_url("new.ply", bucket="models")
        assert "/api/v1/uploads/download/models/new.ply" in download_url
        
        # Deletion
        assert adapter.delete("points.bin", bucket="models") is True
        assert adapter.exists("points.bin", bucket="models") is False
        assert adapter.delete("nonexistent.bin", bucket="models") is False
