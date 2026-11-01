#!/bin/sh
set -e

# Initialize standard VĀSTU S3 buckets in MinIO dynamically using env vars
MINIO_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_PASS="${MINIO_ROOT_PASSWORD:-minioadminpassword2026}"
MINIO_HOST="${MINIO_HOST:-vastu-minio:9000}"

# Prefer the distribution package; the upstream binary download can return 410.
MC_CMD="$(command -v mc || command -v mcli || true)"
if [ -z "$MC_CMD" ] && command -v apk >/dev/null 2>&1; then
    apk add --no-cache minio-client
    MC_CMD="$(command -v mc || command -v mcli || true)"
fi
if [ -z "$MC_CMD" ]; then
    echo "ERROR: MinIO client is unavailable; install mc or minio-client." >&2
    exit 1
fi

echo "Configuring MinIO client alias for http://${MINIO_HOST}..."
# Wait for MinIO service to accept connection
connected=false
for i in $(seq 1 30); do
    if ${MC_CMD} alias set local "http://${MINIO_HOST}" "${MINIO_USER}" "${MINIO_PASS}" >/dev/null 2>&1; then
        echo "✓ MinIO connection established."
        connected=true
        break
    fi
    echo "Waiting for MinIO service at http://${MINIO_HOST}... ($i/30)"
    sleep 2
done

[ "$connected" = true ] || { echo "ERROR: MinIO connection failed" >&2; exit 1; }

echo "Creating standard VĀSTU storage buckets if they do not exist..."
${MC_CMD} mb --ignore-existing local/vastu-raw-captures
${MC_CMD} mb --ignore-existing local/vastu-artifacts
${MC_CMD} mb --ignore-existing local/vastu-exports

echo "Setting public read policy on vastu-artifacts for zero-install 3D viewer streaming..."
${MC_CMD} anonymous set download local/vastu-artifacts

echo "✓ VĀSTU MinIO Buckets initialized successfully."
