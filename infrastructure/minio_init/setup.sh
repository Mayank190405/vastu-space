#!/bin/sh
set -e

# Initialize standard VĀSTU S3 buckets in MinIO dynamically using env vars
MINIO_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_PASS="${MINIO_ROOT_PASSWORD:-minioadminpassword2026}"
MINIO_HOST="${MINIO_HOST:-vastu-minio:9000}"

echo "Configuring MinIO client alias for http://${MINIO_HOST}..."
/usr/bin/mc alias set local "http://${MINIO_HOST}" "${MINIO_USER}" "${MINIO_PASS}"

echo "Creating standard VĀSTU storage buckets if they do not exist..."
/usr/bin/mc mb --ignore-existing local/vastu-raw-captures
/usr/bin/mc mb --ignore-existing local/vastu-artifacts
/usr/bin/mc mb --ignore-existing local/vastu-exports

echo "Setting public read policy on vastu-artifacts for zero-install 3D viewer streaming..."
/usr/bin/mc anonymous set download local/vastu-artifacts || true

echo "✓ VĀSTU MinIO Buckets initialized successfully."
