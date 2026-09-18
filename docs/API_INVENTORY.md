# API CONTRACT INVENTORY
*Generated for Phase 2.6 Audit*

## Global Base Path: `/api/v1`
## Global Middleware:
- RequestID, RealIP, Logger, Recoverer, Timeout (60s)
- CORS (Allowed: GET, POST, PUT, DELETE, OPTIONS; Allowed Headers: Accept, Authorization, Content-Type, X-CSRF-Token)

---

## 1. Authentication (`/auth`)
| Method | Path | Auth Required | Handler | Description |
|---|---|---|---|---|
| POST | `/signup/user` | Public | `SignupUser` | Creates a new unverified user |
| POST | `/verify-otp` | Public | `VerifyUserOTP` | Validates email OTP for login/signup |
| POST | `/request-otp` | Public | `RequestOTP` | Triggers a new OTP email |
| POST | `/login` | Public | `Login` | Email + Password authentication |
| POST | `/google` | Public | `GoogleAuth` | Google OAuth Login |
| POST | `/google/signup` | Public | `GoogleSignup` | Google OAuth Signup |
| POST | `/apple` | Public | `AppleAuth` | Apple OAuth Login |
| POST | `/apple/signup` | Public | `AppleSignup` | Apple OAuth Signup |
| POST | `/refresh` | Public | `Refresh` | Refresh JWT using refresh token |
| GET | `/me` | **Bearer JWT** | `GetMe` | Retrieve current authenticated user profile |

## 2. Organizations (`/orgs`)
| Method | Path | Auth Required | Handler | Description |
|---|---|---|---|---|
| POST | `/signup` | Public | `SignupOrganization` | Create a new organization (Tenant) |
| POST | `/verify-otp` | Public | `VerifyOrgOTP` | Verify organization creation |
| GET | `/validate/{orgCode}` | Public | `ValidateOrg` | Validate invite code |
| POST | `/join` | **Bearer JWT** | `RequestJoinOrg` | Request to join a tenant |
| GET | `/{orgId}/members/pending` | **Bearer JWT** (Admin) | `GetPendingRequests` | List pending join requests |
| POST | `/{orgId}/members/{memberId}/approve` | **Bearer JWT** (Admin) | `ApproveMember` | Approve member into tenant |
| POST | `/{orgId}/members/{memberId}/reject` | **Bearer JWT** (Admin) | `RejectMember` | Reject member from tenant |
| POST | `/{orgId}/regenerate-code` | **Bearer JWT** (Admin) | `RegenerateOrgCode` | Generate new invite code |

## 3. Projects (`/projects`)
**All endpoints require Bearer JWT.**

| Method | Path | Handler | Description |
|---|---|---|---|
| POST | `/` | `Create` | Create a new project (Tenant Scoped) |
| GET | `/` | `List` | List projects (Tenant Scoped) |
| GET | `/trash` | `ListTrash` | List soft-deleted projects |
| GET | `/{projectId}` | `Get` | Get project details |
| PUT | `/{projectId}` | `Update` | Update project metadata |
| DELETE | `/{projectId}` | `SoftDelete` | Move project to trash |
| POST | `/{projectId}/restore` | `Restore` | Restore from trash |
| DELETE | `/{projectId}/permanent` | `PermanentDelete` | Hard delete project |
| DELETE | `/{projectId}/archive` | `Archive` | Archive project |
| GET | `/{projectId}/timeline` | `GetTimeline` | Get project timeline events |
| PUT | `/{projectId}/timeline/{eventId}/status`| `UpdateTimelineEventStatus` | Update milestone status |
| POST | `/{projectId}/timeline/{eventId}/comments`| `AddTimelineComment` | Add comment to milestone |
| GET | `/{projectId}/chat` | `GetChat` | Get real-time chat messages |
| POST | `/{projectId}/chat` | `SendMessage` | Send chat message |
| POST | `/{projectId}/chat/{messageId}/resolve` | `ResolveMessage` | Mark urgency resolved |
| GET | `/{projectId}/client-emails` | `GetClientEmails` | Get email logs |
| POST | `/{projectId}/client-emails/send` | `SendClientEmail` | Trigger email to client |
| POST | `/{projectId}/client-emails/{logId}/resend`| `ResendClientEmail` | Resend specific email |
| GET | `/{projectId}/activities` | `GetActivities` | Audit log of project activities |

## 4. Captures (`/captures`)
**All endpoints require Bearer JWT.**

| Method | Path | Handler | Description |
|---|---|---|---|
| POST | `/` | `Create` | Register new capture session |
| GET | `/{id}` | `Get` | Get capture details |
| GET | `/project/{projectId}` | `ListByProject` | List captures for project |
| PUT | `/{id}/status` | `UpdateStatus` | Update upload/processing status |

## 5. Resumable Uploads (`/uploads`)
**All endpoints require Bearer JWT.**

| Method | Path | Handler | Description |
|---|---|---|---|
| POST | `/init` | `Init` | Initialize a resumable 5MB chunked upload session |
| POST | `/{sessionId}/chunk/{chunkIndex}`| `UploadChunk` | Upload binary chunk |
| GET | `/{sessionId}/progress` | `GetProgress` | Get chunk upload progress |
| POST | `/{sessionId}/complete` | `Complete` | Trigger quarantine check and merge |

## 6. Job Orchestrator (`/jobs`)
**All endpoints require Bearer JWT.**

| Method | Path | Handler | Description |
|---|---|---|---|
| POST | `/` | `Create` | Submit new reconstruction job |
| GET | `/{id}` | `Get` | Get job status & state |
| GET | `/project/{projectId}` | `ListByProject` | List jobs in a project |
| PUT | `/{id}/progress` | `UpdateProgress` | Update stage (Worker Auth Required) |
| POST | `/{id}/logs` | `AddLog` | Append execution logs |
| GET | `/{id}/logs` | `GetLogs` | Read execution logs |

## 7. Models (`/models`)
**All endpoints require Bearer JWT.**

| Method | Path | Handler | Description |
|---|---|---|---|
| POST | `/` | `Create` | Register 3D model asset |
| GET | `/{id}` | `Get` | Get model details |
| GET | `/project/{projectId}/active`| `GetActive` | Get the primary LOD for project |
| GET | `/project/{projectId}` | `ListByProject` | List all LODs/models |
| POST | `/{id}/artifacts` | `AddArtifact` | Add binary asset reference to model |

## 8. POIs (`/pois`)
**All endpoints require Bearer JWT.**

| Method | Path | Handler | Description |
|---|---|---|---|
| POST | `/` | `Create` | Create a 3D Point of Interest |
| GET | `/{id}` | `Get` | Get POI details |
| GET | `/project/{projectId}` | `ListByProject` | List POIs |
| PUT | `/{id}` | `Update` | Update POI coordinates/metadata |
| DELETE | `/{id}` | `Delete` | Remove POI |

## 9. Search (`/search`)
**All endpoints require Bearer JWT.**

| Method | Path | Handler | Description |
|---|---|---|---|
| POST | `/spatial` | `SearchSpatial` | Execute ST_DWithin and semantic text queries |

## 10. Navigation (`/navigation`)
**All endpoints require Bearer JWT.**

| Method | Path | Handler | Description |
|---|---|---|---|
| POST | `/nodes` | `CreateNode` | Create pathfinding node |
| GET | `/nodes/project/{projectId}` | `ListNodes` | List nodes for graph |
| POST | `/edges` | `CreateEdge` | Create pathfinding edge (distance/wheelchair) |
| GET | `/edges/project/{projectId}` | `ListEdges` | List edges |
| POST | `/route` | `CalculateRoute` | Execute Dijkstra/A* routing |

## 11. Viewer (`/viewer`)
**All endpoints require Bearer JWT.**

| Method | Path | Handler | Description |
|---|---|---|---|
| POST | `/bookmarks` | `CreateBookmark` | Save camera viewpoint |
| GET | `/bookmarks/project/{projectId}`| `ListBookmarks` | List camera viewpoints |
| DELETE | `/bookmarks/{id}` | `DeleteBookmark` | Delete viewpoint |
| POST | `/annotations` | `CreateAnnotation`| Create 3D semantic annotation |
| GET | `/annotations/project/{projectId}`| `ListAnnotations`| List annotations |
| DELETE | `/annotations/{id}` | `DeleteAnnotation`| Delete annotation |

## System Endpoints
| Method | Path | Auth Required | Description |
|---|---|---|---|
| GET | `/health` | Public | System Healthcheck `/healthz` equivalent |
| GET | `/uploads/*` | Public | Static file server for local dev (S3 bypass) |
