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
            
            // 2. Subtle Scanning Reticle in Center
            VStack {
                Spacer()
                ZStack {
                    Circle()
                        .stroke(cameraManager.isRecording ? VastuColors.brandGold : Color.white.opacity(0.35), lineWidth: cameraManager.isRecording ? 2 : 1)
                        .frame(width: 90, height: 90)
                    
                    if cameraManager.isRecording {
                        Circle()
                            .fill(VastuColors.brandGold.opacity(0.15))
                            .frame(width: 80, height: 80)
                    }
                }
                Spacer()
            }
            .allowsHitTesting(false)
            
            // 3. Floating Overlays Layer
            VStack(spacing: 0) {
                // Top Floating Bar
                HStack(spacing: 8) {
                    // Back Button
                    Button(action: { presentationMode.wrappedValue.dismiss() }) {
                        Image(systemName: "chevron.left")
                            .font(.system(size: 15, weight: .bold))
                            .foregroundColor(.white)
                            .frame(width: 38, height: 38)
                            .background(Color.black.opacity(0.55))
                            .clipShape(Circle())
                    }
                    .disabled(cameraManager.isRecording)
                    .opacity(cameraManager.isRecording ? 0.3 : 1.0)
                    
                    Spacer()
                    
                    // Session Name & Live Recording Timer
                    HStack(spacing: 6) {
                        if cameraManager.isRecording {
                            Circle()
                                .fill(Color.red)
                                .frame(width: 8, height: 8)
                        }
                        Text(floor != nil ? "\(project.name) • \(floor!.name)" : project.name)
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(VastuColors.brandGold)
                            .lineLimit(1)
                        
                        Text(formatSeconds(cameraManager.recordedSeconds))
                            .font(.system(size: 13, weight: .bold, design: .monospaced))
                            .foregroundColor(cameraManager.isRecording ? .white : .white.opacity(0.9))
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 7)
                    .background(Color.black.opacity(0.65))
                    .cornerRadius(18)
                    .overlay(RoundedRectangle(cornerRadius: 18).stroke(cameraManager.isRecording ? Color.red.opacity(0.8) : VastuColors.brandGold.opacity(0.5), lineWidth: 1))
                    
                    Spacer()
                    
                    // Status Icons (WiFi, Battery, AE Lock)
                    HStack(spacing: 5) {
                        // WiFi Icon
                        Image(systemName: isWifiConnected ? "wifi" : "wifi.slash")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(isWifiConnected ? VastuColors.brandSuccess : VastuColors.brandError)
                            .padding(6)
                            .background(Color.black.opacity(0.55))
                            .clipShape(Circle())
                        
                        // Battery Pill (tap to toggle dev bypass)
                        Button(action: {
                            withAnimation { isDevBatteryBypass.toggle() }
                        }) {
                            HStack(spacing: 2) {
                                Image(systemName: isCharging ? "battery.100.bolt" : (batteryLevel > 80 ? "battery.100" : "battery.25"))
                                    .font(.system(size: 10))
                                    .foregroundColor(isBatteryAllowed ? VastuColors.brandSuccess : VastuColors.brandError)
                                Text("\(batteryLevel)%")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(isBatteryAllowed ? .white : VastuColors.brandError)
                            }
                            .padding(.horizontal, 6)
                            .padding(.vertical, 5)
                            .background(Color.black.opacity(0.55))
                            .cornerRadius(12)
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(isBatteryAllowed ? Color.clear : Color.red.opacity(0.8), lineWidth: 1))
                        }
                        
                        // AE Lock Button
                        Button(action: { cameraManager.toggleExposureLock() }) {
                            Image(systemName: cameraManager.isExposureLocked ? "lock.fill" : "lock.open")
                                .font(.system(size: 11))
                                .foregroundColor(cameraManager.isExposureLocked ? VastuColors.brandGold : .white)
                                .padding(6)
                                .background(Color.black.opacity(0.55))
                                .clipShape(Circle())
                        }
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 48)
                
                // Permissions Warning Floating Chip (if needed)
                if !permissionManager.allPermissionsGranted {
                    Button(action: {
                        permissionManager.requestAllPermissions()
                    }) {
                        HStack(spacing: 6) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .font(.system(size: 11))
                                .foregroundColor(VastuColors.brandWarning)
                            Text("Camera / GPS access needed • Tap to enable")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.white)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color(red: 0.15, green: 0.12, blue: 0.08).opacity(0.9))
                        .cornerRadius(14)
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandGold, lineWidth: 1))
                    }
                    .padding(.top, 6)
                }
                
                // Sleek Floating SOP Guide Pill
                let currentStep = qualityEngine.sopSteps[qualityEngine.currentSOPIndex]
                let sopSpeechText = "Step \(currentStep.id): \(currentStep.title). \(currentStep.description)"
                
                HStack(spacing: 8) {
                    // Prev Button
                    Button(action: { qualityEngine.previousSOPStep() }) {
                        Image(systemName: "chevron.left")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(qualityEngine.currentSOPIndex > 0 ? VastuColors.brandGold : Color.gray.opacity(0.5))
                    }
                    .disabled(qualityEngine.currentSOPIndex == 0)
                    
                    // Main Step Text
                    Button(action: { withAnimation { isSopExpanded.toggle() } }) {
                        HStack(spacing: 4) {
                            Text("Step \(currentStep.id):")
                                .font(.system(size: 11, weight: .heavy))
                                .foregroundColor(VastuColors.brandGold)
                            Text(currentStep.title)
                                .font(.system(size: 11, weight: .semibold))
                                .foregroundColor(.white)
                                .lineLimit(1)
                            Image(systemName: isSopExpanded ? "chevron.up" : "chevron.down")
                                .font(.system(size: 9, weight: .bold))
                                .foregroundColor(VastuColors.brandGold)
                        }
                    }
                    
                    // Next Button
                    Button(action: { qualityEngine.nextSOPStep() }) {
                        Image(systemName: "chevron.right")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(qualityEngine.currentSOPIndex < qualityEngine.sopSteps.count - 1 ? VastuColors.brandGold : Color.gray.opacity(0.5))
                    }
                    .disabled(qualityEngine.currentSOPIndex == qualityEngine.sopSteps.count - 1)
                    
                    // TTS Read Aloud Icon Button
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
                            DispatchQueue.main.asyncAfter(deadline: .now() + 6) {
                                isSpeakingSop = false
                            }
                        }
                    }) {
                        Image(systemName: isSpeakingSop ? "speaker.wave.3.fill" : "speaker.wave.2")
                            .font(.system(size: 11))
                            .foregroundColor(isSpeakingSop ? VastuColors.brandGold : .white)
                            .padding(4)
                            .background(Color.white.opacity(0.15))
                            .clipShape(Circle())
                    }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(Color.black.opacity(0.7))
                .cornerRadius(16)
                .overlay(RoundedRectangle(cornerRadius: 16).stroke(VastuColors.brandBronze.opacity(0.6), lineWidth: 1))
                .padding(.top, 6)
                
                // Collapsible Step Detail Card (Only visible when expanded)
                if isSopExpanded {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(currentStep.description)
                            .font(.system(size: 11))
                            .foregroundColor(.white.opacity(0.95))
                            .lineLimit(3)
                    }
                    .padding(8)
                    .frame(maxWidth: 320)
                    .background(Color.black.opacity(0.85))
                    .cornerRadius(8)
                    .padding(.top, 4)
                    .transition(.opacity.combined(with: .scale(scale: 0.95)))
                }
                
                // Real-time Motion Quality Warning (Only shown during active recording when needed)
                if cameraManager.isRecording {
                    let qualityFeedback = qualityEngine.qualityFeedback
                    if qualityFeedback.level != .optimal {
                        HStack(spacing: 5) {
                            Image(systemName: "exclamationmark.circle.fill")
                                .font(.system(size: 11))
                            Text(qualityFeedback.title + " • " + qualityFeedback.correctiveAction)
                                .font(.system(size: 11, weight: .bold))
                        }
                        .foregroundColor(.white)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(getQualityColor(qualityFeedback.level).opacity(0.9))
                        .cornerRadius(12)
                        .padding(.top, 6)
                        .transition(.opacity)
                    }
                }
                
                Spacer()
                
                // Floating Bottom Control Bar (Minimal & Translucent)
                VStack(spacing: 8) {
                    // Status Subtitle Line
                    if let error = errorMessage {
                        Text(error)
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(VastuColors.brandError)
                            .padding(.horizontal, 16)
                    } else {
                        Text(!isBatteryAllowed ? "Battery low (\(batteryLevel)%). Tap battery badge to bypass." : statusText)
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(!isBatteryAllowed ? VastuColors.brandError : .white.opacity(0.85))
                            .lineLimit(1)
                    }
                    
                    // Main Shutter Button
                    Button(action: {
                        toggleRecording()
                    }) {
                        ZStack {
                            Circle()
                                .stroke(Color.white.opacity(0.9), lineWidth: 3.5)
                                .frame(width: 70, height: 70)
                            
                            if cameraManager.isRecording {
                                RoundedRectangle(cornerRadius: 6)
                                    .fill(VastuColors.brandError)
                                    .frame(width: 28, height: 28)
                            } else if !isBatteryAllowed {
                                Image(systemName: "lock.fill")
                                    .font(.system(size: 20))
                                    .foregroundColor(.gray)
                            } else {
                                Circle()
                                    .fill(VastuColors.brandGold)
                                    .frame(width: 56, height: 56)
                            }
                        }
                    }
                    .disabled(!isBatteryAllowed && !cameraManager.isRecording)
                    
                    // Storage Indicator Subtitle
                    Text("\(availableStorageMB / 1024) GB storage available")
                        .font(.system(size: 9))
                        .foregroundColor(.white.opacity(0.5))
                }
                .padding(.top, 10)
                .padding(.bottom, 8)
                .frame(maxWidth: .infinity)
                .background(
                    LinearGradient(
                        gradient: Gradient(colors: [Color.clear, Color.black.opacity(0.85)]),
                        startPoint: .top,
                        endPoint: .bottom
                    )
                    .ignoresSafeArea(edges: .bottom)
                )
            }
        }
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
            // Stop recording with proper moov atom completion
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
                    
                    // Validate Video
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
            // Start recording
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
