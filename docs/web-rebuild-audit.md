# VĀSTU Web Application Rebuild Audit

**Document:** `docs/web-rebuild-audit.md`  
**Date:** September 7, 2026  
**Auditor:** Lead Frontend Architect  
**Purpose:** Comprehensive audit of existing legacy web frontend prior to architectural rebuild.

---

## 1. Technical Stack & Build System

| Dimension | Legacy Implementation | Classification | Target Architecture |
| :--- | :--- | :--- | :--- |
| **Framework** | Next.js 14.2.8 (App Router) with mixed SSR/Client components | **REPLACE** | React 18 + TypeScript + Vite + Single-Page Client Architecture |
| **Build System** | Next.js webpack/turbopack via `next build` | **REPLACE** | Vite 5 with Rollup, strict ES modules, sub-second HMR |
| **Language** | TypeScript 5.5.4 (Loose / Partial Strictness) | **REIMPLEMENT** | TypeScript 5.5+ in `strict: true` mode across all modules |
| **CSS System** | TailwindCSS 3.4.19 + arbitrary utility classes + `globals.css` | **REPLACE** | Centralized VĀSTU Design Tokens + CSS Modules / Theme Tokens |
| **Containerization** | `Dockerfile.frontend` (multi-stage node:20-alpine runner) | **REIMPLEMENT** | Lightweight Nginx/Caddy container serving Vite SPA bundle |

---

## 2. Inventory of Existing Routes & Pages

| Route | File Path | Current Status / Issues | Classification | Rebuild Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `/` | `src/app/page.tsx` | Monolithic landing page (438 lines) with embedded preloader, hero, and simulator | **REPLACE** | Clean landing gateway with typed routing |
| `/login` | `src/app/login/page.tsx` | Legacy mixed login with OTP/password modal dependencies | **REPLACE** | Dedicated `/login` page using `services/api/auth.ts` |
| `/signup` | `src/app/signup/page.tsx` | Multi-step signup with organization code coupling | **REPLACE** | Standardized `/register` route |
| `/dashboard` | `src/app/dashboard/page.tsx` | Monolithic legacy dashboard (14KB) coupled to `DashboardContext` | **DELETE** | Clean `/dashboard` overview connected to server state |
| `/dashboard/*` (16 sub-routes) | `src/app/dashboard/{activity, analytics, buildings, capture, members, models, notifications, organization, processing, profile, projects, quality, roles, settings, spatial, viewer}` | Duplicated, fragmented legacy admin/user mix with dead mock states | **DELETE** | Segregated into User App (`/projects`, `/spaces`) and Admin App (`/admin/*`) |
| `/capture` | `src/app/capture/page.tsx` | 15-screen operator prototype in single file `MobileApp.tsx` | **REIMPLEMENT** | Clean modular feature flow under `/spaces/:spaceId/captures` and `/spaces/:spaceId/rescan` |
| `/spaces` | `src/app/spaces/page.tsx` | Client projects list | **REIMPLEMENT** | Rebuilt with domain service layer & React Router |
| `/spaces/projects/[id]` | `src/app/spaces/projects/[id]/page.tsx` | Spaces inventory for a project | **REIMPLEMENT** | Clean `/projects/:projectId` page |
| `/spaces/[id]` | `src/app/spaces/[id]/page.tsx` | Space overview card | **REIMPLEMENT** | Clean `/spaces/:spaceId` page |
| `/spaces/[id]/viewer` | `src/app/spaces/[id]/viewer/page.tsx` | 3D viewer container with coupled modals | **REIMPLEMENT** | Modular `/spaces/:spaceId/viewer` with decoupled Viewer subsystem |
| `/spaces/login` | `src/app/spaces/login/page.tsx` | Redundant secondary login screen | **DELETE** | Single authoritative `/login` with role-based redirection |
| `/admin` | `src/app/admin/page.tsx` | Operations dashboard prototype | **REIMPLEMENT** | Clean `/admin` dashboard with real server telemetry |
| `/admin/*` (13 sub-routes) | `src/app/admin/{projects, users, spaces, captures, jobs, quality, rescans, models, system, audit, login}` | Prototypes with hardcoded table data | **REIMPLEMENT** | Enterprise operations center with typed services |

---

## 3. Existing Components Audit

| Component | Path | Description & Deficiencies | Classification |
| :--- | :--- | :--- | :--- |
| `ThreeSpatialViewer.tsx` | `src/components/viewer/ThreeSpatialViewer.tsx` | 1381-line monolithic Three.js component. Mixes scene setup, rendering, first-person kinematics, collision detection, HUD state, UI DOM, and metrics submission in one file. | **REIMPLEMENT (Modularize)**: Extract collision algorithms, kinematics, and shaders; replace monolithic component with `viewer/` package. |
| `AdminSidebar.tsx` | `src/components/admin/AdminSidebar.tsx` | 440-line legacy navigation sidebar coupled to `DashboardContext`. | **DELETE** |
| `OperationsSidebar.tsx`| `src/components/admin/OperationsSidebar.tsx` | Clean admin sidebar structure. | **REIMPLEMENT** into `features/admin/AdminSidebar.tsx` |
| `CustomerSidebar.tsx` | `src/components/spatial/CustomerSidebar.tsx` | Customer sidebar. | **REIMPLEMENT** into `features/spaces/CustomerSidebar.tsx` |
| `MobileApp.tsx` | `src/components/mobile/MobileApp.tsx` | 890-line single-component 15-screen flow. Good UX state progression, but monolithic state. | **REIMPLEMENT** into modular `features/capture/` |
| `SpatialWorkspace.tsx` | `src/components/SpatialWorkspace.tsx` | 49KB legacy spatial workspace with hardcoded mock telemetry and duplicate viewer. | **DELETE** |
| `SpatialHeroSimulator.tsx`| `src/components/SpatialHeroSimulator.tsx` | Interactive 3D hero canvas with hardcoded vertex particles. | **KEEP** (Clean as reusable demo canvas in `features/home/`) |
| `AdminDashboard.tsx` | `src/components/AdminDashboard.tsx` | Obsolete dashboard view. | **DELETE** |
| `BenchmarkCalculator.tsx`| `src/components/BenchmarkCalculator.tsx` | ROI calculator component. | **DELETE** |
| `JoinOrgModal.tsx` | `src/components/JoinOrgModal.tsx` | Legacy modal with inline fetch. | **DELETE** |
| `OrgSignupModal.tsx` | `src/components/OrgSignupModal.tsx` | 19KB legacy registration modal with inline state and raw CSS. | **DELETE** |
| `UserAuthModal.tsx` | `src/components/UserAuthModal.tsx` | Legacy auth modal. | **DELETE** |
| `SignupChoiceModal.tsx`| `src/components/SignupChoiceModal.tsx` | Obsolete choice modal. | **DELETE** |
| `SegmentedToggle.tsx` | `src/components/SegmentedToggle.tsx` | Simple toggle widget. | **REIMPLEMENT** into design system `SegmentedControl.tsx` |
| `VastuPreloader.tsx` | `src/components/VastuPreloader.tsx` | Architectural compass loading animation. | **KEEP** (Refactor into design system `VastuPreloader.tsx`) |
| `VastuConvergenceAnimation.tsx` | `src/components/VastuConvergenceAnimation.tsx` | SVG canvas animation. | **KEEP** (Refactor into design system `VastuConvergenceAnimation.tsx`) |
| `VastuOrgIdInput.tsx` | `src/components/VastuOrgIdInput.tsx` | Org code formatter input. | **DELETE** |
| `Navbar.tsx` | `src/components/Navbar.tsx` | Top bar coupled to legacy user state. | **REPLACE** with standard App Header |

---

## 4. State Management Audit

| Layer | Legacy State Architecture | Deficiencies | Target Architecture |
| :--- | :--- | :--- | :--- |
| **Server State** | Ad-hoc `useEffect` fetches, inconsistent `localStorage` reads, missing cache invalidation | No query caching, duplicate network requests, stale data, unhandled error boundaries | TanStack Query (`@tanstack/react-query`) or typed domain repository stores with cache keys |
| **Client UI State** | Fragmented `useState` passed 4 levels deep, `DashboardContext` holding mixed user/org/pending states | Global store bloated with ephemeral modal flags; UI state tightly coupled to data fetching | Lightweight Zustand or scoped React Context for UI state (drawers, camera mode, active layers, search filters) |
| **Viewer State** | Mutated internal React state (`playerCoords`, `playerSpeed`, `telemetry`) causing 60fps React re-renders | High React render churn, dropped frames | Decoupled Three.js render loop with event emitters and reactive subscription hooks |

---

## 5. Backend API & Contract Assumptions

### Verified Real Backend Endpoints (Go Chi Server on Port 8080)
- **Auth**: `POST /api/v1/auth/signup/user`, `POST /api/v1/auth/verify-otp`, `POST /api/v1/auth/request-otp`, `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `GET /api/v1/auth/me`
- **Orgs**: `POST /api/v1/orgs/signup`, `POST /api/v1/orgs/verify-otp`, `GET /api/v1/orgs/validate/{orgCode}`, `POST /api/v1/orgs/join`
- **Projects**: `GET /api/v1/projects`, `POST /api/v1/projects`, `GET /api/v1/projects/{projectId}`, `PUT /api/v1/projects/{projectId}`, `DELETE /api/v1/projects/{projectId}`
- **Captures**: `POST /api/v1/captures`, `GET /api/v1/captures/{id}`, `GET /api/v1/captures/project/{projectId}`
- **Uploads**: `POST /api/v1/uploads/init`, `POST /api/v1/uploads/{sessionId}/chunk/{chunkIndex}`, `GET /api/v1/uploads/{sessionId}/progress`, `POST /api/v1/uploads/{sessionId}/complete`
- **Jobs**: `POST /api/v1/jobs`, `GET /api/v1/jobs/{id}`, `GET /api/v1/jobs/project/{projectId}`, `POST /api/v1/jobs/{id}/logs`, `GET /api/v1/jobs/{id}/logs`
- **Models**: `POST /api/v1/models`, `GET /api/v1/models/{id}`, `GET /api/v1/models/project/{projectId}/active`, `GET /api/v1/models/project/{projectId}`
- **POIs**: `POST /api/v1/pois`, `GET /api/v1/pois/{id}`, `GET /api/v1/pois/project/{projectId}`, `PUT /api/v1/pois/{id}`, `DELETE /api/v1/pois/{id}`
- **Search**: `POST /api/v1/search/spatial` (query, category, room, min_confidence)
- **Navigation**: `POST /api/v1/navigation/nodes`, `GET /api/v1/navigation/nodes/project/{projectId}`, `POST /api/v1/navigation/edges`, `GET /api/v1/navigation/edges/project/{projectId}`, `POST /api/v1/navigation/route`
- **Viewer**: `POST /api/v1/viewer/bookmarks`, `GET /api/v1/viewer/bookmarks/project/{projectId}`, `POST /api/v1/viewer/annotations`, `GET /api/v1/viewer/annotations/project/{projectId}`

### Contract Discrepancies & Missing Contracts
1. **WebSocket Real-Time Pipeline Events**: The Go control plane does not yet register a native WebSocket route. Real-time events (`JOB_STARTED`, `PROGRESS_UPDATED`, `STAGE_CHANGED`, `QUALITY_UPDATED`) must be handled via a typed WebSocket client with a resilient HTTP polling fallback and Mock Streaming Socket.
2. **Quality & Rescan Endpoint**: Backend calculates quality within pipeline workers; frontend needs explicit typed service contracts (`services/api/quality.ts`, `services/api/rescans.ts`).
3. **Tri-Representation Models**: Model endpoints exist, but visual vs structural vs collision breakdown requires standardized DTO adapters (`services/api/models.ts`).

---

## 6. Assets, Algorithms, & Code Classification Summary

### KEEP (Objectively Reusable Assets & Algorithms)
1. `public/logo.png` — High-resolution VĀSTU brand identity emblem.
2. `src/types/representations.ts` — Tri-representation interface contracts (`VisualModelFormat`, `CollisionObstacle`, `MetricTransform`).
3. `src/types/spatial.ts` — Typed data models for POIs, search results, routes, jobs, and models.
4. Three.js AABB Raycast & Collision Math (`ThreeSpatialViewer.tsx` lines 150-250) — Bounding box human collision check and ground plane projection.
5. Mathematical Plane Normal & Horizon Line rendering algorithm.
6. `VastuConvergenceAnimation.tsx` & `VastuPreloader.tsx` — Custom visual identity animations.

### REIMPLEMENT (Essential Features to Re-architect from Scratch)
1. **Application Foundation**: Replace Next.js App Router with clean Vite + React 18 SPA + strict TypeScript.
2. **Services Architecture**: Centralized `services/api/` with Axios/Fetch client, interceptors, error mapping, and `services/websocket/` with connection lifecycle.
3. **Design System**: Centralized atomic design system (`Button`, `Input`, `Dialog`, `Drawer`, `Card`, `Table`, `Badge`, `StatCard`, etc.) in `components/ui/`.
4. **Spatial Viewer Subsystem**: Modular `viewer/` package with `core/`, `scene/`, `camera/`, `layers/`, `interaction/`, `navigation/`, `streaming/`.
5. **Operator Capture & Rescan**: Clean multi-step flow supporting Mock and Real hardware modes under `features/capture/`.
6. **Admin Operations Center**: SRE command center with live pipeline job telemetry, CUDA logs, and infrastructure topology under `features/admin/`.

### REPLACE
1. Ad-hoc CSS & Tailwind utility spaghetti $\rightarrow$ Systematic theme tokens (Architectural Studio + Spatial Computing + Premium Technical SaaS).
2. Monolithic `ThreeSpatialViewer.tsx` $\rightarrow$ Isolated, decoupled `viewer/` subsystem with discrete layers (`VisualLayer`, `StructuralLayer`, `CollisionLayer`, `POILayer`, `NavigationLayer`).
3. Mixed admin/user routes in `/dashboard` $\rightarrow$ Segregated `/admin` and `/projects` / `/spaces` route hierarchies.

### DELETE
1. `src/app/dashboard/*` (16 legacy subdirectories)
2. `src/components/AdminDashboard.tsx`, `BenchmarkCalculator.tsx`, `JoinOrgModal.tsx`, `OrgSignupModal.tsx`, `UserAuthModal.tsx`, `SignupChoiceModal.tsx`, `SpatialWorkspace.tsx`, `VastuOrgIdInput.tsx`
3. `src/components/admin/AdminSidebar.tsx`, `AdminHeader.tsx`
4. Hard-coded mock-only dead code and fake timer loops.

---

## 7. Rebuild Readiness Verdict

Phase 0 audit is complete. All existing assets, routes, components, and contracts are classified.
The codebase is fully prepared for Phase 1 recovery checkpoint preservation and subsequent clean Vite rebuild.
