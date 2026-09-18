import Foundation

public struct FrameIMUAssociation: Codable {
    public let frameIndex: Int
    public let frameTimestampNs: Int64
    public let nearestImuTimestampNs: Int64
    public let timeDifferenceNs: Int64
    public let imuSampleCountInWindow: Int
    
    public init(frameIndex: Int, frameTimestampNs: Int64, nearestImuTimestampNs: Int64, timeDifferenceNs: Int64, imuSampleCountInWindow: Int) {
        self.frameIndex = frameIndex
        self.frameTimestampNs = frameTimestampNs
        self.nearestImuTimestampNs = nearestImuTimestampNs
        self.timeDifferenceNs = timeDifferenceNs
        self.imuSampleCountInWindow = imuSampleCountInWindow
    }
}

public struct SyncManifest: Codable {
    public let sessionName: String
    public let videoDurationMs: Int64
    public let imuDurationMs: Int64
    public let clockOffsetNs: Int64
    public let timestampDriftMs: Int64
    public let totalFrames: Int
    public let totalImuSamples: Int64
    public let estimatedFps: Float
    public let syncQuality: String // "EXCELLENT", "GOOD", "ACCEPTABLE", "DEGRADED"
    public let isMonotonic: Bool
    public let frameAssociations: [FrameIMUAssociation]
}

public struct SensorSyncEngine {
    
    private static let associationWindowNs: Int64 = 20_000_000 // 20ms window
    
    public static func generateSyncManifest(
        sessionName: String,
        videoValidation: VideoValidationResult,
        imuValidation: IMUValidationResult,
        videoStartTimestampNs: Int64,
        imuFileURL: URL,
        outputDirectoryURL: URL
    ) -> SyncManifest {
        // Read IMU timestamps
        var imuTimestamps: [Int64] = []
        if let content = try? String(contentsOf: imuFileURL, encoding: .utf8) {
            let lines = content.components(separatedBy: .newlines).filter { !$0.trimmingCharacters(in: .whitespaces).isEmpty }
            for index in 1..<lines.count {
                let tokens = lines[index].components(separatedBy: ",")
                if let ts = Int64(tokens[0].trimmingCharacters(in: .whitespaces)) {
                    if imuTimestamps.isEmpty || ts != imuTimestamps.last {
                        imuTimestamps.append(ts)
                    }
                }
            }
        }
        
        let firstImuTs = imuTimestamps.first ?? videoStartTimestampNs
        let clockOffsetNs = videoStartTimestampNs - firstImuTs
        let imuDurationMs = Int64(imuValidation.durationSeconds * 1000)
        let driftMs = abs(videoValidation.durationMs - imuDurationMs)
        
        let totalFrames: Int
        if videoValidation.nominalFrameRate > 0 {
            totalFrames = max(1, Int((Double(videoValidation.durationMs) * Double(videoValidation.nominalFrameRate)) / 1000.0))
        } else {
            totalFrames = 60
        }
        
        let frameIntervalNs = totalFrames > 1 ? (videoValidation.durationMs * 1_000_000) / Int64(totalFrames) : 16_666_666
        
        var associations: [FrameIMUAssociation] = []
        
        for frameIdx in 0..<totalFrames {
            let frameTimeNs = videoStartTimestampNs + (Int64(frameIdx) * frameIntervalNs)
            
            var nearestTs = firstImuTs
            var minDiff = Int64.max
            var windowCount = 0
            
            for imuTs in imuTimestamps {
                let diff = abs(imuTs - frameTimeNs)
                if diff < minDiff {
                    minDiff = diff
                    nearestTs = imuTs
                }
                if diff <= associationWindowNs {
                    windowCount += 1
                }
            }
            
            associations.append(
                FrameIMUAssociation(
                    frameIndex: frameIdx,
                    frameTimestampNs: frameTimeNs,
                    nearestImuTimestampNs: nearestTs,
                    timeDifferenceNs: minDiff,
                    imuSampleCountInWindow: windowCount
                )
            )
        }
        
        let syncQuality: String
        if driftMs < 50 && imuValidation.isMonotonic && imuValidation.largeGapCount == 0 {
            syncQuality = "EXCELLENT"
        } else if driftMs < 150 && imuValidation.isMonotonic {
            syncQuality = "GOOD"
        } else if driftMs < 300 {
            syncQuality = "ACCEPTABLE"
        } else {
            syncQuality = "DEGRADED"
        }
        
        let manifest = SyncManifest(
            sessionName: sessionName,
            videoDurationMs: videoValidation.durationMs,
            imuDurationMs: imuDurationMs,
            clockOffsetNs: clockOffsetNs,
            timestampDriftMs: driftMs,
            totalFrames: totalFrames,
            totalImuSamples: imuValidation.totalSamples,
            estimatedFps: videoValidation.nominalFrameRate,
            syncQuality: syncQuality,
            isMonotonic: imuValidation.isMonotonic,
            frameAssociations: associations
        )
        
        // Write to sync_manifest.json
        let manifestURL = outputDirectoryURL.appendingPathComponent("sync_manifest.json")
        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted
        if let data = try? encoder.encode(manifest) {
            try? data.write(to: manifestURL)
        }
        
        return manifest
    }
}
