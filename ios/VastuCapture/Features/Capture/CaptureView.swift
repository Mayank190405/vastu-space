import SwiftUI
import ARKit
import Combine

public final class CaptureCoordinator: NSObject, ObservableObject, CaptureSessionManagerDelegate, InferenceSchedulerDelegate {
    public let manager = CaptureSessionManager()
    public let floorplanEngine = LiveFloorplanEngine()
    public let guidance = GuidedCaptureIntelligence()
    public let sceneManager = SceneUnderstandingManager.shared
    
    @Published public var elapsedSeconds: Int = 0
    @Published public var latestQuality = FrameQualityMetric(sharpnessScore: 100, exposureScore: 0.5, isBlurry: false, isOverexposed: false, isUnderexposed: false)
    @Published public var latestSegmentation: SegmentationResult?
    @Published public var latestBoundaries: BoundaryExtractionResult?
    @Published public var latestQualityAssessment: ComprehensiveQualityAssessment?
    
    private var timer: Timer?
    private var initialHeadingDeg: Double = 0.0
    
    public override init() {
        super.init()
        manager.delegate = self
        InferenceScheduler.shared.delegate = self
        LocalModelManager.shared.loadSegmentationModel()
    }
    
    public func startLiveCamera() {
        manager.startLiveCamera()
    }
    
    public func pauseLiveCamera() {
        stopTimer()
        manager.pauseLiveCamera()
    }
    
    public func startRecording(session: CaptureSession) throws {
        elapsedSeconds = 0
        floorplanEngine.reset()
        guidance.reset()
        sceneManager.reset()
        AIConfidenceEvaluator.shared.reset()
        InferenceScheduler.shared.reset()
        startTimer()
        try manager.startRecording(session: session)
    }
    
    public func togglePause() {
        if manager.isPaused {
            try? manager.resumeRecording()
        } else {
            manager.pauseRecording()
        }
    }
    
    public func finishRecording() throws -> URL {
        stopTimer()
        return try manager.finishRecording()
    }
    
    // MARK: - InferenceSchedulerDelegate
    public func schedulerDidProduceInference(
        segmentation: SegmentationResult,
        boundaries: BoundaryExtractionResult,
        quality: ComprehensiveQualityAssessment
    ) {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            self.latestSegmentation = segmentation
            self.latestBoundaries = boundaries
            self.latestQualityAssessment = quality
            self.latestQuality = FrameQualityMetric(
                sharpnessScore: quality.sharpnessScore,
                exposureScore: quality.exposureRatio,
                isBlurry: quality.isBlurry,
                isOverexposed: quality.isOverexposed,
                isUnderexposed: quality.isUnderexposed
            )
            
            let readiness = AIConfidenceEvaluator.shared.evaluateFrame(
                segmentation: segmentation,
                boundaries: boundaries,
                quality: quality,
                trackingState: self.manager.activeTrackingText
            )
            if !readiness.isReadyForReconstruction && self.manager.isRecording {
                self.guidance.activePrompt = readiness.reasoning
            }
        }
    }
    
    public func schedulerDidDropFrame() {}
    
    // MARK: - CaptureSessionManagerDelegate
    public func captureManager(_ manager: CaptureSessionManager, didUpdatePose pose: CameraPose, headingDeg: Double) {
        if initialHeadingDeg == 0.0 { initialHeadingDeg = headingDeg }
        let currentHeading = headingDeg - initialHeadingDeg
        
        let rays: [BoundaryRayCandidate]
        if let liveRays = latestBoundaries?.boundaryRays, !liveRays.isEmpty {
            rays = liveRays
        } else {
            rays = [
                BoundaryRayCandidate(rayCamera: simd_normalize(simd_make_float3(-0.3, -0.6, 1.0)), confidence: 0.8),
                BoundaryRayCandidate(rayCamera: simd_normalize(simd_make_float3(0.0, -0.6, 1.0)), confidence: 0.9),
                BoundaryRayCandidate(rayCamera: simd_normalize(simd_make_float3(0.3, -0.6, 1.0)), confidence: 0.8)
            ]
        }
        
        floorplanEngine.processFrame(
            pose: pose,
            rays: rays,
            headingDeg: currentHeading,
            quality: latestQualityAssessment
        )
        guidance.update(
            pose: pose,
            quality: latestQuality,
            trackingState: manager.activeTrackingText,
            coveragePct: floorplanEngine.floorplanMap.coveragePercentage
        )
    }
    
    public func captureManager(_ manager: CaptureSessionManager, didRecordKeyframe index: Int, total: Int) {}
    public func captureManager(_ manager: CaptureSessionManager, didChangeTrackingStatus text: String, isWarning: Bool) {}
    
    public func computeQualityAudit() -> CaptureQualityAudit {
        let baseline = max(
            manager.translationBaselineMeters,
            guidance.translationBaselineMeters,
            floorplanEngine.latestParallax.translationBaselineM
        )
        return CaptureQualityAudit(
            keyframeCount: manager.keyframeCount,
            durationSeconds: Double(elapsedSeconds),
            meanSharpness: latestQuality.sharpnessScore,
            meanExposure: latestQuality.exposureScore * 255.0,
            trackingStabilityPct: manager.isTrackingDegraded ? 65.0 : 96.0,
            translationalBaselineM: baseline,
            angularCoverageDeg: min(360.0, floorplanEngine.floorplanMap.coveragePercentage * 3.6),
            wallBoundaryCoveragePct: floorplanEngine.floorplanMap.coveragePercentage
        )
    }
    
    // MARK: - Timer
    private func startTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            DispatchQueue.main.async {
                guard let self = self else { return }
                if !self.manager.isPaused {
                    self.elapsedSeconds += 1
                }
            }
        }
    }
    
    private func stopTimer() {
        timer?.invalidate()
        timer = nil
    }
}

public struct CaptureView: View {
    public let session: CaptureSession
    public let onFinishCapture: (URL, CaptureQualityAudit) -> Void
    public let onCancel: () -> Void
    
    @StateObject private var coordinator = CaptureCoordinator()
    @State private var showAIOverlay: Bool = true
    @State private var showDepthHeatmap: Bool = false
    @State private var isFloorplanExpanded: Bool = false
    @State private var showPrematureFinishAlert: Bool = false

    public init(
        session: CaptureSession,
        onFinishCapture: @escaping (URL, CaptureQualityAudit) -> Void,
        onCancel: @escaping () -> Void
    ) {
        self.session = session
        self.onFinishCapture = onFinishCapture
        self.onCancel = onCancel
    }

    public var body: some View {
        ZStack {
            // 1. Live ARKit Fullscreen Camera View
            ARLiveCameraRepresentable(session: coordinator.manager.arController.session)
                .ignoresSafeArea()
            
            // 1b. Real-Time AR Segmentation & Structural Boundary Overlay
            if showAIOverlay {
                ARSegmentationOverlay(
                    segmentation: coordinator.latestSegmentation,
                    boundaries: coordinator.latestBoundaries,
                    quality: coordinator.latestQualityAssessment,
                    showMasks: true
                )
                .ignoresSafeArea()
                
                // 1c. On-Device Furniture & Monocular Depth AI Overlay
                AIObjectOverlayView(
                    detectedObjects: coordinator.sceneManager.detectedObjects,
                    trackedFurniture: coordinator.sceneManager.trackedFurniture,
                    depthResult: coordinator.sceneManager.latestDepthResult,
                    showDepthHeatmap: showDepthHeatmap
                )
                .ignoresSafeArea()
            }
            
            // 2. HUD & Mini-map Overlay Layer
            VStack(spacing: 0) {
                topHeaderBar
                
                if coordinator.manager.isTrackingDegraded {
                    trackingDegradedBanner
                        .padding(.top, 14)
                } else {
                    ScanningHUD(
                        instruction: coordinator.floorplanEngine.latestInstruction,
                        parallax: coordinator.floorplanEngine.latestParallax,
                        qualityAudit: coordinator.floorplanEngine.latestQualityAudit
                    )
                    .padding(.top, 14)
                }
                
                Spacer()
                
                bottomControls
            }
            
            // 3. Fullscreen Expanded 2D Floorplan Modal
            if isFloorplanExpanded {
                Color.black.opacity(0.85)
                    .ignoresSafeArea()
                    .onTapGesture { isFloorplanExpanded = false }
                
                VStack(spacing: 16) {
                    HStack {
                        Text("Provisional 2D Room Floorplan")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(.white)
                        Spacer()
                        Button(action: { isFloorplanExpanded = false }) {
                            Image(systemName: "xmark.circle.fill")
                                .font(.system(size: 24))
                                .foregroundColor(.white.opacity(0.8))
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 50)
                    
                    LiveFloorplanView(floorplanMap: coordinator.floorplanEngine.floorplanMap, isExpanded: true)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .padding(.horizontal, 16)
                        .padding(.bottom, 40)
                }
            }
        }
        .alert("Mandatory 90% Quality Gate Required (IOS-008)", isPresented: $showPrematureFinishAlert) {
            Button("Keep Scanning", role: .cancel) {}
        } message: {
            let audit = coordinator.floorplanEngine.latestQualityAudit
            let warnings = audit.preFinishWarnings
            let text = warnings.isEmpty ? "Additional room observations required." : warnings.joined(separator: "\n• ")
            Text("Current Quality Score: \(Int(audit.overallScore))% (Mandatory Gate: 90%)\n\n• \(text)\n\nFinal submission is locked until the score reaches 90% and all critical checks pass.")
        }
        .onAppear {
            coordinator.startLiveCamera()
        }
        .onDisappear {
            coordinator.pauseLiveCamera()
        }
        .onReceive(coordinator.manager.$completedPackageURL) { packageURL in
            if let url = packageURL {
                let audit = coordinator.computeQualityAudit()
                onFinishCapture(url, audit)
            }
        }
    }
    
    // MARK: - Top Header Bar
    private var topHeaderBar: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 6) {
                TrackingStatusPill(
                    state: coordinator.manager.activeTrackingText,
                    isWarning: coordinator.manager.isTrackingDegraded
                )
                
                // Session Info Pill
                HStack(spacing: 6) {
                    Text(session.roomName)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundColor(.white)
                    Text("•")
                        .foregroundColor(.white.opacity(0.6))
                    Text(session.projectName)
                        .font(.system(size: 12))
                        .foregroundColor(.white.opacity(0.8))
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(.ultraThinMaterial)
                .cornerRadius(12)
            }
            
            Spacer()
            
            // AI Mask Overlay Toggle Button
            Button(action: { showAIOverlay.toggle() }) {
                Image(systemName: showAIOverlay ? "eye.fill" : "eye.slash.fill")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(showAIOverlay ? .green : .white.opacity(0.6))
                    .frame(width: 34, height: 34)
                    .background(.ultraThinMaterial)
                    .clipShape(Circle())
            }
            
            // Depth Heatmap Toggle Button
            Button(action: { showDepthHeatmap.toggle() }) {
                Image(systemName: showDepthHeatmap ? "square.3.layers.3d.down.right.slash" : "square.3.layers.3d.down.right")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(showDepthHeatmap ? .cyan : .white.opacity(0.6))
                    .frame(width: 34, height: 34)
                    .background(.ultraThinMaterial)
                    .clipShape(Circle())
            }
            
            // Live Top-Down Floorplan Mini-Map (tap to expand)
            LiveFloorplanView(floorplanMap: coordinator.floorplanEngine.floorplanMap, isExpanded: false)
                .frame(width: 130, height: 100)
                .onTapGesture {
                    withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                        isFloorplanExpanded = true
                    }
                }
        }
        .padding(.horizontal, 16)
        .padding(.top, 14)
    }
    
    // MARK: - Tracking Degraded Alert Banner
    private var trackingDegradedBanner: some View {
        HStack(spacing: 10) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(VastuColors.brandError)
                .font(.system(size: 16))
            Text("⚠️ Tracking degraded — slow movement, keep floor in view")
                .font(.system(size: 12, weight: .bold))
                .foregroundColor(.white)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(Color.red.opacity(0.75))
        .cornerRadius(12)
    }
    
    // MARK: - Bottom Controls
    private var bottomControls: some View {
        VStack(spacing: 16) {
            // Live Stats (Keyframes, Baseline, Timer)
            if coordinator.manager.isRecording {
                HStack(spacing: 16) {
                    statPill(label: "KEYFRAMES", value: "\(coordinator.manager.keyframeCount)")
                    statPill(label: "BASELINE", value: String(format: "%.2f m", max(coordinator.manager.translationBaselineMeters, coordinator.guidance.translationBaselineMeters, coordinator.floorplanEngine.latestParallax.translationBaselineM)))
                    statPill(label: "DROPPED", value: "\(coordinator.manager.droppedFrameCount)")
                    statPill(label: "DURATION", value: formatTime(coordinator.elapsedSeconds))
                }
            }
            
            // Shutter Controls (Cancel, Record/Stop, Pause/Resume, Finish)
            HStack(spacing: 28) {
                // Cancel Button
                Button(action: onCancel) {
                    Image(systemName: "xmark")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(.white)
                        .frame(width: 44, height: 44)
                        .background(.ultraThinMaterial)
                        .clipShape(Circle())
                }
                .disabled(coordinator.manager.isRecording)
                .opacity(coordinator.manager.isRecording ? 0.3 : 1.0)
                
                // Pause / Resume Button
                if coordinator.manager.isRecording {
                    Button(action: { coordinator.togglePause() }) {
                        Image(systemName: coordinator.manager.isPaused ? "play.fill" : "pause.fill")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundColor(.white)
                            .frame(width: 44, height: 44)
                            .background(.ultraThinMaterial)
                            .clipShape(Circle())
                    }
                } else {
                    Spacer().frame(width: 44)
                }
                
                // Primary Shutter Record Button
                Button(action: toggleRecording) {
                    ZStack {
                        Circle()
                            .strokeBorder(coordinator.manager.isRecording ? Color.red : Color.white, lineWidth: 4)
                            .frame(width: 82, height: 82)
                        
                        if coordinator.manager.isRecording {
                            RoundedRectangle(cornerRadius: 8)
                                .fill(coordinator.manager.isPaused ? Color.orange : Color.red)
                                .frame(width: 32, height: 32)
                        } else {
                            Circle()
                                .fill(VastuColors.brandBronze)
                                .frame(width: 68, height: 68)
                        }
                    }
                }
                .sensoryFeedback(.impact(weight: .heavy), trigger: coordinator.manager.isRecording)
                
                // Finish / Complete Button
                if coordinator.manager.isRecording {
                    Button(action: {
                        requestFinishCapture()
                    }) {
                        Image(systemName: "checkmark")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundColor(.white)
                            .frame(width: 44, height: 44)
                            .background(VastuColors.brandSuccess)
                            .clipShape(Circle())
                    }
                } else {
                    Spacer().frame(width: 44)
                }
            }
            
            Text(instructionsText)
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(.white.opacity(0.8))
        }
        .padding(.bottom, 36)
        .frame(maxWidth: .infinity)
        .background(
            LinearGradient(
                colors: [Color.clear, Color.black.opacity(0.88)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea(edges: .bottom)
        )
    }
    
    private var instructionsText: String {
        if !coordinator.manager.isRecording {
            return "Position phone at doorway and tap Start to record room"
        } else if coordinator.manager.isPaused {
            return "Capture paused • Tap Play to resume walking"
        } else {
            return "Walk along wall perimeter (~0.3 m/s) • Tap Checkmark when done"
        }
    }
    
    private func statPill(label: String, value: String) -> some View {
        VStack(spacing: 2) {
            Text(label)
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .foregroundColor(.white.opacity(0.6))
            Text(value)
                .font(.system(size: 14, weight: .bold, design: .monospaced))
                .foregroundColor(VastuColors.brandIvory)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(.ultraThinMaterial)
        .cornerRadius(10)
    }
    
    // MARK: - Actions
    private func toggleRecording() {
        if coordinator.manager.isRecording {
            requestFinishCapture()
        } else {
            do {
                try coordinator.startRecording(session: session)
            } catch {
                print("❌ Failed to start recording: \(error)")
            }
        }
    }
    
    private func requestFinishCapture() {
        let audit = coordinator.floorplanEngine.latestQualityAudit
        if audit.submissionAllowed {
            finishCapture()
        } else {
            showPrematureFinishAlert = true
        }
    }
    
    private func finishCapture() {
        do {
            _ = try coordinator.finishRecording()
        } catch {
            print("❌ Failed to finish recording: \(error)")
        }
    }
    
    private func formatTime(_ sec: Int) -> String {
        let m = sec / 60
        let s = sec % 60
        return String(format: "%02d:%02d", m, s)
    }
}

public struct ARLiveCameraRepresentable: UIViewRepresentable {
    public let session: ARSession
    public init(session: ARSession) {
        self.session = session
    }
    public func makeUIView(context: Context) -> ARSCNView {
        let view = ARSCNView(frame: .zero)
        view.session = session
        view.automaticallyUpdatesLighting = true
        return view
    }
    public func updateUIView(_ view: ARSCNView, context: Context) {}
}

// Backward compatibility alias for existing code
public typealias LiveSpatialCaptureView = CaptureView
