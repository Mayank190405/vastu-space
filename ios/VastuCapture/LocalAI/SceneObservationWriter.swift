import Foundation

/// Logs timestamped 3D scene observations and furniture tracks to the capture package
public final class SceneObservationWriter {
    public let fileURL: URL
    private var fileHandle: FileHandle?
    private let lock = NSLock()
    public private(set) var recordedObservationsCount: Int = 0
    
    public init(fileURL: URL) throws {
        self.fileURL = fileURL
        let fm = FileManager.default
        if !fm.fileExists(atPath: fileURL.path) {
            fm.createFile(atPath: fileURL.path, contents: nil)
        }
        self.fileHandle = try FileHandle(forWritingTo: fileURL)
    }
    
    public func recordObservation(
        track: TrackedFurnitureObject,
        timestamp: TimeInterval
    ) {
        lock.lock()
        defer { lock.unlock() }
        guard let handle = fileHandle else { return }
        
        let record: [String: Any] = [
            "timestamp": timestamp,
            "track_id": track.id,
            "category": track.category.rawValue,
            "label": track.label,
            "confidence": round(track.confidence * 100) / 100.0,
            "position_3d": [
                "x": round(track.position3D.x * 1000) / 1000.0,
                "y": round(track.position3D.y * 1000) / 1000.0,
                "z": round(track.position3D.z * 1000) / 1000.0
            ],
            "dimensions_3d": [
                "width": track.dimensions.width,
                "height": track.dimensions.height,
                "depth": track.dimensions.depth
            ],
            "uncertainty_m": round(track.uncertaintyMeters * 1000) / 1000.0,
            "observation_count": track.observationCount,
            "is_stable": track.isStable
        ]
        
        if let data = try? JSONSerialization.data(withJSONObject: record) {
            handle.write(data)
            handle.write(Data([0x0A]))
            recordedObservationsCount += 1
        }
    }
    
    public func close() {
        lock.lock()
        defer { lock.unlock() }
        try? fileHandle?.close()
        fileHandle = nil
    }
}

