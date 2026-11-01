#!/bin/sh
set -e

# Initialize standard VĀSTU S3 buckets in MinIO dynamically using env vars
MINIO_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_PASS="${MINIO_ROOT_PASSWORD:-minioadminpassword2026}"
MINIO_HOST="${MINIO_HOST:-vastu-minio:9000}"

# Resolve or download mc client if missing
MC_CMD="$(command -v mc || command -v mcli || echo "/usr/bin/mc")"
if ! command -v "${MC_CMD}" >/dev/null 2>&1 && [ ! -x "${MC_CMD}" ]; then
    echo "Locating MinIO client (mc)..."
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /tmp/mc
        chmod +x /tmp/mc
        MC_CMD="/tmp/mc"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO /tmp/mc https://dl.min.io/client/mc/release/linux-amd64/mc
        chmod +x /tmp/mc
        MC_CMD="/tmp/mc"
    elif command -v apk >/dev/null 2>&1; then
        apk add --no-cache minio-client
        MC_CMD="$(command -v mc || command -v mcli)"
    fi
fi

echo "Configuring MinIO client alias for http://${MINIO_HOST}..."
# Wait for MinIO service to accept connection
for i in $(seq 1 30); do
    if ${MC_CMD} alias set local "http://${MINIO_HOST}" "${MINIO_USER}" "${MINIO_PASS}" >/dev/null 2>&1; then
        echo "✓ MinIO connection established."
        break
    fi
    echo "Waiting for MinIO service at http://${MINIO_HOST}... ($i/30)"
    sleep 2
done

echo "Creating standard VĀSTU storage buckets if they do not exist..."
${MC_CMD} mb --ignore-existing local/vastu-raw-captures || true
${MC_CMD} mb --ignore-existing local/vastu-artifacts || true
${MC_CMD} mb --ignore-existing local/vastu-exports || true

echo "Setting public read policy on vastu-artifacts for zero-install 3D viewer streaming..."
${MC_CMD} anonymous set download local/vastu-artifacts || true

echo "✓ VĀSTU MinIO Buckets initialized successfully."
