import Foundation
import simd

public final class LiveFloorplanEngine: ObservableObject {
    @Published public var floorplanMap = LiveFloorplanMap()
    @Published public var latestCoverage: CoverageReport
    @Published public var latestParallax: ParallaxMetric
    @Published public var latestInstruction: GuidanceInstruction
    @Published public var latestQualityAudit: ComprehensiveCaptureAudit
    
    private var lastCameraPos: Point2D?
    private var frameCounter: Int = 0
    
    public init() {
        self.latestCoverage = CoverageReport(
            perimeterCoveragePct: 0.0,
            angularCoveragePct: 0.0,
            totalEstimatedPerimeterM: 10.0,
            observedPerimeterM: 0.0,
            missingSectors: Array(0..<16),
            isSufficient: false
        )
        self.latestParallax = ParallaxMetric(
            translationBaselineM: 0.0,
            pathLengthM: 0.0,
            pathBoundingAreaM2: 0.0,
            trr: 1.0,
            isRotationOnly: false,
            isSufficient: false
        )
        self.latestInstruction = GuidanceInstruction(
            text: "Walk slowly along walls (0.3 m/s) • Keep floor in view",
            severity: .info,
            directionalCue: .forward,
            missingAreaSummary: nil
        )
        self.latestQualityAudit = ComprehensiveCaptureAudit(
            overallScore: 0.0,
            coverageScore: 0.0,
            parallaxScore: 0.0,
            visualQualityScore: 100.0,
            trackingStabilityScore: 100.0,
            isReadyForFinalization: false,
            canFinalizeWithoutWarning: false,
            preFinishWarnings: ["Capture not started"],
            auditSummary: "Initializing room scan"
        )
    }
    
    public func reset() {
        FloorAnchorEstimator.shared.reset()
        WallBoundaryMapper.shared.reset()
        RoomCoverageTracker.shared.reset()
        ParallaxAnalyzer.shared.reset()
        
        floorplanMap = LiveFloorplanMap()
        lastCameraPos = nil
        frameCounter = 0
        
        latestCoverage = CoverageReport(
            perimeterCoveragePct: 0.0,
            angularCoveragePct: 0.0,
            totalEstimatedPerimeterM: 10.0,
            observedPerimeterM: 0.0,
            missingSectors: Array(0..<16),
            isSufficient: false
        )
        latestParallax = ParallaxMetric(
            translationBaselineM: 0.0,
            pathLengthM: 0.0,
            pathBoundingAreaM2: 0.0,
            trr: 1.0,
            isRotationOnly: false,
            isSufficient: false
        )
        latestInstruction = GuidanceInstruction(
            text: "Walk slowly along walls (0.3 m/s) • Keep floor in view",
            severity: .info,
            directionalCue: .forward,
            missingAreaSummary: nil
        )
        latestQualityAudit = ComprehensiveCaptureAudit(
            overallScore: 0.0,
            coverageScore: 0.0,
            parallaxScore: 0.0,
            visualQualityScore: 100.0,
            trackingStabilityScore: 100.0,
            isReadyForFinalization: false,
            canFinalizeWithoutWarning: false,
            preFinishWarnings: [],
            auditSummary: "Starting capture"
        )
    }
    
    /// Processes a single frame with camera pose, AI boundary rays, and quality metrics
    public func processFrame(
        pose: CameraPose,
        rays: [BoundaryRayCandidate],
        headingDeg: Double,
        quality: ComprehensiveQualityAssessment? = nil,
        timestamp: TimeInterval = ProcessInfo.processInfo.systemUptime
    ) {
        frameCounter += 1
        
        let camX = pose.position[0]
        let camY = pose.position[1]
        let camZ = pose.position[2]
        let currentPos = Point2D(x: camX, z: camZ)
        
        // 1. Update camera motion trail
        if let last = lastCameraPos {
            let dx = currentPos.x - last.x
            let dz = currentPos.z - last.z
            let dist = sqrt(dx * dx + dz * dz)
            if dist > 0.06 { // Append every 6cm of movement
                floorplanMap.cameraTrail.append(currentPos)
                lastCameraPos = currentPos
            }
        } else {
            floorplanMap.cameraTrail.append(currentPos)
            lastCameraPos = currentPos
        }
        
        floorplanMap.currentCameraHeadingDeg = headingDeg
        
        // 2. Intersect camera rays with the floor plane (Y = 0.0)
        let camPosSimd = simd_make_float3(Float(camX), Float(camY), Float(camZ))
        let rotMatrix = simd_float3x3(
            simd_make_float3(Float(pose.transform[0][0]), Float(pose.transform[1][0]), Float(pose.transform[2][0])),
            simd_make_float3(Float(pose.transform[0][1]), Float(pose.transform[1][1]), Float(pose.transform[2][1])),
            simd_make_float3(Float(pose.transform[0][2]), Float(pose.transform[1][2]), Float(pose.transform[2][2]))
        )
        
        for candidate in rays {
            let hit = FloorAnchorEstimator.shared.intersectFloor(
                cameraPosition: camPosSimd,
                cameraRotation: rotMatrix,
                rayCamera: candidate.rayCamera,
                rayConfidence: candidate.confidence
            )
            
            if hit.isValid {
                WallBoundaryMapper.shared.addObservation(
                    point: hit.worldPoint,
                    confidence: hit.confidence,
                    timestamp: timestamp
                )
            }
        }
        
        // 3. Extract stable boundary points and fitted wall segments (every 2 frames for smooth throughput)
        let stablePoints = WallBoundaryMapper.shared.getStableBoundaryPoints(minHits: 1)
        floorplanMap.boundaryPoints = stablePoints
        
        if frameCounter % 2 == 0 || floorplanMap.observedWalls.isEmpty {
            let (observed, estimated) = WallBoundaryMapper.shared.extractFittedWallSegments()
            floorplanMap.observedWalls = observed
            floorplanMap.estimatedWalls = estimated
            
            // Legacy compatibility
            floorplanMap.detectedWalls = observed.map {
                WallCandidate2D(id: $0.id, start: $0.start, end: $0.end, confidence: $0.confidence)
            }
            
            // 4. Extract corners
            let corners = CornerDetectionEngine.shared.detectCorners(
                walls: observed,
                stableBoundaryPoints: stablePoints
            )
            floorplanMap.corners = corners
        }
        
        // 5. Parallax Analysis (every frame)
        let parallax = ParallaxAnalyzer.shared.evaluateParallax(
            cameraPosition: currentPos,
            cameraHeadingDeg: headingDeg,
            timestamp: timestamp
        )
        latestParallax = parallax
        
        // 6. Coverage Tracking (every frame)
        let coverage = RoomCoverageTracker.shared.evaluateCoverage(
            cameraPosition: currentPos,
            cameraHeadingDeg: headingDeg,
            observedWalls: floorplanMap.observedWalls,
            boundaryPoints: stablePoints
        )
        latestCoverage = coverage
        floorplanMap.coveragePercentage = max(coverage.angularCoveragePct, coverage.perimeterCoveragePct)
        floorplanMap.missingSectors = coverage.missingSectors
        
        // 7. Dynamic AI Guidance
        let isDegraded = (pose.trackingState != "NORMAL" && pose.trackingState != "READY")
        let instruction = ScanGuidanceEngine.shared.evaluateGuidance(
            trackingState: pose.trackingState,
            quality: quality,
            parallax: parallax,
            coverage: coverage,
            corners: floorplanMap.corners
        )
        latestInstruction = instruction
        
        // 8. Capture Quality Audit
        let qualityAudit = CaptureQualityEvaluator.shared.evaluateQuality(
            coverage: coverage,
            parallax: parallax,
            quality: quality,
            isTrackingDegraded: isDegraded,
            cornersCount: floorplanMap.corners.count
        )
        latestQualityAudit = qualityAudit
    }
}

public final class GuidedCaptureIntelligence: ObservableObject {
    @Published public var activePrompt: String = "Walk slowly along walls (0.3 m/s) • Keep floor in view"
    @Published public var translationBaselineMeters: Double = 0.0
    @Published public var isBaselineSufficient: Bool = false
    
    private var initialPosition: Point2D?
    private var maxDisplacement: Double = 0.0
    
    public init() {}
    
    public func reset() {
        initialPosition = nil
        maxDisplacement = 0.0
        translationBaselineMeters = 0.0
        isBaselineSufficient = false
        activePrompt = "Walk slowly along walls (0.3 m/s) • Keep floor in view"
    }
    
    public func update(
        pose: CameraPose,
        quality: FrameQualityMetric,
        trackingState: String,
        coveragePct: Double
    ) {
        let pos = Point2D(x: pose.position[0], z: pose.position[2])
        if initialPosition == nil {
            initialPosition = pos
        }
        
        if let initPos = initialPosition {
            let dx = pos.x - initPos.x
            let dz = pos.z - initPos.z
            let disp = sqrt(dx * dx + dz * dz)
            if disp > maxDisplacement {
                maxDisplacement = disp
                translationBaselineMeters = round(disp * 100) / 100.0
                isBaselineSufficient = translationBaselineMeters >= 0.80
            }
        }
        
        // Evaluate dynamic guidance hierarchy
        if trackingState == "LIMITED_EXCESSIVE_MOTION" {
            activePrompt = "⚠️ Too fast — slow your walking speed to ~0.3 m/s"
        } else if quality.isBlurry {
            activePrompt = "⚠️ Hold camera steady — motion blur detected"
        } else if quality.isUnderexposed {
            activePrompt = "💡 Low light — turn on room lights if possible"
        } else if trackingState == "LIMITED_INSUFFICIENT_FEATURES" {
            activePrompt = "⚠️ Blank wall — keep floor baseboard in view"
        } else if !isBaselineSufficient {
            activePrompt = "Step sideways along the floor (\(String(format: "%.1f", translationBaselineMeters))m / 0.8m baseline)"
        } else if coveragePct < 80.0 {
            activePrompt = "Continue perimeter loop to capture remaining walls"
        } else {
            activePrompt = "✅ Optimal coverage — complete loop at the doorway"
        }
    }
}
