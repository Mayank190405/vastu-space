import Foundation
import CoreVideo
import simd

public struct BoundaryContactPoint: Equatable {
    public let imagePointNormalized: CGPoint // (0.0 ... 1.0, 0.0 ... 1.0)
    public let imagePointPixels: CGPoint // in image resolution
    public let cameraRay: simd_float3 // Normalized unit direction in camera space
    public let confidence: Double
    
    public init(
        imagePointNormalized: CGPoint,
        imagePointPixels: CGPoint,
        cameraRay: simd_float3,
        confidence: Double
    ) {
        self.imagePointNormalized = imagePointNormalized
        self.imagePointPixels = imagePointPixels
        self.cameraRay = cameraRay
        self.confidence = confidence
    }
}

public struct BoundaryExtractionResult {
    public let contactPoints: [BoundaryContactPoint]
    public let boundaryRays: [BoundaryRayCandidate]
    public let averageBoundaryConfidence: Double
    public let polylineNormalized: [CGPoint]
    public let timestamp: TimeInterval
    
    public init(
        contactPoints: [BoundaryContactPoint],
        boundaryRays: [BoundaryRayCandidate],
        averageBoundaryConfidence: Double,
        polylineNormalized: [CGPoint],
        timestamp: TimeInterval
    ) {
        self.contactPoints = contactPoints
        self.boundaryRays = boundaryRays
        self.averageBoundaryConfidence = averageBoundaryConfidence
        self.polylineNormalized = polylineNormalized
        self.timestamp = timestamp
    }
}

/// Extracts structural floor-wall contact boundaries and unprojects them into camera 3D space rays
public final class BoundaryDetectionEngine {
    public static let shared = BoundaryDetectionEngine()
    
    public init() {}
    
    /// Extracts floor-wall contact line from segmentation map and camera calibration
    public func extractBoundaries(
        segmentation: SegmentationResult,
        intrinsics: CameraIntrinsics
    ) -> BoundaryExtractionResult {
        let cols = segmentation.gridWidth
        let rows = segmentation.gridHeight
        let w = Double(intrinsics.imageWidth)
        let h = Double(intrinsics.imageHeight)
        let fx = intrinsics.fx
        let fy = intrinsics.fy
        let cx = intrinsics.cx
        let cy = intrinsics.cy
        
        var contactPoints: [BoundaryContactPoint] = []
        var boundaryRays: [BoundaryRayCandidate] = []
        var polyline: [CGPoint] = []
        var totalConfidence: Double = 0.0
        
        // Scan each column from bottom (floor) upwards to find the interface where floor meets wall
        for c in stride(from: 1, to: cols - 1, by: 1) {
            var transitionRow: Int? = nil
            var transitionConfidence: Double = 0.0
            
            // Start scanning from row (rows - 2) up to row 3
            for r in stride(from: rows - 2, through: 3, by: -1) {
                let currentIdx = r * cols + c
                let nextUpIdx = (r - 1) * cols + c
                
                let currentClass = segmentation.classMap[currentIdx]
                let nextUpClass = segmentation.classMap[nextUpIdx]
                
                // Transition condition: current is floor and above is wall (or background/boundary)
                if currentClass == .floor && (nextUpClass == .wall || nextUpClass == .background) {
                    transitionRow = r
                    let pFloor = Double(segmentation.floorConfidenceMap[currentIdx])
                    let pWall = Double(segmentation.wallConfidenceMap[nextUpIdx])
                    transitionConfidence = (pFloor + pWall) / 2.0
                    break
                }
            }
            
            if let row = transitionRow {
                let normX = (Double(c) + 0.5) / Double(cols)
                let normY = (Double(row) + 0.5) / Double(rows)
                
                let pixelX = normX * w
                let pixelY = normY * h
                
                // Unproject (pixelX, pixelY) into normalized camera 3D ray
                let x_c = Float((pixelX - cx) / fx)
                let y_c = Float((pixelY - cy) / fy)
                let z_c: Float = 1.0
                let ray = simd_normalize(simd_make_float3(x_c, y_c, z_c))
                
                let conf = max(0.4, min(1.0, transitionConfidence))
                
                let point = BoundaryContactPoint(
                    imagePointNormalized: CGPoint(x: normX, y: normY),
                    imagePointPixels: CGPoint(x: pixelX, y: pixelY),
                    cameraRay: ray,
                    confidence: conf
                )
                
                contactPoints.append(point)
                boundaryRays.append(BoundaryRayCandidate(rayCamera: ray, confidence: conf))
                polyline.append(CGPoint(x: normX, y: normY))
                totalConfidence += conf
            }
        }
        
        let avgConf = contactPoints.isEmpty ? 0.0 : (totalConfidence / Double(contactPoints.count))
        
        return BoundaryExtractionResult(
            contactPoints: contactPoints,
            boundaryRays: boundaryRays,
            averageBoundaryConfidence: avgConf,
            polylineNormalized: polyline,
            timestamp: segmentation.timestamp
        )
    }
}

