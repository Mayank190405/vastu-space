import Foundation

public final class LocalMLDiagnostics {
    public static let shared = LocalMLDiagnostics()
    
    private let lock = NSLock()
    private var segmentationTimes: [Double] = []
    private var qualityTimes: [Double] = []
    private var inferenceTimestamps: [Double] = []
    
    public private(set) var totalInferences: Int = 0
    public private(set) var currentFPS: Double = 0.0
    public private(set) var avgLatencyMs: Double = 0.0
    
    public init() {}
    
    public func recordInference(segmentationTimeMs: Double, qualityTimeMs: Double) {
        lock.lock()
        defer { lock.unlock() }
        
        totalInferences += 1
        segmentationTimes.append(segmentationTimeMs)
        qualityTimes.append(qualityTimeMs)
        
        let now = CFAbsoluteTimeGetCurrent()
        inferenceTimestamps.append(now)
        
        // Keep last 30 samples for running metrics
        if segmentationTimes.count > 30 {
            segmentationTimes.removeFirst()
            qualityTimes.removeFirst()
        }
        
        // Remove timestamps older than 2 seconds for instantaneous FPS calculation
        inferenceTimestamps.removeAll(where: { now - $0 > 2.0 })
        if inferenceTimestamps.count >= 2 {
            let elapsed = inferenceTimestamps.last! - inferenceTimestamps.first!
            if elapsed > 0.1 {
                currentFPS = Double(inferenceTimestamps.count - 1) / elapsed
            }
        }
        
        let totalSeg = segmentationTimes.reduce(0.0, +)
        let totalQual = qualityTimes.reduce(0.0, +)
        avgLatencyMs = (totalSeg + totalQual) / Double(segmentationTimes.count)
    }
    
    public func getDiagnosticsSummary() -> [String: Any] {
        lock.lock()
        defer { lock.unlock() }
        
        let thermalStateStr: String
        switch ProcessInfo.processInfo.thermalState {
        case .nominal: thermalStateStr = "NOMINAL"
        case .fair: thermalStateStr = "FAIR"
        case .serious: thermalStateStr = "SERIOUS"
        case .critical: thermalStateStr = "CRITICAL"
        @unknown default: thermalStateStr = "UNKNOWN"
        }
        
        let avgSeg = segmentationTimes.isEmpty ? 0.0 : (segmentationTimes.reduce(0.0, +) / Double(segmentationTimes.count))
        let avgQual = qualityTimes.isEmpty ? 0.0 : (qualityTimes.reduce(0.0, +) / Double(qualityTimes.count))
        
        return [
            "total_inferences": totalInferences,
            "current_fps": round(currentFPS * 10.0) / 10.0,
            "avg_latency_ms": round(avgLatencyMs * 100.0) / 100.0,
            "avg_segmentation_ms": round(avgSeg * 100.0) / 100.0,
            "avg_quality_ms": round(avgQual * 100.0) / 100.0,
            "thermal_state": thermalStateStr,
            "local_ai_mode": "ON_DEVICE_ZERO_CLOUD"
        ]
    }
    
    public func reset() {
        lock.lock()
        defer { lock.unlock() }
        segmentationTimes.removeAll()
        qualityTimes.removeAll()
        inferenceTimestamps.removeAll()
        totalInferences = 0
        currentFPS = 0.0
        avgLatencyMs = 0.0
    }
}

