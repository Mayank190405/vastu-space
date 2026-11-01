import Foundation
import simd

/// Analyzes camera motion to detect pure rotational scanning and enforce sufficient translational parallax
public final class ParallaxAnalyzer {
    public static let shared = ParallaxAnalyzer()
    
    private var initialPosition: Point2D?
    private var previousPosition: Point2D?
    private var previousHeadingRad: Double = 0.0
    
    private var totalPathLength: Double = 0.0
    private var maxDisplacement: Double = 0.0
    
    private var minX: Double = Double.infinity
    private var maxX: Double = -Double.infinity
    private var minZ: Double = Double.infinity
    private var maxZ: Double = -Double.infinity
    
    // Rolling window for Translation-to-Rotation Ratio (TRR)
    private var recentDeltas: [(trans: Double, rot: Double, time: TimeInterval)] = []
    
    public init() {}
    
    public func reset() {
        initialPosition = nil
        previousPosition = nil
        previousHeadingRad = 0.0
        totalPathLength = 0.0
        maxDisplacement = 0.0
        minX = Double.infinity
        maxX = -Double.infinity
        minZ = Double.infinity
        maxZ = -Double.infinity
        recentDeltas.removeAll()
    }
    
    public func evaluateParallax(
        cameraPosition: Point2D,
        cameraHeadingDeg: Double,
        timestamp: TimeInterval
    ) -> ParallaxMetric {
        let headingRad = cameraHeadingDeg * .pi / 180.0
        
        if initialPosition == nil {
            initialPosition = cameraPosition
            previousPosition = cameraPosition
            previousHeadingRad = headingRad
            minX = cameraPosition.x
            maxX = cameraPosition.x
            minZ = cameraPosition.z
            maxZ = cameraPosition.z
        }
        
        guard let prev = previousPosition else {
            return ParallaxMetric(
                translationBaselineM: 0.0,
                pathLengthM: 0.0,
                pathBoundingAreaM2: 0.0,
                trr: 1.0,
                isRotationOnly: false,
                isSufficient: false
            )
        }
        
        // 1. Delta translation and rotation
        let dx = cameraPosition.x - prev.x
        let dz = cameraPosition.z - prev.z
        let dTrans = sqrt(dx * dx + dz * dz)
        
        var dRot = abs(headingRad - previousHeadingRad)
        if dRot > .pi { dRot = 2.0 * .pi - dRot }
        
        totalPathLength += dTrans
        
        // 2. Maximum baseline from origin
        if let origin = initialPosition {
            let origDx = cameraPosition.x - origin.x
            let origDz = cameraPosition.z - origin.z
            let disp = sqrt(origDx * origDx + origDz * origDz)
            if disp > maxDisplacement {
                maxDisplacement = disp
            }
        }
        
        // 3. Path bounding box area
        if cameraPosition.x < minX { minX = cameraPosition.x }
        if cameraPosition.x > maxX { maxX = cameraPosition.x }
        if cameraPosition.z < minZ { minZ = cameraPosition.z }
        if cameraPosition.z > maxZ { maxZ = cameraPosition.z }
        let boundingArea = max(0.0, (maxX - minX) * (maxZ - minZ))
        
        // 4. TRR rolling window (last 2.0 seconds)
        recentDeltas.append((trans: dTrans, rot: dRot, time: timestamp))
        recentDeltas.removeAll { timestamp - $0.time > 2.0 }
        
        let windowTrans = recentDeltas.reduce(0.0) { $0 + $1.trans }
        let windowRot = recentDeltas.reduce(0.0) { $0 + $1.rot }
        
        let trr = windowTrans / (windowRot + 0.0001)
        
        // Flag rotation-only: operator rotated > 0.45 rad (~25 deg) in 2 seconds with < 0.10m bodily translation
        let isRotationOnly = (windowRot > 0.45 && windowTrans < 0.10)
        
        // Sufficient parallax requires:
        // - At least 0.80 meter baseline displacement
        // - At least 1.20 meters cumulative path
        // - Non-degenerate 2D bounding area (> 0.15 m² or maxDisplacement >= 1.0m)
        let isSufficient = (maxDisplacement >= 0.80 && totalPathLength >= 1.20 && (boundingArea >= 0.15 || maxDisplacement >= 1.0))
        
        previousPosition = cameraPosition
        previousHeadingRad = headingRad
        
        return ParallaxMetric(
            translationBaselineM: round(maxDisplacement * 100) / 100.0,
            pathLengthM: round(totalPathLength * 100) / 100.0,
            pathBoundingAreaM2: round(boundingArea * 100) / 100.0,
            trr: round(trr * 100) / 100.0,
            isRotationOnly: isRotationOnly,
            isSufficient: isSufficient
        )
    }
}
