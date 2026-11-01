import Foundation
import simd
import CoreGraphics

public struct CalibrationRecord: Codable {
    public let fx: Double
    public let fy: Double
    public let cx: Double
    public let cy: Double
    public let imageWidth: Int
    public let imageHeight: Int
    public let distortionModel: String
    public let sensorOrientation: String
    public let coordinateConvention: String
    
    public init(
        fx: Double,
        fy: Double,
        cx: Double,
        cy: Double,
        imageWidth: Int,
        imageHeight: Int,
        distortionModel: String = "PINHOLE",
        sensorOrientation: String = "PORTRAIT"
    ) {
        self.fx = fx
        self.fy = fy
        self.cx = cx
        self.cy = cy
        self.imageWidth = imageWidth
        self.imageHeight = imageHeight
        self.distortionModel = distortionModel
        self.sensorOrientation = sensorOrientation
        self.coordinateConvention = "+Y is World-Up, Right-Handed, Meter metric units"
    }
}

public final class CameraCalibrationManager {
    public private(set) var activeCalibration: CalibrationRecord?
    
    public var currentIntrinsics: CameraIntrinsics {
        guard let calib = activeCalibration else {
            return CameraIntrinsics.defaultFallback()
        }
        return CameraIntrinsics(
            fx: calib.fx,
            fy: calib.fy,
            cx: calib.cx,
            cy: calib.cy,
            imageWidth: calib.imageWidth,
            imageHeight: calib.imageHeight
        )
    }
    
    public init() {}
    
    public func updateCalibration(intrinsics: simd_float3x3, resolution: CGSize) -> CalibrationRecord {
        // ARKit intrinsics format:
        // [ fx   0   cx ]
        // [  0  fy   cy ]
        // [  0   0    1 ]
        let fx = Double(intrinsics[0, 0])
        let fy = Double(intrinsics[1, 1])
        let cx = Double(intrinsics[2, 0])
        let cy = Double(intrinsics[2, 1])
        let width = Int(resolution.width)
        let height = Int(resolution.height)
        
        let record = CalibrationRecord(
            fx: fx,
            fy: fy,
            cx: cx,
            cy: cy,
            imageWidth: width,
            imageHeight: height
        )
        self.activeCalibration = record
        return record
    }
    
    public func exportCalibrationJSON() throws -> Data {
        guard let calib = activeCalibration else {
            // Default 1080p fallback
            let fallback = CalibrationRecord(fx: 1440.0, fy: 1440.0, cx: 540.0, cy: 960.0, imageWidth: 1080, imageHeight: 1920)
            return try JSONEncoder().encode(fallback)
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(calib)
    }
}

