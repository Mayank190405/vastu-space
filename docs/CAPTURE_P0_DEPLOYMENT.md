# Capture P0 deployment

Branch: `codex/p0-capture-video-recovery`

## EC2

Back up the database and inspect `git status --short` before updating the checkout. Earlier infrastructure repairs may appear as local changes; preserve those before switching branches. Fetch and check out `origin/codex/p0-capture-video-recovery`.

```sh
docker compose -f docker-compose.prod.yml exec -T vastu-postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > capture-p0-backup.dump
docker compose -f docker-compose.prod.yml run --rm vastu-migrate
docker compose -f docker-compose.prod.yml run --rm vastu-minio-init
docker compose -f docker-compose.prod.yml build vastu-backend vastu-worker vastu-frontend vastu-api
docker compose -f docker-compose.prod.yml up -d --no-deps vastu-backend vastu-worker vastu-frontend vastu-api
docker compose -f docker-compose.prod.yml logs --tail=50 vastu-backend vastu-worker vastu-api
```

Migration 22 adds persisted capture/upload/job bindings and verified video/viewer fields. Migrations 20 and 21 now have unique version numbers. Do not force migration versions or drop tables. Preserve the existing S3 credentials and shared uploads volume. The worker image now includes core, ml, navigation, and scripts; restarting the old image alone does not install the fix. Check disk space before rebuilding the large worker image.

## iPhone

Rebuild and install `ios/VastuCapture.xcodeproj` with your normal signing configuration. The old installed app simulates uploads and cannot perform this workflow. Create a fresh QR session on the updated dashboard, scan it, record a new video, and upload. A failed upload retains the local video and can resume stored chunks using the same session.

## Required verification

- Verify device heartbeat and persisted session ID on desktop.
- Verify SHA-256-confirmed video storage in MinIO, dashboard playback, and a real processing job UUID.
- Verify actual worker events, actionable failures, and processing retry.
- Verify viewer generation passes the reconstruction quality gate before a link appears.
- Test interrupted upload, expired grant, and worker failure. Expired sessions currently require operator intervention; automatic grant renewal is not implemented.

Do not close the P0 based on builds or health checks. A new iPhone recording must complete the production workflow. Failed quality gates must remain visible rather than publishing a substitute model.

## Validation

Frontend production build, Go server/worker builds, iOS simulator build, and focused session/upload tests passed. The full Go suite has existing auth-test compilation errors. No new iPhone recording or successful production reconstruction has been verified by this patch.

## Metric-depth and retry recovery

The worker build now installs pinned metric-depth dependencies, caches a pinned Depth Anything V2 Metric Indoor Small checkpoint, and runs a real inference check. If model download or validation fails, the image build must fail. Runtime uses the local metric model cache; approximate depth remains disallowed. Each automatic reconstruction attempt writes to a separate `attempts/attempt-*/result` directory, preserving previous failed output. Rebuild and recreate `vastu-worker`, then retry the existing failed processing job from its scan dashboard. No new recording, migration, or iOS build is required for this repair.
