import Foundation

public enum GuidanceSeverity: String, Codable {
    case alert = "ALERT"     // Critical tracking or integrity failure
    case warning = "WARNING" // Capture flaw (blur, speed, lighting, rotation)
    case info = "INFO"       // Missing coverage, viewpoint suggestion
    case success = "SUCCESS" // Quality reaches threshold (>= 90%)
}

public enum DirectionalCue: String, Codable {
    case forward = "FORWARD"
    case left = "LEFT"
    case right = "RIGHT"
    case steady = "STEADY"
    case stepSideways = "STEP_SIDEWAYS"
    case tiltDown = "TILT_DOWN"
    case tiltUp = "TILT_UP"
    case none = "NONE"
}

public struct GuidanceInstruction: Codable {
    public let text: String
    public let severity: GuidanceSeverity
    public let directionalCue: DirectionalCue
    public let missingAreaSummary: String?
    public let targetRegionId: String?
    
    public init(
        text: String,
        severity: GuidanceSeverity,
        directionalCue: DirectionalCue,
        missingAreaSummary: String? = nil,
        targetRegionId: String? = nil
    ) {
        self.text = text
        self.severity = severity
        self.directionalCue = directionalCue
        self.missingAreaSummary = missingAreaSummary
        self.targetRegionId = targetRegionId
    }
}

/// Advanced AI Real-Time Capture Guidance System implementing strict 7-level priority arbitration (IOS-009)
public final class ScanGuidanceEngine {
    public static let shared = ScanGuidanceEngine()
    
    public init() {}
    
    public func evaluateGuidance(
        trackingState: String,
        quality: ComprehensiveQualityAssessment?,
        parallax: ParallaxMetric,
        coverage: CoverageReport,
        corners: [RoomCorner2D],
        selectedRescanRegion: String? = nil,
        floorObserved: Bool = true,
        ceilingObserved: Bool = false,
        overallScore: Double = 0.0
    ) -> GuidanceInstruction {
        
        // -------------------------------------------------------------
        // PRIORITY 1: Tracking Failure
        // -------------------------------------------------------------
        if trackingState == "LIMITED_RELOCALIZING" || trackingState == "LIMITED_INSUFFICIENT_FEATURES" || trackingState == "NOT_AVAILABLE" {
            return GuidanceInstruction(
                text: "Return to a previously scanned area.",
                severity: .alert,
                directionalCue: .steady,
                missingAreaSummary: "Tracking lost • relocalizing against mapped features"
            )
        }
        
        if trackingState == "LIMITED_EXCESSIVE_MOTION" {
            return GuidanceInstruction(
                text: "Move your phone more slowly.",
                severity: .alert,
                directionalCue: .steady,
                missingAreaSummary: "Excessive motion detected by VIO sensor"
            )
        }
        
        // -------------------------------------------------------------
        // PRIORITY 2: Critical Capture Integrity & Active Rescan Mode
        // -------------------------------------------------------------
        if let rescanRegion = selectedRescanRegion {
            return GuidanceInstruction(
                text: "Move toward the highlighted region and follow the guide.",
                severity: .info,
                directionalCue: .forward,
                missingAreaSummary: "Targeted rescan of \(rescanRegion)",
                targetRegionId: rescanRegion
            )
        }
        
        // -------------------------------------------------------------
        // PRIORITY 3: Missing Room Coverage (Walls, Floor, Ceiling)
        // -------------------------------------------------------------
        if !floorObserved {
            return GuidanceInstruction(
                text: "Tilt your camera slightly downward.",
                severity: .warning,
                directionalCue: .tiltDown,
                missingAreaSummary: "Ground plane missing"
            )
        }
        
        if !coverage.missingSectors.isEmpty && coverage.angularCoveragePct < 85.0 {
            let nextMissing = coverage.missingSectors.first ?? 0
            let regionId = "wall-sector-\(String(format: "%02d", nextMissing))"
            return GuidanceInstruction(
                text: "Scan the highlighted wall.",
                severity: .info,
                directionalCue: .forward,
                missingAreaSummary: "\(coverage.missingSectors.count) wall segments remaining",
                targetRegionId: regionId
            )
        }
        
        if !ceilingObserved && coverage.angularCoveragePct >= 80.0 {
            return GuidanceInstruction(
                text: "Point your camera toward the upper wall and ceiling.",
                severity: .info,
                directionalCue: .tiltUp,
                missingAreaSummary: "Upper architectural boundary unmapped"
            )
        }
        
        // -------------------------------------------------------------
        // PRIORITY 4: Insufficient Viewpoint Diversity (Parallax / Baseline)
        // -------------------------------------------------------------
        if parallax.isRotationOnly || parallax.translationBaselineM < 0.80 {
            return GuidanceInstruction(
                text: "Move sideways to capture this wall from another angle.",
                severity: .warning,
                directionalCue: .stepSideways,
                missingAreaSummary: "Pure rotation detected • multi-view baseline required"
            )
        }
        
        // -------------------------------------------------------------
        // PRIORITY 5: Blur or Exposure Problems
        // -------------------------------------------------------------
        if let q = quality {
            if q.isBlurry {
                return GuidanceInstruction(
                    text: "Hold your phone steady.",
                    severity: .warning,
                    directionalCue: .steady,
                    missingAreaSummary: "Motion blur detected in recent frames"
                )
            }
            if q.isUnderexposed {
                return GuidanceInstruction(
                    text: "Move to a brighter position.",
                    severity: .warning,
                    directionalCue: .none,
                    missingAreaSummary: "Low ambient lighting"
                )
            }
        }
        
        // -------------------------------------------------------------
        // PRIORITY 6: Furniture Observation Recommendations
        // -------------------------------------------------------------
        let unscannedCorners = corners.filter { !$0.isDirectlyObserved }
        if let firstUnscanned = unscannedCorners.first {
            return GuidanceInstruction(
                text: "Scan the room corner (\(Int(firstUnscanned.angleDegrees))°) to anchor wall junction",
                severity: .info,
                directionalCue: .forward,
                missingAreaSummary: "Unanchored corner junction"
            )
        }
        
        // -------------------------------------------------------------
        // PRIORITY 7: General Recording Assistance & Threshold Notification
        // -------------------------------------------------------------
        if overallScore >= 90.0 {
            return GuidanceInstruction(
                text: "Capture quality is sufficient. Review the room before submitting.",
                severity: .success,
                directionalCue: .none,
                missingAreaSummary: "Mandatory 90% quality threshold achieved"
            )
        } else {
            return GuidanceInstruction(
                text: "Continue walking perimeter to close loop (Score: \(Int(overallScore))% / 90% needed)",
                severity: .info,
                directionalCue: .forward,
                missingAreaSummary: "Closing perimeter loop"
            )
        }
    }
}
