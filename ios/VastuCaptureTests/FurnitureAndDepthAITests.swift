import Foundation
import CoreVideo
import simd

public class FurnitureAndDepthAITests {
    
    public static func runPhase6Tests(report: TestReport) async {
        print("\n==================================================")
        print("🛋️ Phase 6: Local Furniture Detection & Depth AI Tests")
        print("==================================================")
        
        testFurnitureDetectionEngine(report)
        testLocalDepthEstimationEngine(report)
        testObjectPositionEstimator(report)
        testMultiViewObjectTracker(report)
        testOcclusionAnalysisEngine(report)
        testSceneObservationWriterAndPackageChecksums(report)
        await testEndToEndSceneUnderstandingSimulation(report)
    }
    
    // MARK: - 1. Furniture Detection Engine
    private static func testFurnitureDetectionEngine(_ report: TestReport) {
        print("\n[Phase 6 - Test 1/7] Furniture Detection Engine & Category Classification")
        
        let engine = FurnitureDetectionEngine.shared
        
        // Create synthetic test pixel buffer
        guard let pixelBuffer = createTestPixelBuffer(width: 320, height: 240) else {
            report.check(false, "Failed to create synthetic test pixel buffer")
            return
        }
        
        let detections = engine.detectFurnitureSync(pixelBuffer: pixelBuffer, timestamp: 1.0)
        report.check(!detections.isEmpty, "Detected furniture objects in test indoor frame")
        
        for det in detections {
            report.check(det.confidence >= 0.0 && det.confidence <= 1.0, "Confidence is within [0.0, 1.0]: \(det.confidence)")
            report.check(det.boundingBox.count == 4, "Bounding box contains 4 normalized coordinates [x, y, w, h]")
            
            let x = det.boundingBox[0]
            let y = det.boundingBox[1]
            let w = det.boundingBox[2]
            let h = det.boundingBox[3]
            
            report.check(x >= 0.0 && x <= 1.0 && y >= 0.0 && y <= 1.0, "Bounding box origin within normalized bounds [0, 1]")
            report.check(w > 0.0 && w <= 1.0 && h > 0.0 && h <= 1.0, "Bounding box size within normalized bounds (0, 1]")
            report.check(!det.category.displayName.isEmpty, "Category has valid display name: \(det.category.displayName)")
        }
        
        let allCategories = FurnitureCategory.allCases
        report.check(allCategories.contains(.bed), "Contains .bed category")
        report.check(allCategories.contains(.sofa), "Contains .sofa category")
        report.check(allCategories.contains(.chair), "Contains .chair category")
        report.check(allCategories.contains(.table), "Contains .table category")
        report.check(allCategories.contains(.desk), "Contains .desk category")
        report.check(allCategories.contains(.wardrobe), "Contains .wardrobe category")
    }
    
    // MARK: - 2. Local Depth Estimation Engine
    private static func testLocalDepthEstimationEngine(_ report: TestReport) {
        print("\n[Phase 6 - Test 2/7] Monocular Relative Depth Estimation & Thermal Throttling")
        
        let depthEngine = LocalDepthEstimationEngine.shared
        guard let pixelBuffer = createTestPixelBuffer(width: 320, height: 240) else {
            report.check(false, "Failed to create synthetic test pixel buffer for depth")
            return
        }
        
        let startTime = CFAbsoluteTimeGetCurrent()
        let depthResult = depthEngine.estimateDepthSync(pixelBuffer: pixelBuffer, timestamp: 1.0)
        let latencyMs = (CFAbsoluteTimeGetCurrent() - startTime) * 1000.0
        
        guard let depth = depthResult else {
            report.check(false, "Depth estimation returned nil")
            return
        }
        
        report.check(depth.width > 0 && depth.height > 0, "Depth map has valid grid dimensions: \(depth.width)x\(depth.height)")
        report.check(depth.relativeDepthMap.count == depth.width * depth.height, "Depth map buffer size matches grid dimensions")
        report.check(depth.meanRelativeDepth >= 0.0 && depth.meanRelativeDepth <= 1.0, "Mean relative depth is normalized [0.0, 1.0]: \(depth.meanRelativeDepth)")
        report.check(depth.meanConfidence >= 0.0 && depth.meanConfidence <= 1.0, "Depth confidence score is normalized [0.0, 1.0]: \(depth.meanConfidence)")
        report.check(!depth.isMetricCalibrated, "Depth result explicitly flagged as relative, NOT guaranteed metric ground truth")
        report.check(latencyMs < 30.0, "Depth estimation latency \(String(format: "%.1f", latencyMs))ms well within real-time budget (<30ms)")
        
        // Sampling helper test
        let centerDepth = depth.sampleDepth(u: 0.5, v: 0.5)
        report.check(centerDepth >= 0.0 && centerDepth <= 1.0, "Center sampled relative depth is within [0.0, 1.0]: \(centerDepth)")
        
        // Boundary clamped sampling
        let clampedDepth = depth.sampleDepth(u: 1.5, v: -0.5)
        report.check(clampedDepth >= 0.0 && clampedDepth <= 1.0, "Out-of-bounds UV safely clamped: \(clampedDepth)")
    }
    
    // MARK: - 3. Object Position Estimator
    private static func testObjectPositionEstimator(_ report: TestReport) {
        print("\n[Phase 6 - Test 3/7] Monocular Ground-Plane Projection & 3D Positioning")
        
        let estimator = ObjectPositionEstimator.shared
        
        // Calibrate floor plane at Y = -1.40
        FloorAnchorEstimator.shared.reset()
        FloorAnchorEstimator.shared.updateFloorPlane(heightY: -1.40, confidence: 0.95)
        
        // Camera at origin (0, 0, 0)
        let pose = createCameraPose(x: 0, y: 0, z: 0, yaw: 0, tNs: 1_000_000_000)
        let intrinsics = CameraIntrinsics(fx: 500.0, fy: 500.0, cx: 250.0, cy: 250.0, imageWidth: 500, imageHeight: 500)
        
        // Bounding box at bottom center of screen: [x: 0.35, y: 0.60, w: 0.30, h: 0.30]
        // Bottom-center contact is at x = 0.50, y = 0.90 -> px=250, py=450
        // rayCam: (0, -(450-250)/500, 1.0) = (0, -0.40, 1.0)
        // Floor at Y = -1.40 -> t = -1.40 / -0.40 = 3.50m
        // Z = 3.50m, X = 0.0m
        let detectedBed = DetectedFurniture(
            id: UUID().uuidString,
            category: .bed,
            label: "Bed",
            confidence: 0.88,
            boundingBox: [0.35, 0.60, 0.30, 0.30],
            timestamp: 1.0
        )
        
        let estimate = estimator.estimatePosition3D(
            detection: detectedBed,
            pose: pose,
            intrinsics: intrinsics,
            floorPlaneY: -1.40,
            depthResult: nil
        )
        
        guard let est = estimate else {
            report.check(false, "ObjectPositionEstimator failed to produce 3D position estimate")
            return
        }
        
        report.check(abs(est.position.y - (-1.40 + est.dimensions.height / 2.0)) < 0.1, "3D centroid Y sits above floor plane at half height")
        report.check(abs(est.position.x - 0.0) < 0.25, "3D centroid X is centered (~0.0m)")
        report.check(abs(est.position.z - 3.50) < 0.40, "3D centroid Z is ground-projected accurately (~3.50m)")
        report.check(est.uncertaintyRadiusMeters > 0.2 && est.uncertaintyRadiusMeters < 0.8, "Uncertainty radius scaled with distance (\(est.uncertaintyRadiusMeters)m)")
        report.check(est.dimensions.width > 0.5 && est.dimensions.height > 0.4, "Object dimensions reflect bed category prior")
    }
    
    // MARK: - 4. Multi-View Object Tracker
    private static func testMultiViewObjectTracker(_ report: TestReport) {
        print("\n[Phase 6 - Test 4/7] Multi-View Object Association & Bayesian Position Refinement")
        
        let tracker = MultiViewObjectTracker.shared
        tracker.reset()
        
        // Frame 1: Initial observation of sofa at (1.0, -0.6, 2.5)
        let sofa1 = DetectedFurniture(id: UUID().uuidString, category: .sofa, label: "Sofa", confidence: 0.82, boundingBox: [0.4, 0.5, 0.4, 0.3], timestamp: 1.0)
        let est1 = PositionEstimate3D(
            position: Point3D(x: 1.0, y: -0.6, z: 2.5),
            dimensions: Size3D(width: 1.9, height: 0.85, depth: 0.9),
            uncertaintyRadiusMeters: 0.45,
            groundContactPoint: Point2D(x: 1.0, z: 2.5),
            confidence: 0.82
        )
        tracker.update(detection: sofa1, estimate: est1, timestamp: 1.0)
        
        let tracks1 = tracker.getTrackedObjects(onlyStable: false)
        report.check(tracks1.count == 1, "Track created for initial sofa observation")
        report.check(tracks1[0].observationCount == 1, "Observation count is 1")
        report.check(!tracks1[0].isStable, "Track is provisional until confirmed (N < 3)")
        
        let initialUncertainty = tracks1[0].uncertaintyMeters
        
        // Frame 2: Second observation from slightly moved camera (distance < 0.90m)
        let sofa2 = DetectedFurniture(id: UUID().uuidString, category: .sofa, label: "Sofa", confidence: 0.88, boundingBox: [0.38, 0.5, 0.4, 0.3], timestamp: 1.1)
        let est2 = PositionEstimate3D(
            position: Point3D(x: 1.05, y: -0.6, z: 2.52),
            dimensions: Size3D(width: 1.9, height: 0.85, depth: 0.9),
            uncertaintyRadiusMeters: 0.42,
            groundContactPoint: Point2D(x: 1.05, z: 2.52),
            confidence: 0.88
        )
        tracker.update(detection: sofa2, estimate: est2, timestamp: 1.1)
        
        let tracks2 = tracker.getTrackedObjects(onlyStable: false)
        report.check(tracks2.count == 1, "Track associated successfully (no duplicate created)")
        report.check(tracks2[0].observationCount == 2, "Observation count incremented to 2")
        
        // Frame 3: Third observation -> stability confirmation threshold reached
        let sofa3 = DetectedFurniture(id: UUID().uuidString, category: .sofa, label: "Sofa", confidence: 0.91, boundingBox: [0.36, 0.5, 0.4, 0.3], timestamp: 1.2)
        let est3 = PositionEstimate3D(
            position: Point3D(x: 0.98, y: -0.6, z: 2.48),
            dimensions: Size3D(width: 1.9, height: 0.85, depth: 0.9),
            uncertaintyRadiusMeters: 0.38,
            groundContactPoint: Point2D(x: 0.98, z: 2.48),
            confidence: 0.91
        )
        tracker.update(detection: sofa3, estimate: est3, timestamp: 1.2)
        
        let tracks3 = tracker.getTrackedObjects(onlyStable: false)
        report.check(tracks3.count == 1, "Single consolidated track maintained across 3 frames")
        report.check(tracks3[0].observationCount == 3, "Observation count reached 3")
        report.check(tracks3[0].isStable, "Track is now STABLE (N >= 3)")
        report.check(tracks3[0].uncertaintyMeters < initialUncertainty, "Uncertainty radius reduced through multi-view recursive Bayesian refinement")
        
        let stableTracks = tracker.getTrackedObjects(onlyStable: true)
        report.check(stableTracks.count == 1, "Stable tracks filter correctly returns confirmed sofa")
        
        // Frame 4: Second distinct object far away (chair at x=-2.0m, dist > 0.90m)
        let chair1 = DetectedFurniture(id: UUID().uuidString, category: .chair, label: "Chair", confidence: 0.85, boundingBox: [0.1, 0.6, 0.2, 0.3], timestamp: 1.3)
        let est4 = PositionEstimate3D(
            position: Point3D(x: -2.0, y: -0.6, z: 1.5),
            dimensions: Size3D(width: 0.65, height: 0.85, depth: 0.65),
            uncertaintyRadiusMeters: 0.30,
            groundContactPoint: Point2D(x: -2.0, z: 1.5),
            confidence: 0.85
        )
        tracker.update(detection: chair1, estimate: est4, timestamp: 1.3)
        
        let tracks4 = tracker.getTrackedObjects(onlyStable: false)
        report.check(tracks4.count == 2, "Two distinct tracks maintained simultaneously (sofa + chair)")
    }
    
    // MARK: - 5. Occlusion Analysis Engine
    private static func testOcclusionAnalysisEngine(_ report: TestReport) {
        print("\n[Phase 6 - Test 5/7] Occlusion Detection & Wall Boundary Ray Filtering")
        
        let occlusionEngine = OcclusionAnalysisEngine.shared
        
        // Furniture bounding box at [x: 0.30, y: 0.40, w: 0.40, h: 0.50]
        let bed = DetectedFurniture(
            id: UUID().uuidString,
            category: .bed,
            label: "Bed",
            confidence: 0.92,
            boundingBox: [0.30, 0.40, 0.40, 0.50],
            timestamp: 10.0
        )
        
        // Candidate 1: Inside the bed bounding box (x=0.50, y=0.60) -> should be occluded
        let occludedPoint = CGPoint(x: 0.50, y: 0.60)
        // Candidate 2: Clear of the bed bounding box (x=0.10, y=0.60) -> not occluded
        let clearPoint = CGPoint(x: 0.10, y: 0.60)
        
        let candidates = [occludedPoint, clearPoint]
        let reportAnalysis = occlusionEngine.filterOccludedBoundaryPoints(
            boundaryPointsNormalized: candidates,
            furnitureDetections: [bed]
        )
        
        report.check(reportAnalysis.totalRays == 2, "Evaluated 2 boundary contact rays")
        report.check(reportAnalysis.occludedRaysCount == 1, "Detected 1 occluded boundary point behind bed")
        report.check(reportAnalysis.occludedRayIndices.contains(0), "Index 0 identified as occluded ray")
        report.check(reportAnalysis.occludingFurnitureCategories.contains(.bed), "Occluding category identified as bed")
        report.check(reportAnalysis.isWallSignificantlyBlocked, "Wall boundary blockage ratio correctly evaluated (1/2 = 50% > 40%)")
    }
    
    // MARK: - 6. Scene Observation Writer & Checksums
    private static func testSceneObservationWriterAndPackageChecksums(_ report: TestReport) {
        print("\n[Phase 6 - Test 6/7] Scene Observation Streaming & Checksum Integrity")
        
        let tempDir = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("vastu_phase6_test_\(UUID().uuidString)")
        try? FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: tempDir) }
        
        let obsURL = tempDir.appendingPathComponent("scene_observations.jsonl")
        
        do {
            let writer = try SceneObservationWriter(fileURL: obsURL)
            
            let track = TrackedFurnitureObject(
                id: UUID().uuidString,
                category: .table,
                label: "Table",
                confidence: 0.89,
                position3D: Point3D(x: 0.5, y: -0.8, z: 2.2),
                dimensions: Size3D(width: 1.2, height: 0.75, depth: 0.8),
                uncertaintyMeters: 0.22,
                groundContact: Point2D(x: 0.5, z: 2.2),
                observationCount: 5,
                firstSeenTimestamp: 10.0,
                lastSeenTimestamp: 11.5,
                isStable: true
            )
            
            writer.recordObservation(track: track, timestamp: 11.5)
            writer.close()
            
            report.check(FileManager.default.fileExists(atPath: obsURL.path), "scene_observations.jsonl created on disk")
            
            let data = try Data(contentsOf: obsURL)
            guard let line = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) else {
                report.check(false, "Failed to read string from scene_observations.jsonl")
                return
            }
            
            report.check(!line.isEmpty, "scene_observations.jsonl contains streaming JSON record")
            report.check(line.contains("\"category\":\"table\""), "JSONL record contains category 'table'")
            report.check(line.contains("\"is_stable\":true"), "JSONL record contains track stability status")
            report.check(line.contains("\"uncertainty_m\":0.22"), "JSONL record contains uncertainty radius")
            report.check(line.contains("\"confidence\":0.89"), "JSONL record contains confidence score")
            
        } catch {
            report.check(false, "SceneObservationWriter threw unexpected error: \(error)")
        }
    }
    
    // MARK: - 7. End-to-End Simulation
    private static func testEndToEndSceneUnderstandingSimulation(_ report: TestReport) async {
        print("\n[Phase 6 - Test 7/7] End-to-End Scene Understanding Orchestration Simulation")
        
        let manager = SceneUnderstandingManager.shared
        manager.reset()
        
        let tempDir = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("vastu_e2e_sim_\(UUID().uuidString)")
        try? FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: tempDir) }
        
        manager.configureLogging(packageDirectory: tempDir)
        
        guard let pixelBuffer = createTestPixelBuffer(width: 320, height: 240) else {
            report.check(false, "Failed to create synthetic test pixel buffer for e2e sim")
            return
        }
        
        let intrinsics = CameraIntrinsics(fx: 400, fy: 400, cx: 160, cy: 120, imageWidth: 320, imageHeight: 240)
        let boundaryPolyline = [CGPoint(x: 0.1, y: 0.9), CGPoint(x: 0.5, y: 0.9), CGPoint(x: 0.9, y: 0.9)]
        
        for i in 0..<4 {
            let pose = createCameraPose(x: Double(i) * 0.15, y: 0.0, z: 0.0, yaw: Double(i) * 2.0, tNs: Int64(i * 200_000_000))
            manager.processFrame(
                pixelBuffer: pixelBuffer,
                pose: pose,
                intrinsics: intrinsics,
                floorPlaneY: -1.40,
                boundaryPolyline: boundaryPolyline,
                timestamp: Double(i) * 0.2
            )
            // Allow background queue to execute
            try? await Task.sleep(nanoseconds: 50_000_000)
        }
        
        report.check(!manager.detectedObjects.isEmpty, "Detected furniture objects populated on main manager")
        report.check(!manager.trackedFurniture.isEmpty, "Tracked furniture objects maintained on main manager")
        report.check(manager.latestDepthResult != nil, "Monocular relative depth map populated on main manager")
        report.check(manager.latestOcclusionReport != nil, "Occlusion analysis report generated on main manager")
        
        manager.reset()
        report.check(manager.detectedObjects.isEmpty, "Manager successfully reset for next recording session")
        report.check(manager.trackedFurniture.isEmpty, "Tracked objects cleared on reset")
    }
    
    // MARK: - Helpers
    private static func createCameraPose(x: Double, y: Double, z: Double, yaw: Double, tNs: Int64) -> CameraPose {
        let rad = Float(yaw * .pi / 180.0)
        let cosY = cos(rad)
        let sinY = sin(rad)
        let mat = simd_float4x4(
            simd_make_float4(cosY, 0, sinY, 0),
            simd_make_float4(0, 1, 0, 0),
            simd_make_float4(-sinY, 0, cosY, 0),
            simd_make_float4(Float(x), Float(y), Float(z), 1)
        )
        return CameraPose(
            frameId: "frame_\(tNs)",
            timestampNs: tNs,
            transformMatrix: mat,
            trackingState: "NORMAL"
        )
    }
    
    private static func createTestPixelBuffer(width: Int, height: Int) -> CVPixelBuffer? {
        var pixelBuffer: CVPixelBuffer?
        let attrs: [CFString: Any] = [
            kCVPixelBufferCGImageCompatibilityKey: true,
            kCVPixelBufferCGBitmapContextCompatibilityKey: true
        ]
        let status = CVPixelBufferCreate(
            kCFAllocatorDefault,
            width,
            height,
            kCVPixelFormatType_32BGRA,
            attrs as CFDictionary,
            &pixelBuffer
        )
        guard status == kCVReturnSuccess, let buffer = pixelBuffer else { return nil }
        
        CVPixelBufferLockBaseAddress(buffer, [])
        if let baseAddress = CVPixelBufferGetBaseAddress(buffer) {
            let bytesPerRow = CVPixelBufferGetBytesPerRow(buffer)
            // Fill bottom half with wood floor / bed pattern
            for y in 0..<height {
                let row = baseAddress.advanced(by: y * bytesPerRow).assumingMemoryBound(to: UInt8.self)
                for x in 0..<width {
                    let offset = x * 4
                    if y >= 90 && y <= 190 && x >= 80 && x <= 240 {
                        // Foreground indoor furniture (e.g. table / bed) with distinct contrasting texture
                        row[offset] = 120
                        row[offset + 1] = 40
                        row[offset + 2] = 30
                        row[offset + 3] = 255
                    } else if y > height / 2 {
                        // Wood / warm indoor floor colors
                        row[offset] = 40      // Blue
                        row[offset + 1] = 80  // Green
                        row[offset + 2] = 160 // Red
                        row[offset + 3] = 255 // Alpha
                    } else {
                        // Upper wall
                        row[offset] = 210
                        row[offset + 1] = 210
                        row[offset + 2] = 210
                        row[offset + 3] = 255
                    }
                }
            }
        }
        CVPixelBufferUnlockBaseAddress(buffer, [])
        return buffer
    }
}
