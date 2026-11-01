import Foundation
import simd

public struct KeyframeDecision {
    public let shouldRecord: Bool
    public let reason: String
    public let translationDelta: Double
    public let rotationDeltaDeg: Double
    public let timeDelta: Double
}

public final class KeyframeSelector {
    public var minTranslationMeters: Double = 0.12    // 12 cm minimum translation
    public var minRotationDegrees: Double = 7.5       // 7.5 degrees minimum angular rotation
    public var minIntervalSeconds: Double = 0.08      // Max 12.5 FPS to prevent redundant frames
    public var maxIntervalSeconds: Double = 0.40      // Ensure continuous feature tracks if moving
    public var minSharpnessScore: Double = 12.0       // Sharpness variance threshold
    
    private var lastKeyframePosition: simd_float3?
    private var lastKeyframeRotation: simd_quatf?
    private var lastKeyframeTimestamp: TimeInterval = 0
    private var totalKeyframesSelected: Int = 0
    
    public init() {}
    
    public func reset() {
        lastKeyframePosition = nil
        lastKeyframeRotation = nil
        lastKeyframeTimestamp = 0
        totalKeyframesSelected = 0
    }
    
    public func evaluate(
        transform: simd_float4x4,
        timestamp: TimeInterval,
        trackingState: String,
        sharpnessScore: Double = 50.0
    ) -> KeyframeDecision {
        // 1. Tracking Quality Gate: Strictly drop frames during degraded or recovery tracking
        guard trackingState == "NORMAL" || trackingState == "normal" else {
            return KeyframeDecision(
                shouldRecord: false,
                reason: "Tracking state is '\(trackingState)' (requires NORMAL)",
                translationDelta: 0,
                rotationDeltaDeg: 0,
                timeDelta: 0
            )
        }
        
        // 2. Sharpness Gate: Reject motion-blurred frames unless stationary fallback
        if sharpnessScore < minSharpnessScore && totalKeyframesSelected > 0 {
            return KeyframeDecision(
                shouldRecord: false,
                reason: "Motion blur detected (sharpness: \(String(format: "%.1f", sharpnessScore)) < \(minSharpnessScore))",
                translationDelta: 0,
                rotationDeltaDeg: 0,
                timeDelta: 0
            )
        }
        
        let position = simd_make_float3(transform.columns.3.x, transform.columns.3.y, transform.columns.3.z)
        let rotation = simd_quatf(transform)
        
        // First keyframe is always selected
        guard let lastPos = lastKeyframePosition,
              let lastRot = lastKeyframeRotation else {
            recordKeyframe(position: position, rotation: rotation, timestamp: timestamp)
            return KeyframeDecision(
                shouldRecord: true,
                reason: "Initial baseline keyframe",
                translationDelta: 0,
                rotationDeltaDeg: 0,
                timeDelta: 0
            )
        }
        
        let timeDelta = timestamp - lastKeyframeTimestamp
        
        // 3. Minimum Interval Gate: Enforce temporal throttling
        if timeDelta < minIntervalSeconds {
            return KeyframeDecision(
                shouldRecord: false,
                reason: "Temporal throttle (dt: \(String(format: "%.3f", timeDelta))s < \(minIntervalSeconds)s)",
                translationDelta: 0,
                rotationDeltaDeg: 0,
                timeDelta: timeDelta
            )
        }
        
        // Compute Euclidean distance in meters
        let transDelta = Double(simd_distance(position, lastPos))
        
        // Compute relative rotation angle in degrees
        let dotProduct = abs(simd_dot(rotation, lastRot))
        let clampedDot = min(1.0, max(-1.0, dotProduct))
        let rotDeltaRad = 2.0 * acos(clampedDot)
        let rotDeltaDeg = Double(rotDeltaRad) * (180.0 / .pi)
        
        // 4. Spatial / Angular Diversity Criteria
        if transDelta >= minTranslationMeters {
            recordKeyframe(position: position, rotation: rotation, timestamp: timestamp)
            return KeyframeDecision(
                shouldRecord: true,
                reason: "Translation threshold met (\(String(format: "%.2f", transDelta))m >= \(minTranslationMeters)m)",
                translationDelta: transDelta,
                rotationDeltaDeg: rotDeltaDeg,
                timeDelta: timeDelta
            )
        }
        
        if rotDeltaDeg >= minRotationDegrees {
            recordKeyframe(position: position, rotation: rotation, timestamp: timestamp)
            return KeyframeDecision(
                shouldRecord: true,
                reason: "Angular diversity threshold met (\(String(format: "%.1f", rotDeltaDeg))° >= \(minRotationDegrees)°)",
                translationDelta: transDelta,
                rotationDeltaDeg: rotDeltaDeg,
                timeDelta: timeDelta
            )
        }
        
        // 5. Maximum Interval Fallback: Maintain track continuity if moving continuously
        if timeDelta >= maxIntervalSeconds && transDelta >= (minTranslationMeters * 0.4) {
            recordKeyframe(position: position, rotation: rotation, timestamp: timestamp)
            return KeyframeDecision(
                shouldRecord: true,
                reason: "Track continuity interval fallback",
                translationDelta: transDelta,
                rotationDeltaDeg: rotDeltaDeg,
                timeDelta: timeDelta
            )
        }
        
        return KeyframeDecision(
            shouldRecord: false,
            reason: "Insufficient camera displacement or rotation",
            translationDelta: transDelta,
            rotationDeltaDeg: rotDeltaDeg,
            timeDelta: timeDelta
        )
    }
    
    private func recordKeyframe(position: simd_float3, rotation: simd_quatf, timestamp: TimeInterval) {
        lastKeyframePosition = position
        lastKeyframeRotation = rotation
        lastKeyframeTimestamp = timestamp
        totalKeyframesSelected += 1
    }
}

