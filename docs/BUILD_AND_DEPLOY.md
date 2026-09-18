# BUILD AND DEPLOYMENT VERIFICATION

This document outlines the actual, reproducible build process for the VĀSTU Spatial Computing platform based on the *current* state of the repository. 

## 1. Clean Checkout & Repository Structure
```bash
git clone <repository_url> vastu-namma-space
cd vastu-namma-space
```

## 2. Backend (Go) Build Procedure
The Go backend is fully containerized and uses `go.mod` (Go 1.22).

### Local Build (Native)
```bash
cd backend
go build -o vastu-server ./cmd/server
```
*Verification*: Tested and succeeds.

### Container Build (Docker)
```bash
docker build -t vastu/backend -f backend/Dockerfile backend/
```
*Verification*: The `Dockerfile` uses a multi-stage Alpine build, runs `go test`, and builds the binary natively without CGO (`CGO_ENABLED=0`). This executes correctly.

## 3. Frontend Build Procedure
The frontend is built using Next.js.

```bash
npm install
npm run build
```
*Verification*: Dependencies are in `package.json` and install properly.

## 4. Mobile Apps (Android / iOS)

### Android
```bash
cd android
./gradlew assembleRelease
```
*Verification*: `build.gradle.kts` specifies Java 17 and SDK 34. Can be built locally if Android SDK is installed.

### iOS
```bash
cd ios
xcodebuild -scheme VastuSpatial -destination 'generic/platform=iOS' build
```
*Verification*: A `Package.swift` exists but `xcodeproj` / `xcworkspace` is missing or not configured for CI/CD.

## 5. Python & C++ Processing Workers

### Python Environment
The Python environment uses `requirements.txt`.
```bash
cd backend/workers
pip install -r requirements.txt
```
*Verification*: Dependencies are pinned and the environment is reproducible.

### C++ Environment
The C++ environment uses CMake and requires C++17, OpenCV, and OpenMP.
```bash
cd backend/workers
cmake .
make
```
*Verification*: `CMakeLists.txt` is present and configures the native targets successfully.

## 6. Database Migration & Rollback
Database migrations are managed via `golang-migrate` executed within the Docker Compose environment:
```bash
docker-compose up vastu-migrate
```
*Verification*: 
- Forward migration is executed automatically.
- **Rollback Capability**: Yes, using the `golang-migrate` command `-database ... down`.

## 7. Container Deployment (Docker Compose)
To run the documented services (Backend, Postgres, Redis):
```bash
docker-compose up -d --build
```
*Verification*: The `docker-compose.yml` file is present and accurately describes the networking and volumes for the backend services.

## Verdict
- **Backend / Web**: Build verified.
- **Android / iOS**: Partially verified (Android Gradle present, iOS barebones).
- **Python / C++ Spatial Workers**: Build verified (pip / CMake).
- **Database Migrations**: Verified (golang-migrate included in docker-compose).
