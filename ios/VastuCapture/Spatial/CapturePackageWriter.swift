import Foundation
import CryptoKit
import simd
import CoreGraphics
import CoreVideo

public final class CapturePackageWriter {
    public let packageDirectory: URL
    public let sessionId: String
    public let projectName: String
    public let roomName: String
    
    public let frameRecorder: CameraFrameRecorder
    public let poseLogger: CameraPoseLogger
    public let calibrationManager: CameraCalibrationManager
    public let trackingEventsURL: URL
    public let boundaryObservationsURL: URL
    public var packageDirectoryURL: URL { return packageDirectory }
    
    private var trackingEvents: [[String: Any]] = []
    private var boundaryFileHandle: FileHandle?
    private var isFinalized: Bool = false
    
    public init(
        parentDirectory: URL,
        sessionId: String,
        projectName: String,
        roomName: String
    ) throws {
        self.sessionId = sessionId
        self.projectName = projectName
        self.roomName = roomName
        
        self.packageDirectory = parentDirectory.appendingPathComponent("capture_\(sessionId)", isDirectory: true)
        let fm = FileManager.default
        if fm.fileExists(atPath: packageDirectory.path) {
            try fm.removeItem(at: packageDirectory)
        }
        try fm.createDirectory(at: packageDirectory, withIntermediateDirectories: true)
        
        // 1. Frames Directory
        let framesDir = packageDirectory.appendingPathComponent("frames", isDirectory: true)
        self.frameRecorder = try CameraFrameRecorder(framesDirectory: framesDir)
        
        // 2. Camera Poses JSONL
        let posesURL = packageDirectory.appendingPathComponent("camera_poses.jsonl")
        self.poseLogger = try CameraPoseLogger(fileURL: posesURL)
        
        // 3. Calibration Manager
        self.calibrationManager = CameraCalibrationManager()
        
        // 4. Tracking Events URL
        self.trackingEventsURL = packageDirectory.appendingPathComponent("tracking_events.jsonl")
        fm.createFile(atPath: trackingEventsURL.path, contents: nil)
        
        // 5. Boundary Observations JSONL
        self.boundaryObservationsURL = packageDirectory.appendingPathComponent("boundary_observations.jsonl")
        fm.createFile(atPath: boundaryObservationsURL.path, contents: nil)
        self.boundaryFileHandle = try? FileHandle(forWritingTo: boundaryObservationsURL)
    }
    
    public convenience init(
        parent: URL,
        sessionId: String,
        projectName: String,
        roomName: String
    ) throws {
        try self.init(parentDirectory: parent, sessionId: sessionId, projectName: projectName, roomName: roomName)
    }
    
    public func recordBoundaryObservations(points: [Point2D], timestampSec: Double) {
        guard let handle = boundaryFileHandle, !points.isEmpty else { return }
        let ptsDict = points.map { ["x": round($0.x * 1000) / 1000.0, "z": round($0.z * 1000) / 1000.0] }
        let record: [String: Any] = [
            "timestamp": timestampSec,
            "count": points.count,
            "points": ptsDict
        ]
        if let data = try? JSONSerialization.data(withJSONObject: record) {
            handle.write(data)
            handle.write(Data([0x0A]))
        }
    }
    
    public func recordTrackingEvent(type: String, timestampSec: Double, details: [String: Any] = [:]) {
        var event = details
        event["event_type"] = type
        event["timestamp_sec"] = timestampSec
        event["timestamp_iso"] = ISO8601DateFormatter().string(from: Date())
        trackingEvents.append(event)
    }
    
    // MARK: - Convenience Methods for Package Ingestion
    public func append(pixelBuffer: CVPixelBuffer, pose: CameraPose, intrinsics: CameraIntrinsics) throws {
        _ = calibrationManager.updateCalibration(
            intrinsics: simd_float3x3(
                simd_make_float3(Float(intrinsics.fx), 0, 0),
                simd_make_float3(0, Float(intrinsics.fy), 0),
                simd_make_float3(Float(intrinsics.cx), Float(intrinsics.cy), 1)
            ),
            resolution: CGSize(width: intrinsics.imageWidth, height: intrinsics.imageHeight)
        )
        
        let frameIdx = frameRecorder.recordedFrameCount + 1
        frameRecorder.recordFrame(pixelBuffer: pixelBuffer, frameIndex: frameIdx)
        
        var mat = matrix_identity_float4x4
        if pose.transform.count == 4 {
            mat = simd_float4x4(rows: [
                simd_make_float4(Float(pose.transform[0][0]), Float(pose.transform[0][1]), Float(pose.transform[0][2]), Float(pose.transform[0][3])),
                simd_make_float4(Float(pose.transform[1][0]), Float(pose.transform[1][1]), Float(pose.transform[1][2]), Float(pose.transform[1][3])),
                simd_make_float4(Float(pose.transform[2][0]), Float(pose.transform[2][1]), Float(pose.transform[2][2]), Float(pose.transform[2][3])),
                simd_make_float4(Float(pose.transform[3][0]), Float(pose.transform[3][1]), Float(pose.transform[3][2]), Float(pose.transform[3][3]))
            ])
        }
        
        let frameId = String(format: "frame_%06d.jpg", frameIdx)
        poseLogger.logPose(
            frameId: frameId,
            timestampSec: Double(pose.timestampNs) / 1_000_000_000.0,
            transform: mat,
            trackingState: pose.trackingState
        )
    }
    
    public func finish(events: [[String: Any]]) throws -> URL {
        for ev in events {
            recordTrackingEvent(type: ev["type"] as? String ?? "EVENT", timestampSec: ev["timestamp"] as? Double ?? 0.0, details: ev)
        }
        return try finalizePackage(totalFrames: frameRecorder.recordedFrameCount, durationSeconds: 1.0)
    }
    
    /// Finalizes capture package, flushes frames and poses, writes manifest and calibration, and generates SHA-256 manifest.
    public func finalizePackage(totalFrames: Int, durationSeconds: Double) throws -> URL {
        guard !isFinalized else { return packageDirectory }
        isFinalized = true
        
        // 1. Flush frame encoder, boundary logger, and close pose logger
        frameRecorder.flush()
        try? boundaryFileHandle?.close()
        boundaryFileHandle = nil
        try poseLogger.close()
        
        // 2. Write calibration.json
        let calibData = try calibrationManager.exportCalibrationJSON()
        try calibData.write(to: packageDirectory.appendingPathComponent("calibration.json"))
        
        // 3. Write tracking_events.jsonl
        var eventsData = Data()
        for ev in trackingEvents {
            if let d = try? JSONSerialization.data(withJSONObject: ev, options: [.sortedKeys]) {
                eventsData.append(d)
                eventsData.append(0x0A)
            }
        }
        try eventsData.write(to: trackingEventsURL)
        
        // 4. Write manifest.json
        var filesList = [
            "calibration.json",
            "camera_poses.jsonl",
            "tracking_events.jsonl",
            "frames"
        ]
        if FileManager.default.fileExists(atPath: boundaryObservationsURL.path) {
            filesList.append("boundary_observations.jsonl")
        }
        let sceneObsURL = packageDirectory.appendingPathComponent("scene_observations.jsonl")
        if FileManager.default.fileExists(atPath: sceneObsURL.path) {
            filesList.append("scene_observations.jsonl")
        }
        
        let manifest: [String: Any] = [
            "schema_version": "3.0.0",
            "session_id": sessionId,
            "project_name": projectName,
            "room_name": roomName,
            "captured_at": ISO8601DateFormatter().string(from: Date()),
            "frame_count": totalFrames,
            "duration_seconds": durationSeconds,
            "coordinate_convention": "+Y is World-Up, Right-Handed, Meter metric units",
            "zero_lidar": true,
            "tracking_system": "Apple ARKit 6-DoF Visual-Inertial Odometry",
            "files": filesList
        ]
        let manifestData = try JSONSerialization.data(withJSONObject: manifest, options: [.prettyPrinted, .sortedKeys])
        try manifestData.write(to: packageDirectory.appendingPathComponent("manifest.json"))
        
        // 5. Generate checksums.sha256 covering all files in package
        try generateChecksumsFile()
        
        return packageDirectory
    }
    
    private func generateChecksumsFile() throws {
        let fm = FileManager.default
        guard let enumerator = fm.enumerator(at: packageDirectory, includingPropertiesForKeys: [.isRegularFileKey]) else { return }
        
        var lines: [String] = []
        for case let fileURL as URL in enumerator {
            guard fileURL.lastPathComponent != "checksums.sha256" else { continue }
            if let isRegular = (try? fileURL.resourceValues(forKeys: [.isRegularFileKey]))?.isRegularFile, isRegular {
                let data = try Data(contentsOf: fileURL)
                let digest = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
                let relativePath = fileURL.path.replacingOccurrences(of: packageDirectory.path + "/", with: "")
                lines.append("\(digest)  \(relativePath)")
            }
        }
        
        let checksumsText = lines.sorted().joined(separator: "\n") + "\n"
        let checksumsURL = packageDirectory.appendingPathComponent("checksums.sha256")
        try checksumsText.data(using: .utf8)?.write(to: checksumsURL)
    }
}

// Backward compatibility alias for existing code
public typealias KeyframePackageWriter = CapturePackageWriter
