import Foundation
import simd

public struct LoggedCameraPose: Codable {
    public let frameId: String
    public let timestampNs: Int64
    public let timestampSec: Double
    public let position: [Double]           // [X, Y, Z] in meters
    public let rotationQuaternion: [Double] // [qx, qy, qz, qw]
    public let transformMatrix: [[Double]]  // 4x4 row-major representation
    public let trackingState: String
    
    public init(
        frameId: String,
        timestampSec: Double,
        transform: simd_float4x4,
        trackingState: String
    ) {
        self.frameId = frameId
        self.timestampSec = timestampSec
        self.timestampNs = Int64(timestampSec * 1_000_000_000.0)
        self.trackingState = trackingState
        
        self.position = [
            Double(transform.columns.3.x),
            Double(transform.columns.3.y),
            Double(transform.columns.3.z)
        ]
        
        let q = simd_quatf(transform)
        self.rotationQuaternion = [
            Double(q.vector.x),
            Double(q.vector.y),
            Double(q.vector.z),
            Double(q.vector.w)
        ]
        
        self.transformMatrix = [
            [Double(transform.columns.0.x), Double(transform.columns.1.x), Double(transform.columns.2.x), Double(transform.columns.3.x)],
            [Double(transform.columns.0.y), Double(transform.columns.1.y), Double(transform.columns.2.y), Double(transform.columns.3.y)],
            [Double(transform.columns.0.z), Double(transform.columns.1.z), Double(transform.columns.2.z), Double(transform.columns.3.z)],
            [Double(transform.columns.0.w), Double(transform.columns.1.w), Double(transform.columns.2.w), Double(transform.columns.3.w)]
        ]
    }
}

public final class CameraPoseLogger {
    private let logFileURL: URL
    private let fileHandle: FileHandle
    private let queue = DispatchQueue(label: "com.vastu.capture.poselogger", qos: .utility)
    private let jsonEncoder = JSONEncoder()
    
    public private(set) var loggedPoseCount: Int = 0
    public private(set) var firstTimestamp: Double?
    public private(set) var lastTimestamp: Double?
    
    public init(fileURL: URL) throws {
        self.logFileURL = fileURL
        let fm = FileManager.default
        if fm.fileExists(atPath: fileURL.path) {
            try fm.removeItem(at: fileURL)
        }
        fm.createFile(atPath: fileURL.path, contents: nil)
        self.fileHandle = try FileHandle(forWritingTo: fileURL)
    }
    
    public func logPose(
        frameId: String,
        timestampSec: Double,
        transform: simd_float4x4,
        trackingState: String
    ) {
        queue.async { [weak self] in
            guard let self = self else { return }
            let record = LoggedCameraPose(
                frameId: frameId,
                timestampSec: timestampSec,
                transform: transform,
                trackingState: trackingState
            )
            
            if self.firstTimestamp == nil {
                self.firstTimestamp = timestampSec
            }
            self.lastTimestamp = timestampSec
            
            do {
                var data = try self.jsonEncoder.encode(record)
                data.append(0x0A) // Newline delimiter for JSONL
                try self.fileHandle.write(contentsOf: data)
                self.loggedPoseCount += 1
            } catch {
                print("❌ Failed to encode/write pose log: \(error)")
            }
        }
    }
    
    public func close() throws {
        queue.sync {
            try? fileHandle.synchronize()
            try? fileHandle.close()
        }
    }
}

