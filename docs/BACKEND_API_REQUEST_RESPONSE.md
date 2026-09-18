# VĀSTU Spatial Computing Platform: Backend API Specification
**Comprehensive Request & Response Documentation for Control Plane and Spatial Services**

---

## 1. Architectural Overview & Service Ports

The VĀSTU backend infrastructure is split into two primary operational planes:

| Service | Technology | Port | Base URL | Scope |
|---|---|---|---|---|
| **Go Core Control Plane** | Go 1.22 + Chi Router | `8080` | `http://localhost:8080/api/v1` | Multi-tenancy, Auth, Organization lifecycle, Project management, Timeline/Chat, Chunked Storage, POI/Navigation CRUD, Viewer state |
| **Python Spatial Control Plane** | Python 3.9+ FastAPI | `8000` | `http://localhost:8000/api/v1` | 22-stage reconstruction pipeline, Tri-representation models, Central quality engine, A* routing, AR relocalization, WebSockets |

### Global Authentication Standard
All protected endpoints expect a standard HTTP `Authorization` Bearer token header:
```http
Authorization: Bearer <jwt_access_token>
```
For Go endpoints: Signed JWT containing `user_id`, `org_id`, `role`, and `email`.
For Python endpoints: Bearer tokens prefixed with `vastu_token_<user_id>` or standard JWTs.

---

## Part I: Go Core Control Plane APIs (Port 8080)

### Response Envelope Standard
Go Control Plane responses standardly follow this JSON envelope:

#### Success Response (`HTTP 200 / 201`):
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": { ... }
}
```

#### Error Response (`HTTP 400 / 401 / 403 / 404 / 500`):
```json
{
  "error": "Detailed error description"
}
```

---

### 1. Authentication Service (`/api/v1/auth`)

#### 1.1 Register New User
- **Method & Path**: `POST /api/v1/auth/signup/user`
- **Auth**: Public
- **Request Body**:
```json
{
  "full_name": "Aditya Rao",
  "email": "aditya@krads.co.in",
  "password": "SecurePassword123!",
  "phone_number": "+919876543210"
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Verification OTP has been sent to your email address",
  "data": {
    "email": "aditya@krads.co.in"
  }
}
```

#### 1.2 Verify User OTP
- **Method & Path**: `POST /api/v1/auth/verify-otp`
- **Auth**: Public
- **Request Body**:
```json
{
  "email": "aditya@krads.co.in",
  "otp_code": "482910",
  "purpose": "SIGNUP" // or "LOGIN"
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Email successfully verified",
  "data": {
    "user": {
      "id": "a576db68-bf04-4c4f-9e76-3f0f7f3408a1",
      "email": "aditya@krads.co.in",
      "full_name": "Aditya Rao",
      "is_active": true,
      "created_at": "2026-03-07T10:00:00Z"
    },
    "tokens": {
      "access_token": "eyJhbGciOiJIUzI1Ni...",
      "refresh_token": "eyJhbGciOiJIUzI1Ni...",
      "expires_in": 3600
    }
  }
}
```

#### 1.3 Request OTP
- **Method & Path**: `POST /api/v1/auth/request-otp`
- **Auth**: Public
- **Request Body**:
```json
{
  "email": "aditya@krads.co.in",
  "purpose": "LOGIN"
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Login verification code dispatched to email",
  "data": {
    "otp_id": "93a38b1f-7fa4-469b-90f7-542152865c1a"
  }
}
```

#### 1.4 User Password Login
- **Method & Path**: `POST /api/v1/auth/login`
- **Auth**: Public
- **Request Body**:
```json
{
  "email": "aditya@krads.co.in",
  "password": "SecurePassword123!"
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "a576db68-bf04-4c4f-9e76-3f0f7f3408a1",
      "email": "aditya@krads.co.in",
      "full_name": "Aditya Rao"
    },
    "tokens": {
      "access_token": "eyJhbGci...",
      "refresh_token": "eyJhbGci...",
      "expires_in": 3600
    },
    "memberships": [
      {
        "org_id": "c71a3641-0f7e-4ea7-90c7-28562d645931",
        "org_name": "Krads Agency Labs",
        "role": "ORGANIZATION_ADMIN"
      }
    ]
  }
}
```

#### 1.5 Refresh Access Token
- **Method & Path**: `POST /api/v1/auth/refresh`
- **Auth**: Public
- **Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Token refreshed",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "refresh_token": "eyJhbGciOiJIUzI1Ni...",
    "expires_in": 3600
  }
}
```

#### 1.6 Get Current User Profile
- **Method & Path**: `GET /api/v1/auth/me`
- **Auth**: Protected (`Bearer <token>`)
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Current user profile",
  "data": {
    "user": {
      "id": "a576db68-bf04-4c4f-9e76-3f0f7f3408a1",
      "email": "aditya@krads.co.in",
      "full_name": "Aditya Rao"
    },
    "active_org": {
      "id": "c71a3641-0f7e-4ea7-90c7-28562d645931",
      "name": "Krads Agency Labs",
      "org_code": "KRADS-8921"
    },
    "active_role": "ORGANIZATION_ADMIN",
    "memberships": [
      {
        "org_id": "c71a3641-0f7e-4ea7-90c7-28562d645931",
        "role": "ORGANIZATION_ADMIN"
      }
    ]
  }
}
```

---

### 2. Organization & Multi-Tenancy Service (`/api/v1/orgs`)

#### 2.1 Register New Organization (Tenant)
- **Method & Path**: `POST /api/v1/orgs/signup`
- **Auth**: Public
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `org_name`: string (e.g. "Krads Agency Labs")
  - `org_type`: string (e.g. "Enterprise")
  - `industry`: string (e.g. "Architecture & Real Estate")
  - `business_email`: string (e.g. "contact@krads.co.in")
  - `phone_number`: string (e.g. "+919876543210")
  - `country`, `state`, `city`: strings
  - `website`: string
  - `admin_name`: string
  - `admin_password`: string
  - `gst_number`, `pan_number`, `registration_number`: strings (Optional tax IDs)
  - `document`: binary file (Business verification PDF / certificate)
  - `logo`: binary file (Optional PNG/JPEG)
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Organization registration initiated. Verification OTP sent to business email.",
  "data": {
    "business_email": "contact@krads.co.in",
    "org_name": "Krads Agency Labs"
  }
}
```

#### 2.2 Verify Organization Registration OTP
- **Method & Path**: `POST /api/v1/orgs/verify-otp`
- **Auth**: Public
- **Request Body**:
```json
{
  "email": "contact@krads.co.in",
  "otp_code": "729401"
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Organization verified successfully",
  "data": {
    "org": {
      "id": "c71a3641-0f7e-4ea7-90c7-28562d645931",
      "name": "Krads Agency Labs",
      "org_code": "KRADS-8921",
      "status": "ACTIVE"
    },
    "tokens": {
      "access_token": "eyJhbGci...",
      "refresh_token": "eyJhbGci..."
    }
  }
}
```

#### 2.3 Validate Organization Invite Code
- **Method & Path**: `GET /api/v1/orgs/validate/{orgCode}`
- **Auth**: Public
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Organisation validated",
  "data": {
    "valid": true,
    "org_id": "c71a3641-0f7e-4ea7-90c7-28562d645931",
    "name": "Krads Agency Labs",
    "org_code": "KRADS-8921",
    "status": "ACTIVE",
    "country": "India"
  }
}
```

#### 2.4 Request to Join Organization
- **Method & Path**: `POST /api/v1/orgs/join`
- **Auth**: Protected (`Bearer <token>`)
- **Request Body**:
```json
{
  "org_code": "KRADS-8921"
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Join request submitted. Pending organization admin approval.",
  "data": {
    "id": "d13a9482-127b-402a-9e45-f09bce4916a2",
    "org_id": "c71a3641-0f7e-4ea7-90c7-28562d645931",
    "user_id": "a576db68-bf04-4c4f-9e76-3f0f7f3408a1",
    "status": "PENDING",
    "created_at": "2026-03-07T11:00:00Z"
  }
}
```

#### 2.5 Approve or Reject Member
- **Method & Path**: `POST /api/v1/orgs/{orgId}/members/{memberId}/approve`
- **Auth**: Protected (Org Admin)
- **Request Body**:
```json
{
  "assigned_role": "CAPTURE_OPERATOR" // or "MEMBER", "EDITOR", "VIEWER"
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Member request approved successfully"
}
```

---

### 3. Project Management Service (`/api/v1/projects`)

#### 3.1 Create Project
- **Method & Path**: `POST /api/v1/projects`
- **Auth**: Protected (`Bearer <token>`)
- **Request Body**:
```json
{
  "name": "RMZ Ecospace Campus 4A",
  "client_name": "RMZ Corp",
  "description": "Commercial office spatial computing digital twin",
  "location_city": "Bengaluru",
  "location_state": "Karnataka",
  "location_country": "India",
  "typology": "commercial_office",
  "ceiling_height_meters": 3.4,
  "total_floors_count": 4,
  "precision_gate_cm": 2.5
}
```
- **Response (`201 Created`)**:
```json
{
  "success": true,
  "message": "Project created successfully",
  "data": {
    "id": "784a91b2-56fa-49cf-82b4-71c6db984102",
    "name": "RMZ Ecospace Campus 4A",
    "slug": "rmz-ecospace-campus-4a",
    "client_name": "RMZ Corp",
    "status": "active",
    "created_at": "2026-03-07T11:30:00Z"
  }
}
```

#### 3.2 List Active Projects
- **Method & Path**: `GET /api/v1/projects`
- **Auth**: Protected (`Bearer <token>`)
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Projects retrieved",
  "data": [
    {
      "id": "784a91b2-56fa-49cf-82b4-71c6db984102",
      "name": "RMZ Ecospace Campus 4A",
      "client_name": "RMZ Corp",
      "typology": "commercial_office",
      "total_area_sqft": 45000.0,
      "total_floors_count": 4,
      "spaces_count": 12,
      "status": "active",
      "created_at": "2026-03-07T11:30:00Z"
    }
  ]
}
```

#### 3.3 Project Timeline & Milestones
- **Method & Path**: `GET /api/v1/projects/{projectId}/timeline`
- **Auth**: Protected
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Timeline events retrieved",
  "data": [
    {
      "id": "184b901a-8451-408f-a9cb-00192837461a",
      "title": "LiDAR Scanning & Mobile Capture",
      "stage": "CAPTURE",
      "status": "COMPLETED",
      "actor_name": "Field Operator Alpha",
      "completed_at": "2026-03-07T14:00:00Z"
    }
  ]
}
```

#### 3.4 Real-Time Project Chat & Urgency Control
- **Method & Path**: `POST /api/v1/projects/{projectId}/chat`
- **Auth**: Protected
- **Request Body**:
```json
{
  "message": "Need re-scan of North corridor due to specular reflections.",
  "is_urgent": true
}
```
- **Response (`201 Created`)**:
```json
{
  "success": true,
  "message": "Message sent successfully",
  "data": {
    "id": "6a9081bc-5612-4f11-9a7c-3f9104812741",
    "project_id": "784a91b2-56fa-49cf-82b4-71c6db984102",
    "sender_id": "a576db68-bf04-4c4f-9e76-3f0f7f3408a1",
    "message": "Need re-scan of North corridor due to specular reflections.",
    "is_urgent": true,
    "is_resolved": false,
    "created_at": "2026-03-07T14:15:00Z"
  }
}
```

---

### 4. Uploads & Chunked Direct Storage (`/api/v1/uploads`)

#### 4.1 Initialize Chunked Upload
- **Method & Path**: `POST /api/v1/uploads/init`
- **Auth**: Protected
- **Request Body**:
```json
{
  "capture_id": "f8910243-9182-419b-a012-781920384716",
  "artifact_type": "VIDEO_RAW", // "DEPTH_STREAM", "IMU_CSV", "POINT_CLOUD"
  "total_bytes": 104857600,
  "chunk_size_bytes": 5242880,
  "total_chunks": 20,
  "file_name": "capture_floor2.mov"
}
```
- **Response (`201 Created`)**:
```json
{
  "success": true,
  "message": "Upload session initiated",
  "data": {
    "session_id": "b1827364-a019-4829-bb19-472910482910",
    "chunk_size": 5242880,
    "total_chunks": 20
  }
}
```

#### 4.2 Upload Chunk
- **Method & Path**: `POST /api/v1/uploads/{sessionId}/chunk/{chunkIndex}`
- **Auth**: Protected
- **Headers**:
  - `X-Chunk-SHA256`: string (Chunk hex checksum)
  - `Content-Type`: `application/octet-stream` or `multipart/form-data`
- **Request Body**: Binary byte stream of chunk.
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Chunk uploaded successfully",
  "data": {
    "chunk_index": 0,
    "bytes_written": 5242880
  }
}
```

#### 4.3 Finalize Upload Session
- **Method & Path**: `POST /api/v1/uploads/{sessionId}/complete`
- **Auth**: Protected
- **Request Body**:
```json
{
  "final_checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Upload finalized and verified successfully",
  "data": {
    "file_url": "/uploads/capture_floor2.mov"
  }
}
```

---

## Part II: Python Spatial Control Plane APIs (Port 8000)

### 1. Spatial Projects & Spaces (`/api/v1/projects`, `/api/v1/spaces`)

#### 1.1 List Projects
- **Method & Path**: `GET /api/v1/projects`
- **Response (`200 OK`)**:
```json
[
  {
    "id": "784a91b2-56fa-49cf-82b4-71c6db984102",
    "name": "RMZ Ecospace Campus 4A",
    "typology": "commercial_office",
    "total_area_sqft": 45000.0,
    "ceiling_height_meters": 3.4,
    "total_floors_count": 4,
    "spaces_count": 12,
    "precision_gate_cm": 2.5,
    "status": "active",
    "created_at": "2026-03-07T11:30:00Z",
    "updated_at": "2026-03-07T11:30:00Z"
  }
]
```

#### 1.2 Register Space Section
- **Method & Path**: `POST /api/v1/spaces`
- **Request Body**:
```json
{
  "project_id": "784a91b2-56fa-49cf-82b4-71c6db984102",
  "name": "Conference Suite 401",
  "space_type": "Meeting Room",
  "area_m2": 48.5,
  "ceiling_height_meters": 3.0,
  "status": "PROCESSING"
}
```
- **Response (`201 Created`)**:
```json
{
  "id": "sp_9a82bc10",
  "project_id": "784a91b2-56fa-49cf-82b4-71c6db984102",
  "name": "Conference Suite 401",
  "space_type": "Meeting Room",
  "status": "PROCESSING",
  "active_version": "1.0.0",
  "quality_score": 0.0,
  "objects_count": 0,
  "pois_count": 0,
  "area_m2": 48.5,
  "created_at": "2026-03-07T12:00:00Z",
  "updated_at": "2026-03-07T12:00:00Z"
}
```

---

### 2. Physical Captures & Contract 1 Ingestion (`/api/v1/captures`)

#### 2.1 Ingest Contract 1 Capture Manifest
- **Method & Path**: `POST /api/v1/captures`
- **Request Body**:
```json
{
  "capture_id": "93b8214a-5690-410a-84bf-391820485910",
  "project_id": "784a91b2-56fa-49cf-82b4-71c6db984102",
  "device_model": "iPhone 15 Pro",
  "device_os_version": "iOS 18.2",
  "app_version": "2.0.0",
  "start_time": "2026-03-07T12:30:00Z",
  "end_time": "2026-03-07T12:35:00Z",
  "frame_count": 9000,
  "has_depth": true,
  "has_imu": true,
  "resolution": [1920, 1080],
  "framerate_fps": 30.0,
  "operator_id": "field_op_01"
}
```
- **Response (`201 Created`)**:
```json
{
  "status": "ACCEPTED",
  "message": "Capture session registered and manifest validated",
  "capture_id": "93b8214a-5690-410a-84bf-391820485910"
}
```

#### 2.2 Validate Capture Session Manifest
- **Method & Path**: `POST /api/v1/captures/{capture_id}/validate`
- **Response (`200 OK`)**:
```json
{
  "is_valid": true,
  "capture_id": "93b8214a-5690-410a-84bf-391820485910",
  "errors": [],
  "warnings": [],
  "checks_passed": [
    "Resolution meets 1080p requirement",
    "IMU telemetry stream continuous at 100Hz",
    "LiDAR depth stream synchronized with RGB timestamps"
  ]
}
```

---

### 3. Automated 22-Stage Orchestrated Pipeline (`/api/v1/jobs`)

#### 3.1 Start Automated Pipeline Execution
- **Method & Path**: `POST /api/v1/jobs/orchestrated`
- **Request Body**:
```json
{
  "project_id": "784a91b2-56fa-49cf-82b4-71c6db984102",
  "capture_id": "93b8214a-5690-410a-84bf-391820485910",
  "operator_id": "field_op_01",
  "device_model": "iPhone 15 Pro",
  "async_mode": true
}
```
- **Response (`201 Created`)**:
```json
{
  "status": "ACCEPTED",
  "message": "22-stage automated pipeline started in background",
  "job_id": "job_e79104fa",
  "progress_endpoint": "/api/v1/jobs/job_e79104fa/progress"
}
```

#### 3.2 Observable Stage-Level Progress
- **Method & Path**: `GET /api/v1/jobs/{job_id}/progress`
- **Response (`200 OK`)**:
```json
{
  "job_id": "job_e79104fa",
  "project_id": "784a91b2-56fa-49cf-82b4-71c6db984102",
  "capture_id": "93b8214a-5690-410a-84bf-391820485910",
  "status": "RUNNING",
  "current_stage": "DENSE_RECONSTRUCTION",
  "overall_progress_pct": 54.5,
  "stage_progress_pct": 80.0,
  "stage_events": [
    {
      "stage": "MOBILE_CAPTURE",
      "status": "COMPLETED",
      "progress_pct": 100.0,
      "message": "Capture verified"
    },
    {
      "stage": "CAMERA_POSE_ESTIMATION",
      "status": "COMPLETED",
      "progress_pct": 100.0,
      "message": "Trajectory bundle adjusted"
    }
  ]
}
```

---

### 4. Tri-Representation Model Assets & Lineage (`/api/v1/models`)

#### 4.1 Retrieve Visual Representation (Web Viewer Stream)
- **Method & Path**: `GET /api/v1/models/{version_id}/visual`
- **Description**: Zero collision / structural overhead. Contains only textured mesh and LOD GLTF assets for rendering.
- **Response (`200 OK`)**:
```json
{
  "model_version_id": "1.0.0",
  "representation_type": "VISUAL",
  "gltf_url": "/storage/models/1.0.0/visual.gltf",
  "texture_atlas_url": "/storage/models/1.0.0/textures.bin",
  "vertex_count": 284100,
  "triangle_count": 568200,
  "lod_tiers": [
    {"lod": 0, "triangles": 568200, "distance_range_m": [0, 5]},
    {"lod": 1, "triangles": 142050, "distance_range_m": [5, 15]},
    {"lod": 2, "triangles": 35500, "distance_range_m": [15, 50]}
  ]
}
```

#### 4.2 Retrieve Structural Representation (BIM/Architectural)
- **Method & Path**: `GET /api/v1/models/{version_id}/structural`
- **Description**: Contains watertight architectural elements: boundary planes, walls, ceiling, openings (doors, windows).
- **Response (`200 OK`)**:
```json
{
  "model_version_id": "1.0.0",
  "representation_type": "STRUCTURAL",
  "floors": [
    {
      "floor_index": 0,
      "elevation_z": 0.0,
      "area_m2": 450.0,
      "boundary_polygon": [[-15.0, -10.0], [15.0, -10.0], [15.0, 10.0], [-15.0, 10.0]]
    }
  ],
  "walls": [
    {
      "wall_id": "wall_north",
      "plane_equation": [0.0, 1.0, 0.0, -10.0],
      "thickness_meters": 0.20,
      "openings": [
        {"type": "DOOR", "width_m": 1.2, "height_m": 2.1, "center_xyz": [0.0, 10.0, 1.05]}
      ]
    }
  ]
}
```

#### 4.3 Retrieve Collision Representation (Kinematics & NavMesh)
- **Method & Path**: `GET /api/v1/models/{version_id}/collision`
- **Description**: Simplified colliders with human body clearance inflation ($r = 0.35\text{m}$) and floor clamping ($1.65\text{m}$).
- **Response (`200 OK`)**:
```json
{
  "model_version_id": "1.0.0",
  "representation_type": "COLLISION",
  "human_radius_meters": 0.35,
  "eye_height_meters": 1.65,
  "walkable_surfaces": [
    {"surface_id": "floor_main", "elevation_y": 0.0, "extent": [-15.0, -10.0, 15.0, 10.0]}
  ],
  "collision_obstacles": [
    {
      "obstacle_id": "table_conference",
      "type": "AABB",
      "center": [0.0, 0.45, 0.0],
      "extent": [2.4, 0.9, 1.4],
      "is_walkable": false
    }
  ]
}
```

#### 4.4 4-Way Differential Model Comparison
- **Method & Path**: `GET /api/v1/models/{version_id}/compare/{target_version_id}`
- **Response (`200 OK`)**:
```json
{
  "source_version": "1.0.0",
  "target_version": "2.0.0",
  "geometry_diff": {
    "changed_cells_count": 3,
    "max_displacement_cm": 1.8,
    "volumetric_change_pct": 0.04
  },
  "pois_diff": {
    "added": ["poi_fire_extinguisher_04"],
    "migrated": ["poi_meeting_room_4"],
    "drift_residuals_m": {"poi_meeting_room_4": 0.012}
  },
  "navigation_diff": {
    "topology_changed": false,
    "blocked_corridors": []
  },
  "confidence_diff": {
    "overall_delta": "+0.03"
  }
}
```

---

### 5. Points of Interest (POIs) & Spatial Query (`/api/v1/pois`)

#### 5.1 3D Spatial Radius Query
- **Method & Path**: `POST /api/v1/pois/spatial-query`
- **Request Body**:
```json
{
  "center_xyz": [2.5, 1.65, -4.0],
  "radius_meters": 8.0,
  "model_version": "1.0.0",
  "k_nearest": 5
}
```
- **Response (`200 OK`)**:
```json
[
  {
    "poi": {
      "id": "e910243a-7182-410a-84bf-391820485910",
      "name": "Fire Exit A",
      "category": "SAFETY",
      "room": "Floor 4 North Corridor",
      "coordinates": {"x": 2.1, "y": 1.65, "z": -4.2}
    },
    "distance_meters": 0.447
  }
]
```

#### 5.2 Raycast Placement (Exact Surface Intersection)
- **Method & Path**: `POST /api/v1/pois/raycast-placement`
- **Request Body**:
```json
{
  "ray_origin": [0.0, 1.65, 0.0],
  "ray_direction": [0.707, -0.2, 0.679],
  "name": "Emergency Defibrillator",
  "category": "MEDICAL",
  "room": "Reception",
  "model_version": "1.0.0"
}
```
- **Response (`201 Created`)**:
```json
{
  "status": "PLACED",
  "poi": {
    "id": "c1928471-1029-482a-99ab-102938475619",
    "name": "Emergency Defibrillator",
    "category": "MEDICAL",
    "coordinates": {"x": 4.25, "y": 1.45, "z": 3.98},
    "normal": [0.0, 0.0, -1.0]
  }
}
```

---

### 6. Indoor Navigation & Route Planning (`/api/v1/navigation`)

#### 6.1 Plan Indoor Route
- **Method & Path**: `POST /api/v1/navigation/plan`
- **Request Body**:
```json
{
  "start_position": [1.0, 1.65, 2.0],
  "destination_coordinates": [8.5, 1.65, -12.0],
  "destination_poi_id": null,
  "enable_smoothing": true,
  "wheelchair_accessible": true,
  "human_radius_m": 0.35,
  "model_version": "1.0.0"
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "total_distance_m": 16.42,
  "estimated_time_sec": 13.6,
  "is_wheelchair_accessible": true,
  "waypoints": [
    [1.0, 1.65, 2.0],
    [2.5, 1.65, 0.0],
    [5.0, 1.65, -6.0],
    [8.5, 1.65, -12.0]
  ],
  "turn_instructions": [
    {"step": 1, "text": "Walk forward 3.2m along corridor", "distance_m": 3.2},
    {"step": 2, "text": "Turn right at Meeting Room 4", "distance_m": 6.8},
    {"step": 3, "text": "Arrive at destination on left", "distance_m": 6.4}
  ]
}
```

#### 6.2 Blocked Non-Walkable Regions with Cause Analysis
- **Method & Path**: `GET /api/v1/navigation/blocked-regions?version=1.0.0`
- **Response (`200 OK`)**:
```json
[
  {
    "id": "blk_conf_table",
    "cause": "OBSTACLE_COLLIDER",
    "source_entity_id": "table_conference",
    "center_3d": [0.0, 0.45, 0.0],
    "extent_3d": [3.1, 0.9, 2.1], // Extent after 0.35m human radius clearance inflation
    "walkable": false
  }
]
```

---

### 7. Central Quality Engine & Targeted Rescans (`/api/v1/quality`, `/api/v1/rescans`)

#### 7.1 Evaluate Space Quality
- **Method & Path**: `GET /api/v1/quality/space/{space_id}`
- **Response (`200 OK`)**:
```json
{
  "space_id": "sp_9a82bc10",
  "overall_score": 0.94,
  "verdict": "PASS",
  "scores": {
    "overall": 0.94,
    "geometry_watertightness": 0.95,
    "tracking_vio_drift": 0.92,
    "spatial_coverage": 0.95,
    "texture_sharpness": 0.91,
    "cell_continuity": 0.97,
    "navigation_connectivity": 0.96
  },
  "metrics": {
    "geometry_score": 95,
    "coverage_pct": 95,
    "tracking_score": 92,
    "navigation_walkability": 96
  },
  "recommendations": ["Space meets sub-2.5cm spatial precision tolerance."]
}
```

#### 7.2 Dispatch Rescan to Field Operator
- **Method & Path**: `POST /api/v1/rescans/{request_id}/dispatch`
- **Request Body**:
```json
{
  "operator_id": "field_operator_02"
}
```
- **Response (`200 OK`)**:
```json
{
  "status": "ASSIGNED",
  "request_id": "rescan_89104",
  "dispatched_at": "2026-03-07T15:30:00Z"
}
```

#### 7.3 Incremental Fusion (Bypassing Global Rebuild)
- **Method & Path**: `POST /api/v1/rescans/{request_id}/integrate`
- **Response (`200 OK`)**:
```json
{
  "status": "FUSED",
  "request_id": "rescan_89104",
  "cell_id": "cell_4_north",
  "global_reconstruction_bypassed": true,
  "boundary_continuity_verified": true
}
```

---

### 8. AR Localization & Camera Relocalization (`/api/v1/ar`)

#### 8.1 Localize AR Device Frame
- **Method & Path**: `POST /api/v1/ar/localize`
- **Request Body**:
```json
{
  "model_id": "rmz_ecospace_4a",
  "detected_markers": [
    {
      "marker_id": "marker_qr_01",
      "corners_2d": [[100, 150], [200, 150], [200, 250], [100, 250]],
      "estimated_distance_m": 1.45
    }
  ],
  "vio_device_pose": {
    "position": [0.0, 1.4, 0.0],
    "rotation_quaternion": [0.0, 0.0, 0.0, 1.0]
  }
}
```
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "model_id": "rmz_ecospace_4a",
  "world_position": [2.45, 1.42, -5.10],
  "rotation_quaternion": [0.01, 0.707, 0.01, 0.707],
  "confidence": 0.98,
  "source": "MARKER_PNP",
  "residual_error_cm": 1.2
}
```

#### 8.2 Project Route Waypoints into AR Screen Coordinates
- **Method & Path**: `POST /api/v1/ar/project-route`
- **Request Body**:
```json
{
  "camera_pose": {
    "position": [2.45, 1.42, -5.10],
    "rotation_quaternion": [0.0, 0.707, 0.0, 0.707]
  },
  "camera_intrinsics": {
    "fx": 1420.5,
    "fy": 1420.5,
    "cx": 960.0,
    "cy": 540.0,
    "width": 1920,
    "height": 1080
  },
  "waypoints": [
    [2.45, 1.42, -5.10],
    [3.0, 1.42, -7.5],
    [5.0, 1.42, -10.0]
  ]
}
```
- **Response (`200 OK`)**:
```json
{
  "projected_points_2d": [
    {"x": 960.0, "y": 540.0, "in_frustum": true, "depth_meters": 0.0},
    {"x": 1054.2, "y": 542.1, "in_frustum": true, "depth_meters": 2.45},
    {"x": 1280.6, "y": 545.0, "in_frustum": true, "depth_meters": 5.82}
  ]
}
```

---

### 9. Infrastructure Telemetry Probes (`/api/v1/infrastructure`)

#### 9.1 Cluster Health & Resource Metrics
- **Method & Path**: `GET /api/v1/infrastructure/nodes`
- **Response (`200 OK`)**:
```json
{
  "cluster": "vastu-local-production",
  "nodes": [
    {
      "id": "node_control_plane",
      "name": "Control Plane",
      "role": "API / Ingestion Gateway",
      "status": "ONLINE",
      "cpu_percent": 12.4,
      "memory_percent": 42.5,
      "latency_ms": 1.2
    },
    {
      "id": "node_postgres",
      "name": "PostgreSQL 16 + PostGIS 3.4",
      "status": "ONLINE",
      "latency_ms": 1.8
    },
    {
      "id": "node_redis",
      "name": "Redis 7 Ephemeral Cache",
      "status": "ONLINE",
      "latency_ms": 0.6
    },
    {
      "id": "node_minio",
      "name": "MinIO S3 Spatial Blob Store",
      "status": "ONLINE",
      "latency_ms": 1.9
    }
  ]
}
```

---

### 10. Real-Time WebSockets (`/api/v1/ws`)

#### 10.1 Global System Events Broadcast
- **URL**: `ws://localhost:8000/api/v1/ws/events`
- **Initial Connection Handshake**:
```json
{
  "type": "CONNECTION_ESTABLISHED",
  "service": "vastu-event-bus",
  "timestamp": 1772960400.12
}
```
- **Client Heartbeat**: Send plain text `"ping"`. Server responds `{"type": "pong"}`.

#### 10.2 Job Progress Stream
- **URL**: `ws://localhost:8000/api/v1/ws/jobs/{job_id}`
- **Server Stream Messages**: Emits `WorkflowJobStatus` updates as the pipeline progresses:
```json
{
  "job_id": "job_e79104fa",
  "status": "RUNNING",
  "current_stage": "SEMANTIC_RECONSTRUCTION",
  "overall_progress_pct": 72.7,
  "stage_progress_pct": 45.0
}
```
Connection automatically terminates when job status reaches `COMPLETED`, `FAILED`, or `CANCELLED`.
