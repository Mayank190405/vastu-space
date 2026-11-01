import Foundation
import CoreVideo
import simd

public final class TestReport {
    public var passed: Int = 0
    public var failed: Int = 0
    public var details: [String] = []
    
    public init() {}
    
    public func check(_ condition: Bool, _ message: String) {
        if condition {
            passed += 1
            details.append("  ✅ PASS: \(message)")
        } else {
            failed += 1
            details.append("  ❌ FAIL: \(message)")
        }
    }
}

public class VastuCaptureTestRunner {
    public static func runAllTests() async -> TestReport {
        let report = TestReport()
        print("==================================================")
        print("🚀 Running VĀSTU Capture Engine Verification Suite")
        print("==================================================")
        
        testQRRedemptionAndSessionState(report)
        testKeyframePackageWriterAndChecksums(report)
        testImageQualityAssessor(report)
        testFloorplanRayProjection(report)
        await SessionAuthorizationManagerTests.runPhase2Tests(report: report)
        await ARKitRecordingEngineTests.runPhase3Tests(report: report)
        await LocalAITests.runPhase4Tests(report: report)
        await LiveFloorplanAndGuidanceTests.runPhase5Tests(report: report)
        await FurnitureAndDepthAITests.runPhase6Tests(report: report)
        await SessionAuthorizationManagerTests.runPhase7Tests(report: report)
        
        print("\n==================================================")
        print("📊 Verification Results: \(report.passed) Passed, \(report.failed) Failed")
        print("==================================================")
        for detail in report.details {
            print(detail)
        }
        return report
    }
    
    // MARK: - 1. QR Redemption & Session State Machine
    private static func testQRRedemptionAndSessionState(_ report: TestReport) {
        print("\n[Suite 1/4] QR Redemption & Session Authorization Flow")
        
        let validPayload = "vastu://capture-session?endpoint=https%3A%2F%2Fapi.vastu.ai&challenge=chal_test_9921&session_id=sess_living_room_01"
        guard let url = URL(string: validPayload),
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
            report.check(false, "Failed to parse valid QR URL")
            return
        }
        
        let queryItems = Dictionary(uniqueKeysWithValues: components.queryItems?.compactMap { item in
            item.value.map { (item.name, $0) }
        } ?? [])
        
        report.check(components.scheme == "vastu", "QR scheme must be vastu://")
        report.check(queryItems["challenge"] == "chal_test_9921", "Extracted challenge matching payload")
        report.check(queryItems["session_id"] == "sess_living_room_01", "Extracted session_id matching payload")
        report.check(queryItems["endpoint"] == "https://api.vastu.ai", "Target endpoint is HTTPS secure")
        
        // Test state transitions
        var currentState = SessionState.unauthorized
        report.check(!currentState.isRecordingActive, "Recording forbidden when UNAUTHORIZED")
        
        currentState = .ready
        report.check(!currentState.isRecordingActive, "Recording ready but not yet started")
        
        currentState = .recording
        report.check(currentState.isRecordingActive, "Recording active when in RECORDING state")
    }
    
    // MARK: - 2. Package Schema & Integrity Writer
    private static func testKeyframePackageWriterAndChecksums(_ report: TestReport) {
        print("\n[Suite 2/4] Keyframe Package Schema & SHA-256 Integrity")
        
        let tempDir = FileManager.default.temporaryDirectory.appendingPathComponent("vastu_test_\(UUID().uuidString)")
        do {
            try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
            let writer = try KeyframePackageWriter(
                parent: tempDir,
                sessionId: "test_session_42",
                projectName: "Grand Residence",
                roomName: "Primary Suite"
            )
            
            // Create a synthetic pixel buffer
            var pixelBuffer: CVPixelBuffer?
            let attrs = [
                kCVPixelBufferCGImageCompatibilityKey: kCFBooleanTrue,
                kCVPixelBufferCGBitmapContextCompatibilityKey: kCFBooleanTrue
            ] as CFDictionary
            CVPixelBufferCreate(kCFAllocatorDefault, 64, 64, kCVPixelFormatType_32BGRA, attrs, &pixelBuffer)
            
            let dummyPose = CameraPose(
                frameId: "frame_000000.jpg",
                timestampNs: 1_000_000_000,
                transformMatrix: matrix_identity_float4x4,
                trackingState: "NORMAL"
            )
            let dummyIntrinsics = CameraIntrinsics(fx: 912, fy: 912, cx: 270, cy: 480, imageWidth: 540, imageHeight: 960)
            
            if let buf = pixelBuffer {
                try writer.append(pixelBuffer: buf, pose: dummyPose, intrinsics: dummyIntrinsics)
            }
            
            let pkgURL = try writer.finish(events: [["type": "NORMAL", "timestamp": 100.0]])
            
            // Validate generated files per Phase 3 Schema
            let manifestPath = pkgURL.appendingPathComponent("manifest.json").path
            let checksumsPath = pkgURL.appendingPathComponent("checksums.sha256").path
            let posesPath = pkgURL.appendingPathComponent("camera_poses.jsonl").path
            let calibPath = pkgURL.appendingPathComponent("calibration.json").path
            let eventsPath = pkgURL.appendingPathComponent("tracking_events.jsonl").path
            let frame1Path = pkgURL.appendingPathComponent("frames/frame_000001.jpg").path
            
            report.check(FileManager.default.fileExists(atPath: manifestPath), "manifest.json created")
            report.check(FileManager.default.fileExists(atPath: checksumsPath), "checksums.sha256 generated")
            report.check(FileManager.default.fileExists(atPath: posesPath), "camera_poses.jsonl streaming log exists")
            report.check(FileManager.default.fileExists(atPath: calibPath), "calibration.json created")
            report.check(FileManager.default.fileExists(atPath: eventsPath), "tracking_events.jsonl created")
            report.check(FileManager.default.fileExists(atPath: frame1Path), "frame_000001.jpg stored")
            
            let checksumsContent = try String(contentsOfFile: checksumsPath, encoding: .utf8)
            report.check(checksumsContent.contains("manifest.json"), "checksums.sha256 includes manifest.json")
            report.check(checksumsContent.contains("frames/frame_000001.jpg"), "checksums.sha256 includes frame_000001.jpg")
            
            try FileManager.default.removeItem(at: tempDir)
        } catch {
            report.check(false, "KeyframePackageWriter error: \(error)")
        }
    }
    
    // MARK: - 3. Image Quality Assessment
    private static func testImageQualityAssessor(_ report: TestReport) {
        print("\n[Suite 3/4] Image Quality Assessor (Blur & Exposure)")
        
        let assessor = ImageQualityAssessor.shared
        
        let width = 640
        let height = 480
        var pixelBuffer: CVPixelBuffer?
        let attrs = [
            kCVPixelBufferCGImageCompatibilityKey: kCFBooleanTrue,
            kCVPixelBufferCGBitmapContextCompatibilityKey: kCFBooleanTrue
        ] as CFDictionary
        
        let status = CVPixelBufferCreate(
            kCFAllocatorDefault,
            width,
            height,
            kCVPixelFormatType_32BGRA,
            attrs,
            &pixelBuffer
        )
        
        report.check(status == kCVReturnSuccess && pixelBuffer != nil, "Created test CVPixelBuffer")
        
        if let buf = pixelBuffer {
            CVPixelBufferLockBaseAddress(buf, [])
            let base = CVPixelBufferGetBaseAddress(buf)
            memset(base, 128, height * CVPixelBufferGetBytesPerRow(buf)) // Uniform grey
            CVPixelBufferUnlockBaseAddress(buf, [])
            
            let start = Date()
            let metric = assessor.evaluate(pixelBuffer: buf)
            let elapsedMs = Date().timeIntervalSince(start) * 1000.0
            
            report.check(elapsedMs < 30.0, "Quality assessment throughput < 30ms (actual: \(String(format: "%.2f", elapsedMs))ms)")
            report.check(metric.isBlurry, "Uniform image detected as blurry (zero Laplacian variance)")
            report.check(!metric.isOverexposed && !metric.isUnderexposed, "Mid-grey image within exposure envelope")
        }
    }
    
    // MARK: - 4. Live Floorplan Engine & Ray Projection
    private static func testFloorplanRayProjection(_ report: TestReport) {
        print("\n[Suite 4/4] Live Floorplan 2D Ray Projection & Grid Accumulator")
        
        let floorplan = LiveFloorplanEngine()
        
        var matrix = matrix_identity_float4x4
        matrix.columns.3 = simd_make_float4(0.0, 1.5, 0.0, 1.0) // Position Y = 1.5m
        
        let pose = CameraPose(
            frameId: "frame_000000.jpg",
            timestampNs: 1_000_000_000,
            transformMatrix: matrix,
            trackingState: "NORMAL"
        )
        
        let ray = BoundaryRayCandidate(
            rayCamera: simd_normalize(simd_make_float3(0.0, -0.6, 1.0)),
            confidence: 0.95
        )
        
        floorplan.processFrame(pose: pose, rays: [ray], headingDeg: 0.0)
        
        report.check(floorplan.floorplanMap.cameraTrail.count == 1, "Camera trail recorded pose")
        report.check(floorplan.floorplanMap.boundaryPoints.count >= 1, "Boundary point projected to ground plane")
        report.check(floorplan.floorplanMap.coveragePercentage > 0.0, "Coverage percentage updated positive")
    }
}
