import Foundation

public enum GuidanceSeverity: String, Codable {
    case info = "INFO"
    case warning = "WARNING"
    case alert = "ALERT"
    case success = "SUCCESS"
}

public enum DirectionalCue: String, Codable {
    case forward = "FORWARD"
    case left = "LEFT"
    case right = "RIGHT"
    case steady = "STEADY"
    case stepSideways = "STEP_SIDEWAYS"
    case none = "NONE"
}

public struct GuidanceInstruction {
    public let text: String
    public let severity: GuidanceSeverity
    public let directionalCue: DirectionalCue
    public let missingAreaSummary: String?
}

/// Intelligent state-machine guiding operators during room scanning with real-time cues
public final class ScanGuidanceEngine {
    public static let shared = ScanGuidanceEngine()
    
    public init() {}
    
    public func evaluateGuidance(
        trackingState: String,
        quality: ComprehensiveQualityAssessment?,
        parallax: ParallaxMetric,
        coverage: CoverageReport,
        corners: [RoomCorner2D]
    ) -> GuidanceInstruction {
        // Priority 1: Tracking loss / safety
        if trackingState == "LIMITED_EXCESSIVE_MOTION" {
            return GuidanceInstruction(
                text: "⚠️ Slow down walking speed to ~0.3 m/s",
                severity: .alert,
                directionalCue: .steady,
                missingAreaSummary: nil
            )
        }
        if trackingState == "LIMITED_INSUFFICIENT_FEATURES" {
            return GuidanceInstruction(
                text: "⚠️ Blank wall — keep textured floor & baseboards in view",
                severity: .alert,
                directionalCue: .steady,
                missingAreaSummary: nil
            )
        }
        if trackingState == "LIMITED_RELOCALIZING" {
            return GuidanceInstruction(
                text: "⚠️ Tracking paused — return to previously scanned area",
                severity: .alert,
                directionalCue: .steady,
                missingAreaSummary: nil
            )
        }
        
        // Priority 2: Visual Frame Quality (Blur & Extreme Exposure)
        if let q = quality {
            if q.isBlurry {
                return GuidanceInstruction(
                    text: "⚠️ Hold camera steady — motion blur detected",
                    severity: .warning,
                    directionalCue: .steady,
                    missingAreaSummary: nil
                )
            }
            if q.isUnderexposed {
                return GuidanceInstruction(
                    text: "💡 Low light — turn on room lights if possible",
                    severity: .warning,
                    directionalCue: .none,
                    missingAreaSummary: nil
                )
            }
            if q.isOverexposed {
                return GuidanceInstruction(
                    text: "☀️ Glare detected — angle phone slightly downward",
                    severity: .warning,
                    directionalCue: .none,
                    missingAreaSummary: nil
                )
            }
        }
        
        // Priority 3: Pure Rotational Scanning (Degenerate Parallax Prevention)
        if parallax.isRotationOnly {
            return GuidanceInstruction(
                text: "👟 Step sideways along the wall • Avoid rotating in place",
                severity: .warning,
                directionalCue: .stepSideways,
                missingAreaSummary: "Insufficient parallax (pure rotation detected)"
            )
        }
        
        // Priority 4: Initial Baseline Translation
        if parallax.translationBaselineM < 0.80 {
            let needed = String(format: "%.1f", 0.80 - parallax.translationBaselineM)
            return GuidanceInstruction(
                text: "Walk along the floor perimeter (need \(needed)m baseline)",
                severity: .info,
                directionalCue: .forward,
                missingAreaSummary: "Establishing initial spatial baseline"
            )
        }
        
        // Priority 5: Unscanned Corners
        let unscannedCorners = corners.filter { !$0.isDirectlyObserved }
        if let firstUnscanned = unscannedCorners.first {
            return GuidanceInstruction(
                text: "Scan the room corner (\(Int(firstUnscanned.angleDegrees))°) to anchor wall junction",
                severity: .info,
                directionalCue: .forward,
                missingAreaSummary: "Unscanned corner at junction"
            )
        }
        
        // Priority 6: Missing Sectors / Opposite Wall
        if !coverage.missingSectors.isEmpty && coverage.angularCoveragePct < 75.0 {
            let missingSummary = "Missing \(coverage.missingSectors.count) room sectors (\(Int(100.0 - coverage.angularCoveragePct))% remaining)"
            return GuidanceInstruction(
                text: "Continue walking perimeter to capture opposite wall",
                severity: .info,
                directionalCue: .forward,
                missingAreaSummary: missingSummary
            )
        }
        
        // Priority 7: Perimeter Loop Closure
        if coverage.perimeterCoveragePct < 80.0 {
            return GuidanceInstruction(
                text: "Follow perimeter to close wall loop (\(Int(coverage.perimeterCoveragePct))% observed)",
                severity: .info,
                directionalCue: .forward,
                missingAreaSummary: "\(Int(coverage.totalEstimatedPerimeterM - coverage.observedPerimeterM))m wall perimeter unmapped"
            )
        }
        
        // Priority 8: Complete & Ready
        return GuidanceInstruction(
            text: "✅ Full room coverage & parallax verified • Tap Finish",
            severity: .success,
            directionalCue: .none,
            missingAreaSummary: nil
        )
    }
}

