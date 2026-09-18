# Developer Contributing & Codebase Guidelines

Welcome to the **VĀSTU / Namma Space** engineering team! This guide establishes our engineering principles, repository workflow, and standards for maintainable collaboration.

---

## 🏗️ 1. Architecture Boundaries & Layer Ownership

The platform is designed with decoupled, contract-driven layers. **Never break these boundaries:**

| Layer | Directory | Tech Stack | Responsibility & Rules |
| :--- | :--- | :--- | :--- |
| **Frontend Web** | `src/` | React 18, TypeScript, Three.js, Vite | Zero-install web viewer, guided capture UI, project portal. Never import backend/worker code directly. |
| **Control Plane** | `api/` | FastAPI, Python 3.10+ | Orchestrates captures, presigned storage URLs, job status, navigation routes. |
| **High-Throughput Backend** | `backend/` | Go, PostgreSQL, PostGIS | Multi-tenant orgs, spatial indices, user authentication, RBAC. |
| **Core Algorithms** | `core/`, `geometry/` | Pure Python, NumPy, SciPy | 13 Canonical Contracts (Pydantic v2), RANSAC plane fitting, spatial hashing, A* routing. Independent of web frameworks. |
| **Worker Pipeline** | `workers/` | Python, PyCOLMAP, Open3D | 9-stage asynchronous photogrammetry pipeline conforming to `BaseWorker` lifecycle. |
| **Mobile Capture** | `android/`, `ios/` | Kotlin (ARCore), Swift (ARKit) | Telemetry capture (RGB + IMU 6-DoF + LiDAR), resumable upload to object storage. |

---

## 🌿 2. Git Branching & Workflow Strategy

To keep `main` stable, production-ready, and deployable at all times:

### Branch Naming Conventions
- `feat/feature-name` &mdash; New features (e.g., `feat/lidar-mesh-stream`)
- `fix/bug-description` &mdash; Bug fixes (e.g., `fix/depth-reprojection-drift`)
- `refactor/scope` &mdash; Code improvements without behavior changes
- `chore/task-name` &mdash; Dependency updates, tooling, configuration

### Daily Development Loop
```bash
# 1. Fetch latest main
git checkout main
git pull origin main

# 2. Create your isolated feature branch
git checkout -b feat/your-feature-name

# 3. Work and run tests locally before committing
npm run build                     # Frontend check
PYTHONPATH=. pytest tests/ -q     # Engine test suite

# 4. Commit using Conventional Commits
git commit -m "feat(viewer): add dynamic waypoint trail highlighting"

# 5. Push and open Pull Request
git push -u origin feat/your-feature-name
```

---

## 🔒 3. Secrets & Configuration Rules

1. **Never commit `.env` or `.env.local` files.** They are automatically ignored by `.gitignore`.
2. All local configuration belongs in `.env`.
3. If you introduce a new environment variable:
   - Add it to `.env.example` with a safe placeholder description.
   - Mention the new variable in your PR description.

---

## 🧪 4. Pre-PR Quality Checklist

Before submitting any Pull Request, ensure:
1. **Frontend**: `npm run build` compiles with zero TypeScript errors.
2. **Backend / Algorithms**: `PYTHONPATH=. pytest tests/` passes all tests.
3. **No Dead Code**: Remove temporary logs, debugger statements, and commented-out experimental blocks.
4. **Clean Diff**: Run `git diff` to verify only intended changes are included.
