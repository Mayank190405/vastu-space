import Foundation
import CoreImage
import Accelerate

public struct FrameQualityMetric {
    public let sharpnessScore: Double
    public let exposureScore: Double // 0.0 to 1.0 (0.5 is optimal)
    public let isBlurry: Bool
    public let isOverexposed: Bool
    public let isUnderexposed: Bool
}

public final class ImageQualityAssessor {
    public static let shared = ImageQualityAssessor()
    private init() {}
    
    /// Evaluates sharpness using high-pass frequency variance and exposure using pixel luminance distribution
    public func evaluate(pixelBuffer: CVPixelBuffer) -> FrameQualityMetric {
        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }
        
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        guard let base = CVPixelBufferGetBaseAddress(pixelBuffer) else {
            return FrameQualityMetric(sharpnessScore: 100, exposureScore: 0.5, isBlurry: false, isOverexposed: false, isUnderexposed: false)
        }
        
        let bytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)
        let sampleStep = 8 // Sample sub-grid for high performance (>60 Hz)
        var totalLuma: Double = 0
        var varianceSum: Double = 0
        var sampleCount: Double = 0
        
        let ptr = base.assumingMemoryBound(to: UInt8.self)
        
        for y in stride(from: sampleStep, to: height - sampleStep, by: sampleStep) {
            for x in stride(from: sampleStep, to: width - sampleStep, by: sampleStep) {
                let offset = y * bytesPerRow + x * 4 // BGRA 4-byte pixels
                let b = Double(ptr[offset])
                let g = Double(ptr[offset + 1])
                let r = Double(ptr[offset + 2])
                let luma = 0.299 * r + 0.587 * g + 0.114 * b
                totalLuma += luma
                
                // Laplacian approximation (difference with horizontal neighbor)
                let nextOffset = y * bytesPerRow + (x + 1) * 4
                let nextLuma = 0.299 * Double(ptr[nextOffset + 2]) + 0.587 * Double(ptr[nextOffset + 1]) + 0.114 * Double(ptr[nextOffset])
                let diff = luma - nextLuma
                varianceSum += diff * diff
                sampleCount += 1.0
            }
        }
        
        let meanLuma = sampleCount > 0 ? (totalLuma / sampleCount) : 128.0
        let sharpness = sampleCount > 0 ? (varianceSum / sampleCount) : 100.0
        let exposureRatio = meanLuma / 255.0
        
        return FrameQualityMetric(
            sharpnessScore: sharpness,
            exposureScore: exposureRatio,
            isBlurry: sharpness < 20.0,
            isOverexposed: exposureRatio > 0.88,
            isUnderexposed: exposureRatio < 0.15
        )
    }
}

