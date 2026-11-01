import Foundation
import CoreML
import Vision

/// Manages loading, caching, warm-up, and fallback for local Core ML models
public final class LocalModelManager {
    public static let shared = LocalModelManager()
    
    public enum ModelStatus {
        case uninitialized
        case loading
        case ready(modelName: String, computeUnits: String)
        case fallbackVision(reason: String)
        case failed(error: String)
    }
    
    public private(set) var status: ModelStatus = .uninitialized
    public private(set) var isWarmedUp: Bool = false
    public private(set) var mlModel: MLModel?
    public private(set) var visionModel: VNCoreMLModel?
    
    private let modelQueue = DispatchQueue(label: "ai.vastu.capture.model-manager", qos: .userInitiated)
    
    public init() {}
    
    /// Initializes and warms up the segmentation model
    public func loadSegmentationModel(bundledModelName: String = "VastuFloorWallSegmenter") {
        modelQueue.sync {
            self.status = .loading
            
            // 1. Check if compiled Core ML model exists in main bundle
            let modelURL = Bundle.main.url(forResource: bundledModelName, withExtension: "mlmodelc")
                ?? Bundle.main.url(forResource: bundledModelName, withExtension: "mlpackage")
            
            if let modelURL = modelURL {
                do {
                    let config = MLModelConfiguration()
                    config.computeUnits = .all // Neural Engine + GPU + CPU
                    
                    let model = try MLModel(contentsOf: modelURL, configuration: config)
                    self.mlModel = model
                    
                    if let vnModel = try? VNCoreMLModel(for: model) {
                        self.visionModel = vnModel
                    }
                    
                    self.status = .ready(modelName: bundledModelName, computeUnits: "NeuralEngine+GPU+CPU")
                    self.warmUpModel()
                } catch {
                    self.status = .fallbackVision(reason: "Bundled model failed to load: \(error.localizedDescription)")
                }
            } else {
                // Graceful fallback to Vision Semantic Fallback Engine
                self.status = .fallbackVision(reason: "No compiled Core ML model bundled; using high-efficiency Vision heuristic fallback")
            }
        }
    }
    
    /// Pre-warms inference pipeline to eliminate first-frame latency spikes
    public func warmUpModel() {
        guard !isWarmedUp else { return }
        
        // Create 256x256 dummy pixel buffer
        var dummyBuffer: CVPixelBuffer?
        let attrs: [CFString: Any] = [
            kCVPixelBufferCGImageCompatibilityKey: true,
            kCVPixelBufferCGBitmapContextCompatibilityKey: true
        ]
        let status = CVPixelBufferCreate(
            kCFAllocatorDefault,
            256,
            256,
            kCVPixelFormatType_32BGRA,
            attrs as CFDictionary,
            &dummyBuffer
        )
        
        guard status == kCVReturnSuccess, let buffer = dummyBuffer else {
            isWarmedUp = true
            return
        }
        
        CVPixelBufferLockBaseAddress(buffer, [])
        if let base = CVPixelBufferGetBaseAddress(buffer) {
            memset(base, 128, CVPixelBufferGetDataSize(buffer))
        }
        CVPixelBufferUnlockBaseAddress(buffer, [])
        
        // Execute warm-up dummy pass
        _ = FloorWallSegmentationEngine.shared.segmentSync(pixelBuffer: buffer, timestamp: 0.0)
        self.isWarmedUp = true
    }
}

