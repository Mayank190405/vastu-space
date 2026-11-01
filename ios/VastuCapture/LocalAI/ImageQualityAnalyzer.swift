import Foundation
import CoreVideo
import Accelerate

public enum QualityGrade: String, Codable {
    case excellent = "EXCELLENT"
    case good = "GOOD"
    case acceptable = "ACCEPTABLE"
    case suboptimal = "SUBOPTIMAL"
    case unusable = "UNUSABLE"
}

public struct ComprehensiveQualityAssessment {
    public let sharpnessScore: Double
    public let exposureRatio: Double // 0.0 to 1.0 (ideal ~0.45 - 0.55)
    public let dynamicRangeScore: Double // 0.0 to 1.0
    public let underExposedFraction: Double // proportion of pixels < 5% luma
    public let overExposedFraction: Double // proportion of pixels > 95% luma
    public let isBlurry: Bool
    public let isOverexposed: Bool
    public let isUnderexposed: Bool
    public let grade: QualityGrade
    public let operatorGuidance: String?
    public let analysisDurationMs: Double
    
    public var isAcceptableForKeyframe: Bool {
        return grade != .unusable && grade != .suboptimal
    }
}

/// Real-time image quality analyzer evaluating sharpness, exposure histograms, and lighting
public final class ImageQualityAnalyzer {
    public static let shared = ImageQualityAnalyzer()
    
    public init() {}
    
    public func analyze(pixelBuffer: CVPixelBuffer) -> ComprehensiveQualityAssessment {
        let startTime = CFAbsoluteTimeGetCurrent()
        
        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }
        
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        let bytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)
        
        guard let base = CVPixelBufferGetBaseAddress(pixelBuffer), width > 0, height > 0 else {
            return ComprehensiveQualityAssessment(
                sharpnessScore: 0.0,
                exposureRatio: 0.5,
                dynamicRangeScore: 0.0,
                underExposedFraction: 0.0,
                overExposedFraction: 0.0,
                isBlurry: true,
                isOverexposed: false,
                isUnderexposed: false,
                grade: .unusable,
                operatorGuidance: "Invalid video frame",
                analysisDurationMs: 0.0
            )
        }
        
        let ptr = base.assumingMemoryBound(to: UInt8.self)
        let sampleStep = 8 // High performance sub-sampling
        
        var histogram = [Int](repeating: 0, count: 16) // 16-bin luminance histogram
        var totalLuma: Double = 0.0
        var varianceSum: Double = 0.0
        var sampleCount: Double = 0.0
        var underExposedCount: Double = 0.0
        var overExposedCount: Double = 0.0
        
        for y in stride(from: sampleStep, to: height - sampleStep, by: sampleStep) {
            let rowOffset = y * bytesPerRow
            for x in stride(from: sampleStep, to: width - sampleStep, by: sampleStep) {
                let offset = rowOffset + x * 4
                let b = Double(ptr[offset])
                let g = Double(ptr[offset + 1])
                let r = Double(ptr[offset + 2])
                let luma = 0.299 * r + 0.587 * g + 0.114 * b
                
                totalLuma += luma
                sampleCount += 1.0
                
                // Histogram binning
                let bin = max(0, min(15, Int(luma / 16.0)))
                histogram[bin] += 1
                
                if luma < 15.0 {
                    underExposedCount += 1.0
                } else if luma > 240.0 {
                    overExposedCount += 1.0
                }
                
                // Laplacian approximation (2nd order horizontal difference)
                let nextOffset = rowOffset + (x + 1) * 4
                let nextLuma = 0.299 * Double(ptr[nextOffset + 2]) + 0.587 * Double(ptr[nextOffset + 1]) + 0.114 * Double(ptr[nextOffset])
                let diff = luma - nextLuma
                varianceSum += (diff * diff)
            }
        }
        
        let meanLuma = sampleCount > 0 ? (totalLuma / sampleCount) : 128.0
        let sharpness = sampleCount > 0 ? (varianceSum / sampleCount) : 0.0
        let exposureRatio = meanLuma / 255.0
        let underRatio = sampleCount > 0 ? (underExposedCount / sampleCount) : 0.0
        let overRatio = sampleCount > 0 ? (overExposedCount / sampleCount) : 0.0
        
        // Count non-empty histogram bins for dynamic range
        let filledBins = histogram.filter { $0 > 5 }.count
        let dynamicRange = Double(filledBins) / 16.0
        
        let isBlurry = sharpness < 20.0
        let isOverexposed = exposureRatio > 0.85 || overRatio > 0.25
        let isUnderexposed = exposureRatio < 0.15 || underRatio > 0.35
        
        let grade: QualityGrade
        var guidance: String? = nil
        
        if isBlurry && (isOverexposed || isUnderexposed) {
            grade = .unusable
            guidance = isUnderexposed ? "Too dark • Turn on room lights" : "Overexposed • Avoid direct light glare"
        } else if isBlurry {
            grade = .suboptimal
            guidance = "Motion blur • Move phone slower"
        } else if isOverexposed {
            grade = .suboptimal
            guidance = "Excessive glare • Angle camera downward"
        } else if isUnderexposed {
            grade = .suboptimal
            guidance = "Low light • Move closer to light source"
        } else if sharpness > 120.0 && dynamicRange > 0.65 {
            grade = .excellent
        } else {
            grade = .good
        }
        
        let durationMs = (CFAbsoluteTimeGetCurrent() - startTime) * 1000.0
        
        return ComprehensiveQualityAssessment(
            sharpnessScore: sharpness,
            exposureRatio: exposureRatio,
            dynamicRangeScore: dynamicRange,
            underExposedFraction: underRatio,
            overExposedFraction: overRatio,
            isBlurry: isBlurry,
            isOverexposed: isOverexposed,
            isUnderexposed: isUnderexposed,
            grade: grade,
            operatorGuidance: guidance,
            analysisDurationMs: durationMs
        )
    }
}

