"""
VĀSTU S3/MinIO Storage Adapter
Production-grade S3 compatible storage integration using boto3.
"""

import os
from typing import Optional
from storage.base import StorageAdapter

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

class S3StorageAdapter(StorageAdapter):
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        default_bucket: str = "vastu-artifacts",
        region_name: str = "us-east-1",
        use_ssl: bool = False
    ):
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
        self.default_bucket = default_bucket or os.getenv("S3_BUCKET", "vastu-artifacts")
        self.region_name = region_name or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.use_ssl = use_ssl

        if HAS_BOTO3:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region_name,
                use_ssl=self.use_ssl,
                config=Config(signature_version="s3v4")
            )
        else:
            self.s3_client = None

    def _ensure_client(self):
        if not HAS_BOTO3 or self.s3_client is None:
            raise RuntimeError("boto3 is not installed; please install boto3 to use S3StorageAdapter")

    def upload_file(self, local_path: str, remote_key: str, bucket: Optional[str] = None) -> str:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        self.s3_client.upload_file(local_path, target_bucket, clean_key)
        return f"s3://{target_bucket}/{clean_key}"

    def download_file(self, remote_key: str, local_path: str, bucket: Optional[str] = None) -> str:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        self.s3_client.download_file(target_bucket, clean_key, local_path)
        return local_path

    def upload_bytes(self, data: bytes, remote_key: str, content_type: str = "application/octet-stream", bucket: Optional[str] = None) -> str:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        self.s3_client.put_object(Bucket=target_bucket, Key=clean_key, Body=data, ContentType=content_type)
        return f"s3://{target_bucket}/{clean_key}"

    def download_bytes(self, remote_key: str, bucket: Optional[str] = None) -> bytes:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        response = self.s3_client.get_object(Bucket=target_bucket, Key=clean_key)
        return response["Body"].read()

    def generate_presigned_upload_url(self, remote_key: str, expires_in_sec: int = 3600, bucket: Optional[str] = None) -> str:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        return self.s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": target_bucket, "Key": clean_key},
            ExpiresIn=expires_in_sec
        )

    def generate_presigned_download_url(self, remote_key: str, expires_in_sec: int = 3600, bucket: Optional[str] = None) -> str:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": target_bucket, "Key": clean_key},
            ExpiresIn=expires_in_sec
        )

    def exists(self, remote_key: str, bucket: Optional[str] = None) -> bool:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        try:
            self.s3_client.head_object(Bucket=target_bucket, Key=clean_key)
            return True
        except ClientError:
            return False

    def delete(self, remote_key: str, bucket: Optional[str] = None) -> bool:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        self.s3_client.delete_object(Bucket=target_bucket, Key=clean_key)
        return True

    def create_multipart_upload(
        self,
        remote_key: str,
        content_type: str = "application/octet-stream",
        bucket: Optional[str] = None
    ) -> str:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        res = self.s3_client.create_multipart_upload(
            Bucket=target_bucket,
            Key=clean_key,
            ContentType=content_type
        )
        return res["UploadId"]

    def generate_presigned_part_url(
        self,
        remote_key: str,
        upload_id: str,
        part_number: int,
        expires_in_sec: int = 3600,
        bucket: Optional[str] = None
    ) -> str:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        return self.s3_client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": target_bucket,
                "Key": clean_key,
                "UploadId": upload_id,
                "PartNumber": part_number
            },
            ExpiresIn=expires_in_sec
        )

    def complete_multipart_upload(
        self,
        remote_key: str,
        upload_id: str,
        parts: list,
        bucket: Optional[str] = None
    ) -> str:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        # format parts for S3 API: [{'PartNumber': int, 'ETag': str}]
        formatted_parts = []
        for p in sorted(parts, key=lambda x: x["part_number"]):
            formatted_parts.append({
                "PartNumber": p["part_number"],
                "ETag": p["etag"].strip('"')
            })
        self.s3_client.complete_multipart_upload(
            Bucket=target_bucket,
            Key=clean_key,
            UploadId=upload_id,
            MultipartUpload={"Parts": formatted_parts}
        )
        return f"s3://{target_bucket}/{clean_key}"

    def abort_multipart_upload(
        self,
        remote_key: str,
        upload_id: str,
        bucket: Optional[str] = None
    ) -> bool:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        try:
            self.s3_client.abort_multipart_upload(
                Bucket=target_bucket,
                Key=clean_key,
                UploadId=upload_id
            )
            return True
        except ClientError:
            return False

    def list_uploaded_parts(
        self,
        remote_key: str,
        upload_id: str,
        bucket: Optional[str] = None
    ) -> list:
        self._ensure_client()
        target_bucket = bucket or self.default_bucket
        clean_key = remote_key.lstrip("/")
        try:
            res = self.s3_client.list_parts(
                Bucket=target_bucket,
                Key=clean_key,
                UploadId=upload_id
            )
            raw_parts = res.get("Parts", [])
            return [
                {
                    "part_number": p["PartNumber"],
                    "etag": p["ETag"].strip('"'),
                    "size_bytes": p["Size"]
                }
                for p in raw_parts
            ]
        except ClientError:
            return []

