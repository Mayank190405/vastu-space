import SwiftUI
import ARKit

/// Intelligent Spatial Capture Dashboard implementing Landscape Split-View, Live Room Map, Real-Time 90% Quality Gate, and Voice Guidance (IOS-011)
public struct CaptureDashboardView: View {
    public let session: CaptureSession
    public let onFinishCapture: (URL, ComprehensiveCaptureAudit) -> Void
    public let onCancel: () -> Void
    
    @StateObject private var coordinator = CaptureCoordinator()
    @StateObject private var tts = TTSGuidanceController.shared
    @StateObject private var rescan = GuidedRescanController.shared
    
    @State private var showAIOverlay: Bool = true
    @State private var showDepthHeatmap: Bool = false
    @State private var showPreSubmissionReview: Bool = false
    @State private var showPrematureFinishAlert: Bool = false
    
    public init(
        session: CaptureSession,
        onFinishCapture: @escaping (URL, ComprehensiveCaptureAudit) -> Void,
        onCancel: @escaping () -> Void
    ) {
        self.session = session
        self.onFinishCapture = onFinishCapture
        self.onCancel = onCancel
    }
    
    public var body: some View {
        GeometryReader { geo in
            let isLandscape = geo.size.width > geo.size.height
            
            ZStack {
                Color(red: 0.03, green: 0.04, blue: 0.06).ignoresSafeArea()
                
                VStack(spacing: 0) {
                    // 1. Top Status Bar (Score, Tracking, Session, AI Status)
                    topStatusBar
                        .frame(height: 52)
                        .background(Color.black.opacity(0.85))
                    
                    // 2. Main Capture Viewport: Left Live Camera | Right Live Room Map
                    if isLandscape {
                        HStack(spacing: 0) {
                            // Left Panel: Live Camera & AR Overlays (55% width)
                            leftCameraPanel
                                .frame(width: geo.size.width * 0.54)
                            
                            // Subtle Divider
                            Rectangle()
                                .fill(Color.white.opacity(0.12))
                                .frame(width: 1)
                            
                            // Right Panel: Live Room Map (46% width)
                            rightRoomMapPanel
                                .frame(width: geo.size.width * 0.46 - 1)
                        }
                    } else {
                        // Portrait Fallback: Stacked Camera + Map
                        VStack(spacing: 0) {
                            leftCameraPanel
                                .frame(height: geo.size.height * 0.52)
                            rightRoomMapPanel
                                .frame(height: geo.size.height * 0.38)
                        }
                    }
                    
                    // 3. Bottom Control Bar
                    bottomControlBar
                        .frame(height: 64)
                        .background(Color.black.opacity(0.92))
                }
                
                // Voice Guidance Subtitle Banner (TTS Display IOS-010)
                if !tts.currentSpokenText.isEmpty {
                    VStack {
                        Spacer().frame(height: 58)
                        spokenSubtitleBanner
                        Spacer()
                    }
                    .transition(.move(edge: .top).combined(with: .opacity))
                }
            }
        }
        .ignoresSafeArea(.keyboard)
        .alert("Minimum 90% Quality Gate Required", isPresented: $showPrematureFinishAlert) {
            Button("Continue Recording", role: .cancel) {}
            if let rescanTarget = coordinator.floorplanEngine.latestQualityAudit.issues.first?.regionId {
                Button("Rescan \(rescanTarget)") {
                    rescan.selectRegion(id: rescanTarget)
                    rescan.startRescan { true }
                }
            }
        } message: {
            let audit = coordinator.floorplanEngine.latestQualityAudit
            Text("Your current capture quality score is \(Int(audit.overallScore))%. Requirement IOS-008 mandates a validated score of at least 90% to prevent reconstruction failure. Please rescan highlighted regions.")
        }
        .sheet(isPresented: $showPreSubmissionReview) {
            PreSubmissionValidationView(
                audit: coordinator.floorplanEngine.latestQualityAudit,
                sessionId: session.id,
                onProceedToUpload: {
                    showPreSubmissionReview = false
                    finishCaptureAndExport()
                },
                onTriggerRescan: { regionId in
                    showPreSubmissionReview = false
                    rescan.selectRegion(id: regionId)
                    rescan.startRescan { true }
                },
                onCancel: {
                    showPreSubmissionReview = false
                }
            )
        }
        .onChange(of: coordinator.floorplanEngine.latestInstruction.text) { newText in
            // Dispatch to TTS
            tts.speakInstruction(coordinator.floorplanEngine.latestInstruction)
        }
    }
    
    // MARK: - 1. Top Status Bar
    private var topStatusBar: some View {
        let audit = coordinator.floorplanEngine.latestQualityAudit
        let scoreColor: Color = {
            switch audit.visualState {
            case .green: return Color.green
            case .amber: return Color.orange
            case .red: return Color.red
            case .gray: return Color.gray
            }
        }()
        
        return HStack(spacing: 16) {
            // Prominent Quality Score Badge (IOS-008, IOS-011)
            HStack(spacing: 6) {
                Circle()
                    .fill(scoreColor)
                    .frame(width: 10, height: 10)
                
                Text("\(Int(audit.overallScore))%")
                    .font(.system(size: 20, weight: .black, design: .monospaced))
                    .foregroundColor(scoreColor)
                
                VStack(alignment: .leading, spacing: 1) {
                    Text("QUALITY")
                        .font(.system(size: 8, weight: .bold, design: .monospaced))
                        .foregroundColor(.white.opacity(0.6))
                    Text(audit.overallScore >= 90 ? "GATE PASSED" : "GATE: 90%")
                        .font(.system(size: 8, weight: .heavy))
                        .foregroundColor(scoreColor)
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(scoreColor.opacity(0.15))
            .cornerRadius(8)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(scoreColor.opacity(0.4), lineWidth: 1))
            
            // Session / Room Identifier
            VStack(alignment: .leading, spacing: 2) {
                Text(session.roomName.isEmpty ? "ROOM CAPTURE" : session.roomName.uppercased())
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(.white)
                Text(session.id)
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(.white.opacity(0.5))
            }
            
            Spacer()
            
            // Camera Tracking Status
            HStack(spacing: 5) {
                Image(systemName: coordinator.manager.isTrackingDegraded ? "exclamationmark.triangle.fill" : "location.fill")
                    .foregroundColor(coordinator.manager.isTrackingDegraded ? .orange : .green)
                    .font(.system(size: 10))
                Text(coordinator.manager.isTrackingDegraded ? "TRACKING LIMITED" : "6-DoF VIO NORMAL")
                    .font(.system(size: 9, weight: .bold, design: .monospaced))
                    .foregroundColor(coordinator.manager.isTrackingDegraded ? .orange : .white.opacity(0.85))
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Color.white.opacity(0.08))
            .cornerRadius(6)
            
            // Local AI Status
            HStack(spacing: 5) {
                Circle().fill(Color.green).frame(width: 6, height: 6)
                Text("LOCAL AI ON-DEVICE")
                    .font(.system(size: 9, weight: .bold, design: .monospaced))
                    .foregroundColor(.white.opacity(0.85))
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Color.white.opacity(0.08))
            .cornerRadius(6)
            
            // Recording Duration
            if coordinator.manager.isRecording {
                HStack(spacing: 4) {
                    Circle().fill(Color.red).frame(width: 7, height: 7)
                    Text(formatTime(coordinator.elapsedSeconds))
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                        .foregroundColor(.white)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.red.opacity(0.2))
                .cornerRadius(6)
            }
        }
        .padding(.horizontal, 16)
    }
    
    // MARK: - 2a. Left Camera Panel
    private var leftCameraPanel: some View {
        ZStack {
            // 1. Live ARKit Fullscreen Camera View
            ARLiveCameraRepresentable(session: coordinator.manager.arController.session)
                .ignoresSafeArea()
            
            // 2. AR Segmentation & Structural Overlays
            if showAIOverlay {
                ARSegmentationOverlay(
                    segmentation: coordinator.latestSegmentation,
                    boundaries: coordinator.latestBoundaries,
                    quality: coordinator.latestQualityAssessment,
                    showMasks: true
                )
                
                AIObjectOverlayView(
                    detectedObjects: coordinator.sceneManager.detectedObjects,
                    trackedFurniture: coordinator.sceneManager.trackedFurniture,
                    depthResult: coordinator.sceneManager.latestDepthResult,
                    showDepthHeatmap: showDepthHeatmap
                )
            }
            
            // 3. Directional Cue Overlay (IOS-009)
            VStack {
                Spacer()
                directionalCueOverlay
                    .padding(.bottom, 12)
            }
            
            // 4. Tracking Warning Banner
            if coordinator.manager.isTrackingDegraded {
                VStack {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.orange)
                        Text("TRACKING DEGRADED — SLOW DOWN & KEEP FLOOR IN VIEW")
                            .font(.system(size: 11, weight: .heavy))
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color.black.opacity(0.85))
                    .cornerRadius(8)
                    .padding(.top, 10)
                    Spacer()
                }
            }
        }
    }
    
    // MARK: - 2b. Right Room Map Panel
    private var rightRoomMapPanel: some View {
        VStack(spacing: 0) {
            LiveRoomMapView(
                floorplanMap: coordinator.floorplanEngine.floorplanMap,
                availableRegions: rescan.availableRegions,
                selectedRegionId: rescan.selectedRegion?.id,
                onSelectRegion: { regId in
                    rescan.selectRegion(id: regId)
                }
            )
            
            // Selected Region Action Bar
            if let selected = rescan.selectedRegion {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(selected.name)
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(.white)
                        Text("Coverage: \(Int(selected.coveragePct))% • Quality: \(Int(selected.qualityScore))%")
                            .font(.system(size: 10))
                            .foregroundColor(.white.opacity(0.7))
                    }
                    Spacer()
                    Button(action: {
                        rescan.startRescan { true }
                    }) {
                        HStack(spacing: 4) {
                            Image(systemName: "arrow.triangle.2.circlepath")
                            Text("Rescan Area")
                        }
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.black)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color.cyan)
                        .cornerRadius(6)
                    }
                }
                .padding(10)
                .background(Color.black.opacity(0.88))
            }
        }
    }
    
    // MARK: - 3. Bottom Control Bar
    private var bottomControlBar: some View {
        let audit = coordinator.floorplanEngine.latestQualityAudit
        let submitReady = audit.submissionAllowed
        
        return HStack(spacing: 18) {
            // Voice Guidance Toggle (IOS-010)
            Button(action: { tts.toggleMute() }) {
                HStack(spacing: 5) {
                    Image(systemName: tts.isMuted ? "speaker.slash.fill" : "speaker.wave.2.fill")
                        .foregroundColor(tts.isMuted ? .orange : Color(red: 0.87, green: 0.72, blue: 0.45))
                    Text(tts.isMuted ? "VOICE OFF" : "VOICE ON")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundColor(.white)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 8)
                .background(Color.white.opacity(0.10))
                .cornerRadius(8)
            }
            
            // Shutter Start / Pause
            Button(action: toggleRecording) {
                HStack(spacing: 6) {
                    Circle()
                        .fill(coordinator.manager.isRecording ? (coordinator.manager.isPaused ? Color.orange : Color.red) : Color(red: 0.87, green: 0.72, blue: 0.45))
                        .frame(width: 14, height: 14)
                    Text(coordinator.manager.isRecording ? (coordinator.manager.isPaused ? "RESUME" : "PAUSE") : "START RECORDING")
                        .font(.system(size: 11, weight: .heavy, design: .monospaced))
                        .foregroundColor(.white)
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
                .background(Color.white.opacity(0.12))
                .cornerRadius(8)
            }
            
            Spacer()
            
            // Review Map / Pre-Submission Validation Button
            Button(action: { showPreSubmissionReview = true }) {
                HStack(spacing: 5) {
                    Image(systemName: "list.clipboard.fill")
                    Text("REVIEW QUALITY")
                }
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundColor(.white)
                .padding(.horizontal, 10)
                .padding(.vertical, 8)
                .background(Color.white.opacity(0.10))
                .cornerRadius(8)
            }
            
            // Mandatory 90% Submit Button (IOS-008: Disabled below 90%)
            Button(action: {
                if submitReady {
                    finishCaptureAndExport()
                } else {
                    showPrematureFinishAlert = true
                }
            }) {
                HStack(spacing: 6) {
                    Image(systemName: submitReady ? "checkmark.circle.fill" : "lock.fill")
                    Text("SUBMIT (≥90%)")
                }
                .font(.system(size: 12, weight: .black, design: .monospaced))
                .foregroundColor(submitReady ? .black : .white.opacity(0.4))
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(submitReady ? Color.green : Color.white.opacity(0.12))
                .cornerRadius(8)
            }
            .disabled(!submitReady && !coordinator.manager.isRecording)
        }
        .padding(.horizontal, 16)
    }
    
    // MARK: - Directional Cue Overlay
    private var directionalCueOverlay: some View {
        let instruction = coordinator.floorplanEngine.latestInstruction
        return HStack(spacing: 8) {
            Image(systemName: cueIcon(instruction.directionalCue))
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.cyan)
            Text(instruction.text)
                .font(.system(size: 12, weight: .bold))
                .foregroundColor(.white)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 7)
        .background(Color.black.opacity(0.80))
        .cornerRadius(20)
        .overlay(RoundedRectangle(cornerRadius: 20).stroke(Color.cyan.opacity(0.5), lineWidth: 1))
    }
    
    // MARK: - Spoken Subtitle Banner (TTS)
    private var spokenSubtitleBanner: some View {
        HStack(spacing: 8) {
            Image(systemName: "waveform")
                .font(.system(size: 13, weight: .bold))
                .foregroundColor(Color(red: 0.87, green: 0.72, blue: 0.45))
            Text(tts.currentSpokenText)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(.white)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(Color.black.opacity(0.88))
        .cornerRadius(12)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color(red: 0.87, green: 0.72, blue: 0.45).opacity(0.5), lineWidth: 1))
        .padding(.horizontal, 24)
    }
    
    private func cueIcon(_ cue: DirectionalCue) -> String {
        switch cue {
        case .forward: return "arrow.up"
        case .left: return "arrow.left"
        case .right: return "arrow.right"
        case .stepSideways: return "arrow.left.and.right"
        case .tiltDown: return "arrow.down.to.line"
        case .tiltUp: return "arrow.up.to.line"
        case .steady: return "hand.raised.fill"
        case .none: return "checkmark"
        }
    }
    
    private func toggleRecording() {
        if coordinator.manager.isRecording {
            coordinator.togglePause()
        } else {
            do {
                try coordinator.startRecording(session: session)
            } catch {
                print("❌ Failed to start recording: \(error)")
            }
        }
    }
    
    private func finishCaptureAndExport() {
        do {
            let url = try coordinator.finishRecording()
            let audit = coordinator.floorplanEngine.latestQualityAudit
            onFinishCapture(url, audit)
        } catch {
            print("❌ Failed to finalize capture: \(error)")
        }
    }
    
    private func formatTime(_ sec: Int) -> String {
        let m = sec / 60
        let s = sec % 60
        return String(format: "%02d:%02d", m, s)
    }
}

