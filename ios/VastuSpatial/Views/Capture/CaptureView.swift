import SwiftUI
import AVFoundation
import Network

public struct CaptureView: View {
    let project: ProjectDTO
    let floor: FloorDTO?
    @Environment(\.presentationMode) var presentationMode
    
    @StateObject private var cameraManager = AVCameraManager()
    @StateObject private var motionManager = MotionSensorManager()
    @StateObject private var qualityEngine = CaptureQualityEngine()
    @StateObject private var permissionManager = PermissionManager.shared
    @ObservedObject private var storageManager = LocalCaptureStorageManager.shared
    @ObservedObject private var uploadManager = ResumableUploadManager.shared
    @StateObject private var neuralNet = VastuSpatialMobileNet.shared
    
    @State private var currentSessionDirectory: URL?
    @State private var recordingStartNs: Int64 = 0
    @State private var statusText: String = "Align camera and tap Record to start 3D scan"
    @State private var errorMessage: String?
    @State private var availableStorageMB: Int64 = StorageMonitor.getAvailableStorageMB()
    
    // Telemetry: Battery & WiFi
    @State private var batteryLevel: Int = 100
    @State private var isCharging: Bool = false
    @State private var isWifiConnected: Bool = true
    @State private var isDevBatteryBypass: Bool = false
    
    // Expandable SOP & Speech Synthesizer
    @State private var isSopExpanded: Bool = false
    @State private var speechSynthesizer = AVSpeechSynthesizer()
    @State private var isSpeakingSop: Bool = false
    
    // Construction Sensor Permissions Sheet
    @State private var showPermissionNotice: Bool = false
    
    private let pathMonitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "VastuNetworkMonitor")
    
    public init(project: ProjectDTO, floor: FloorDTO? = nil) {
        self.project = project
        self.floor = floor
    }
    
    private var isBatteryAllowed: Bool {
        return batteryLevel > 80 || isDevBatteryBypass
    }
    
    public var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            
            // 1. Full-Screen Camera Viewfinder
            CameraPreviewView(session: cameraManager.captureSession)
                .ignoresSafeArea()
            
            // 2. Center Scanning Reticle & Corner Bounds
            VStack {
                Spacer()
                ZStack {
                    // Outer targeting ring
                    Circle()
                        .stroke(
                            cameraManager.isRecording ? VastuColors.brandGold : Color.white.opacity(0.4),
                            style: StrokeStyle(lineWidth: cameraManager.isRecording ? 2.5 : 1.5, dash: cameraManager.isRecording ? [] : [6, 4])
                        )
                        .frame(width: 110, height: 110)
                        .scaleEffect(cameraManager.isRecording ? 1.05 : 1.0)
                        .animation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true), value: cameraManager.isRecording)
                    
                    // Crosshair tick marks
                    Rectangle().fill(Color.white.opacity(0.5)).frame(width: 12, height: 1.5)
                    Rectangle().fill(Color.white.opacity(0.5)).frame(width: 1.5, height: 12)
                    
                    if cameraManager.isRecording {
                        Circle()
                            .fill(VastuColors.brandGold.opacity(0.18))
                            .frame(width: 96, height: 96)
                    }
                }
                Spacer()
            }
            .allowsHitTesting(false)
            
            // 3. Floating HUD & Controls Overlay Layer
            VStack(spacing: 0) {
                // Unified Glassmorphic Header Bar
                HStack(spacing: 10) {
                    // Clean Custom Back Button (Replaces default bar)
                    Button(action: { presentationMode.wrappedValue.dismiss() }) {
                        Image(systemName: "chevron.left")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundColor(.white)
                            .frame(width: 40, height: 40)
                            .background(.ultraThinMaterial)
                            .clipShape(Circle())
                            .overlay(Circle().stroke(Color.white.opacity(0.2), lineWidth: 1))
                    }
                    .disabled(cameraManager.isRecording)
                    .opacity(cameraManager.isRecording ? 0.3 : 1.0)
                    
                    // Center Project / Floor Name & Live Recording Monospace Counter
                    HStack(spacing: 8) {
                        if cameraManager.isRecording {
                            Circle()
                                .fill(Color.red)
                                .frame(width: 8, height: 8)
                                .opacity(0.9)
                        }
                        
                        Text(floor != nil ? "\(project.name) • \(floor!.name)" : project.name)
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundColor(VastuColors.brandIvory)
                            .lineLimit(1)
                        
                        if cameraManager.isRecording {
                            Text(formatSeconds(cameraManager.recordedSeconds))
                                .font(.system(size: 13, weight: .bold, design: .monospaced))
                                .foregroundColor(.white)
                        }
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 8)
                    .background(.ultraThinMaterial)
                    .cornerRadius(20)
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(cameraManager.isRecording ? Color.red.opacity(0.8) : VastuColors.brandBronze.opacity(0.4), lineWidth: 1)
                    )
                    
                    Spacer(minLength: 0)
                    
                    // Right Status Badge Pill (WiFi, Battery, Exposure Lock)
                    HStack(spacing: 8) {
                        // AE Lock Toggle
                        Button(action: { cameraManager.toggleExposureLock() }) {
                            Image(systemName: cameraManager.isExposureLocked ? "lock.fill" : "lock.open")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(cameraManager.isExposureLocked ? VastuColors.brandGold : .white.opacity(0.9))
                        }
                        
                        // WiFi Indicator
                        Image(systemName: isWifiConnected ? "wifi" : "wifi.slash")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(isWifiConnected ? VastuColors.brandSuccess : VastuColors.brandError)
                        
                        // Battery Badge (Tap to bypass)
                        Button(action: { withAnimation { isDevBatteryBypass.toggle() } }) {
                            HStack(spacing: 3) {
                                Image(systemName: isCharging ? "battery.100.bolt" : (batteryLevel > 80 ? "battery.100" : "battery.25"))
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(isBatteryAllowed ? VastuColors.brandSuccess : VastuColors.brandError)
                                Text("\(batteryLevel)%")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(isBatteryAllowed ? .white : VastuColors.brandError)
                            }
                        }
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(.ultraThinMaterial)
                    .cornerRadius(20)
                    .overlay(RoundedRectangle(cornerRadius: 20).stroke(Color.white.opacity(0.2), lineWidth: 1))
                }
                .padding(.horizontal, 16)
                .padding(.top, 12)
                
                // Permission Warning Chip
                if !permissionManager.allPermissionsGranted {
                    Button(action: { permissionManager.requestAllPermissions() }) {
                        HStack(spacing: 6) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .font(.system(size: 12))
                                .foregroundColor(VastuColors.brandWarning)
                            Text("Camera / Location permissions required • Tap to enable")
                                .font(.system(size: 12, weight: .semibold))
                                .foregroundColor(.white)
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 7)
                        .background(Color.black.opacity(0.8))
                        .cornerRadius(16)
                        .overlay(RoundedRectangle(cornerRadius: 16).stroke(VastuColors.brandGold, lineWidth: 1))
                    }
                    .padding(.top, 10)
                }
                
                // SOP Guidance Floating Bar
                let currentStep = qualityEngine.sopSteps[qualityEngine.currentSOPIndex]
                let sopSpeechText = "Step \(currentStep.id): \(currentStep.title). \(currentStep.description)"
                
                VStack(spacing: 6) {
                    HStack(spacing: 10) {
                        Button(action: { qualityEngine.previousSOPStep() }) {
                            Image(systemName: "chevron.left")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(qualityEngine.currentSOPIndex > 0 ? VastuColors.brandGold : Color.white.opacity(0.3))
                        }
                        .disabled(qualityEngine.currentSOPIndex == 0)
                        
                        Button(action: { withAnimation(.spring(response: 0.3)) { isSopExpanded.toggle() } }) {
                            HStack(spacing: 6) {
                                Text("STEP \(currentStep.id)/\(qualityEngine.sopSteps.count):")
                                    .font(.system(size: 11, weight: .heavy))
                                    .foregroundColor(VastuColors.brandGold)
                                Text(currentStep.title)
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundColor(.white)
                                    .lineLimit(1)
                                Image(systemName: isSopExpanded ? "chevron.up" : "chevron.down")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(VastuColors.brandGold)
                            }
                        }
                        
                        Button(action: { qualityEngine.nextSOPStep() }) {
                            Image(systemName: "chevron.right")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(qualityEngine.currentSOPIndex < qualityEngine.sopSteps.count - 1 ? VastuColors.brandGold : Color.white.opacity(0.3))
                        }
                        .disabled(qualityEngine.currentSOPIndex == qualityEngine.sopSteps.count - 1)
                        
                        // Speech Guide Button
                        Button(action: {
                            if isSpeakingSop {
                                speechSynthesizer.stopSpeaking(at: .immediate)
                                isSpeakingSop = false
                            } else {
                                let utterance = AVSpeechUtterance(string: sopSpeechText)
                                utterance.rate = 0.48
                                utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
                                speechSynthesizer.speak(utterance)
                                isSpeakingSop = true
                                DispatchQueue.main.asyncAfter(deadline: .now() + 5) {
                                    isSpeakingSop = false
                                }
                            }
                        }) {
                            Image(systemName: isSpeakingSop ? "speaker.wave.3.fill" : "speaker.wave.2")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(isSpeakingSop ? VastuColors.brandGold : .white)
                                .padding(5)
                                .background(Color.white.opacity(0.15))
                                .clipShape(Circle())
                        }
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 8)
                    .background(.ultraThinMaterial)
                    .cornerRadius(20)
                    .overlay(RoundedRectangle(cornerRadius: 20).stroke(VastuColors.brandBronze.opacity(0.5), lineWidth: 1))
                    
                    if isSopExpanded {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(currentStep.description)
                                .font(.system(size: 12))
                                .foregroundColor(.white.opacity(0.95))
                                .multilineTextAlignment(.center)
                        }
                        .padding(10)
                        .frame(maxWidth: 320)
                        .background(Color.black.opacity(0.85))
                        .cornerRadius(12)
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.15), lineWidth: 1))
                        .transition(.opacity.combined(with: .scale(scale: 0.95)))
                    }
                }
                .padding(.top, 10)
                
                // Real-time Motion Quality Warning (Only shown during active recording when needed)
                if cameraManager.isRecording {
                    let qualityFeedback = qualityEngine.qualityFeedback
                    if qualityFeedback.level != .optimal {
                        HStack(spacing: 6) {
                            Image(systemName: "exclamationmark.circle.fill")
                                .font(.system(size: 12))
                            Text(qualityFeedback.title + " • " + qualityFeedback.correctiveAction)
                                .font(.system(size: 12, weight: .bold))
                        }
                        .foregroundColor(.white)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 7)
                        .background(getQualityColor(qualityFeedback.level).opacity(0.9))
                        .cornerRadius(16)
                        .padding(.top, 8)
                        .transition(.opacity)
                    }
                }
                
                Spacer()
                
                // Bottom Control Bar
                VStack(spacing: 12) {
                    // Status Subtitle Line
                    if let error = errorMessage {
                        Text(error)
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(VastuColors.brandError)
                            .padding(.horizontal, 20)
                    } else {
                        Text(!isBatteryAllowed ? "Battery low (\(batteryLevel)%). Tap battery badge to bypass." : statusText)
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(!isBatteryAllowed ? VastuColors.brandError : .white.opacity(0.9))
                            .lineLimit(1)
                    }
                    
                    // Main Shutter Button
                    Button(action: { toggleRecording() }) {
                        ZStack {
                            Circle()
                                .stroke(Color.white, lineWidth: 4)
                                .frame(width: 76, height: 76)
                            
                            if cameraManager.isRecording {
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(VastuColors.brandError)
                                    .frame(width: 30, height: 30)
                            } else if !isBatteryAllowed {
                                Image(systemName: "lock.fill")
                                    .font(.system(size: 22))
                                    .foregroundColor(.gray)
                            } else {
                                Circle()
                                    .fill(VastuColors.brandGold)
                                    .frame(width: 62, height: 62)
                            }
                        }
                    }
                    .disabled(!isBatteryAllowed && !cameraManager.isRecording)
                    
                    // Storage Indicator Subtitle
                    Text("\(availableStorageMB / 1024) GB storage available")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(.white.opacity(0.6))
                }
                .padding(.top, 14)
                .padding(.bottom, 24)
                .frame(maxWidth: .infinity)
                .background(
                    LinearGradient(
                        gradient: Gradient(colors: [Color.clear, Color.black.opacity(0.95)]),
                        startPoint: .top,
                        endPoint: .bottom
                    )
                    .ignoresSafeArea(edges: .bottom)
                )
            }
        }
        .navigationBarBackButtonHidden(true)
        .toolbar(.hidden, for: .navigationBar)
        .onAppear {
            permissionManager.requestAllPermissions()
            
            UIDevice.current.isBatteryMonitoringEnabled = true
            let level = UIDevice.current.batteryLevel
            if level >= 0 {
                batteryLevel = Int(level * 100)
            } else {
                batteryLevel = 100 // Default for simulator
            }
            isCharging = UIDevice.current.batteryState == .charging || UIDevice.current.batteryState == .full
            
            pathMonitor.pathUpdateHandler = { path in
                DispatchQueue.main.async {
                    isWifiConnected = path.usesInterfaceType(.wifi) || path.usesInterfaceType(.wiredEthernet) || path.status == .satisfied
                }
            }
            pathMonitor.start(queue: monitorQueue)
            
            cameraManager.startSession()
        }
        .onDisappear {
            pathMonitor.cancel()
            speechSynthesizer.stopSpeaking(at: .immediate)
            cameraManager.stopSession()
        }
        .onChange(of: permissionManager.cameraAuthorized) { _, isAuth in
            if isAuth {
                cameraManager.startSession()
            }
        }
    }
    
    private func toggleRecording() {
        if cameraManager.isRecording {
            statusText = "Finalizing video capture & writing file headers..."
            
            Task {
                do {
                    let videoURL = try await cameraManager.stopRecordingAsync()
                    _ = Int64(mach_absolute_time())
                    let _ = motionManager.stopRecording()
                    
                    await MainActor.run {
                        statusText = "Validating video stream & packaging capture..."
                    }
                    
                    guard let sessionDir = currentSessionDirectory else { return }
                    let imuURL = sessionDir.appendingPathComponent("imu_stream.csv")
                    let manifestURL = sessionDir.appendingPathComponent("manifest.json")
                    
                    let videoValidation = await VideoValidator.validateVideo(fileURL: videoURL)
                    guard videoValidation.isValid else {
                        await MainActor.run {
                            errorMessage = videoValidation.errorMessage ?? "Video corrupted or missing"
                        }
                        return
                    }
                    
                    let timeStamp = DateFormatter.localizedString(from: Date(), dateStyle: .short, timeStyle: .medium)
                    let captureId = UUID().uuidString
                    let metadata: [String: String] = [
                        "projectId": project.id,
                        "projectName": project.name,
                        "floorId": floor?.id ?? "",
                        "floorName": floor?.name ?? "",
                        "sopCompletedSteps": "\(qualityEngine.currentSOPIndex + 1)",
                        "sopCoverageScore": String(format: "%.2f", qualityEngine.getCoverageQualityScore()),
                        "batteryLevel": "\(batteryLevel)",
                        "wifiConnected": "\(isWifiConnected)"
                    ]
                    
                    let _ = try await storageManager.packageAndIndexCapture(
                        captureId: captureId,
                        projectId: project.id,
                        sessionName: "Scan_\(timeStamp)",
                        sessionDir: sessionDir,
                        videoURL: videoURL,
                        imuURL: imuURL,
                        manifestURL: manifestURL,
                        metadata: metadata
                    )
                    
                    await MainActor.run {
                        statusText = "Capture packaged & indexed! Enqueueing upload..."
                        uploadManager.startUpload(captureId: captureId, fileURL: videoURL)
                        
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                            presentationMode.wrappedValue.dismiss()
                        }
                    }
                } catch {
                    await MainActor.run {
                        errorMessage = "Packaging error: \(error.localizedDescription)"
                    }
                }
            }
        } else {
            errorMessage = nil
            guard StorageMonitor.hasSufficientStorage(minMB: 200) else {
                errorMessage = "Insufficient storage: Less than 200MB available"
                return
            }
            
            let captureId = UUID().uuidString
            let sessionDir = storageManager.createCaptureDirectory(captureId: captureId)
            currentSessionDirectory = sessionDir
            let videoURL = sessionDir.appendingPathComponent("rgb_video.mp4")
            let imuURL = sessionDir.appendingPathComponent("imu_stream.csv")
            
            recordingStartNs = Int64(mach_absolute_time())
            motionManager.startRecording(outputURL: imuURL)
            cameraManager.startRecording(to: videoURL) { result in
                switch result {
                case .success:
                    break
                case .failure(let error):
                    DispatchQueue.main.async {
                        self.errorMessage = error.localizedDescription
                    }
                }
            }
            statusText = "Recording active: Follow SOP guidelines"
        }
    }
    
    private func formatSeconds(_ secs: Int) -> String {
        let m = secs / 60
        let s = secs % 60
        return String(format: "%02d:%02d", m, s)
    }
    
    private func getQualityColor(_ level: QualityLevel) -> Color {
        switch level {
        case .optimal: return VastuColors.brandSuccess
        case .motionBlur: return VastuColors.brandError
        case .insufficientOverlap: return VastuColors.brandWarning
        case .lowFeatureDensity: return VastuColors.brandWarning
        case .lowLight: return VastuColors.brandWarning
        case .rescanRequired: return VastuColors.brandError
        }
    }
}
