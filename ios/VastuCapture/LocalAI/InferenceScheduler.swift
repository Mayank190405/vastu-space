import Foundation
import CoreVideo
import simd

public protocol InferenceSchedulerDelegate: AnyObject {
    func schedulerDidProduceInference(
        segmentation: SegmentationResult,
        boundaries: BoundaryExtractionResult,
        quality: ComprehensiveQualityAssessment
    )
    func schedulerDidDropFrame()
}

/// Asynchronous inference scheduler with backpressure control and thermal throttling
public final class InferenceScheduler {
    public static let shared = InferenceScheduler()
    
    public weak var delegate: InferenceSchedulerDelegate?
    
    private let inferenceQueue = DispatchQueue(label: "ai.vastu.capture.inference-queue", qos: .userInitiated)
    private var isBusy: Bool = false
    private let lock = NSLock()
    
    private var lastInferenceTimestamp: TimeInterval = 0.0
    private var currentIntervalSec: TimeInterval = 0.10 // 10 Hz nominal
    
    // Diagnostics metrics
    public private(set) var totalFramesSubmitted: Int = 0
    public private(set) var totalFramesProcessed: Int = 0
    public private(set) var totalFramesDropped: Int = 0
    
    public init() {
        updateThermalPolicy()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(thermalStateDidChange),
            name: ProcessInfo.thermalStateDidChangeNotification,
            object: nil
        )
    }
    
    deinit {
        NotificationCenter.default.removeObserver(self)
    }
    
    @objc private func thermalStateDidChange() {
        updateThermalPolicy()
    }
    
    public func updateThermalPolicy() {
        let thermalState = ProcessInfo.processInfo.thermalState
        switch thermalState {
        case .nominal:
            currentIntervalSec = 0.10 // 10 Hz
        case .fair:
            currentIntervalSec = 0.125 // 8 Hz
        case .serious:
            currentIntervalSec = 0.20 // 5 Hz
        case .critical:
            currentIntervalSec = 0.50 // 2 Hz
        @unknown default:
            currentIntervalSec = 0.10
        }
    }
    
    /// Override interval for testing or battery saver
    public func setTargetFrequency(hz: Double) {
        guard hz > 0.0 else { return }
        currentIntervalSec = 1.0 / hz
    }
    
    /// Submits an AR frame for asynchronous AI analysis without blocking tracking
    public func submitFrame(
        pixelBuffer: CVPixelBuffer,
        timestamp: TimeInterval,
        intrinsics: CameraIntrinsics,
        cameraPose: CameraPose? = nil
    ) {
        lock.lock()
        totalFramesSubmitted += 1
        
        // 1. Frequency throttling check
        let elapsed = timestamp - lastInferenceTimestamp
        if elapsed < currentIntervalSec {
            totalFramesDropped += 1
            lock.unlock()
            delegate?.schedulerDidDropFrame()
            return
        }
        
        // 2. Concurrency drop policy (never queue frames)
        if isBusy {
            totalFramesDropped += 1
            lock.unlock()
            delegate?.schedulerDidDropFrame()
            return
        }
        
        isBusy = true
        lastInferenceTimestamp = timestamp
        lock.unlock()
        
        inferenceQueue.async { [weak self] in
            guard let self = self else { return }
            
            // Execute AI pipeline
            let segmentation = FloorWallSegmentationEngine.shared.segmentSync(
                pixelBuffer: pixelBuffer,
                timestamp: timestamp
            )
            
            let boundaries = BoundaryDetectionEngine.shared.extractBoundaries(
                segmentation: segmentation,
                intrinsics: intrinsics
            )
            
            let quality = ImageQualityAnalyzer.shared.analyze(
                pixelBuffer: pixelBuffer
            )
            
            // Phase 6: On-device scene understanding & furniture tracking
            let poseToUse = cameraPose ?? CameraPose(
                frameId: "live",
                timestampNs: Int64(timestamp * 1_000_000_000),
                transformMatrix: matrix_identity_float4x4,
                trackingState: "NORMAL"
            )
            SceneUnderstandingManager.shared.processFrame(
                pixelBuffer: pixelBuffer,
                pose: poseToUse,
                intrinsics: intrinsics,
                floorPlaneY: FloorAnchorEstimator.shared.floorPlaneY,
                boundaryPolyline: boundaries.polylineNormalized,
                timestamp: timestamp
            )
            
            self.lock.lock()
            self.totalFramesProcessed += 1
            self.isBusy = false
            self.lock.unlock()
            
            // Update diagnostics
            LocalMLDiagnostics.shared.recordInference(
                segmentationTimeMs: segmentation.inferenceDurationMs,
                qualityTimeMs: quality.analysisDurationMs
            )
            
            self.delegate?.schedulerDidProduceInference(
                segmentation: segmentation,
                boundaries: boundaries,
                quality: quality
            )
        }
    }
    
    public func reset() {
        lock.lock()
        defer { lock.unlock() }
        isBusy = false
        lastInferenceTimestamp = 0.0
        totalFramesSubmitted = 0
        totalFramesProcessed = 0
        totalFramesDropped = 0
    }
}

