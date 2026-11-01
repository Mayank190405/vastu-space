import Foundation

public struct ComprehensiveCaptureAudit {
    public let overallScore: Double // 0 to 100
    public let coverageScore: Double // 0 to 100
    public let parallaxScore: Double // 0 to 100
    public let visualQualityScore: Double // 0 to 100
    public let trackingStabilityScore: Double // 0 to 100
    public let isReadyForFinalization: Bool
    public let canFinalizeWithoutWarning: Bool
    public let preFinishWarnings: [String]
    public let auditSummary: String
}

/// Evaluates multi-factor capture quality and prevents premature capture finalization
public final class CaptureQualityEvaluator {
    public static let shared = CaptureQualityEvaluator()
    
    public init() {}
    
    public func evaluateQuality(
        coverage: CoverageReport,
        parallax: ParallaxMetric,
        quality: ComprehensiveQualityAssessment?,
        isTrackingDegraded: Bool,
        cornersCount: Int
    ) -> ComprehensiveCaptureAudit {
        var warnings: [String] = []
        
        // 1. Coverage Score (0 - 100)
        let coverageScore = (coverage.perimeterCoveragePct * 0.5) + (coverage.angularCoveragePct * 0.5)
        if coverage.angularCoveragePct < 65.0 {
            warnings.append("Incomplete room coverage: \(Int(100.0 - coverage.angularCoveragePct))% of viewing directions uncaptured.")
        }
        if coverage.perimeterCoveragePct < 55.0 {
            warnings.append("Missing major wall segments: \(Int(100.0 - coverage.perimeterCoveragePct))% of wall perimeter unmapped.")
        }
        
        // 2. Parallax Score (0 - 100)
        let baselineScore = min(100.0, (parallax.translationBaselineM / 1.20) * 100.0)
        let pathScore = min(100.0, (parallax.pathLengthM / 3.0) * 100.0)
        let parallaxScore = (baselineScore * 0.6) + (pathScore * 0.4)
        
        if parallax.translationBaselineM < 0.70 {
            warnings.append("Insufficient camera motion baseline (\(String(format: "%.1f", parallax.translationBaselineM))m / 1.0m recommended). Step further along walls.")
        }
        if parallax.isRotationOnly {
            warnings.append("Pure rotational scanning detected. 3D reconstruction requires camera translation.")
        }
        
        // 3. Visual Quality Score (0 - 100)
        let visualQualityScore: Double
        if let q = quality {
            switch q.grade {
            case .excellent: visualQualityScore = 100.0
            case .good: visualQualityScore = 85.0
            case .acceptable: visualQualityScore = 65.0
            case .suboptimal: visualQualityScore = 35.0
            case .unusable: visualQualityScore = 0.0
            }
            if q.isBlurry {
                warnings.append("Motion blur detected in recent frames. Hold phone steadier.")
            }
        } else {
            visualQualityScore = 80.0
        }
        
        // 4. Tracking Stability Score (0 - 100)
        let trackingStabilityScore = isTrackingDegraded ? 40.0 : 95.0
        if isTrackingDegraded {
            warnings.append("ARKit tracking currently degraded. Slow movement and keep floor in view.")
        }
        
        // 5. Corner Bonus (0 - 5 points)
        let cornerBonus = min(5.0, Double(cornersCount) * 1.25)
        
        // Weighted Composite Score
        let composite = (coverageScore * 0.35) +
                        (parallaxScore * 0.25) +
                        (visualQualityScore * 0.20) +
                        (trackingStabilityScore * 0.15) +
                        cornerBonus
        
        let overallScore = max(0.0, min(100.0, composite))
        
        let isReady = overallScore >= 55.0 && !isTrackingDegraded
        let canFinalizeWithoutWarning = overallScore >= 75.0 && warnings.isEmpty
        
        let summary: String
        if canFinalizeWithoutWarning {
            summary = "Optimal room capture quality (\(Int(overallScore))%) — Ready for 3D reconstruction"
        } else if isReady {
            summary = "Acceptable capture (\(Int(overallScore))%) with \(warnings.count) minor warnings"
        } else {
            summary = "Capture incomplete (\(Int(overallScore))%) — Further scanning required"
        }
        
        return ComprehensiveCaptureAudit(
            overallScore: round(overallScore * 10) / 10.0,
            coverageScore: round(coverageScore * 10) / 10.0,
            parallaxScore: round(parallaxScore * 10) / 10.0,
            visualQualityScore: round(visualQualityScore * 10) / 10.0,
            trackingStabilityScore: round(trackingStabilityScore * 10) / 10.0,
            isReadyForFinalization: isReady,
            canFinalizeWithoutWarning: canFinalizeWithoutWarning,
            preFinishWarnings: warnings,
            auditSummary: summary
        )
    }
}

