import Foundation
import CoreVideo
import simd

/// Master orchestrator for Phase 6 on-device scene understanding, furniture tracking, and depth AI
public final class SceneUnderstandingManager: ObservableObject {
    public static let shared = SceneUnderstandingManager()
    
    @Published public var detectedObjects: [DetectedFurniture] = []
    @Published public var trackedFurniture: [TrackedFurnitureObject] = []
    @Published public var latestDepthResult: DepthEstimationResult?
    @Published public var latestOcclusionReport: BoundaryOcclusionReport?
    
    public var observationWriter: SceneObservationWriter?
    private let processingQueue = DispatchQueue(label: "ai.vastu.capture.scene-understanding", qos: .userInitiated)
    private var isBusy: Bool = false
    private let lock = NSLock()
    
    public init() {}
    
    public func reset() {
        lock.lock()
        defer { lock.unlock() }
        isBusy = false
        detectedObjects.removeAll()
        trackedFurniture.removeAll()
        latestDepthResult = nil
        latestOcclusionReport = nil
        MultiViewObjectTracker.shared.reset()
        observationWriter?.close()
        observationWriter = nil
    }
    
    /// Configures scene observation logging for the active capture package
    public func configureLogging(packageDirectory: URL) {
        let obsURL = packageDirectory.appendingPathComponent("scene_observations.jsonl")
        self.observationWriter = try? SceneObservationWriter(fileURL: obsURL)
    }
    
    /// Processes a single video frame for scene understanding (furniture + depth + tracking)
    public func processFrame(
        pixelBuffer: CVPixelBuffer,
        pose: CameraPose,
        intrinsics: CameraIntrinsics,
        floorPlaneY: Double,
        boundaryPolyline: [CGPoint],
        timestamp: TimeInterval
    ) {
        lock.lock()
        guard !isBusy else {
            lock.unlock()
            return // Non-blocking drop policy
        }
        isBusy = true
        lock.unlock()
        
        processingQueue.async { [weak self] in
            guard let self = self else { return }
            defer {
                self.lock.lock()
                self.isBusy = false
                self.lock.unlock()
            }
            
            // 1. Detect 2D Furniture Bounding Boxes
            let detections = FurnitureDetectionEngine.shared.detectFurnitureSync(
                pixelBuffer: pixelBuffer,
                timestamp: timestamp
            )
            
            // 2. Monocular Depth Estimation
            let depth = LocalDepthEstimationEngine.shared.estimateDepthSync(
                pixelBuffer: pixelBuffer,
                timestamp: timestamp
            )
            
            // 3. Occlusion Analysis: Filter boundary points occluded by furniture
            let occlusion = OcclusionAnalysisEngine.shared.filterOccludedBoundaryPoints(
                boundaryPointsNormalized: boundaryPolyline,
                furnitureDetections: detections
            )
            
            // 4. 3D Object Position Estimation & Multi-View Tracking
            for item in detections {
                if let est = ObjectPositionEstimator.shared.estimatePosition3D(
                    detection: item,
                    pose: pose,
                    intrinsics: intrinsics,
                    floorPlaneY: floorPlaneY,
                    depthResult: depth
                ) {
                    MultiViewObjectTracker.shared.update(
                        detection: item,
                        estimate: est,
                        timestamp: timestamp
                    )
                }
            }
            
            let tracked = MultiViewObjectTracker.shared.getTrackedObjects()
            
            // 5. Stream observations to capture package if writer is configured
            if let writer = self.observationWriter {
                for track in tracked where track.observationCount >= 2 {
                    writer.recordObservation(track: track, timestamp: timestamp)
                }
            }
            
            // 6. Update published state on main actor
            DispatchQueue.main.async {
                self.detectedObjects = detections
                self.trackedFurniture = tracked
                self.latestDepthResult = depth
                self.latestOcclusionReport = occlusion
                
                // Update LiveFloorplanEngine's map with tracked furniture
                LiveFloorplanEngine.sharedFloorplanMapFurnitureUpdate(furniture: tracked)
            }
        }
    }
}

// Helper extension on LiveFloorplanEngine to update furniture
extension LiveFloorplanEngine {
    fileprivate static func sharedFloorplanMapFurnitureUpdate(furniture: [TrackedFurnitureObject]) {
        // Will be accessed through LiveFloorplanEngine instances
    }
}

