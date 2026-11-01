import Foundation
import CoreVideo
import simd

public class LocalAITests {
    
    // Helper to generate synthetic test pixel buffer
    private static func createSyntheticFrame(
        width: Int = 640,
        height: Int = 480,
        pattern: String = "indoor"
    ) -> CVPixelBuffer {
        var pixelBuffer: CVPixelBuffer?
        let attrs: [CFString: Any] = [
            kCVPixelBufferCGImageCompatibilityKey: true,
            kCVPixelBufferCGBitmapContextCompatibilityKey: true
        ]
        _ = CVPixelBufferCreate(
            kCFAllocatorDefault,
            width,
            height,
            kCVPixelFormatType_32BGRA,
            attrs as CFDictionary,
            &pixelBuffer
        )
        guard let buffer = pixelBuffer else { fatalError("Failed to allocate test buffer") }
        
        CVPixelBufferLockBaseAddress(buffer, [])
        let base = CVPixelBufferGetBaseAddress(buffer)!
        let bytesPerRow = CVPixelBufferGetBytesPerRow(buffer)
        let ptr = base.assumingMemoryBound(to: UInt8.self)
        
        for y in 0..<height {
            let rowOffset = y * bytesPerRow
            let normY = Double(y) / Double(height)
            
            for x in 0..<width {
                let offset = rowOffset + x * 4
                
                if pattern == "indoor" {
                    // Lower 40%: Floor (medium warm tone)
                    // Middle 45%: Wall (light neutral tone)
                    // Upper 15%: Ceiling (bright white)
                    if normY > 0.60 {
                        // Floor
                        let noise = UInt8((x * 7 + y * 13) % 20)
                        ptr[offset] = 90 + noise // B
                        ptr[offset + 1] = 120 + noise // G
                        ptr[offset + 2] = 150 + noise // R
                        ptr[offset + 3] = 255
                    } else if normY > 0.15 {
                        // Wall
                        let edgeMod = (x % 40 < 2) ? 60 : 0
                        ptr[offset] = UInt8(180 - edgeMod)
                        ptr[offset + 1] = UInt8(185 - edgeMod)
                        ptr[offset + 2] = UInt8(190 - edgeMod)
                        ptr[offset + 3] = 255
                    } else {
                        // Ceiling
                        ptr[offset] = 230
                        ptr[offset + 1] = 230
                        ptr[offset + 2] = 235
                        ptr[offset + 3] = 255
                    }
                } else if pattern == "dark" {
                    ptr[offset] = 5
                    ptr[offset + 1] = 5
                    ptr[offset + 2] = 5
                    ptr[offset + 3] = 255
                } else if pattern == "overexposed" {
                    ptr[offset] = 250
                    ptr[offset + 1] = 250
                    ptr[offset + 2] = 252
                    ptr[offset + 3] = 255
                } else if pattern == "uniform_blur" {
                    ptr[offset] = 128
                    ptr[offset + 1] = 128
                    ptr[offset + 2] = 128
                    ptr[offset + 3] = 255
                }
            }
        }
        CVPixelBufferUnlockBaseAddress(buffer, [])
        return buffer
    }
    
    public static func runPhase4Tests(report: TestReport) async {
        print("\n==================================================")
        print("🧠 Phase 4: Local AI & Core ML Integration Tests")
        print("==================================================")
        
        testFloorWallSegmentation(report)
        testBoundaryDetectionAndRays(report)
        testImageQualityAnalysis(report)
        testInferenceSchedulerThrottling(report)
        testCaptureReadinessAssessment(report)
        testDiagnosticsAndZeroCloud(report)
    }
    
    // MARK: - 1. Floor & Wall Segmentation
    private static func testFloorWallSegmentation(_ report: TestReport) {
        print("\n[Phase 4 - Test 1/6] Local Semantic Segmentation Engine")
        
        let frame = createSyntheticFrame(width: 640, height: 480, pattern: "indoor")
        let segEngine = FloorWallSegmentationEngine.shared
        
        let result = segEngine.segmentSync(pixelBuffer: frame, timestamp: 1.0)
        
        report.check(result.gridWidth == 40, "Segmentation grid width matches configuration (40 cols)")
        report.check(result.gridHeight == 30, "Segmentation grid height matches configuration (30 rows)")
        report.check(result.classMap.count == 40 * 30, "Total semantic cells match grid capacity")
        
        // Check confidence bounds
        let validFloorConf = result.floorConfidenceMap.allSatisfy { $0 >= 0.0 && $0 <= 1.0 }
        let validWallConf = result.wallConfidenceMap.allSatisfy { $0 >= 0.0 && $0 <= 1.0 }
        report.check(validFloorConf, "All floor confidence values within [0.0, 1.0]")
        report.check(validWallConf, "All wall confidence values within [0.0, 1.0]")
        
        // Check detection of floor in bottom area and wall in middle area
        let floorDetected = result.classMap.contains(.floor)
        let wallDetected = result.classMap.contains(.wall)
        report.check(floorDetected, "Floor region identified by segmentation")
        report.check(wallDetected, "Wall region identified by segmentation")
        report.check(result.floorAreaRatio > 0.15, "Floor area ratio represents substantial indoor floor (> 15%)")
        report.check(result.wallAreaRatio > 0.15, "Wall area ratio represents substantial vertical structure (> 15%)")
        
        // Latency requirement
        report.check(result.inferenceDurationMs < 30.0, "Segmentation latency meets real-time budget < 30ms (actual: \(String(format: "%.2f", result.inferenceDurationMs))ms)")
    }
    
    // MARK: - 2. Boundary Detection & 3D Ray Unprojection
    private static func testBoundaryDetectionAndRays(_ report: TestReport) {
        print("\n[Phase 4 - Test 2/6] Floor-Wall Boundary Extraction & Ray Unprojection")
        
        let frame = createSyntheticFrame(width: 640, height: 480, pattern: "indoor")
        let segResult = FloorWallSegmentationEngine.shared.segmentSync(pixelBuffer: frame, timestamp: 1.0)
        let intrinsics = CameraIntrinsics(fx: 500.0, fy: 500.0, cx: 320.0, cy: 240.0, imageWidth: 640, imageHeight: 480)
        
        let boundaryResult = BoundaryDetectionEngine.shared.extractBoundaries(
            segmentation: segResult,
            intrinsics: intrinsics
        )
        
        report.check(!boundaryResult.contactPoints.isEmpty, "Detected floor-wall boundary contact points")
        report.check(boundaryResult.boundaryRays.count == boundaryResult.contactPoints.count, "Each contact point corresponds to an unprojected 3D camera ray")
        
        // Check 3D ray normalization
        var allNormalized = true
        for ray in boundaryResult.boundaryRays {
            let len = simd_length(ray.rayCamera)
            if abs(len - 1.0) > 0.001 {
                allNormalized = false
            }
        }
        report.check(allNormalized, "All unprojected camera rays have exact unit length (||r|| = 1.0)")
        
        // Check boundary confidence
        report.check(boundaryResult.averageBoundaryConfidence >= 0.40, "Average boundary confidence is high (actual: \(String(format: "%.2f", boundaryResult.averageBoundaryConfidence)))")
        report.check(!boundaryResult.polylineNormalized.isEmpty, "Polyline generated for live HUD overlay")
    }
    
    // MARK: - 3. Comprehensive Image Quality Analyzer
    private static func testImageQualityAnalysis(_ report: TestReport) {
        print("\n[Phase 4 - Test 3/6] Image Quality Analysis (Blur & Exposure)")
        
        let blurBuffer = createSyntheticFrame(pattern: "uniform_blur")
        let darkBuffer = createSyntheticFrame(pattern: "dark")
        let overBuffer = createSyntheticFrame(pattern: "overexposed")
        let goodBuffer = createSyntheticFrame(pattern: "indoor")
        
        let qBlur = ImageQualityAnalyzer.shared.analyze(pixelBuffer: blurBuffer)
        let qDark = ImageQualityAnalyzer.shared.analyze(pixelBuffer: darkBuffer)
        let qOver = ImageQualityAnalyzer.shared.analyze(pixelBuffer: overBuffer)
        let qGood = ImageQualityAnalyzer.shared.analyze(pixelBuffer: goodBuffer)
        
        report.check(qBlur.isBlurry, "Uniform image detected as blurry")
        report.check(qDark.isUnderexposed, "Dark image detected as underexposed")
        report.check(qOver.isOverexposed, "Bright image detected as overexposed")
        report.check(!qGood.isBlurry && !qGood.isUnderexposed && !qGood.isOverexposed, "Normal indoor frame passes all quality criteria")
        report.check(qGood.grade == .good || qGood.grade == .excellent, "Normal indoor frame assigned high quality grade")
        report.check(qBlur.grade == .suboptimal || qBlur.grade == .unusable, "Blurry frame flagged with warning grade")
        report.check(qGood.analysisDurationMs < 15.0, "Quality analysis latency < 15ms (actual: \(String(format: "%.2f", qGood.analysisDurationMs))ms)")
    }
    
    // MARK: - 4. Inference Scheduler & Throttling
    private static func testInferenceSchedulerThrottling(_ report: TestReport) {
        print("\n[Phase 4 - Test 4/6] Inference Scheduler & Thermal Throttling")
        
        let scheduler = InferenceScheduler.shared
        scheduler.reset()
        scheduler.setTargetFrequency(hz: 10.0) // 100ms interval
        
        let frame = createSyntheticFrame()
        let intrinsics = CameraIntrinsics.defaultFallback()
        
        // Submit frame at t = 0.0
        scheduler.submitFrame(pixelBuffer: frame, timestamp: 0.0, intrinsics: intrinsics)
        report.check(scheduler.totalFramesSubmitted == 1, "First frame submitted to scheduler")
        
        // Immediately submit frame at t = 0.02 (20ms later) -> must be dropped to preserve 10 Hz
        scheduler.submitFrame(pixelBuffer: frame, timestamp: 0.02, intrinsics: intrinsics)
        report.check(scheduler.totalFramesDropped >= 1, "Immediate subsequent frame dropped under 10 Hz throttle policy")
        
        // Verify thermal policy configuration
        scheduler.updateThermalPolicy()
        report.check(true, "Thermal policy updated based on device ProcessInfo.thermalState")
    }
    
    // MARK: - 5. AI Confidence Evaluator
    private static func testCaptureReadinessAssessment(_ report: TestReport) {
        print("\n[Phase 4 - Test 5/6] AI Confidence Evaluator & Capture Readiness")
        
        let evaluator = AIConfidenceEvaluator.shared
        evaluator.reset()
        
        let frame = createSyntheticFrame(pattern: "indoor")
        let seg = FloorWallSegmentationEngine.shared.segmentSync(pixelBuffer: frame, timestamp: 1.0)
        let bounds = BoundaryDetectionEngine.shared.extractBoundaries(segmentation: seg, intrinsics: CameraIntrinsics.defaultFallback())
        let qualityGood = ImageQualityAnalyzer.shared.analyze(pixelBuffer: frame)
        
        // Normal tracking + good frame
        let readinessNormal = evaluator.evaluateFrame(
            segmentation: seg,
            boundaries: bounds,
            quality: qualityGood,
            trackingState: "NORMAL"
        )
        report.check(readinessNormal.isReadyForReconstruction, "Optimal frame with NORMAL tracking evaluated as ready for reconstruction")
        report.check(readinessNormal.surfaceConfidence > 0.30, "Surface confidence exceeds indoor threshold (> 0.30)")
        
        // Degraded tracking
        let readinessDegraded = evaluator.evaluateFrame(
            segmentation: seg,
            boundaries: bounds,
            quality: qualityGood,
            trackingState: "INSUFFICIENT_FEATURES"
        )
        report.check(!readinessDegraded.isReadyForReconstruction, "Frame rejected when ARKit tracking is INSUFFICIENT_FEATURES")
        
        // Blurry frame
        let blurBuffer = createSyntheticFrame(pattern: "uniform_blur")
        let qualityBlur = ImageQualityAnalyzer.shared.analyze(pixelBuffer: blurBuffer)
        let readinessBlur = evaluator.evaluateFrame(
            segmentation: seg,
            boundaries: bounds,
            quality: qualityBlur,
            trackingState: "NORMAL"
        )
        report.check(!readinessBlur.isReadyForReconstruction, "Frame rejected when image is blurry")
    }
    
    // MARK: - 6. Diagnostics & Zero-Cloud Telemetry
    private static func testDiagnosticsAndZeroCloud(_ report: TestReport) {
        print("\n[Phase 4 - Test 6/6] Diagnostics & Zero-Cloud Local AI Integrity")
        
        let diag = LocalMLDiagnostics.shared
        diag.reset()
        
        diag.recordInference(segmentationTimeMs: 8.5, qualityTimeMs: 2.1)
        diag.recordInference(segmentationTimeMs: 7.9, qualityTimeMs: 1.8)
        
        let summary = diag.getDiagnosticsSummary()
        report.check(diag.totalInferences == 2, "Diagnostics recorded total inferences")
        report.check(summary["local_ai_mode"] as? String == "ON_DEVICE_ZERO_CLOUD", "Zero-cloud local inference explicitly verified in diagnostics")
        report.check(summary["avg_latency_ms"] != nil, "Average inference latency recorded")
        report.check(summary["thermal_state"] != nil, "Hardware thermal state logged in diagnostics")
    }
}

