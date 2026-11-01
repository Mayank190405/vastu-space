import Foundation

public struct StorageMonitor {
    public static func getAvailableStorageMB() -> Int64 {
        do {
            let values = try URL(fileURLWithPath: NSHomeDirectory()).resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey])
            if let capacity = values.volumeAvailableCapacityForImportantUsage {
                return capacity / (1024 * 1024)
            }
        } catch {
            // Fallback to POSIX statfs
        }
        
        var stat = statfs()
        if statfs(NSHomeDirectory(), &stat) == 0 {
            let freeBytes = Int64(stat.f_bavail) * Int64(stat.f_bsize)
            return freeBytes / (1024 * 1024)
        }
        return 1024 // 1GB default assumption
    }
}

