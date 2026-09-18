## 📌 Pull Request Overview

### Summary of Changes
<!-- Provide a clear, concise bullet-point summary of what this PR does and why -->
- 

### Layer / Subsystem Affected
- [ ] Frontend (`src/`, React, Three.js, Viewer)
- [ ] API & Control Plane (`api/`, FastAPI)
- [ ] Go Backend & Database (`backend/`, `database/migrations/`)
- [ ] Photogrammetry & Algorithms (`core/`, `geometry/`, `workers/`)
- [ ] Mobile Client (`android/` or `ios/`)
- [ ] Infrastructure & Tooling (`docker/`, CI/CD, scripts)

---

## 🧪 Verification & Testing

- [ ] `npm run build` passes locally with zero TypeScript errors
- [ ] `PYTHONPATH=. pytest tests/` passes all tests
- [ ] Tested locally in browser or emulator (attached screenshot/recording if UI change)

---

## 🔒 Security & Code Standards Checklist

- [ ] **No committed secrets**: No `.env`, private tokens, or passwords are committed
- [ ] If new environment variables were introduced, `.env.example` has been updated
- [ ] Preserved clean architectural boundaries (no cross-layer coupling)
- [ ] Clean conventional commit history
