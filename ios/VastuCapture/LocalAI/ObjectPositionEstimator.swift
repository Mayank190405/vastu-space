import Foundation
import simd

/// Computes 3D position estimates and uncertainty bounds for detected indoor furniture
public final class ObjectPositionEstimator {
    public static let shared = ObjectPositionEstimator()
    
    public init() {}
    
    /// Estimates 3D position in world coordinates from 2D detection, camera pose, and floor calibration
    public func estimatePosition3D(
        detection: DetectedFurniture,
        pose: CameraPose,
        intrinsics: CameraIntrinsics,
        floorPlaneY: Double = 0.0,
        depthResult: DepthEstimationResult? = nil
    ) -> PositionEstimate3D? {
        let bb = detection.boundingBox // [xMin, yMin, width, height] in normalized coordinates (0..1)
        guard bb.count == 4 else { return nil }
        
        let xCenterNorm = bb[0] + bb[2] / 2.0
        let yBottomNorm = bb[1] + bb[3] // Base of object touching floor
        
        let imgW = Double(intrinsics.imageWidth)
        let imgH = Double(intrinsics.imageHeight)
        
        // Pixel coordinates of bottom center
        let px = xCenterNorm * imgW
        let py = yBottomNorm * imgH
        
        // Unproject bottom center into camera-space 3D unit ray
        // Note: in camera coordinates (+Y up, +Z forward), downward in image space (py > cy) yields negative Y
        let xc = Float((px - intrinsics.cx) / intrinsics.fx)
        let yc = -Float((py - intrinsics.cy) / intrinsics.fy)
        let rayCam = simd_normalize(simd_make_float3(xc, yc, 1.0))
        
        let camX = pose.position[0]
        let camY = pose.position[1]
        let camZ = pose.position[2]
        let camPosSimd = simd_make_float3(Float(camX), Float(camY), Float(camZ))
        
        let rotMatrix = simd_float3x3(
            simd_make_float3(Float(pose.transform[0][0]), Float(pose.transform[1][0]), Float(pose.transform[2][0])),
            simd_make_float3(Float(pose.transform[0][1]), Float(pose.transform[1][1]), Float(pose.transform[2][1])),
            simd_make_float3(Float(pose.transform[0][2]), Float(pose.transform[1][2]), Float(pose.transform[2][2]))
        )
        
        // Intersect base ray with horizontal floor plane
        let hit = FloorAnchorEstimator.shared.intersectFloor(
            cameraPosition: camPosSimd,
            cameraRotation: rotMatrix,
            rayCamera: rayCam,
            rayConfidence: detection.confidence
        )
        
        let groundContact: Point2D
        let distanceM: Double
        
        if hit.isValid {
            groundContact = hit.worldPoint
            distanceM = hit.distanceMeters
        } else {
            // Fallback estimation using relative depth estimate if floor ray is out of bounds
            let defaultDist = 2.0
            distanceM = defaultDist
            let rayWorld = rotMatrix * rayCam
            let hitX = camX + distanceM * Double(rayWorld.x)
            let hitZ = camZ + distanceM * Double(rayWorld.z)
            groundContact = Point2D(x: hitX, z: hitZ)
        }
        
        // Category dimension prior (typical indoor furniture sizes)
        let dims = categoryPriorDimensions(category: detection.category, distance: distanceM, boxWidthNorm: bb[2])
        
        // 3D center position is elevated above ground contact by half height
        let posY = floorPlaneY + dims.height / 2.0
        let pos3D = Point3D(x: groundContact.x, y: posY, z: groundContact.z)
        
        // Uncertainty radius increases with distance and lower detection confidence
        let baseUncertainty = 0.15 // 15cm minimum
        let distanceUncertainty = (distanceM / 5.0) * 0.35 // grows with distance
        let confidencePenalty = (1.0 - detection.confidence) * 0.40
        let uncertainty = baseUncertainty + distanceUncertainty + confidencePenalty
        
        return PositionEstimate3D(
            position: pos3D,
            dimensions: dims,
            uncertaintyRadiusMeters: round(uncertainty * 100) / 100.0,
            groundContactPoint: groundContact,
            confidence: detection.confidence
        )
    }
    
    private func categoryPriorDimensions(
        category: FurnitureCategory,
        distance: Double,
        boxWidthNorm: Double
    ) -> Size3D {
        switch category {
        case .bed:
            return Size3D(width: 1.80, height: 0.90, depth: 2.00)
        case .sofa:
            return Size3D(width: 1.90, height: 0.85, depth: 0.90)
        case .chair:
            return Size3D(width: 0.65, height: 0.85, depth: 0.65)
        case .table:
            return Size3D(width: 1.20, height: 0.75, depth: 0.80)
        case .cabinet:
            return Size3D(width: 1.00, height: 1.20, depth: 0.50)
        case .desk:
            return Size3D(width: 1.30, height: 0.75, depth: 0.70)
        case .wardrobe:
            return Size3D(width: 1.20, height: 2.00, depth: 0.60)
        case .tvStand:
            return Size3D(width: 1.40, height: 0.50, depth: 0.45)
        case .door:
            return Size3D(width: 0.90, height: 2.10, depth: 0.10)
        case .window:
            return Size3D(width: 1.20, height: 1.20, depth: 0.15)
        case .unknown:
            return Size3D(width: 0.80, height: 0.80, depth: 0.80)
        }
    }
}
