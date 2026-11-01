import Foundation
import simd

public struct FloorHitResult {
    public let worldPoint: Point2D
    public let distanceMeters: Double
    public let confidence: Double
    public let isValid: Bool
}

/// Estimates and tracks the room floor plane (Y-up metric coordinate system) and performs ray intersections
public final class FloorAnchorEstimator {
    public static let shared = FloorAnchorEstimator()
    
    // Default world floor plane height (Y = 0.0)
    public private(set) var floorPlaneY: Double = 0.0
    public private(set) var isPlaneCalibrated: Bool = false
    
    private var observedFloorHeights: [Double] = []
    private let minRayDistance: Double = 0.25 // 25 cm minimum
    private let maxRayDistance: Double = 7.50 // 7.5 meters maximum indoor reach
    
    public init() {}
    
    public func reset() {
        floorPlaneY = 0.0
        isPlaneCalibrated = false
        observedFloorHeights.removeAll()
    }
    
    /// Calibrates the floor plane height from an external ARPlaneAnchor or lowest stable contact points
    public func updateFloorPlane(heightY: Double, confidence: Double = 0.9) {
        guard confidence > 0.5 else { return }
        observedFloorHeights.append(heightY)
        if observedFloorHeights.count > 30 {
            observedFloorHeights.removeFirst()
        }
        
        // Running median filter for stability
        let sorted = observedFloorHeights.sorted()
        let median = sorted[sorted.count / 2]
        self.floorPlaneY = median
        self.isPlaneCalibrated = true
    }
    
    /// Intersects a camera-space boundary ray with the calibrated horizontal floor plane
    public func intersectFloor(
        cameraPosition: simd_float3,
        cameraRotation: simd_float3x3,
        rayCamera: simd_float3,
        rayConfidence: Double
    ) -> FloorHitResult {
        let camY = Double(cameraPosition.y)
        let rayWorld = cameraRotation * rayCamera
        let ry = Double(rayWorld.y)
        
        // Camera must be above floor (camY > floorPlaneY) and ray must point downward (ry < -0.05)
        guard camY > floorPlaneY + 0.10, ry < -0.05 else {
            return FloorHitResult(worldPoint: Point2D(x: 0, z: 0), distanceMeters: 0, confidence: 0, isValid: false)
        }
        
        // t = (Y_floor - C_y) / R_y
        let t = (floorPlaneY - camY) / ry
        
        guard t >= minRayDistance && t <= maxRayDistance else {
            return FloorHitResult(worldPoint: Point2D(x: 0, z: 0), distanceMeters: t, confidence: 0, isValid: false)
        }
        
        let hitX = Double(cameraPosition.x) + t * Double(rayWorld.x)
        let hitZ = Double(cameraPosition.z) + t * Double(rayWorld.z)
        
        // Confidence decays with distance (higher distance = greater angular unprojection error)
        let distanceAttenuation = max(0.2, 1.0 - (t / maxRayDistance) * 0.6)
        let hitConfidence = rayConfidence * distanceAttenuation
        
        return FloorHitResult(
            worldPoint: Point2D(x: hitX, z: hitZ),
            distanceMeters: t,
            confidence: hitConfidence,
            isValid: true
        )
    }
}

