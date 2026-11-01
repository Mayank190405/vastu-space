import Foundation
import simd

public struct GridCell2D: Hashable {
    public let ix: Int
    public let iz: Int
    
    public init(x: Double, z: Double, resolutionMeters: Double = 0.05) {
        self.ix = Int(floor(x / resolutionMeters))
        self.iz = Int(floor(z / resolutionMeters))
    }
    
    public func centerPoint(resolutionMeters: Double = 0.05) -> Point2D {
        return Point2D(
            x: (Double(ix) + 0.5) * resolutionMeters,
            z: (Double(iz) + 0.5) * resolutionMeters
        )
    }
}

public struct ObservationCell {
    public var hitCount: Int = 0
    public var totalConfidence: Double = 0.0
    public var lastSeenTimestamp: TimeInterval = 0.0
    public var meanPoint: Point2D
}

/// Aggregates world-space floor-wall contact points, performs grid binning, and fits 2D wall segments
public final class WallBoundaryMapper {
    public static let shared = WallBoundaryMapper()
    
    public let gridResolutionMeters: Double = 0.06 // 6cm spatial bins
    private var cellAccumulator: [GridCell2D: ObservationCell] = [:]
    private let lock = NSLock()
    
    public init() {}
    
    public func reset() {
        lock.lock()
        defer { lock.unlock() }
        cellAccumulator.removeAll()
    }
    
    /// Incorporates a new world-space floor contact observation
    public func addObservation(point: Point2D, confidence: Double, timestamp: TimeInterval) {
        lock.lock()
        defer { lock.unlock() }
        
        let cell = GridCell2D(x: point.x, z: point.z, resolutionMeters: gridResolutionMeters)
        if var existing = cellAccumulator[cell] {
            existing.hitCount += 1
            existing.totalConfidence += confidence
            existing.lastSeenTimestamp = timestamp
            // Running weighted average of coordinates inside cell
            let alpha = 1.0 / Double(existing.hitCount)
            let newX = existing.meanPoint.x * (1.0 - alpha) + point.x * alpha
            let newZ = existing.meanPoint.z * (1.0 - alpha) + point.z * alpha
            existing.meanPoint = Point2D(x: newX, z: newZ)
            cellAccumulator[cell] = existing
        } else {
            cellAccumulator[cell] = ObservationCell(
                hitCount: 1,
                totalConfidence: confidence,
                lastSeenTimestamp: timestamp,
                meanPoint: point
            )
        }
        
        // Memory safety cap: Keep at most 800 active spatial bins
        if cellAccumulator.count > 800 {
            // Prune lowest hit count cells
            let sortedKeys = cellAccumulator.keys.sorted {
                (cellAccumulator[$0]?.hitCount ?? 0) < (cellAccumulator[$1]?.hitCount ?? 0)
            }
            for k in sortedKeys.prefix(150) {
                cellAccumulator.removeValue(forKey: k)
            }
        }
    }
    
    /// Returns all accumulated points that have achieved statistical stability
    public func getStableBoundaryPoints(minHits: Int = 2) -> [Point2D] {
        lock.lock()
        defer { lock.unlock() }
        
        return cellAccumulator.values.compactMap { cell in
            guard cell.hitCount >= minHits else { return nil }
            return cell.meanPoint
        }
    }
    
    /// Extracts fitted 2D wall segments preserving irregular room geometry (non-orthogonal angles supported)
    public func extractFittedWallSegments() -> (observed: [WallSegment2D], estimated: [WallSegment2D]) {
        let stablePoints = getStableBoundaryPoints(minHits: 1)
        guard stablePoints.count >= 4 else {
            return (observed: [], estimated: [])
        }
        
        var remainingPoints = stablePoints
        var observedWalls: [WallSegment2D] = []
        let inlierThreshold = 0.08 // 8cm inlier distance
        let maxWalls = 12
        
        // Iterative RANSAC to extract linear wall segments without forcing right angles
        while remainingPoints.count >= 4 && observedWalls.count < maxWalls {
            var bestInliers: [Point2D] = []
            
            // Deterministic + random sampling for stability
            let n = remainingPoints.count
            for i in 0..<min(n, 20) {
                for j in (i + 1)..<min(n, 20) {
                    let p1 = remainingPoints[i]
                    let p2 = remainingPoints[j]
                    let dx = p2.x - p1.x
                    let dz = p2.z - p1.z
                    let len = sqrt(dx * dx + dz * dz)
                    guard len >= 0.20 else { continue }
                    
                    let nx = -dz / len
                    let nz = dx / len
                    let c = nx * p1.x + nz * p1.z
                    
                    var currentInliers: [Point2D] = []
                    for pt in remainingPoints {
                        let dist = abs(nx * pt.x + nz * pt.z - c)
                        if dist <= inlierThreshold {
                            currentInliers.append(pt)
                        }
                    }
                    
                    if currentInliers.count > bestInliers.count {
                        bestInliers = currentInliers
                    }
                }
            }
            
            if bestInliers.count >= 4, let wall = fitLineSegment(points: bestInliers, type: .observed) {
                if wall.lengthMeters >= 0.25 {
                    observedWalls.append(wall)
                }
                let inlierSet = Set(bestInliers)
                remainingPoints.removeAll { inlierSet.contains($0) }
            } else {
                break
            }
        }
        
        // Connect endpoints of nearby non-collinear segments to form estimated/provisional boundaries
        var estimatedWalls: [WallSegment2D] = []
        if observedWalls.count >= 2 {
            for i in 0..<observedWalls.count {
                for j in (i + 1)..<observedWalls.count {
                    let w1 = observedWalls[i]
                    let w2 = observedWalls[j]
                    
                    let gap1 = distance(w1.end, w2.start)
                    let gap2 = distance(w1.start, w2.end)
                    let minGap = min(gap1, gap2)
                    
                    if minGap > 0.20 && minGap < 1.50 {
                        let startPt = (gap1 < gap2) ? w1.end : w1.start
                        let endPt = (gap1 < gap2) ? w2.start : w2.end
                        let estimatedSeg = WallSegment2D(
                            start: startPt,
                            end: endPt,
                            confidence: 0.50,
                            type: .estimated
                        )
                        estimatedWalls.append(estimatedSeg)
                    }
                }
            }
        }
        
        return (observed: observedWalls, estimated: estimatedWalls)
    }
    
    // Fits a 2D line segment using covariance eigen-decomposition
    private func fitLineSegment(points: [Point2D], type: WallObservationType) -> WallSegment2D? {
        guard points.count >= 2 else { return nil }
        
        // Center of mass
        let meanX = points.reduce(0.0) { $0 + $1.x } / Double(points.count)
        let meanZ = points.reduce(0.0) { $0 + $1.z } / Double(points.count)
        
        // Covariance matrix elements
        var varX: Double = 0.0
        var varZ: Double = 0.0
        var covXZ: Double = 0.0
        
        for pt in points {
            let dx = pt.x - meanX
            let dz = pt.z - meanZ
            varX += dx * dx
            varZ += dz * dz
            covXZ += dx * dz
        }
        
        // Principal orientation angle theta = 0.5 * atan2(2 * covXZ, varX - varZ)
        let theta = 0.5 * atan2(2.0 * covXZ, varX - varZ)
        let dirX = cos(theta)
        let dirZ = sin(theta)
        
        // Project all points onto direction vector to find min and max extents
        var minProj = Double.infinity
        var maxProj = -Double.infinity
        
        for pt in points {
            let proj = (pt.x - meanX) * dirX + (pt.z - meanZ) * dirZ
            if proj < minProj { minProj = proj }
            if proj > maxProj { maxProj = proj }
        }
        
        let start = Point2D(x: meanX + minProj * dirX, z: meanZ + minProj * dirZ)
        let end = Point2D(x: meanX + maxProj * dirX, z: meanZ + maxProj * dirZ)
        
        let length = sqrt(pow(end.x - start.x, 2) + pow(end.z - start.z, 2))
        guard length > 0.10 else { return nil }
        
        let confidence = min(0.95, 0.55 + Double(points.count) * 0.03)
        return WallSegment2D(start: start, end: end, confidence: confidence, type: type)
    }
    
    private func distance(_ p1: Point2D, _ p2: Point2D) -> Double {
        let dx = p1.x - p2.x
        let dz = p1.z - p2.z
        return sqrt(dx * dx + dz * dz)
    }
}
