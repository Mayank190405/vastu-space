import Foundation

public struct StorageMonitor {
    
    public static let criticalThresholdMB: Int64 = 200
    public static let warningThresholdMB: Int64 = 500
    
    public static func getAvailableStorageMB() -> Int64 {
        do {
            let docURL = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory
            let values = try docURL.resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey])
            if let capacity = values.volumeAvailableCapacityForImportantUsage {
                return capacity / (1024 * 1024)
            }
        } catch {
            print("Storage check error: \(error)")
        }
        return 1024 // Fallback
    }
    
    public static func hasSufficientStorage(minMB: Int64 = criticalThresholdMB) -> Bool {
        return getAvailableStorageMB() >= minMB
    }
    
    public static func isStorageLow() -> Bool {
        return getAvailableStorageMB() < warningThresholdMB
    }
    
    public static func formatStorageMB(_ mb: Int64) -> String {
        if mb >= 1024 {
            return String(format: "%.1f GB", Double(mb) / 1024.0)
        } else {
            return "\(mb) MB"
        }
    }
    
    public static func isThermalThrottled() -> Bool {
        let state = ProcessInfo.processInfo.thermalState
        return state == .serious || state == .critical
    }
}
