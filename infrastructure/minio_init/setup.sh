#!/bin/sh
# Initialize standard VĀSTU S3 buckets in MinIO
mc alias set local http://vastu-minio:9000 minioadmin minioadminpassword2026
mc mb --ignore-existing local/vastu-raw-captures
mc mb --ignore-existing local/vastu-artifacts
mc mb --ignore-existing local/vastu-exports
mc anonymous set download local/vastu-artifacts
echo "VĀSTU MinIO Buckets initialized successfully."
