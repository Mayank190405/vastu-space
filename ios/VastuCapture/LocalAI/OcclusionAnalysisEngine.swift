import Foundation

public struct BoundaryOcclusionReport {
    public let totalRays: Int
    public let occludedRaysCount: Int
    public let occludedRayIndices: Set<Int>
    public let occludingFurnitureCategories: Set<FurnitureCategory>
    public let isWallSignificantlyBlocked: Bool
}

/// Identifies when movable furniture occludes structural floor-wall boundaries
public final class OcclusionAnalysisEngine {
    public static let shared = OcclusionAnalysisEngine()
    
    public init() {}
    
    /// Evaluates which floor-wall boundary contact rays are occluded by foreground furniture
    public func filterOccludedBoundaryPoints(
        boundaryPointsNormalized: [CGPoint], // (0..1, 0..1)
        furnitureDetections: [DetectedFurniture]
    ) -> BoundaryOcclusionReport {
        guard !furnitureDetections.isEmpty, !boundaryPointsNormalized.isEmpty else {
            return BoundaryOcclusionReport(
                totalRays: boundaryPointsNormalized.count,
                occludedRaysCount: 0,
                occludedRayIndices: [],
                occludingFurnitureCategories: [],
                isWallSignificantlyBlocked: false
            )
        }
        
        var occludedIndices = Set<Int>()
        var occludingCategories = Set<FurnitureCategory>()
        
        for (idx, pt) in boundaryPointsNormalized.enumerated() {
            for item in furnitureDetections {
                let bb = item.boundingBox
                guard bb.count == 4 else { continue }
                
                // Expand box slightly (3% margin) to capture baseboard contact occlusion
                let xMin = bb[0] - 0.03
                let yMin = bb[1] - 0.03
                let xMax = bb[0] + bb[2] + 0.03
                let yMax = bb[1] + bb[3] + 0.03
                
                let px = Double(pt.x)
                let py = Double(pt.y)
                
                if px >= xMin && px <= xMax && py >= yMin && py <= yMax {
                    occludedIndices.insert(idx)
                    occludingCategories.insert(item.category)
                    break
                }
            }
        }
        
        let occludedCount = occludedIndices.count
        let ratio = Double(occludedCount) / Double(boundaryPointsNormalized.count)
        let isSignificant = ratio > 0.40 // More than 40% of boundary is blocked by furniture
        
        return BoundaryOcclusionReport(
            totalRays: boundaryPointsNormalized.count,
            occludedRaysCount: occludedCount,
            occludedRayIndices: occludedIndices,
            occludingFurnitureCategories: occludingCategories,
            isWallSignificantlyBlocked: isSignificant
        )
    }
}

