import Foundation
import simd

public struct CameraPose: Codable {
    public let frameId: String
    public let timestampNs: Int64
    public let transform: [[Double]] // 4x4 transformation matrix
    public let position: [Double]     // [X, Y, Z]
    public let trackingState: String
    
    public init(frameId: String, timestampNs: Int64, transformMatrix: simd_float4x4, trackingState: String) {
        self.frameId = frameId
        self.timestampNs = timestampNs
        self.transform = [
            [Double(transformMatrix.columns.0.x), Double(transformMatrix.columns.1.x), Double(transformMatrix.columns.2.x), Double(transformMatrix.columns.3.x)],
            [Double(transformMatrix.columns.0.y), Double(transformMatrix.columns.1.y), Double(transformMatrix.columns.2.y), Double(transformMatrix.columns.3.y)],
            [Double(transformMatrix.columns.0.z), Double(transformMatrix.columns.1.z), Double(transformMatrix.columns.2.z), Double(transformMatrix.columns.3.z)],
            [Double(transformMatrix.columns.0.w), Double(transformMatrix.columns.1.w), Double(transformMatrix.columns.2.w), Double(transformMatrix.columns.3.w)]
        ]
        self.position = [
            Double(transformMatrix.columns.3.x),
            Double(transformMatrix.columns.3.y),
            Double(transformMatrix.columns.3.z)
        ]
        self.trackingState = trackingState
    }
}

public struct CameraIntrinsics: Codable {
    public let calibrationId: String
    public let fx: Double
    public let fy: Double
    public let cx: Double
    public let cy: Double
    public let imageWidth: Int
    public let imageHeight: Int
    public let distortionModel: String
    
    public init(fx: Double, fy: Double, cx: Double, cy: Double, imageWidth: Int, imageHeight: Int) {
        self.calibrationId = "calib_\(imageWidth)x\(imageHeight)"
        self.fx = fx
        self.fy = fy
        self.cx = cx
        self.cy = cy
        self.imageWidth = imageWidth
        self.imageHeight = imageHeight
        self.distortionModel = "PINHOLE"
    }
    
    public static func defaultFallback(width: Int = 1920, height: Int = 1440) -> CameraIntrinsics {
        return CameraIntrinsics(
            fx: 1420.0,
            fy: 1420.0,
            cx: Double(width) / 2.0,
            cy: Double(height) / 2.0,
            imageWidth: width,
            imageHeight: height
        )
    }
}

public struct CaptureQualityAudit: Codable {
    public let keyframeCount: Int
    public let durationSeconds: Double
    public let meanSharpness: Double
    public let meanExposure: Double
    public let trackingStabilityPct: Double
    public let translationalBaselineM: Double
    public let angularCoverageDeg: Double
    public let wallBoundaryCoveragePct: Double
    public let overallScore: Double
    public let isAcceptableForReconstruction: Bool
    public let recommendationPrompt: String
    
    public init(
        keyframeCount: Int,
        durationSeconds: Double,
        meanSharpness: Double,
        meanExposure: Double,
        trackingStabilityPct: Double,
        translationalBaselineM: Double,
        angularCoverageDeg: Double,
        wallBoundaryCoveragePct: Double
    ) {
        self.keyframeCount = keyframeCount
        self.durationSeconds = durationSeconds
        self.meanSharpness = meanSharpness
        self.meanExposure = meanExposure
        self.trackingStabilityPct = trackingStabilityPct
        self.translationalBaselineM = translationalBaselineM
        self.angularCoverageDeg = angularCoverageDeg
        self.wallBoundaryCoveragePct = wallBoundaryCoveragePct
        
        let score = (
            min(1.0, Double(keyframeCount) / 25.0) * 0.25 +
            min(1.0, translationalBaselineM / 1.0) * 0.35 +
            (trackingStabilityPct / 100.0) * 0.20 +
            (wallBoundaryCoveragePct / 100.0) * 0.20
        )
        self.overallScore = round(score * 1000) / 1000.0
        self.isAcceptableForReconstruction = (self.overallScore >= 0.90) && keyframeCount >= 12 && translationalBaselineM >= 0.40 && trackingStabilityPct >= 75.0
        
        if self.overallScore < 0.90 {
            self.recommendationPrompt = "Capture score (\(Int(self.overallScore * 100))%) is below the mandatory 90% gate (IOS-008). Rescan required before submission."
        } else if translationalBaselineM < 0.40 {
            self.recommendationPrompt = "Move body laterally across the room floor to establish a triangulation baseline."
        } else if wallBoundaryCoveragePct < 60.0 {
            self.recommendationPrompt = "Walk along the unobserved walls to complete room enclosure."
        } else if trackingStabilityPct < 75.0 {
            self.recommendationPrompt = "Avoid rapid whipping; walk slower at ~0.3 m/s."
        } else {
            self.recommendationPrompt = "Scan meets architectural quality criteria."
        }
    }
}

public struct Point2D: Codable, Equatable, Hashable {
    public let x: Double
    public let z: Double
    
    public init(x: Double, z: Double) {
        self.x = x
        self.z = z
    }
}

public struct WallCandidate2D: Codable, Identifiable {
    public let id: String
    public let start: Point2D
    public let end: Point2D
    public let confidence: Double
    
    public init(id: String = UUID().uuidString, start: Point2D, end: Point2D, confidence: Double) {
        self.id = id
        self.start = start
        self.end = end
        self.confidence = confidence
    }
}

public enum WallObservationType: String, Codable {
    case observed = "OBSERVED"
    case estimated = "ESTIMATED"
    case missing = "MISSING"
}

public struct WallSegment2D: Codable, Identifiable, Equatable {
    public let id: String
    public let start: Point2D
    public let end: Point2D
    public let confidence: Double
    public let type: WallObservationType
    public let lengthMeters: Double
    
    public init(
        id: String = UUID().uuidString,
        start: Point2D,
        end: Point2D,
        confidence: Double = 0.85,
        type: WallObservationType = .observed
    ) {
        self.id = id
        self.start = start
        self.end = end
        self.confidence = confidence
        self.type = type
        let dx = end.x - start.x
        let dz = end.z - start.z
        self.lengthMeters = sqrt(dx * dx + dz * dz)
    }
}

public struct RoomCorner2D: Codable, Identifiable, Equatable {
    public let id: String
    public let position: Point2D
    public let angleDegrees: Double
    public let confidence: Double
    public let isDirectlyObserved: Bool
    
    public init(
        id: String = UUID().uuidString,
        position: Point2D,
        angleDegrees: Double,
        confidence: Double,
        isDirectlyObserved: Bool = true
    ) {
        self.id = id
        self.position = position
        self.angleDegrees = angleDegrees
        self.confidence = confidence
        self.isDirectlyObserved = isDirectlyObserved
    }
}

public struct CoverageReport: Codable {
    public let perimeterCoveragePct: Double
    public let angularCoveragePct: Double
    public let totalEstimatedPerimeterM: Double
    public let observedPerimeterM: Double
    public let missingSectors: [Int] // 0 to 15 radial sectors
    public let isSufficient: Bool
    
    public init(
        perimeterCoveragePct: Double,
        angularCoveragePct: Double,
        totalEstimatedPerimeterM: Double,
        observedPerimeterM: Double,
        missingSectors: [Int],
        isSufficient: Bool
    ) {
        self.perimeterCoveragePct = perimeterCoveragePct
        self.angularCoveragePct = angularCoveragePct
        self.totalEstimatedPerimeterM = totalEstimatedPerimeterM
        self.observedPerimeterM = observedPerimeterM
        self.missingSectors = missingSectors
        self.isSufficient = isSufficient
    }
}

public struct ParallaxMetric: Codable {
    public let translationBaselineM: Double
    public let pathLengthM: Double
    public let pathBoundingAreaM2: Double
    public let trr: Double // Translation-to-Rotation Ratio (m/rad)
    public let isRotationOnly: Bool
    public let isSufficient: Bool
    
    public init(
        translationBaselineM: Double,
        pathLengthM: Double,
        pathBoundingAreaM2: Double,
        trr: Double,
        isRotationOnly: Bool,
        isSufficient: Bool
    ) {
        self.translationBaselineM = translationBaselineM
        self.pathLengthM = pathLengthM
        self.pathBoundingAreaM2 = pathBoundingAreaM2
        self.trr = trr
        self.isRotationOnly = isRotationOnly
        self.isSufficient = isSufficient
    }
}

public struct Point3D: Codable, Equatable, Hashable {
    public let x: Double
    public let y: Double
    public let z: Double
    
    public init(x: Double, y: Double, z: Double) {
        self.x = x
        self.y = y
        self.z = z
    }
}

public struct Size3D: Codable, Equatable {
    public let width: Double  // X extent
    public let height: Double // Y extent
    public let depth: Double  // Z extent
    
    public init(width: Double, height: Double, depth: Double) {
        self.width = width
        self.height = height
        self.depth = depth
    }
}

public enum FurnitureCategory: String, Codable, CaseIterable {
    case bed = "bed"
    case sofa = "sofa"
    case chair = "chair"
    case table = "table"
    case cabinet = "cabinet"
    case desk = "desk"
    case wardrobe = "wardrobe"
    case tvStand = "tv_stand"
    case door = "door"
    case window = "window"
    case unknown = "unknown"
    
    public var displayName: String {
        switch self {
        case .bed: return "Bed"
        case .sofa: return "Sofa"
        case .chair: return "Chair"
        case .table: return "Table"
        case .cabinet: return "Cabinet"
        case .desk: return "Desk"
        case .wardrobe: return "Wardrobe"
        case .tvStand: return "TV Stand"
        case .door: return "Door"
        case .window: return "Window"
        case .unknown: return "Object"
        }
    }
}

public struct DetectedFurniture: Codable, Identifiable, Equatable {
    public let id: String
    public let category: FurnitureCategory
    public let label: String
    public let confidence: Double // 0.0 to 1.0
    public let boundingBox: [Double] // [xMin, yMin, width, height] normalized (0.0 to 1.0)
    public let timestamp: TimeInterval
    
    public init(
        id: String = UUID().uuidString,
        category: FurnitureCategory,
        label: String,
        confidence: Double,
        boundingBox: [Double],
        timestamp: TimeInterval
    ) {
        self.id = id
        self.category = category
        self.label = label
        self.confidence = confidence
        self.boundingBox = boundingBox
        self.timestamp = timestamp
    }
}

public struct PositionEstimate3D: Codable, Equatable {
    public let position: Point3D
    public let dimensions: Size3D
    public let uncertaintyRadiusMeters: Double
    public let groundContactPoint: Point2D
    public let confidence: Double
    
    public init(
        position: Point3D,
        dimensions: Size3D,
        uncertaintyRadiusMeters: Double,
        groundContactPoint: Point2D,
        confidence: Double
    ) {
        self.position = position
        self.dimensions = dimensions
        self.uncertaintyRadiusMeters = uncertaintyRadiusMeters
        self.groundContactPoint = groundContactPoint
        self.confidence = confidence
    }
}

public struct TrackedFurnitureObject: Codable, Identifiable, Equatable {
    public let id: String
    public let category: FurnitureCategory
    public let label: String
    public var confidence: Double
    public var position3D: Point3D
    public var dimensions: Size3D
    public var uncertaintyMeters: Double
    public var groundContact: Point2D
    public var observationCount: Int
    public var firstSeenTimestamp: TimeInterval
    public var lastSeenTimestamp: TimeInterval
    public var isStable: Bool
    
    public init(
        id: String = UUID().uuidString,
        category: FurnitureCategory,
        label: String,
        confidence: Double,
        position3D: Point3D,
        dimensions: Size3D,
        uncertaintyMeters: Double,
        groundContact: Point2D,
        observationCount: Int = 1,
        firstSeenTimestamp: TimeInterval,
        lastSeenTimestamp: TimeInterval,
        isStable: Bool = false
    ) {
        self.id = id
        self.category = category
        self.label = label
        self.confidence = confidence
        self.position3D = position3D
        self.dimensions = dimensions
        self.uncertaintyMeters = uncertaintyMeters
        self.groundContact = groundContact
        self.observationCount = observationCount
        self.firstSeenTimestamp = firstSeenTimestamp
        self.lastSeenTimestamp = lastSeenTimestamp
        self.isStable = isStable
    }
}

public struct DepthEstimationResult {
    public let width: Int
    public let height: Int
    public let relativeDepthMap: [Float] // 0.0 (near) to 1.0 (far)
    public let confidenceMap: [Float]    // 0.0 to 1.0
    public let estimatedMinDistanceMeters: Double
    public let estimatedMaxDistanceMeters: Double
    public let isMetricCalibrated: Bool
    public let inferenceLatencyMs: Double
    public let timestamp: TimeInterval
    
    public init(
        width: Int,
        height: Int,
        relativeDepthMap: [Float],
        confidenceMap: [Float],
        estimatedMinDistanceMeters: Double = 0.3,
        estimatedMaxDistanceMeters: Double = 6.0,
        isMetricCalibrated: Bool = false,
        inferenceLatencyMs: Double,
        timestamp: TimeInterval
    ) {
        self.width = width
        self.height = height
        self.relativeDepthMap = relativeDepthMap
        self.confidenceMap = confidenceMap
        self.estimatedMinDistanceMeters = estimatedMinDistanceMeters
        self.estimatedMaxDistanceMeters = estimatedMaxDistanceMeters
        self.isMetricCalibrated = isMetricCalibrated
        self.inferenceLatencyMs = inferenceLatencyMs
        self.timestamp = timestamp
    }
    
    public var meanRelativeDepth: Float {
        guard !relativeDepthMap.isEmpty else { return 0.5 }
        return relativeDepthMap.reduce(0, +) / Float(relativeDepthMap.count)
    }
    
    public var meanConfidence: Float {
        guard !confidenceMap.isEmpty else { return 0.8 }
        return confidenceMap.reduce(0, +) / Float(confidenceMap.count)
    }
    
    public func sampleDepth(u: Double, v: Double) -> Float {
        guard width > 0, height > 0, !relativeDepthMap.isEmpty else { return 0.5 }
        let clampedU = max(0.0, min(1.0, u))
        let clampedV = max(0.0, min(1.0, v))
        let x = min(width - 1, Int(clampedU * Double(width)))
        let y = min(height - 1, Int(clampedV * Double(height)))
        let index = y * width + x
        guard index >= 0, index < relativeDepthMap.count else { return 0.5 }
        return relativeDepthMap[index]
    }
}

public struct LiveFloorplanMap: Codable {
    public var boundaryPoints: [Point2D] = []
    public var detectedWalls: [WallCandidate2D] = []
    public var observedWalls: [WallSegment2D] = []
    public var estimatedWalls: [WallSegment2D] = []
    public var corners: [RoomCorner2D] = []
    public var furnitureObjects: [TrackedFurnitureObject] = []
    public var cameraTrail: [Point2D] = []
    public var currentCameraHeadingDeg: Double = 0.0
    public var coveragePercentage: Double = 0.0
    public var missingSectors: [Int] = []
    
    public init() {}
}

