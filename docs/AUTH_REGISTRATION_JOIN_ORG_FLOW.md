# VĀSTU Spatial: Detailed End-to-End Flow Specification
## Authentication, Registration, Organization Onboarding & Team Membership

---

## 1. System Architecture Overview

VĀSTU Spatial employs a **Multi-Tenant Workspace Model** where every user belongs to one or more organizations or an individual personal workspace.

```mermaid
graph TD
    User([User Client: Web / iOS / Android])
    API[VĀSTU REST API Gateway :8000]
    AuthEngine[Go Auth & Security Service]
    Postgres[(PostgreSQL 16 Multi-Tenant DB)]
    
    User -->|HTTPS / REST + Bearer JWT| API
    API --> AuthEngine
    AuthEngine --> Postgres
    
    subgraph PostgreSQL Database Schema
        U[(users)]
        AID[(auth_identities)]
        O[(organizations)]
        OM[(organization_members)]
        OI[(organization_invites)]
        RT[(refresh_tokens)]
    end
    
    Postgres --- U
    Postgres --- AID
    Postgres --- O
    Postgres --- OM
    Postgres --- OI
    Postgres --- RT
```

---

## 2. Detailed Flow 1: Passwordless OTP Login & Registration

Passwordless OTP authentication is the primary login method across mobile and web. It handles both **Sign In** (existing user) and **Instant Sign Up** (new user).

### 2.1 Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Client)
    participant UI as Client UI (Web/iOS/Android)
    participant API as VĀSTU API (/api/v1/auth)
    participant DB as PostgreSQL DB
    
    User->>UI: Enters Email or Phone (e.g., architect@vastu.spatial)
    UI->>API: POST /api/v1/auth/otp/send { email, purpose: "LOGIN" }
    
    activate API
    API->>API: Rate Limit Check (Max 5 requests/15 min)
    API->>API: Generate 6-digit cryptographically secure OTP
    API->>DB: Upsert OTP challenge (expires_at: NOW + 10 min)
    API-->>UI: 200 OK { success: true, message: "OTP sent" }
    deactivate API
    
    UI->>User: Displays 6-digit OTP Input Screen
    User->>UI: Types 6-digit code (e.g., 123456)
    
    UI->>API: POST /api/v1/auth/otp/verify { email, otp_code, purpose: "LOGIN" }
    activate API
    API->>DB: Query OTP challenge where email=? AND otp_code=? AND expires_at > NOW()
    
    alt OTP Invalid or Expired
        API-->>UI: 400 Bad Request { error: "Invalid or expired OTP code" }
        UI-->>User: Show red inline error banner
    else OTP Valid
        API->>DB: Mark challenge as USED
        API->>DB: Upsert User (is_email_verified = true)
        API->>DB: Query Organization Memberships & Active Roles
        API->>API: Generate JWT Access Token (15m expiry) + Refresh Token (30d expiry)
        API->>DB: Insert hashed refresh token
        API-->>UI: 200 OK { token, user, organization, memberships }
        deactivate API
        
        UI->>UI: Persist tokens in secure client storage
        alt Has Active Organization
            UI->>User: Navigate to Dashboard Screen
        else Has Pending Join Request
            UI->>User: Navigate to Pending Approval Screen
        else No Organization
            UI->>User: Navigate to Organization Creation Wizard
        end
    end
```

### 2.2 API Specifications & Payloads

#### Step 1: Request OTP
- **Endpoint**: `POST /api/v1/auth/otp/send`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "email": "architect@company.com",
    "purpose": "login"
  }
  ```
- **Responses**:
  - `200 OK`:
    ```json
    {
      "success": true,
      "message": "Verification code dispatched successfully",
      "data": {
        "email": "architect@company.com"
      }
    }
    ```
  - `429 Too Many Requests`:
    ```json
    {
      "success": false,
      "error": "Rate limit exceeded. Please wait 2 minutes before requesting a new OTP."
    }
    ```

#### Step 2: Verify OTP
- **Endpoint**: `POST /api/v1/auth/otp/verify`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "email": "architect@company.com",
    "otp_code": "123456",
    "purpose": "login"
  }
  ```
- **Responses**:
  - `200 OK`:
    ```json
    {
      "success": true,
      "data": {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "user": {
          "id": "7b8f9e12-4567-890a-bcde-f1234567890a",
          "email": "architect@company.com",
          "phone": "+918208363287",
          "full_name": "Mayank Bajaj",
          "is_email_verified": true,
          "created_at": "2026-09-08T10:00:00Z"
        },
        "organization": {
          "id": "e2a14bc0-1234-5678-90ab-cdef12345678",
          "org_code": "MRXZFQBQD3S",
          "name": "Acme Spatial Studio",
          "legal_name": "Acme Spatial Studio Pvt Ltd",
          "status": "active"
        },
        "memberships": [
          {
            "id": "mem_01",
            "org_id": "e2a14bc0-1234-5678-90ab-cdef12345678",
            "role": "OWNER",
            "status": "ACTIVE"
          }
        ]
      }
    }
    ```
  - `400 Bad Request`:
    ```json
    {
      "success": false,
      "error": "Invalid verification code. 2 attempts remaining."
    }
    ```

---

## 3. Detailed Flow 2: Organization Founder Onboarding (Enterprise Studio)

When an enterprise studio founder registers their company, the backend executes an **Atomic Database Transaction** (`CreateOrganizationAtomic`).

### 3.1 Step-by-Step Onboarding Wizard

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Founder Onboarding Wizard                       │
├────────────────────────────────────────────────────────────────────────┤
│ Step 1: Founder Credentials (Name, Email, Phone, Password, Email OTP)   │
│ Step 2: Studio Information (Name, Legal Name, Industry, Org Type, Size)│
│ Step 3: Business Identifiers & Tax Documents (GSTIN, Registration Doc) │
│ Step 4: Studio Physical Address (Line 1 & 2, City, State, PIN, Country)│
│ Step 5: Atomic Submission & Processing Animation                       │
│ Step 6: Studio Created (Displays 12-char Org Code, WhatsApp Invite)    │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Backend Atomic Transaction Execution

```mermaid
sequenceDiagram
    autonumber
    participant Client as Web / iOS / Android
    participant API as Backend Handler
    participant TX as PostgreSQL Transaction (BEGIN)
    
    Client->>API: POST /api/v1/auth/signup/organization (Full Payload)
    activate API
    API->>TX: BEGIN TRANSACTION
    
    Note over TX: Step 1: Upsert User Record
    TX->>TX: INSERT INTO users (email, phone, full_name, password_hash, is_email_verified)
    
    Note over TX: Step 2: Auth Identity
    TX->>TX: INSERT INTO auth_identities (user_id, provider='EMAIL', provider_subject=email)
    
    Note over TX: Step 3: Organization Entity & Unique Org Code
    TX->>TX: Generate cryptographically random 12-char string (e.g. MRXZFQBQD3S)
    TX->>TX: INSERT INTO organizations (org_code, name, legal_name, org_type, industry, address...)
    
    Note over TX: Step 4: Assign Founder Ownership
    TX->>TX: INSERT INTO organization_members (org_id, user_id, role='OWNER', status='ACTIVE')
    
    Note over TX: Step 5: Generate Default 30-Day Invite Link
    TX->>TX: Generate 32-byte secure token
    TX->>TX: INSERT INTO organization_invites (org_id, token_hash, expires_at=NOW()+30d, max_uses=100)
    
    alt Any Database Constraint Fails (e.g. duplicate email)
        TX->>TX: ROLLBACK TRANSACTION
        API-->>Client: 409 Conflict { error: "An organization or user with this email already exists" }
    else All Steps Succeeded
        TX->>TX: COMMIT TRANSACTION
        API->>API: Generate Access JWT Token (claims: user_id, active_org_id, role="OWNER")
        API-->>Client: 201 Created { token, user, organization, invite }
    end
    deactivate API
```

### 3.3 Founder Registration Request Payload

```json
{
  "applicant_name": "Mayank Bajaj",
  "email": "mayank@vastu.spatial",
  "phone": "+918208363287",
  "password": "SecurePassword123!",
  "organization_name": "Acme Spatial Architecture",
  "legal_name": "Acme Spatial Architecture Pvt Ltd",
  "organization_type": "Architecture",
  "industry": "Commercial & Residential Spatial Design",
  "official_email": "contact@acmespatial.com",
  "official_phone": "+918208363287",
  "website": "https://acmespatial.com",
  "number_of_employees": "11-50",
  "year_established": 2024,
  "description": "BIM and 3D Gaussian Splatting Spatial Capture Studio",
  "identifier_type": "GSTIN",
  "identifier_value": "29AAAAA0000A1Z5",
  "address_line1": "100 Outer Ring Road, Tech Corridor",
  "address_line2": "Suite 400",
  "locality": "Bellandur",
  "city": "Bengaluru",
  "state": "Karnataka",
  "pincode": "560103",
  "country": "India"
}
```

### 3.4 Founder Registration Response Payload (`201 Created`)

```json
{
  "success": true,
  "message": "Organization created and founder registered successfully",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "d821e2a0-4567-890a-bcde-f1234567890a",
      "email": "mayank@vastu.spatial",
      "full_name": "Mayank Bajaj",
      "phone": "+918208363287"
    },
    "organization": {
      "id": "b9f1a234-1234-5678-90ab-cdef12345678",
      "org_code": "MRXZFQBQD3S",
      "name": "Acme Spatial Architecture",
      "legal_name": "Acme Spatial Architecture Pvt Ltd",
      "status": "active"
    },
    "invite": {
      "invite_url": "https://vastu.spatial/join/MRXZFQBQD3S/9a8b7c6d5e4f",
      "whatsapp_message": "Join Acme Spatial Architecture on VĀSTU Spatial: https://vastu.spatial/join/MRXZFQBQD3S/9a8b7c6d5e4f"
    }
  }
}
```

---

## 4. Detailed Flow 3: Team Member Join & Approval

Team members join an existing organization via two paths.

### 4.1 State Machine for Member Status

```mermaid
stateDiagram-v2
    [*] --> PENDING_APPROVAL: Join via 12-char Org Code
    [*] --> ACTIVE: Join via Valid Token Link
    
    PENDING_APPROVAL --> ACTIVE: Admin Approves Request
    PENDING_APPROVAL --> REJECTED: Admin Declines Request
    
    ACTIVE --> SUSPENDED: Admin Deactivates Member
    SUSPENDED --> ACTIVE: Admin Reactivates Member
    ACTIVE --> [*]: Member Removed
    REJECTED --> [*]
```

---

### 4.2 Path A: Join via 12-Character Organization Code

```mermaid
sequenceDiagram
    autonumber
    actor Member as Team Member (Client)
    actor Admin as Studio Admin / Owner
    participant API as VĀSTU API Server
    participant DB as PostgreSQL DB
    
    Member->>API: POST /api/v1/auth/join/org { org_code: "MRXZFQBQD3S", full_name, email, requested_role }
    activate API
    API->>DB: Find Organization by org_code="MRXZFQBQD3S"
    alt Org Code Does Not Exist
        API-->>Member: 404 Not Found { error: "Invalid organization code" }
    else Org Found
        API->>DB: INSERT INTO organization_members (org_id, user_id, role, status='PENDING_APPROVAL')
        API-->>Member: 200 OK { message: "Join request submitted. Awaiting approval." }
        deactivate API
        
        Note over Member: Member UI shows PendingApprovalPage
        
        Admin->>API: GET /api/v1/organizations/me/join-requests (Bearer Token)
        API->>DB: SELECT * FROM organization_members WHERE org_id=active_org AND status='PENDING_APPROVAL'
        API-->>Admin: 200 OK [ { id: "req_99", full_name: "Rahul Mehta", email: "rahul@company.com", requested_role: "EDITOR" } ]
        
        Admin->>API: PATCH /api/v1/organizations/me/join-requests/req_99 { status: "APPROVED" }
        activate API
        API->>DB: UPDATE organization_members SET status='ACTIVE' WHERE id='req_99'
        API-->>Admin: 200 OK { success: true, message: "Member approved" }
        deactivate API
        
        Note over Member: On next app refresh or poll, Member gains full access to /dashboard
    end
```

---

### 4.3 Path B: Join via Tokenized Public Invite Link

```mermaid
sequenceDiagram
    autonumber
    actor Invitee as Team Invitee (Web Browser)
    participant UI as EmployeeJoinPage.tsx
    participant API as VĀSTU API Server
    participant DB as PostgreSQL DB
    
    Invitee->>UI: Opens https://vastu.spatial/join/MRXZFQBQD3S/9a8b7c6d5e4f
    UI->>API: GET /api/v1/organizations/invites/MRXZFQBQD3S/9a8b7c6d5e4f
    activate API
    API->>DB: Query invite where token_hash=SHA256(token) AND expires_at > NOW() AND uses < max_uses
    alt Invite Invalid or Expired
        API-->>UI: 400 Bad Request { error: "Invite link expired or revoked" }
        UI-->>Invitee: Show error banner
    else Valid Invite
        API-->>UI: 200 OK { organization_name: "Acme Spatial Architecture", org_code: "MRXZFQBQD3S", assigned_role: "EDITOR" }
        deactivate API
        
        UI->>Invitee: Displays Studio Profile + Employee Registration Form
        Invitee->>UI: Fills Name, Work Email, Phone, Password + Completes OTP Verification
        UI->>API: POST /api/v1/auth/signup/employee { full_name, email, password, org_code, invite_token }
        
        activate API
        API->>DB: Increment invite uses
        API->>DB: Upsert User
        API->>DB: INSERT INTO organization_members (org_id, user_id, role='EDITOR', status='ACTIVE')
        API->>API: Generate Access JWT Token (claims: user_id, active_org_id, role="EDITOR")
        API-->>UI: 200 OK { token, user, organization }
        deactivate API
        
        UI->>Invitee: Direct transition to /dashboard
    end
```

---

## 5. Role-Based Access Control (RBAC) Matrix

| Permission / Action | `OWNER` | `ADMIN` | `EDITOR` | `VIEWER` |
| :--- | :---: | :---: | :---: | :---: |
| **Delete Organization** | ✅ | ❌ | ❌ | ❌ |
| **Manage Billing & GSTIN** | ✅ | ✅ | ❌ | ❌ |
| **Approve Join Requests** | ✅ | ✅ | ❌ | ❌ |
| **Generate Invite Links** | ✅ | ✅ | ❌ | ❌ |
| **Change Member Roles** | ✅ | ✅ | ❌ | ❌ |
| **Create 3D Spatial Projects** | ✅ | ✅ | ✅ | ❌ |
| **Upload LiDAR & Video Captures** | ✅ | ✅ | ✅ | ❌ |
| **Trigger Gaussian Splat Processing**| ✅ | ✅ | ✅ | ❌ |
| **View 3D Digital Twins & Floorplans**| ✅ | ✅ | ✅ | ✅ |
| **Export BIM / USDZ / OBJ Models** | ✅ | ✅ | ✅ | ✅ |

---

## 6. Comprehensive Error Handling & Status Codes

| Error Scenario | HTTP Code | Error JSON Response | Client Remediation |
| :--- | :---: | :--- | :--- |
| **Expired or invalid OTP** | `400` | `{"success": false, "error": "Invalid or expired OTP code"}` | Allow user to re-enter or tap "Resend OTP" |
| **OTP Rate Limit Exceeded**| `429` | `{"success": false, "error": "Too many requests. Please wait 2 minutes."}` | Disable send button with countdown timer |
| **Duplicate Organization Name / Email** | `409` | `{"success": false, "error": "Organization or work email already registered"}` | Prompt user to log in instead of creating a new org |
| **Invalid GSTIN Format** | `400` | `{"success": false, "error": "Invalid GSTIN. Expected 15 characters"}` | Pre-validate via regex `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$` |
| **Invalid Org Code** | `404` | `{"success": false, "error": "No organization found with code MRXZFQBQD3S"}` | Prompt user to re-check the 12-char code with their studio lead |
| **Expired Invite Link** | `410` | `{"success": false, "error": "This invitation link has expired"}` | Prompt user to request a fresh invite link from their admin |
| **Expired JWT Token** | `401` | `{"success": false, "error": "Token expired"}` | Transparently call `/api/v1/auth/token/refresh` |
