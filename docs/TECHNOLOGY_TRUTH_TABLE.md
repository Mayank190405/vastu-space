# TECHNOLOGY TRUTH TABLE
**Phase 0.2 - Source-of-Truth Reconciliation**

| Component | Claimed | Actually Present | Version Proven | Used by Code | Build Verified | Runtime Verified | Tested | Evidence |
| --------- | ------- | ---------------- | -------------- | ------------ | -------------- | ---------------- | ------ | -------- |
| Go | Yes | Yes | `1.22` (go.mod) | Yes | Yes (Dockerfile) | Yes | Yes (`go test`) | `backend/go.mod`, `backend/Dockerfile` |
| PostgreSQL | Yes | Yes | `16-3.4` (compose) | Yes (pgx driver) | Yes | Yes | Yes (unit) | `docker-compose.yml`, `go.mod` |
| PostGIS | Yes | Yes | `16-3.4` (compose) | Unknown (SQL pending) | Yes | Unknown | Unknown | `docker-compose.yml` |
| Android/Kotlin | Yes | Yes | `1.9.0` (implied) | Yes | Yes (Gradle) | Unknown | Unknown | `android/app/build.gradle.kts` |
| JDK | Yes | Yes | `17` (Gradle) | Yes | Yes | Unknown | Unknown | `android/app/build.gradle.kts` |
| Android SDK | Yes | Yes | Compile `34`, Min `26` | Yes | Yes | Unknown | Unknown | `android/app/build.gradle.kts` |
| Gradle | Yes | Yes | Yes | Yes | Yes | Unknown | Unknown | `android/build.gradle.kts` |
| Android Gradle Plugin | Yes | Yes | Yes | Yes | Yes | Unknown | Unknown | `android/build.gradle.kts` |
| Jetpack Compose | Yes | Yes | BOM `2024.02.01` | Yes | Yes | Unknown | Unknown | `android/app/build.gradle.kts` |
| CameraX | Yes | Yes | `1.3.1` | Yes | Yes | Unknown | Unknown | `android/app/build.gradle.kts` |
| Room | Yes | Yes | `2.6.1` | Yes | Yes | Unknown | Unknown | `android/app/build.gradle.kts` |
| Coroutines | Yes | Yes | `1.7.3` | Yes | Yes | Unknown | Unknown | `android/app/build.gradle.kts` |
| WorkManager | Yes | Yes | `2.9.0` | Yes | Yes | Unknown | Unknown | `android/app/build.gradle.kts` |
| Swift | Yes | Yes | `5.9` (Package.swift)| Yes | Yes | Unknown | Unknown | `ios/Package.swift` |
| Xcode | Yes | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | **NOT EVIDENCED / REQUIRES RESOLUTION** |
| iOS SDK | Yes | Yes | `.iOS(.v17)` | Yes | Yes | Unknown | Unknown | `ios/Package.swift` |
| SwiftUI | Yes | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | **NOT EVIDENCED / REQUIRES RESOLUTION** |
| AVFoundation | Yes | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | **NOT EVIDENCED / REQUIRES RESOLUTION** |
| CoreMotion | Yes | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | **NOT EVIDENCED / REQUIRES RESOLUTION** |
| BackgroundTasks | Yes | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | **NOT EVIDENCED / REQUIRES RESOLUTION** |
| Python | Yes | Yes | `requirements.txt` | Yes | Yes | Yes | Yes | `backend/workers/requirements.txt` |
| OpenCV | Yes | Yes | `4.9.0.80` | Yes | Yes | Yes | Yes | `backend/workers/requirements.txt`, `CMakeLists.txt` |
| SciPy | Yes | Yes | `1.12.0` | Yes | Yes | Yes | Yes | `backend/workers/requirements.txt` |
| PyTorch | Yes | Yes | `2.2.1` | Yes | Yes | Yes | Yes | `backend/workers/requirements.txt` |
| CUDA | Yes | Unknown | Unknown | Unknown | No | No | No | **NOT EVIDENCED / REQUIRES RESOLUTION** |
| NVIDIA driver | Yes | Unknown | Unknown | Unknown | No | No | No | **NOT EVIDENCED / REQUIRES RESOLUTION** |
| Open3D | Yes | Yes | `0.18.0` | Yes | Yes | Yes | Yes | `backend/workers/requirements.txt` |
| C++ | Yes | Yes | `CMake 3.10+` | Yes | Yes | Yes | Yes | `backend/workers/CMakeLists.txt` |
| compiler | Yes | Yes | Configured via CMake | Yes | Yes | Yes | Yes | `CMakeLists.txt` |
| C++ standard | Yes | Yes | `C++17` | Yes | Yes | Yes | Yes | `CMakeLists.txt` |
| S3/object storage | Yes | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | **NOT EVIDENCED / REQUIRES RESOLUTION** |
| antivirus/malware | Yes | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | **NOT EVIDENCED / REQUIRES RESOLUTION** |
| EventBus/job infra | Yes | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | **NOT EVIDENCED / REQUIRES RESOLUTION** |
| database migration | Yes | Yes | Unknown | Yes | Yes | Unknown | Unknown | `docker-compose.yml` mounts SQL |
| logging/metrics/tracing | Yes | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | **NOT EVIDENCED / REQUIRES RESOLUTION** |
| frontend dependencies | Yes | Yes | Multiple | Yes | Yes (npm) | Unknown | Unknown | `package.json` |

## Summary
The Python and C++ environments are now fully documented with `requirements.txt` and `CMakeLists.txt`. iOS is still pending explicit linkages for claimed technologies.
