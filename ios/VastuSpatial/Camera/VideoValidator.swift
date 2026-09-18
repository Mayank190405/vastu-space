import Foundation
import AVFoundation

public struct VideoValidationResult {
    public let isValid: Bool
    public let width: Int
    public let height: Int
    public let durationMs: Int64
    public let nominalFrameRate: Float
    public let fileSizeBytes: Int64
    public let errorMessage: String?
    
    public init(
        isValid: Bool,
        width: Int = 0,
        height: Int = 0,
        durationMs: Int64 = 0,
        nominalFrameRate: Float = 0,
        fileSizeBytes: Int64 = 0,
        errorMessage: String? = nil
    ) {
        self.isValid = isValid
        self.width = width
        self.height = height
        self.durationMs = durationMs
        self.nominalFrameRate = nominalFrameRate
        self.fileSizeBytes = fileSizeBytes
        self.errorMessage = errorMessage
    }
}

public struct VideoValidator {
    
    public static let minDurationMs: Int64 = 1000 // 1 second min
    public static let minFileSizeBytes: Int64 = 100 * 1024 // 100KB min
    
    public static func validateVideo(fileURL: URL) async -> VideoValidationResult {
        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            return VideoValidationResult(isValid: false, errorMessage: "Video file does not exist on disk.")
        }
        
        let attributes = try? FileManager.default.attributesOfItem(atPath: fileURL.path)
        let fileSize = (attributes?[.size] as? NSNumber)?.int64Value ?? 0
        
        guard fileSize >= minFileSizeBytes else {
            return VideoValidationResult(
                isValid: false,
                fileSizeBytes: fileSize,
                errorMessage: "Video file size too small (\(fileSize) bytes) - capture was likely aborted prematurely."
            )
        }
        
        let asset = AVURLAsset(url: fileURL)
        
        do {
            let isPlayable = try await asset.load(.isPlayable)
            guard isPlayable else {
                return VideoValidationResult(
                    isValid: false,
                    fileSizeBytes: fileSize,
                    errorMessage: "Asset is not playable or contains invalid header atoms."
                )
            }
            
            let tracks = try await asset.loadTracks(withMediaType: .video)
            guard let videoTrack = tracks.first else {
                return VideoValidationResult(
                    isValid: false,
                    fileSizeBytes: fileSize,
                    errorMessage: "No readable video track found in recorded container."
                )
            }
            
            let duration = try await asset.load(.duration)
            let durationMs = Int64(CMTimeGetSeconds(duration) * 1000)
            
            guard durationMs >= minDurationMs else {
                return VideoValidationResult(
                    isValid: false,
                    durationMs: durationMs,
                    fileSizeBytes: fileSize,
                    errorMessage: "Recording duration is too short (\(durationMs)ms). Minimum 1 second required."
                )
            }
            
            let naturalSize = try await videoTrack.load(.naturalSize)
            let nominalFrameRate = try await videoTrack.load(.nominalFrameRate)
            
            return VideoValidationResult(
                isValid: true,
                width: Int(naturalSize.width),
                height: Int(naturalSize.height),
                durationMs: durationMs,
                nominalFrameRate: nominalFrameRate,
                fileSizeBytes: fileSize
            )
        } catch {
            return VideoValidationResult(
                isValid: false,
                fileSizeBytes: fileSize,
                errorMessage: "Failed to validate video asset: \(error.localizedDescription)"
            )
        }
    }
}
