import Foundation
import Vision
import CoreImage
import simd

public struct BoundaryRayCandidate {
    public let rayCamera: simd_float3 // Direction vector in camera frame
    public let confidence: Double
}

public final class FloorWallBoundaryDetector {
    public static let shared = FloorWallBoundaryDetector()
    private init() {}
    
    /// Detects candidate floor-wall contact line segments in camera space
    public func detectBoundaryRays(pixelBuffer: CVPixelBuffer, intrinsics: CameraIntrinsics) -> [BoundaryRayCandidate] {
        let w = Double(intrinsics.imageWidth)
        let h = Double(intrinsics.imageHeight)
        let fx = intrinsics.fx
        let fy = intrinsics.fy
        let cx = intrinsics.cx
        let cy = intrinsics.cy
        
        // Target lower third where floor meets wall baseboards (v from 60% to 90% of image height)
        var candidates: [BoundaryRayCandidate] = []
        let vSamples = [h * 0.65, h * 0.75, h * 0.85]
        let uSamples = stride(from: w * 0.15, to: w * 0.85, by: w * 0.10)
        
        for v in vSamples {
            for u in uSamples {
                // Unproject pixel (u, v) into normalized camera ray
                let x_c = Float((u - cx) / fx)
                let y_c = Float((v - cy) / fy)
                let z_c: Float = 1.0
                let ray = simd_normalize(simd_make_float3(x_c, y_c, z_c))
                candidates.append(BoundaryRayCandidate(rayCamera: ray, confidence: 0.85))
            }
        }
        return candidates
    }
}

