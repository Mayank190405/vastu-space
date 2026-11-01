import Foundation
import simd

/// Tracks angular viewing diversity, perimeter completeness, and missing room boundaries
public final class RoomCoverageTracker {
    public static let shared = RoomCoverageTracker()
    
    private let totalSectors: Int = 16 // 16 radial bins (22.5 degrees each)
    private var observedSectors = Set<Int>()
    private var roomCentroid: Point2D = Point2D(x: 0, z: 0)
    
    public init() {}
    
    public func reset() {
        observedSectors.removeAll()
        roomCentroid = Point2D(x: 0, z: 0)
    }
    
    /// Updates coverage with current camera heading and observed walls
    public func evaluateCoverage(
        cameraPosition: Point2D,
        cameraHeadingDeg: Double,
        observedWalls: [WallSegment2D],
        boundaryPoints: [Point2D]
    ) -> CoverageReport {
        // 1. Update room centroid estimate if boundary points exist
        if !boundaryPoints.isEmpty {
            let sumX = boundaryPoints.reduce(0.0) { $0 + $1.x }
            let sumZ = boundaryPoints.reduce(0.0) { $0 + $1.z }
            roomCentroid = Point2D(x: sumX / Double(boundaryPoints.count), z: sumZ / Double(boundaryPoints.count))
        }
        
        // 2. Map camera heading to 16 radial sectors
        var normalizedHeading = cameraHeadingDeg.truncatingRemainder(dividingBy: 360.0)
        if normalizedHeading < 0 { normalizedHeading += 360.0 }
        let sectorIndex = Int(normalizedHeading / (360.0 / Double(totalSectors))) % totalSectors
        observedSectors.insert(sectorIndex)
        
        let angularPct = (Double(observedSectors.count) / Double(totalSectors)) * 100.0
        
        // 3. Perimeter coverage estimation
        let totalObservedMeters = observedWalls.reduce(0.0) { $0 + $1.lengthMeters }
        
        // Estimate room perimeter from bounding box of boundary points
        var minX = cameraPosition.x - 1.0
        var maxX = cameraPosition.x + 1.0
        var minZ = cameraPosition.z - 1.0
        var maxZ = cameraPosition.z + 1.0
        
        for pt in boundaryPoints {
            if pt.x < minX { minX = pt.x }
            if pt.x > maxX { maxX = pt.x }
            if pt.z < minZ { minZ = pt.z }
            if pt.z > maxZ { maxZ = pt.z }
        }
        
        let roomWidth = max(2.0, maxX - minX)
        let roomLength = max(2.0, maxZ - minZ)
        let estimatedPerimeter = 2.0 * (roomWidth + roomLength)
        
        let perimeterPct = min(100.0, (totalObservedMeters / estimatedPerimeter) * 100.0)
        
        // 4. Missing sectors
        var missing: [Int] = []
        for s in 0..<totalSectors {
            if !observedSectors.contains(s) {
                missing.append(s)
            }
        }
        
        // Coverage is sufficient if operator has scanned >= 75% of angular sectors and observed major walls
        let isSufficient = angularPct >= 75.0 && (totalObservedMeters >= 4.0 || perimeterPct >= 65.0)
        
        return CoverageReport(
            perimeterCoveragePct: round(perimeterPct * 10) / 10.0,
            angularCoveragePct: round(angularPct * 10) / 10.0,
            totalEstimatedPerimeterM: round(estimatedPerimeter * 10) / 10.0,
            observedPerimeterM: round(totalObservedMeters * 10) / 10.0,
            missingSectors: missing,
            isSufficient: isSufficient
        )
    }
}

