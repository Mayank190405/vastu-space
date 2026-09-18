import Foundation

public struct IMUValidationResult {
    public let isValid: Bool
    public let totalSamples: Int64
    public let durationSeconds: Double
    public let averageFrequencyHz: Double
    public let isMonotonic: Bool
    public let duplicateTimestampCount: Int
    public let largeGapCount: Int
    public let errorMessage: String?
    
    public init(
        isValid: Bool,
        totalSamples: Int64 = 0,
        durationSeconds: Double = 0.0,
        averageFrequencyHz: Double = 0.0,
        isMonotonic: Bool = true,
        duplicateTimestampCount: Int = 0,
        largeGapCount: Int = 0,
        errorMessage: String? = nil
    ) {
        self.isValid = isValid
        self.totalSamples = totalSamples
        self.durationSeconds = durationSeconds
        self.averageFrequencyHz = averageFrequencyHz
        self.isMonotonic = isMonotonic
        self.duplicateTimestampCount = duplicateTimestampCount
        self.largeGapCount = largeGapCount
        self.errorMessage = errorMessage
    }
}

public struct IMUValidator {
    
    private static let maxAllowableGapNs: Int64 = 50_000_000 // 50ms gap
    private static let minRequiredSamples: Int64 = 50
    
    public static func validateIMUFile(at fileURL: URL) async -> IMUValidationResult {
        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            return IMUValidationResult(isValid: false, errorMessage: "IMU telemetry file does not exist on disk.")
        }
        
        do {
            let data = try Data(contentsOf: fileURL)
            guard let content = String(data: data, encoding: .utf8) else {
                return IMUValidationResult(isValid: false, errorMessage: "Failed to decode IMU telemetry file.")
            }
            
            let lines = content.components(separatedBy: .newlines).filter { !$0.trimmingCharacters(in: .whitespaces).isEmpty }
            guard lines.count > 1 else {
                return IMUValidationResult(isValid: false, errorMessage: "IMU telemetry file is empty.")
            }
            
            var totalSamples: Int64 = 0
            var firstTimestampNs: Int64 = 0
            var lastTimestampNs: Int64 = 0
            var prevTimestampNs: Int64 = 0
            var isMonotonic = true
            var duplicateCount = 0
            var gapCount = 0
            
            for index in 1..<lines.count {
                let tokens = lines[index].components(separatedBy: ",")
                if tokens.count >= 5 {
                    guard let timestampNs = Int64(tokens[0].trimmingCharacters(in: .whitespaces)) else { continue }
                    
                    if totalSamples == 0 {
                        firstTimestampNs = timestampNs
                        prevTimestampNs = timestampNs
                    } else {
                        if timestampNs <= prevTimestampNs {
                            if timestampNs == prevTimestampNs {
                                duplicateCount += 1
                            } else {
                                isMonotonic = false
                            }
                        } else if timestampNs - prevTimestampNs > maxAllowableGapNs {
                            gapCount += 1
                        }
                        prevTimestampNs = timestampNs
                    }
                    
                    lastTimestampNs = timestampNs
                    totalSamples += 1
                }
            }
            
            guard totalSamples >= minRequiredSamples else {
                return IMUValidationResult(
                    isValid: false,
                    totalSamples: totalSamples,
                    errorMessage: "Insufficient IMU samples (\(totalSamples)). At least \(minRequiredSamples) required."
                )
            }
            
            let durationNs = lastTimestampNs - firstTimestampNs
            let durationSec = durationNs > 0 ? Double(durationNs) / 1_000_000_000.0 : 0.0
            let avgHz = durationSec > 0 ? Double(totalSamples) / durationSec : 0.0
            
            return IMUValidationResult(
                isValid: isMonotonic && totalSamples > 0,
                totalSamples: totalSamples,
                durationSeconds: durationSec,
                averageFrequencyHz: avgHz,
                isMonotonic: isMonotonic,
                duplicateTimestampCount: duplicateCount,
                largeGapCount: gapCount,
                errorMessage: !isMonotonic ? "IMU stream contains non-monotonic timestamps" : nil
            )
        } catch {
            return IMUValidationResult(isValid: false, errorMessage: "Error reading IMU file: \(error.localizedDescription)")
        }
    }
}
