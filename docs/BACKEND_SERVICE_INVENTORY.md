# BACKEND SERVICE INVENTORY
*Generated for Phase 2.1 Audit*

**Canonical service-to-service map (why each hop exists, Go + Python + workers + on-device):** [SERVICE_TO_SERVICE_ARCHITECTURE.md](./SERVICE_TO_SERVICE_ARCHITECTURE.md)

| Service | File | Tables Used | Description | Tenant Scoped |
|---|---|---|---|---|
| AuthService | `auth_service.go` | `users`, `organizations`, `organization_members`, `otps`, `user_auth_providers` | Handles signup, login (Email, Google, Apple), OTP generation/verification, and JWT issuance. | No (Cross-tenant) |
| OrgService | `org_service.go` | `organizations`, `organization_members`, `users` | Manages Organization creation, invites, member approvals, and tenant boundary definition. | Yes |
| ProjectService| `project_service.go` | `projects`, `project_timeline`, `project_chat`, `project_client_emails`, `project_activity_logs` | Manages spatial digital twin project lifecycle, metadata, soft deletion, timelines, chat, and activities. | Yes |
| CaptureService| `capture_service.go` | `captures` | Tracks physical RGB/IMU captures from mobile devices. | Yes |
| UploadService | `upload_service.go` | `uploads`, `captures` | Manages 5MB chunked resumable binary ingestion and quarantine checks. | Yes |
| JobService | `job_service.go` | `processing_jobs` | Orchestrates the reconstruction pipeline states (Preprocessing -> ... -> Complete). | Yes |
| ModelService | `model_service.go` | `models`, `model_artifacts` | Manages 3D asset metadata, LOD tracking, and binary associations. | Yes |
| POIService | `poi_service.go` | `spatial_pois` | Manages 3D Spatial POIs with `(x, y, z, floor_level)` coordinates. | Yes |
| SearchService | `search_service.go` | `spatial_pois`, `projects` | Executes PostGIS spatial indexing (`ST_DWithin`) and semantic search operations. | Yes |
| NavigationService| `navigation_service.go`| `navigation_nodes`, `navigation_edges` | Executes Dijkstra / A* indoor pathfinding, filtering by wheelchair accessibility and floor. | Yes |
| ViewerService | `viewer_service.go` | `viewer_bookmarks`, `viewer_annotations` | Manages 3DGS camera viewpoints and user annotations inside the digital twin. | Yes |
| OTPService | `otp_service.go` | `otps` | Generates and emails time-limited OTP codes for signup/login. | No |
| GoogleService / AppleService | `google_service.go`, `apple_service.go` | — | Verifies SSO ID tokens so the client is not trusted as an identity provider. | No |
| LocationService | `location_service.go` | — | Nominatim geocode/reverse for project wizard site address. | No |
| RescanService | `rescan_service.go` | `rescan_requests` | Localized micro-rescan cards after quality FAIL. | Yes |
| OrchestratorService | `orchestrator_service.go` | `processing_jobs`, captures, models | Subscribes to upload validation and spawns reconstruction with heartbeat/retry. | Yes |

## Dependency & Injection Graph
Services are initialized in `backend/cmd/server/main.go`. 
All services utilize dependency injection for repositories (PostgreSQL) and external services (SMTP Mailer, Google Auth, Apple Auth, JWT Manager).
