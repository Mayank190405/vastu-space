import Foundation
import simd
import CoreVideo

public class ARKitRecordingEngineTests {
    public static func runPhase3Tests(report: TestReport) async {
        print("\n==================================================")
        print("🎥 Phase 3: ARKit Room Recording Engine Tests")
        print("==================================================")
        
        testKeyframeSelectorThresholds(report)
        testKeyframeSelectorTrackingDegradation(report)
        testCameraCalibrationManager(report)
        testCameraPoseLogger(report)
        testCapturePackageWriterHierarchy(report)
        testCaptureSessionManagerAuthorizationLock(report)
    }
    
    // 1. Keyframe Selector Spatial & Angular Thresholds
    private static func testKeyframeSelectorThresholds(_ report: TestReport) {
        print("\n[Phase 3 - Test 1/6] Smart Keyframe Spatial & Angular Selection")
        let selector = KeyframeSelector()
        
        // Initial frame must be selected as baseline
        let initTransform = matrix_identity_float4x4
        let dec1 = selector.evaluate(transform: initTransform, timestamp: 100.0, trackingState: "NORMAL")
        report.check(dec1.shouldRecord == true, "Initial frame selected as anchor")
        
        // Minor movement (2 cm, 1 deg) within 0.1s should be rejected
        var minorTransform = matrix_identity_float4x4
        minorTransform.columns.3 = simd_make_float4(0.02, 0.0, 0.0, 1.0)
        let dec2 = selector.evaluate(transform: minorTransform, timestamp: 100.1, trackingState: "NORMAL")
        report.check(dec2.shouldRecord == false, "Minor 2cm movement rejected")
        
        // Translation movement (15 cm > 12 cm threshold) after 0.1s should be selected
        var transTransform = matrix_identity_float4x4
        transTransform.columns.3 = simd_make_float4(0.15, 0.0, 0.0, 1.0)
        let dec3 = selector.evaluate(transform: transTransform, timestamp: 100.2, trackingState: "NORMAL")
        report.check(dec3.shouldRecord == true, "15cm translation accepted as new keyframe")
        
        // Pure rotation movement (10 degrees around Y axis) should be selected
        let angleRad = Float(10.0 * .pi / 180.0)
        var rotTransform = transTransform
        rotTransform.columns.0 = simd_make_float4(cos(angleRad), 0, -sin(angleRad), 0)
        rotTransform.columns.2 = simd_make_float4(sin(angleRad), 0, cos(angleRad), 0)
        let dec4 = selector.evaluate(transform: rotTransform, timestamp: 100.35, trackingState: "NORMAL")
        report.check(dec4.shouldRecord == true, "10° angular rotation diversity accepted")
    }
    
    // 2. Keyframe Selector Tracking Degraded Rejection
    private static func testKeyframeSelectorTrackingDegradation(_ report: TestReport) {
        print("\n[Phase 3 - Test 2/6] Degraded Tracking Quality Frame Rejection")
        let selector = KeyframeSelector()
        
        var transform = matrix_identity_float4x4
        transform.columns.3 = simd_make_float4(0.5, 0.0, 0.0, 1.0)
        
        let dec1 = selector.evaluate(transform: transform, timestamp: 100.0, trackingState: "EXCESSIVE_MOTION")
        report.check(dec1.shouldRecord == false, "Frame strictly rejected during EXCESSIVE_MOTION")
        
        let dec2 = selector.evaluate(transform: transform, timestamp: 100.1, trackingState: "RELOCALIZING")
        report.check(dec2.shouldRecord == false, "Frame strictly rejected during RELOCALIZING")
        
        let dec3 = selector.evaluate(transform: transform, timestamp: 100.2, trackingState: "INSUFFICIENT_FEATURES")
        report.check(dec3.shouldRecord == false, "Frame strictly rejected during INSUFFICIENT_FEATURES")
    }
    
    // 3. Camera Calibration Intrinsics Extraction
    private static func testCameraCalibrationManager(_ report: TestReport) {
        print("\n[Phase 3 - Test 3/6] Camera Calibration Manager")
        let manager = CameraCalibrationManager()
        
        let intrinsics = simd_float3x3(
            simd_make_float3(1442.5, 0, 0),
            simd_make_float3(0, 1443.1, 0),
            simd_make_float3(540.2, 960.8, 1)
        )
        let resolution = CGSize(width: 1080, height: 1920)
        
        let calib = manager.updateCalibration(intrinsics: intrinsics, resolution: resolution)
        report.check(calib.imageWidth == 1080 && calib.imageHeight == 1920, "Image resolution preserved")
        report.check(abs(calib.fx - 1442.5) < 0.01, "Focal length fx parsed accurately")
        report.check(abs(calib.fy - 1443.1) < 0.01, "Focal length fy parsed accurately")
        report.check(abs(calib.cx - 540.2) < 0.01, "Principal point cx parsed accurately")
        report.check(abs(calib.cy - 960.8) < 0.01, "Principal point cy parsed accurately")
        
        do {
            let json = try manager.exportCalibrationJSON()
            let str = String(data: json, encoding: .utf8) ?? ""
            report.check(str.contains("\"distortionModel\" : \"PINHOLE\""), "Distortion model is PINHOLE")
            report.check(str.contains("World-Up"), "Documented coordinate convention included")
        } catch {
            report.check(false, "Failed to export calibration JSON: \(error)")
        }
    }
    
    // 4. Camera Pose Logger Streaming
    private static func testCameraPoseLogger(_ report: TestReport) {
        print("\n[Phase 3 - Test 4/6] Camera Pose Logger Streaming")
        let tempDir = FileManager.default.temporaryDirectory.appendingPathComponent("vastu_poselog_\(UUID().uuidString)")
        try? FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        let logURL = tempDir.appendingPathComponent("camera_poses.jsonl")
        
        do {
            let logger = try CameraPoseLogger(fileURL: logURL)
            var transform = matrix_identity_float4x4
            transform.columns.3 = simd_make_float4(1.25, 1.60, -2.40, 1.0)
            
            logger.logPose(frameId: "frame_000001.jpg", timestampSec: 10.5, transform: transform, trackingState: "NORMAL")
            try logger.close()
            
            let content = try String(contentsOf: logURL, encoding: .utf8)
            report.check(content.contains("frame_000001.jpg"), "Pose record contains matching frameId")
            report.check(content.contains("1.25"), "Position X coordinate logged")
            report.check(content.contains("1.6"), "Position Y coordinate logged")
            report.check(content.contains("-2.4"), "Position Z coordinate logged")
            
            try? FileManager.default.removeItem(at: tempDir)
        } catch {
            report.check(false, "Pose logger error: \(error)")
        }
    }
    
    // 5. Capture Package Writer Hierarchy & SHA-256 Manifest
    private static func testCapturePackageWriterHierarchy(_ report: TestReport) {
        print("\n[Phase 3 - Test 5/6] Capture Package Writer Hierarchy & SHA-256 Manifest")
        let tempDir = FileManager.default.temporaryDirectory.appendingPathComponent("vastu_pkg_\(UUID().uuidString)")
        try? FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        
        do {
            let writer = try CapturePackageWriter(
                parentDirectory: tempDir,
                sessionId: "sess_verify_007",
                projectName: "Azure Villa",
                roomName: "Great Room"
            )
            
            // Add a synthetic frame
            var pixelBuffer: CVPixelBuffer?
            let attrs = [kCVPixelBufferCGImageCompatibilityKey: kCFBooleanTrue, kCVPixelBufferCGBitmapContextCompatibilityKey: kCFBooleanTrue] as CFDictionary
            CVPixelBufferCreate(kCFAllocatorDefault, 64, 64, kCVPixelFormatType_32BGRA, attrs, &pixelBuffer)
            
            if let buf = pixelBuffer {
                writer.frameRecorder.recordFrame(pixelBuffer: buf, frameIndex: 1)
            }
            
            writer.poseLogger.logPose(
                frameId: "frame_000001.jpg",
                timestampSec: 100.0,
                transform: matrix_identity_float4x4,
                trackingState: "NORMAL"
            )
            
            writer.recordTrackingEvent(type: "SESSION_INITIALIZED", timestampSec: 99.9)
            
            let pkgDir = try writer.finalizePackage(totalFrames: 1, durationSeconds: 2.5)
            
            // Validate required files per Phase 3 specifications:
            let manifestPath = pkgDir.appendingPathComponent("manifest.json").path
            let calibPath = pkgDir.appendingPathComponent("calibration.json").path
            let posesPath = pkgDir.appendingPathComponent("camera_poses.jsonl").path
            let eventsPath = pkgDir.appendingPathComponent("tracking_events.jsonl").path
            let checksumsPath = pkgDir.appendingPathComponent("checksums.sha256").path
            let frame1Path = pkgDir.appendingPathComponent("frames/frame_000001.jpg").path
            
            report.check(FileManager.default.fileExists(atPath: manifestPath), "manifest.json exists")
            report.check(FileManager.default.fileExists(atPath: calibPath), "calibration.json exists")
            report.check(FileManager.default.fileExists(atPath: posesPath), "camera_poses.jsonl exists")
            report.check(FileManager.default.fileExists(atPath: eventsPath), "tracking_events.jsonl exists")
            report.check(FileManager.default.fileExists(atPath: checksumsPath), "checksums.sha256 exists")
            report.check(FileManager.default.fileExists(atPath: frame1Path), "frames/frame_000001.jpg exists")
            
            let manifestData = try Data(contentsOf: URL(fileURLWithPath: manifestPath))
            let manifestJSON = try JSONSerialization.jsonObject(with: manifestData) as? [String: Any]
            report.check(manifestJSON?["schema_version"] as? String == "3.0.0", "Schema version is 3.0.0")
            report.check(manifestJSON?["zero_lidar"] as? Bool == true, "zero_lidar flag set to true")
            
            let checksumsText = try String(contentsOfFile: checksumsPath, encoding: .utf8)
            report.check(checksumsText.contains("manifest.json"), "checksums.sha256 verifies manifest.json")
            report.check(checksumsText.contains("calibration.json"), "checksums.sha256 verifies calibration.json")
            report.check(checksumsText.contains("camera_poses.jsonl"), "checksums.sha256 verifies camera_poses.jsonl")
            report.check(checksumsText.contains("frames/frame_000001.jpg"), "checksums.sha256 verifies frame_000001.jpg")
            
            try? FileManager.default.removeItem(at: tempDir)
        } catch {
            report.check(false, "CapturePackageWriter error: \(error)")
        }
    }
    
    // 6. Capture Session Manager Authorization Lock
    private static func testCaptureSessionManagerAuthorizationLock(_ report: TestReport) {
        print("\n[Phase 3 - Test 6/6] Capture Session Manager Authorization Lock")
        let manager = CaptureSessionManager()
        
        // Reset authorization state to unauthorized
        SessionAuthorizationManager.shared.resetToScanner()
        
        let dummySession = CaptureSession(
            id: "sess_unauth",
            projectId: "proj_1",
            projectName: "Villa",
            roomId: "room_1",
            roomName: "Kitchen",
            operatorName: nil,
            createdAt: Date(),
            expiresAt: Date().addingTimeInterval(3600),
            state: .unauthorized,
            grantToken: "token",
            uploadURL: nil,
            maxDurationSeconds: 600
        )
        
        do {
            try manager.startRecording(session: dummySession)
            report.check(false, "Recording started without valid authorization!")
        } catch {
            report.check(true, "CaptureSessionManager strictly refused to start recording without active grant")
        }
        report.check(manager.isRecording == false, "Recording flag remains false")
    }
}

