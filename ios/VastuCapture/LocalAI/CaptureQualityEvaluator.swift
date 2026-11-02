import Foundation

public enum VisualQualityState: String, Codable {
    case red = "RED"       // Critical failure or insufficient quality (< 70)
    case amber = "AMBER"   // Additional observations required (70 - 89)
    case green = "GREEN"   // Validated region or session meeting requirements (>= 90)
    case gray = "GRAY"     // Unobserved or unverified area
    
    public var displayName: String {
        switch self {
        case .red: return "Critical / Incomplete (<70%)"
        case .amber: return "Needs Additional Capture (70-89%)"
        case .green: return "Validated Quality (≥90%)"
        case .gray: return "Unobserved Region"
        }
    }
}

public struct QualityCategoryScore: Codable {
    public let spatialSurfaceCoverage: Double      // Weight: 25%
    public let cameraTrackingReliability: Double   // Weight: 20%
    public let multiViewObservationQuality: Double // Weight: 20%
    public let depthAndGeometryConsistency: Double // Weight: 20%
    public let captureSharpnessAndExposure: Double // Weight: 10%
    public let sessionDataIntegrity: Double        // Weight: 5%
    
    public init(
        spatialSurfaceCoverage: Double,
        cameraTrackingReliability: Double,
        multiViewObservationQuality: Double,
        depthAndGeometryConsistency: Double,
        captureSharpnessAndExposure: Double,
        sessionDataIntegrity: Double
    ) {
        self.spatialSurfaceCoverage = max(0.0, min(100.0, spatialSurfaceCoverage))
        self.cameraTrackingReliability = max(0.0, min(100.0, cameraTrackingReliability))
        self.multiViewObservationQuality = max(0.0, min(100.0, multiViewObservationQuality))
        self.depthAndGeometryConsistency = max(0.0, min(100.0, depthAndGeometryConsistency))
        self.captureSharpnessAndExposure = max(0.0, min(100.0, captureSharpnessAndExposure))
        self.sessionDataIntegrity = max(0.0, min(100.0, sessionDataIntegrity))
    }
}

public struct QualityIssue: Identifiable, Codable {
    public var id: String { "\(regionId)_\(type)" }
    public let regionId: String
    public let type: String
    public let severity: String // "high", "medium", "low"
    public let recommendedAction: String // "rescan", "step_sideways", "slow_down", "tilt_downward"
    
    public init(regionId: String, type: String, severity: String, recommendedAction: String) {
        self.regionId = regionId
        self.type = type
        self.severity = severity
        self.recommendedAction = recommendedAction
    }
}

public struct ComprehensiveCaptureAudit: Codable {
    public let overallScore: Double // 0 to 100
    public let categoryScores: QualityCategoryScore
    public let threshold: Double // 90.0
    public let submissionAllowed: Bool
    public let criticalChecksPassed: Bool
    public let issues: [QualityIssue]
    public let unobservedRegions: [String]
    public let verifiedCompleteRegions: [String]
    public let preFinishWarnings: [String]
    public let auditSummary: String
    public let visualState: VisualQualityState
    
    // Backward compatibility properties for existing UI components
    public var coverageScore: Double { categoryScores.spatialSurfaceCoverage }
    public var parallaxScore: Double { categoryScores.multiViewObservationQuality }
    public var visualQualityScore: Double { categoryScores.captureSharpnessAndExposure }
    public var trackingStabilityScore: Double { categoryScores.cameraTrackingReliability }
    public var isReadyForFinalization: Bool { submissionAllowed }
    public var canFinalizeWithoutWarning: Bool { submissionAllowed && preFinishWarnings.isEmpty }
    
    public static func initial() -> ComprehensiveCaptureAudit {
        ComprehensiveCaptureAudit(
            overallScore: 0.0,
            categoryScores: QualityCategoryScore(
                spatialSurfaceCoverage: 0.0,
                cameraTrackingReliability: 100.0,
                multiViewObservationQuality: 0.0,
                depthAndGeometryConsistency: 0.0,
                captureSharpnessAndExposure: 100.0,
                sessionDataIntegrity: 0.0
            ),
            threshold: 90.0,
            submissionAllowed: false,
            criticalChecksPassed: false,
            issues: [
                QualityIssue(regionId: "room-perimeter", type: "not_started", severity: "high", recommendedAction: "Start recording room")
            ],
            unobservedRegions: ["room-perimeter"],
            verifiedCompleteRegions: [],
            preFinishWarnings: ["Capture not started"],
            auditSummary: "Initializing room scan",
            visualState: .gray
        )
    }
    
    public init(
        overallScore: Double,
        categoryScores: QualityCategoryScore,
        threshold: Double = 90.0,
        submissionAllowed: Bool,
        criticalChecksPassed: Bool,
        issues: [QualityIssue],
        unobservedRegions: [String],
        verifiedCompleteRegions: [String],
        preFinishWarnings: [String],
        auditSummary: String,
        visualState: VisualQualityState
    ) {
        self.overallScore = overallScore
        self.categoryScores = categoryScores
        self.threshold = threshold
        self.submissionAllowed = submissionAllowed
        self.criticalChecksPassed = criticalChecksPassed
        self.issues = issues
        self.unobservedRegions = unobservedRegions
        self.verifiedCompleteRegions = verifiedCompleteRegions
        self.preFinishWarnings = preFinishWarnings
        self.auditSummary = auditSummary
        self.visualState = visualState
    }
}

/// Evaluates multi-factor capture quality against the mandatory 90% submission gate (IOS-008, IOS-014)
public final class CaptureQualityEvaluator {
    public static let shared = CaptureQualityEvaluator()
    public static let mandatoryThreshold: Double = 90.0
    
    public init() {}
    
    public func evaluateQuality(
        coverage: CoverageReport,
        parallax: ParallaxMetric,
        quality: ComprehensiveQualityAssessment?,
        isTrackingDegraded: Bool,
        cornersCount: Int,
        keyframeCount: Int = 16,
        floorObserved: Bool = true,
        ceilingObserved: Bool = false
    ) -> ComprehensiveCaptureAudit {
        var issues: [QualityIssue] = []
        var warnings: [String] = []
        var unobserved: [String] = []
        var verified: [String] = []
        
        // -------------------------------------------------------------
        // CATEGORY 1: Spatial Surface Coverage (Weight: 25%)
        // -------------------------------------------------------------
        // Distinguishes unknown/unobserved regions from verified complete regions.
        let perimeterFactor = min(100.0, coverage.perimeterCoveragePct)
        let angularFactor = min(100.0, coverage.angularCoveragePct)
        let floorFactor: Double = floorObserved ? 100.0 : 40.0
        let ceilingFactor: Double = ceilingObserved ? 100.0 : 60.0
        let rawCoverage = (perimeterFactor * 0.40) + (angularFactor * 0.30) + (floorFactor * 0.15) + (ceilingFactor * 0.15)
        let spatialCoverageScore = max(0.0, min(100.0, rawCoverage))
        
        // Audit wall sectors
        for sector in coverage.missingSectors {
            let regionName = "wall-sector-\(String(format: "%02d", sector))"
            unobserved.append(regionName)
            issues.append(QualityIssue(
                regionId: regionName,
                type: "insufficient_coverage",
                severity: "high",
                recommendedAction: "Scan the highlighted wall."
            ))
        }
        
        if !floorObserved {
            issues.append(QualityIssue(
                regionId: "floor-datum",
                type: "missing_floor",
                severity: "high",
                recommendedAction: "Tilt your camera slightly downward."
            ))
            warnings.append("Floor plane missing or poorly observed. Tilt camera downward.")
        } else {
            verified.append("floor-datum")
        }
        
        if !ceilingObserved && coverage.angularCoveragePct > 60.0 {
            issues.append(QualityIssue(
                regionId: "ceiling-boundary",
                type: "missing_ceiling",
                severity: "medium",
                recommendedAction: "Point your camera toward the upper wall and ceiling."
            ))
        } else if ceilingObserved {
            verified.append("ceiling-boundary")
        }
        
        if coverage.angularCoveragePct < 85.0 {
            warnings.append("Incomplete room coverage: \(Int(100.0 - coverage.angularCoveragePct))% of viewing directions uncaptured.")
        }
        if coverage.perimeterCoveragePct < 80.0 {
            warnings.append("Missing wall segments: \(Int(100.0 - coverage.perimeterCoveragePct))% of wall perimeter unmapped.")
        }
        
        // -------------------------------------------------------------
        // CATEGORY 2: Camera Tracking Reliability (Weight: 20%)
        // -------------------------------------------------------------
        var trackingScore: Double = 98.0
        if isTrackingDegraded {
            trackingScore = 35.0
            issues.append(QualityIssue(
                regionId: "camera-vio",
                type: "tracking_lost",
                severity: "high",
                recommendedAction: "Return to a previously scanned area."
            ))
            warnings.append("ARKit tracking currently degraded. Move slowly and keep textured surfaces in view.")
        } else {
            verified.append("camera-vio")
        }
        
        // -------------------------------------------------------------
        // CATEGORY 3: Multi-View Observation Quality (Weight: 20%)
        // -------------------------------------------------------------
        // Evaluates translation baseline, path bounding area, and rotation vs translation.
        let baselineRatio = min(1.0, parallax.translationBaselineM / 1.50)
        let pathRatio = min(1.0, parallax.pathLengthM / 4.0)
        var multiViewScore = (baselineRatio * 65.0) + (pathRatio * 35.0)
        
        if parallax.isRotationOnly {
            multiViewScore = min(multiViewScore, 30.0)
            issues.append(QualityIssue(
                regionId: "trajectory-parallax",
                type: "insufficient_translation",
                severity: "high",
                recommendedAction: "Move sideways to capture this wall from another angle."
            ))
            warnings.append("Pure rotational scanning detected. Step sideways along walls to create multi-view baseline.")
        } else if parallax.translationBaselineM < 0.80 {
            issues.append(QualityIssue(
                regionId: "trajectory-baseline",
                type: "low_baseline",
                severity: "medium",
                recommendedAction: "Move sideways to capture this wall from another angle."
            ))
            warnings.append("Low camera translation baseline (\(String(format: "%.2f", parallax.translationBaselineM))m / 1.50m recommended).")
        } else {
            verified.append("trajectory-parallax")
        }
        
        // -------------------------------------------------------------
        // CATEGORY 4: Depth and Geometry Consistency (Weight: 20%)
        // -------------------------------------------------------------
        // Anchored by structural corners, ground-plane estimation, and depth confidence.
        let cornerFactor = min(100.0, (Double(cornersCount) / 4.0) * 100.0)
        let depthConfidenceFactor: Double = (quality != nil) ? 95.0 : 75.0
        let depthGeomScore = (cornerFactor * 0.40) + (depthConfidenceFactor * 0.60)
        
        if cornersCount < 3 {
            issues.append(QualityIssue(
                regionId: "architectural-corners",
                type: "unanchored_corners",
                severity: "medium",
                recommendedAction: "Scan the room corner to anchor wall junction."
            ))
        } else {
            verified.append("architectural-corners")
        }
        
        // -------------------------------------------------------------
        // CATEGORY 5: Capture Sharpness and Exposure (Weight: 10%)
        // -------------------------------------------------------------
        var visualScore: Double = 90.0
        if let q = quality {
            switch q.grade {
            case .excellent: visualScore = 100.0
            case .good: visualScore = 88.0
            case .acceptable: visualScore = 70.0
            case .suboptimal: visualScore = 40.0
            case .unusable: visualScore = 10.0
            }
            
            if q.isBlurry {
                visualScore = min(visualScore, 45.0)
                issues.append(QualityIssue(
                    regionId: "camera-frame",
                    type: "motion_blur",
                    severity: "high",
                    recommendedAction: "Hold your phone steady."
                ))
                warnings.append("Motion blur detected. Hold camera steady while moving.")
            }
            if q.isUnderexposed {
                issues.append(QualityIssue(
                    regionId: "lighting-level",
                    type: "poor_lighting",
                    severity: "medium",
                    recommendedAction: "Move to a brighter position."
                ))
                warnings.append("Low lighting detected. Increase room illumination.")
            }
        }
        
        // -------------------------------------------------------------
        // CATEGORY 6: Session Data Integrity (Weight: 5%)
        // -------------------------------------------------------------
        let hasSufficientFrames = keyframeCount >= 12
        let integrityScore: Double = (hasSufficientFrames && !isTrackingDegraded) ? 100.0 : 50.0
        if !hasSufficientFrames {
            issues.append(QualityIssue(
                regionId: "session-keyframes",
                type: "insufficient_frames",
                severity: "high",
                recommendedAction: "Continue recording to capture at least 16 keyframes."
            ))
            warnings.append("Insufficient keyframes recorded (\(keyframeCount) / 16 minimum).")
        } else {
            verified.append("session-manifest")
        }
        
        // -------------------------------------------------------------
        // COMPOSITE WEIGHTED SCORE (Mandated: 25% + 20% + 20% + 20% + 10% + 5% = 100%)
        // -------------------------------------------------------------
        let composite = (spatialCoverageScore * 0.25) +
                        (trackingScore * 0.20) +
                        (multiViewScore * 0.20) +
                        (depthGeomScore * 0.20) +
                        (visualScore * 0.10) +
                        (integrityScore * 0.05)
        
        let overallScore = round(max(0.0, min(100.0, composite)) * 10) / 10.0
        
        // -------------------------------------------------------------
        // CRITICAL INTEGRITY GATES & 90% THRESHOLD (IOS-008)
        // -------------------------------------------------------------
        // Acceptance criteria: A session with score 89 CANNOT be submitted.
        // A session with score >= 90 can be submitted ONLY when critical checks pass.
        let criticalChecksPassed = !isTrackingDegraded &&
                                   !parallax.isRotationOnly &&
                                   hasSufficientFrames &&
                                   spatialCoverageScore >= 60.0 &&
                                   trackingScore >= 70.0
        
        let submissionAllowed = (overallScore >= Self.mandatoryThreshold) && criticalChecksPassed
        
        // Visual quality state
        let visualState: VisualQualityState
        if !criticalChecksPassed || overallScore < 70.0 {
            visualState = .red
        } else if overallScore < Self.mandatoryThreshold {
            visualState = .amber
        } else {
            visualState = .green
        }
        
        let summary: String
        if submissionAllowed {
            summary = "Validated capture quality (\(Int(overallScore))%) meets or exceeds the mandatory 90% threshold. Ready for final submission."
        } else if overallScore >= Self.mandatoryThreshold && !criticalChecksPassed {
            summary = "Score reaches \(Int(overallScore))% but critical tracking/coverage checks failed. Please perform targeted rescan."
        } else {
            let ptsNeeded = Int(ceil(Self.mandatoryThreshold - overallScore))
            summary = "Provisional score \(Int(overallScore))% is below the required 90% gate. +\(ptsNeeded)% needed to enable submission."
        }
        
        let catScores = QualityCategoryScore(
            spatialSurfaceCoverage: round(spatialCoverageScore * 10) / 10.0,
            cameraTrackingReliability: round(trackingScore * 10) / 10.0,
            multiViewObservationQuality: round(multiViewScore * 10) / 10.0,
            depthAndGeometryConsistency: round(depthGeomScore * 10) / 10.0,
            captureSharpnessAndExposure: round(visualScore * 10) / 10.0,
            sessionDataIntegrity: round(integrityScore * 10) / 10.0
        )
        
        return ComprehensiveCaptureAudit(
            overallScore: overallScore,
            categoryScores: catScores,
            threshold: Self.mandatoryThreshold,
            submissionAllowed: submissionAllowed,
            criticalChecksPassed: criticalChecksPassed,
            issues: issues,
            unobservedRegions: unobserved,
            verifiedCompleteRegions: verified,
            preFinishWarnings: warnings,
            auditSummary: summary,
            visualState: visualState
        )
    }
}
