import Foundation
import simd

public struct CaptureReadinessAssessment {
    public let surfaceConfidence: Double // 0.0 to 1.0
    public let boundaryStability: Double // 0.0 to 1.0
    public let overallAIScore: Double // 0.0 to 1.0
    public let isReadyForReconstruction: Bool
    public let reasoning: String
}

/// Evaluates confidence, stability, and reconstruction suitability of local AI observations
public final class AIConfidenceEvaluator {
    public static let shared = AIConfidenceEvaluator()
    
    private var previousBoundaryRays: [BoundaryRayCandidate] = []
    private var recentStabilityScores: [Double] = []
    
    public init() {}
    
    public func reset() {
        previousBoundaryRays.removeAll()
        recentStabilityScores.removeAll()
    }
    
    /// Evaluates overall AI confidence and suitability for keyframe registration
    public func evaluateFrame(
        segmentation: SegmentationResult,
        boundaries: BoundaryExtractionResult,
        quality: ComprehensiveQualityAssessment,
        trackingState: String
    ) -> CaptureReadinessAssessment {
        // 1. Surface Confidence (weighted combination of floor + wall area and confidence)
        let floorWeight: Float = 0.55
        let wallWeight: Float = 0.45
        let surfaceConf = Double(
            segmentation.averageFloorConfidence * floorWeight +
            segmentation.averageWallConfidence * wallWeight
        )
        
        // 2. Boundary Stability (angular consistency with previous observation)
        var stability: Double = 1.0
        if !previousBoundaryRays.isEmpty && !boundaries.boundaryRays.isEmpty {
            let count = min(previousBoundaryRays.count, boundaries.boundaryRays.count)
            var angularDiffSum: Float = 0.0
            for i in 0..<count {
                let dotVal = simd_dot(previousBoundaryRays[i].rayCamera, boundaries.boundaryRays[i].rayCamera)
                let clampedDot = max(-1.0, min(1.0, dotVal))
                let angleRad = acos(clampedDot)
                angularDiffSum += angleRad
            }
            let avgAngleDeg = Double(angularDiffSum / Float(count)) * 180.0 / .pi
            // If average boundary shift is small (< 5 deg), stability is high
            stability = max(0.0, min(1.0, 1.0 - (avgAngleDeg / 15.0)))
        }
        previousBoundaryRays = boundaries.boundaryRays
        recentStabilityScores.append(stability)
        if recentStabilityScores.count > 10 {
            recentStabilityScores.removeFirst()
        }
        
        let avgStability = recentStabilityScores.reduce(0.0, +) / Double(recentStabilityScores.count)
        
        // 3. Composite score (Quality + Surface + Stability)
        let qualityScore: Double
        switch quality.grade {
        case .excellent: qualityScore = 1.0
        case .good: qualityScore = 0.85
        case .acceptable: qualityScore = 0.65
        case .suboptimal: qualityScore = 0.35
        case .unusable: qualityScore = 0.0
        }
        
        let overallScore = (qualityScore * 0.40) + (surfaceConf * 0.35) + (avgStability * 0.25)
        
        // 4. Decision logic
        let isReady: Bool
        let reason: String
        
        if trackingState != "NORMAL" && trackingState != "READY" {
            isReady = false
            reason = "Tracking unstable (\(trackingState))"
        } else if !quality.isAcceptableForKeyframe {
            isReady = false
            reason = quality.operatorGuidance ?? "Image quality too low"
        } else if surfaceConf < 0.30 {
            isReady = false
            reason = "Insufficient indoor boundary features detected"
        } else if overallScore < 0.50 {
            isReady = false
            reason = "Low AI observation confidence (\(Int(overallScore * 100))%)"
        } else {
            isReady = true
            reason = "Optimal capture frame"
        }
        
        return CaptureReadinessAssessment(
            surfaceConfidence: surfaceConf,
            boundaryStability: avgStability,
            overallAIScore: overallScore,
            isReadyForReconstruction: isReady,
            reasoning: reason
        )
    }
}

