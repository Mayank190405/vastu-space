import Foundation
import simd

/// Identifies wall intersections and structural room corners while preserving irregular room geometry
public final class CornerDetectionEngine {
    public static let shared = CornerDetectionEngine()
    
    public init() {}
    
    /// Detects candidate corners from fitted wall segments
    public func detectCorners(
        walls: [WallSegment2D],
        stableBoundaryPoints: [Point2D]
    ) -> [RoomCorner2D] {
        guard walls.count >= 2 else { return [] }
        
        var corners: [RoomCorner2D] = []
        var detectedCornerPositions: [Point2D] = []
        
        for i in 0..<walls.count {
            for j in (i + 1)..<walls.count {
                let w1 = walls[i]
                let w2 = walls[j]
                
                // Line 1: (x1, z1) to (x2, z2) -> A1 x + B1 z = C1
                let a1 = w1.end.z - w1.start.z
                let b1 = w1.start.x - w1.end.x
                let c1 = a1 * w1.start.x + b1 * w1.start.z
                
                // Line 2: (x3, z3) to (x4, z4) -> A2 x + B2 z = C2
                let a2 = w2.end.z - w2.start.z
                let b2 = w2.start.x - w2.end.x
                let c2 = a2 * w2.start.x + b2 * w2.start.z
                
                let det = a1 * b2 - a2 * b1
                
                // If det == 0, lines are parallel
                if abs(det) < 0.001 { continue }
                
                let ix = (b2 * c1 - b1 * c2) / det
                let iz = (a1 * c2 - a2 * c1) / det
                let cornerPoint = Point2D(x: ix, z: iz)
                
                // Proximity check: corner must be reasonably close to endpoints of both segments (< 0.65m)
                let distToW1 = min(distance(cornerPoint, w1.start), distance(cornerPoint, w1.end))
                let distToW2 = min(distance(cornerPoint, w2.start), distance(cornerPoint, w2.end))
                
                guard distToW1 < 0.65 && distToW2 < 0.65 else { continue }
                
                // Prevent duplicate corners within 0.25m
                let isDuplicate = detectedCornerPositions.contains { distance($0, cornerPoint) < 0.25 }
                if isDuplicate { continue }
                
                // Compute angle between wall vectors
                let dir1 = simd_normalize(simd_make_float2(Float(w1.end.x - w1.start.x), Float(w1.end.z - w1.start.z)))
                let dir2 = simd_normalize(simd_make_float2(Float(w2.end.x - w2.start.x), Float(w2.end.z - w2.start.z)))
                let dotVal = max(-1.0, min(1.0, simd_dot(dir1, dir2)))
                let angleRad = acos(abs(dotVal))
                let angleDeg = Double(angleRad) * 180.0 / .pi
                
                // Skip if wall segments are virtually collinear (angle < 15 deg)
                guard angleDeg > 15.0 else { continue }
                
                // Check if corner has direct boundary observations nearby (< 0.30m)
                let nearbyPoints = stableBoundaryPoints.filter { distance($0, cornerPoint) < 0.30 }
                let isDirectlyObserved = !nearbyPoints.isEmpty
                
                let baseConf = (w1.confidence + w2.confidence) / 2.0
                let finalConf = isDirectlyObserved ? min(0.98, baseConf + 0.15) : baseConf * 0.8
                
                let corner = RoomCorner2D(
                    position: cornerPoint,
                    angleDegrees: round(angleDeg * 10) / 10.0,
                    confidence: round(finalConf * 100) / 100.0,
                    isDirectlyObserved: isDirectlyObserved
                )
                
                corners.append(corner)
                detectedCornerPositions.append(cornerPoint)
            }
        }
        
        return corners
    }
    
    private func distance(_ p1: Point2D, _ p2: Point2D) -> Double {
        let dx = p1.x - p2.x
        let dz = p1.z - p2.z
        return sqrt(dx * dx + dz * dz)
    }
}

