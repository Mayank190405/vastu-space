import Foundation
import simd

public class LiveFloorplanAndGuidanceTests {
    
    public static func runPhase5Tests(report: TestReport) async {
        print("\n==================================================")
        print("📐 Phase 5: AI-Guided Scanning & Live Floorplan Tests")
        print("==================================================")
        
        testFloorAnchorEstimator(report)
        testWallBoundaryMapperAndArbitraryAngles(report)
        testCornerDetection(report)
        testRoomCoverageTracker(report)
        testParallaxAndRotationDetection(report)
        testScanGuidanceHierarchy(report)
        testCaptureQualityEvaluationAndWarnings(report)
        testEndToEndFloorplanSimulation(report)
    }
    
    // MARK: - 1. Floor Anchor Estimator
    private static func testFloorAnchorEstimator(_ report: TestReport) {
        print("\n[Phase 5 - Test 1/8] Floor Plane Estimation & Raycasting")
        
        let estimator = FloorAnchorEstimator.shared
        estimator.reset()
        
        // Calibrate floor height at Y = -1.40m relative to initial camera
        estimator.updateFloorPlane(heightY: -1.40, confidence: 0.95)
        report.check(estimator.isPlaneCalibrated, "Floor plane calibrated from observations")
        report.check(abs(estimator.floorPlaneY - (-1.40)) < 0.01, "Floor plane height set to -1.40m")
        
        // Camera at (0, 0, 0), ray points down-forward: (0, -0.7071, 0.7071)
        // Intersection should occur where Y = -1.40 -> t = -1.40 / -0.7071 = 1.9799m
        // Z = 0 + 1.9799 * 0.7071 = 1.40m
        let camPos = simd_make_float3(0, 0, 0)
        let camRot = matrix_identity_float3x3
        let rayCam = simd_normalize(simd_make_float3(0, -1.0, 1.0))
        
        let hit = estimator.intersectFloor(
            cameraPosition: camPos,
            cameraRotation: camRot,
            rayCamera: rayCam,
            rayConfidence: 0.90
        )
        
        report.check(hit.isValid, "Downward camera ray intersected floor plane")
        report.check(abs(hit.worldPoint.z - 1.40) < 0.05, "Hit world Z position mathematically accurate (~1.40m)")
        report.check(abs(hit.worldPoint.x - 0.00) < 0.01, "Hit world X position mathematically accurate (0.0m)")
        report.check(hit.distanceMeters > 1.8 && hit.distanceMeters < 2.1, "Hit distance within expected geometric bounds")
        
        // Reject upward ray (looking at ceiling)
        let upwardRay = simd_normalize(simd_make_float3(0, 1.0, 0.5))
        let upwardHit = estimator.intersectFloor(cameraPosition: camPos, cameraRotation: camRot, rayCamera: upwardRay, rayConfidence: 0.9)
        report.check(!upwardHit.isValid, "Upward ray safely rejected without intersecting floor plane")
        
        // Reject extreme distance (> 7.5m)
        let shallowRay = simd_normalize(simd_make_float3(0, -0.05, 1.0))
        let farHit = estimator.intersectFloor(cameraPosition: camPos, cameraRotation: camRot, rayCamera: shallowRay, rayConfidence: 0.9)
        report.check(!farHit.isValid, "Extreme range ray (> 7.5m) safely rejected to prevent unprojection distortion")
    }
    
    // MARK: - 2. Wall Boundary Mapper & Arbitrary Angles
    private static func testWallBoundaryMapperAndArbitraryAngles(_ report: TestReport) {
        print("\n[Phase 5 - Test 2/8] Wall Boundary Mapper & Non-Orthogonal Wall Fitting")
        
        let mapper = WallBoundaryMapper.shared
        mapper.reset()
        
        // Create an irregular wall segment slanted at 45 degrees: from (1.0, 1.0) to (3.0, 3.0)
        for i in 0...10 {
            let t = Double(i) / 10.0
            let x = 1.0 + 2.0 * t
            let z = 1.0 + 2.0 * t
            // Add repeated observations with slight noise
            mapper.addObservation(point: Point2D(x: x, z: z), confidence: 0.85, timestamp: 1.0)
            mapper.addObservation(point: Point2D(x: x + 0.01, z: z - 0.01), confidence: 0.88, timestamp: 1.1)
        }
        
        // Create a horizontal wall segment: from (1.0, 1.0) to (-1.5, 1.0)
        for i in 0...8 {
            let t = Double(i) / 8.0
            let x = 1.0 - 2.5 * t
            let z = 1.0
            mapper.addObservation(point: Point2D(x: x, z: z), confidence: 0.90, timestamp: 1.0)
            mapper.addObservation(point: Point2D(x: x, z: z + 0.01), confidence: 0.90, timestamp: 1.1)
        }
        
        let stablePts = mapper.getStableBoundaryPoints(minHits: 2)
        report.check(stablePts.count >= 15, "Multi-observation accumulator retained stable boundary points")
        
        let (observed, _) = mapper.extractFittedWallSegments()
        report.check(observed.count >= 2, "Fitted at least 2 distinct wall segments")
        
        // Verify 45-degree angle preservation (not forced to 90 degrees)
        let slantedWall = observed.first { abs(($0.end.x - $0.start.x) - ($0.end.z - $0.start.z)) < 0.20 }
        report.check(slantedWall != nil, "Preserved irregular non-orthogonal wall geometry (~45° slope)")
        report.check(observed.allSatisfy { $0.type == .observed }, "Directly observed wall segments marked as .observed")
    }
    
    // MARK: - 3. Corner Detection
    private static func testCornerDetection(_ report: TestReport) {
        print("\n[Phase 5 - Test 3/8] Room Corner Detection & Angle Estimation")
        
        let cornerEngine = CornerDetectionEngine.shared
        
        // Wall 1: Along X-axis from (0, 0) to (3.0, 0)
        let w1 = WallSegment2D(start: Point2D(x: 0.0, z: 0.0), end: Point2D(x: 3.0, z: 0.0), confidence: 0.9, type: .observed)
        // Wall 2: Along Z-axis from (3.0, 0) to (3.0, 2.5) -> forms a 90° corner at (3.0, 0.0)
        let w2 = WallSegment2D(start: Point2D(x: 3.0, z: 0.0), end: Point2D(x: 3.0, z: 2.5), confidence: 0.9, type: .observed)
        
        let corners = cornerEngine.detectCorners(
            walls: [w1, w2],
            stableBoundaryPoints: [Point2D(x: 3.0, z: 0.0)]
        )
        
        report.check(corners.count == 1, "Detected exactly 1 wall junction corner")
        guard let corner = corners.first else { return }
        
        report.check(abs(corner.position.x - 3.0) < 0.05, "Corner X position accurate (~3.0m)")
        report.check(abs(corner.position.z - 0.0) < 0.05, "Corner Z position accurate (~0.0m)")
        report.check(abs(corner.angleDegrees - 90.0) < 3.0, "Corner angle correctly estimated at ~90°")
        report.check(corner.isDirectlyObserved, "Corner near stable boundary points flagged as directly observed")
    }
    
    // MARK: - 4. Room Coverage Tracker
    private static func testRoomCoverageTracker(_ report: TestReport) {
        print("\n[Phase 5 - Test 4/8] Room Coverage & Missing Sector Tracking")
        
        let tracker = RoomCoverageTracker.shared
        tracker.reset()
        
        let walls = [
            WallSegment2D(start: Point2D(x: -2, z: -2), end: Point2D(x: 2, z: -2), confidence: 0.9),
            WallSegment2D(start: Point2D(x: 2, z: -2), end: Point2D(x: 2, z: 2), confidence: 0.9)
        ]
        let pts = [Point2D(x: -2, z: -2), Point2D(x: 2, z: -2), Point2D(x: 2, z: 2)]
        
        // Scan 4 out of 16 sectors
        var cov = tracker.evaluateCoverage(cameraPosition: Point2D(x: 0, z: 0), cameraHeadingDeg: 0.0, observedWalls: walls, boundaryPoints: pts)
        cov = tracker.evaluateCoverage(cameraPosition: Point2D(x: 0, z: 0), cameraHeadingDeg: 45.0, observedWalls: walls, boundaryPoints: pts)
        cov = tracker.evaluateCoverage(cameraPosition: Point2D(x: 0, z: 0), cameraHeadingDeg: 90.0, observedWalls: walls, boundaryPoints: pts)
        cov = tracker.evaluateCoverage(cameraPosition: Point2D(x: 0, z: 0), cameraHeadingDeg: 135.0, observedWalls: walls, boundaryPoints: pts)
        
        report.check(cov.angularCoveragePct > 20.0 && cov.angularCoveragePct < 35.0, "Angular coverage tracks surveyed radial sectors")
        report.check(!cov.missingSectors.isEmpty, "Missing uncaptured radial sectors identified")
        report.check(!cov.isSufficient, "Partial scan correctly evaluated as insufficient coverage")
        
        // Survey remaining sectors (360-degree sweep)
        for deg in stride(from: 0.0, to: 360.0, by: 20.0) {
            cov = tracker.evaluateCoverage(cameraPosition: Point2D(x: 0, z: 0), cameraHeadingDeg: deg, observedWalls: walls, boundaryPoints: pts)
        }
        report.check(cov.angularCoveragePct >= 90.0, "360-degree sweep achieves high angular coverage (>= 90%)")
    }
    
    // MARK: - 5. Parallax & Pure Rotation Detection
    private static func testParallaxAndRotationDetection(_ report: TestReport) {
        print("\n[Phase 5 - Test 5/8] Parallax Analysis & Pure Rotation Detection")
        
        let analyzer = ParallaxAnalyzer.shared
        analyzer.reset()
        
        // Simulate pure rotation: phone turns in place without changing translation
        var pMetric = analyzer.evaluateParallax(cameraPosition: Point2D(x: 0, z: 0), cameraHeadingDeg: 0.0, timestamp: 0.0)
        pMetric = analyzer.evaluateParallax(cameraPosition: Point2D(x: 0.01, z: 0.0), cameraHeadingDeg: 30.0, timestamp: 0.5)
        pMetric = analyzer.evaluateParallax(cameraPosition: Point2D(x: 0.02, z: 0.0), cameraHeadingDeg: 60.0, timestamp: 1.0)
        pMetric = analyzer.evaluateParallax(cameraPosition: Point2D(x: 0.02, z: 0.0), cameraHeadingDeg: 90.0, timestamp: 1.5)
        
        report.check(pMetric.isRotationOnly, "Detected pure rotational movement without sufficient translation")
        report.check(!pMetric.isSufficient, "Pure rotation flagged as insufficient parallax")
        
        // Simulate bodily translation: operator walks 1.5 meters sideways
        analyzer.reset()
        for i in 0...15 {
            let t = Double(i) * 0.10
            pMetric = analyzer.evaluateParallax(
                cameraPosition: Point2D(x: t, z: t * 0.3),
                cameraHeadingDeg: 10.0 + Double(i) * 2.0,
                timestamp: Double(i) * 0.2
            )
        }
        
        report.check(!pMetric.isRotationOnly, "Bodily translation cleared rotation-only warning")
        report.check(pMetric.translationBaselineM >= 1.40, "Baseline displacement measured accurately (~1.5m)")
        report.check(pMetric.isSufficient, "Translational parallax verified sufficient for 3D reconstruction")
    }
    
    // MARK: - 6. Scan Guidance Engine Hierarchy
    private static func testScanGuidanceHierarchy(_ report: TestReport) {
        print("\n[Phase 5 - Test 6/8] Scan Guidance Engine State Hierarchy")
        
        let engine = ScanGuidanceEngine.shared
        
        let dummyParallax = ParallaxMetric(translationBaselineM: 0.3, pathLengthM: 0.5, pathBoundingAreaM2: 0.1, trr: 1.0, isRotationOnly: false, isSufficient: false)
        let dummyCoverage = CoverageReport(perimeterCoveragePct: 20.0, angularCoveragePct: 25.0, totalEstimatedPerimeterM: 12.0, observedPerimeterM: 2.4, missingSectors: [1, 2, 3], isSufficient: false)
        
        // Priority 1: Excessive motion alert
        let gMotion = engine.evaluateGuidance(trackingState: "LIMITED_EXCESSIVE_MOTION", quality: nil, parallax: dummyParallax, coverage: dummyCoverage, corners: [])
        report.check(gMotion.severity == .alert, "Excessive motion triggers ALERT severity")
        report.check(gMotion.text.contains("Slow down"), "Guidance instructs operator to slow walking speed")
        
        // Priority 3: Pure rotation warning
        let rotParallax = ParallaxMetric(translationBaselineM: 0.1, pathLengthM: 0.1, pathBoundingAreaM2: 0.0, trr: 0.05, isRotationOnly: true, isSufficient: false)
        let gRot = engine.evaluateGuidance(trackingState: "NORMAL", quality: nil, parallax: rotParallax, coverage: dummyCoverage, corners: [])
        report.check(gRot.severity == .warning, "Pure rotation triggers WARNING severity")
        report.check(gRot.directionalCue == .stepSideways, "Directional cue prompts STEP_SIDEWAYS")
        
        // Priority 8: Full completion
        let fullParallax = ParallaxMetric(translationBaselineM: 1.5, pathLengthM: 4.0, pathBoundingAreaM2: 1.2, trr: 1.2, isRotationOnly: false, isSufficient: true)
        let fullCoverage = CoverageReport(perimeterCoveragePct: 85.0, angularCoveragePct: 90.0, totalEstimatedPerimeterM: 12.0, observedPerimeterM: 10.2, missingSectors: [], isSufficient: true)
        let gDone = engine.evaluateGuidance(trackingState: "NORMAL", quality: nil, parallax: fullParallax, coverage: fullCoverage, corners: [])
        report.check(gDone.severity == .success, "Full coverage and parallax triggers SUCCESS status")
        report.check(gDone.text.contains("Finish"), "Guidance prompts user to Finish")
    }
    
    // MARK: - 7. Capture Quality Evaluation & Pre-Finish Warnings
    private static func testCaptureQualityEvaluationAndWarnings(_ report: TestReport) {
        print("\n[Phase 5 - Test 7/8] Capture Quality Evaluation & Pre-Finish Warnings")
        
        let evaluator = CaptureQualityEvaluator.shared
        
        // Premature capture state (only 25% coverage, 0.3m baseline)
        let partialCov = CoverageReport(perimeterCoveragePct: 30.0, angularCoveragePct: 35.0, totalEstimatedPerimeterM: 12.0, observedPerimeterM: 3.6, missingSectors: [1, 2, 3], isSufficient: false)
        let partialParallax = ParallaxMetric(translationBaselineM: 0.35, pathLengthM: 0.8, pathBoundingAreaM2: 0.1, trr: 1.0, isRotationOnly: false, isSufficient: false)
        
        let prematureAudit = evaluator.evaluateQuality(
            coverage: partialCov,
            parallax: partialParallax,
            quality: nil,
            isTrackingDegraded: false,
            cornersCount: 1
        )
        
        report.check(!prematureAudit.canFinalizeWithoutWarning, "Premature capture disallowed from finalizing without warnings")
        report.check(!prematureAudit.preFinishWarnings.isEmpty, "Actionable pre-finish warnings generated for operator")
        report.check(prematureAudit.preFinishWarnings.contains { $0.contains("baseline") }, "Warning identifies insufficient motion baseline")
        report.check(prematureAudit.preFinishWarnings.contains { $0.contains("coverage") || $0.contains("wall") }, "Warning identifies missing room coverage")
        
        // High quality completed capture
        let fullCov = CoverageReport(perimeterCoveragePct: 85.0, angularCoveragePct: 90.0, totalEstimatedPerimeterM: 12.0, observedPerimeterM: 10.2, missingSectors: [], isSufficient: true)
        let fullParallax = ParallaxMetric(translationBaselineM: 1.4, pathLengthM: 4.5, pathBoundingAreaM2: 1.5, trr: 1.5, isRotationOnly: false, isSufficient: true)
        
        let completeAudit = evaluator.evaluateQuality(
            coverage: fullCov,
            parallax: fullParallax,
            quality: nil,
            isTrackingDegraded: false,
            cornersCount: 4
        )
        
        report.check(completeAudit.canFinalizeWithoutWarning, "High quality scan allows clean finalization without warnings")
        report.check(completeAudit.overallScore >= 75.0, "Overall capture quality score exceeds threshold (actual: \(completeAudit.overallScore)%)")
        report.check(completeAudit.preFinishWarnings.isEmpty, "Zero warnings on completed high-quality capture")
    }
    
    // MARK: - 8. End-to-End Live Floorplan Simulation
    private static func testEndToEndFloorplanSimulation(_ report: TestReport) {
        print("\n[Phase 5 - Test 8/8] End-to-End Live Floorplan Simulation Loop")
        
        let engine = LiveFloorplanEngine()
        engine.reset()
        
        // Calibrate floor
        FloorAnchorEstimator.shared.updateFloorPlane(heightY: -1.30)
        
        // Simulate walking around a 3x3m room perimeter (6 directions)
        let waypoints: [(pos: Point2D, heading: Double)] = [
            (Point2D(x: 0.0, z: 0.0), 0.0),
            (Point2D(x: 1.0, z: 0.0), 60.0),
            (Point2D(x: 2.0, z: 1.0), 120.0),
            (Point2D(x: 1.5, z: 2.0), 180.0),
            (Point2D(x: 0.5, z: 1.8), 240.0),
            (Point2D(x: 0.0, z: 0.5), 300.0)
        ]
        
        for (idx, wp) in waypoints.enumerated() {
            var transform = matrix_identity_float4x4
            transform.columns.3 = simd_make_float4(Float(wp.pos.x), 0.0, Float(wp.pos.z), 1.0)
            
            let pose = CameraPose(
                frameId: String(format: "sim_%d", idx),
                timestampNs: Int64(idx * 500_000_000),
                transformMatrix: transform,
                trackingState: "NORMAL"
            )
            
            let rays = [
                BoundaryRayCandidate(rayCamera: simd_normalize(simd_make_float3(-0.4, -0.7, 1.0)), confidence: 0.85),
                BoundaryRayCandidate(rayCamera: simd_normalize(simd_make_float3(0.0, -0.7, 1.0)), confidence: 0.90),
                BoundaryRayCandidate(rayCamera: simd_normalize(simd_make_float3(0.4, -0.7, 1.0)), confidence: 0.85)
            ]
            
            engine.processFrame(pose: pose, rays: rays, headingDeg: wp.heading)
        }
        
        report.check(!engine.floorplanMap.cameraTrail.isEmpty, "Live camera trail recorded consecutive positions")
        report.check(!engine.floorplanMap.boundaryPoints.isEmpty, "Accumulated world boundary points on floor plane")
        report.check(engine.floorplanMap.coveragePercentage > 30.0, "Live floorplan coverage percentage updated dynamically")
        report.check(engine.latestParallax.translationBaselineM > 1.0, "Parallax baseline tracked across simulation (> 1.0m)")
        report.check(!engine.latestInstruction.text.isEmpty, "Scan guidance active and delivering live instructions")
    }
}
