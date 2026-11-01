import SwiftUI
import AVFoundation

public struct QRScannerView: View {
    @ObservedObject var authManager = SessionAuthorizationManager.shared
    public let onAuthorized: (CaptureSession) -> Void
    
    @State private var isCameraAuthorized: Bool = false
    @State private var isTorchOn: Bool = false
    @State private var isProcessing: Bool = false
    @State private var manualInputText: String = ""
    @State private var showManualInputSheet: Bool = false
    @State private var scanLineOffset: CGFloat = -110

    public init(onAuthorized: @escaping (CaptureSession) -> Void) {
        self.onAuthorized = onAuthorized
    }

    public var body: some View {
        ZStack {
            // Dark architectural base background
            Color.black.ignoresSafeArea()
            
            // 1. Live AVFoundation Camera QR Scanner Viewport
            if isCameraAuthorized {
                CameraQRReaderRepresentable(isTorchOn: isTorchOn) { scannedCode in
                    handleScannedCode(scannedCode)
                }
                .ignoresSafeArea()
            } else {
                cameraPermissionPrompt
            }
            
            // 2. Animated Target Reticle Overlay
            scannerOverlay
            
            // 3. Top Header Controls & Bottom Status HUD
            VStack {
                topNavigationBar
                Spacer()
                bottomStatusCard
            }
        }
        .onAppear {
            checkCameraPermission()
            withAnimation(.easeInOut(duration: 1.8).repeatForever(autoreverses: true)) {
                scanLineOffset = 110
            }
        }
        .sheet(isPresented: $showManualInputSheet) {
            manualInputSheet
        }
    }
    
    // MARK: - Top Navigation Bar
    private var topNavigationBar: some View {
        HStack(spacing: 8) {
            Image(systemName: "camera.metering.matrix")
                .font(.system(size: 16, weight: .bold))
                .foregroundColor(VastuColors.brandBronze)
            Text("VĀSTU CAPTURE")
                .font(.system(size: 14, weight: .bold, design: .monospaced))
                .foregroundColor(VastuColors.brandIvory)
            
            Spacer()
            
            // Torch toggle button
            Button(action: toggleTorch) {
                Image(systemName: isTorchOn ? "bolt.fill" : "bolt.slash.fill")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(isTorchOn ? VastuColors.brandGold : .white)
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(Circle())
            }
            
            // Manual entry button
            Button(action: { showManualInputSheet = true }) {
                Image(systemName: "keyboard")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.white)
                    .padding(8)
                    .background(.ultraThinMaterial)
                    .clipShape(Circle())
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 16)
    }
    
    // MARK: - Viewfinder Reticle Overlay
    private var scannerOverlay: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 24)
                .strokeBorder(isProcessing ? VastuColors.brandGold : Color.white.opacity(0.8), lineWidth: 3)
                .frame(width: 260, height: 260)
            
            // Animated Scan Line
            if !isProcessing && isCameraAuthorized {
                Rectangle()
                    .fill(
                        LinearGradient(
                            colors: [Color.clear, VastuColors.brandGold, Color.clear],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .frame(width: 240, height: 2)
                    .offset(y: scanLineOffset)
            }
            
            // Corner Accents
            VStack {
                HStack {
                    CornerBracket(orientation: .topLeft)
                    Spacer()
                    CornerBracket(orientation: .topRight)
                }
                Spacer()
                HStack {
                    CornerBracket(orientation: .bottomLeft)
                    Spacer()
                    CornerBracket(orientation: .bottomRight)
                }
            }
            .frame(width: 270, height: 270)
        }
    }
    
    // MARK: - Bottom Status Card
    private var bottomStatusCard: some View {
        VStack(spacing: 12) {
            if isProcessing || authManager.state == .qrValidating {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: VastuColors.brandGold))
                    .scaleEffect(1.2)
                Text("Redeeming QR Challenge with VĀSTU Backend...")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(.white)
            } else if let err = authManager.errorMessage {
                VStack(spacing: 8) {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(VastuColors.brandError)
                        Text(err)
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(.white)
                            .multilineTextAlignment(.leading)
                    }
                    
                    Button("Scan Again") {
                        authManager.resetToScanner()
                        isProcessing = false
                    }
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(VastuColors.brandGold)
                    .padding(.top, 4)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(Color.red.opacity(0.3))
                .cornerRadius(10)
            } else {
                Text("Scan Session Authorization QR")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(.white)
                Text("Each room capture requires a valid single-use QR challenge. Unrestricted recording is disabled.")
                    .font(.system(size: 12))
                    .foregroundColor(.white.opacity(0.65))
                    .multilineTextAlignment(.center)
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity)
        .background(.ultraThinMaterial)
        .cornerRadius(16)
        .padding(.horizontal, 20)
        .padding(.bottom, 34)
    }
    
    // MARK: - Camera Permission Prompt
    private var cameraPermissionPrompt: some View {
        VStack(spacing: 16) {
            Image(systemName: "camera.fill")
                .font(.system(size: 48))
                .foregroundColor(VastuColors.brandBronze)
            Text("Camera Access Required")
                .font(.system(size: 18, weight: .bold))
                .foregroundColor(.white)
            Text("VĀSTU Capture requires the camera to scan authorized session QR codes and record spatial rooms.")
                .font(.system(size: 13))
                .foregroundColor(.white.opacity(0.7))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
            
            Button("Enable Camera in Settings") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            }
            .buttonStyle(VastuPrimaryButtonStyle())
            .padding(.horizontal, 40)
        }
    }
    
    // MARK: - Scanned Code Handler
    private func handleScannedCode(_ code: String) {
        guard !isProcessing else { return }
        isProcessing = true
        
        Task {
            let result = await authManager.redeemQR(rawCode: code)
            await MainActor.run {
                self.isProcessing = false
                switch result {
                case .success(let session):
                    self.onAuthorized(session)
                case .failure:
                    // Error is already bound to authManager.errorMessage
                    break
                }
            }
        }
    }
    
    private func toggleTorch() {
        guard let device = AVCaptureDevice.default(for: .video), device.hasTorch else { return }
        do {
            try device.lockForConfiguration()
            device.torchMode = isTorchOn ? .off : .on
            isTorchOn.toggle()
            device.unlockForConfiguration()
        } catch {
            print("Torch error: \(error)")
        }
    }
    
    private func checkCameraPermission() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            isCameraAuthorized = true
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { granted in
                DispatchQueue.main.async {
                    self.isCameraAuthorized = granted
                }
            }
        default:
            isCameraAuthorized = false
        }
    }
    
    // MARK: - Manual Input Sheet (Fallback)
    private var manualInputSheet: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text("Enter Session URI or Token")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundColor(VastuColors.brandText)
                    .padding(.top, 20)
                
                Text("Type the session code or deep-link issued by your VĀSTU portal.")
                    .font(.system(size: 13))
                    .foregroundColor(VastuColors.brandTextMuted)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
                
                TextField("vastu://capture-session?session_id=...", text: $manualInputText)
                    .autocorrectionDisabled()
                    .padding(14)
                    .background(VastuColors.brandIvory)
                    .cornerRadius(10)
                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                    .padding(.horizontal, 24)
                
                Button("Validate & Authorize") {
                    showManualInputSheet = false
                    handleScannedCode(manualInputText)
                }
                .buttonStyle(VastuPrimaryButtonStyle())
                .disabled(manualInputText.trimmingCharacters(in: .whitespaces).isEmpty)
                .padding(.horizontal, 24)
                
                // Sample QR challenge generator for testing
                Button("Generate Test Session QR") {
                    showManualInputSheet = false
                    let nonce = UUID().uuidString.prefix(8)
                    let testURI = "vastu://capture-session?endpoint=https%3A%2F%2Fvastu.krads.co.in&challenge=chal_\(nonce)&session_id=sess_\(nonce)&project_name=Grand%20Terrace&room_name=Master%20Suite&nonce=\(nonce)"
                    handleScannedCode(testURI)
                }
                .font(.system(size: 13, weight: .medium))
                .foregroundColor(VastuColors.brandBronze)
                
                Spacer()
            }
            .background(VastuColors.brandParchment.ignoresSafeArea())
        }
    }
}

// MARK: - Visual Corner Bracket
private enum BracketOrientation { case topLeft, topRight, bottomLeft, bottomRight }

private struct CornerBracket: View {
    let orientation: BracketOrientation
    var body: some View {
        Text("⌜")
            .font(.system(size: 34, weight: .bold))
            .foregroundColor(VastuColors.brandBronze)
            .rotationEffect(angle)
    }
    private var angle: Angle {
        switch orientation {
        case .topLeft: return .degrees(0)
        case .topRight: return .degrees(90)
        case .bottomRight: return .degrees(180)
        case .bottomLeft: return .degrees(270)
        }
    }
}

// MARK: - AVFoundation QR Video Reader
private struct CameraQRReaderRepresentable: UIViewControllerRepresentable {
    let isTorchOn: Bool
    let onCodeScanned: (String) -> Void
    
    func makeUIViewController(context: Context) -> QRScannerViewController {
        let vc = QRScannerViewController()
        vc.onCodeScanned = onCodeScanned
        return vc
    }
    func updateUIViewController(_ uiViewController: QRScannerViewController, context: Context) {}
}

private final class QRScannerViewController: UIViewController, AVCaptureMetadataOutputObjectsDelegate {
    var onCodeScanned: ((String) -> Void)?
    private let captureSession = AVCaptureSession()
    private var previewLayer: AVCaptureVideoPreviewLayer?
    
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        
        guard let device = AVCaptureDevice.default(for: .video),
              let input = try? AVCaptureDeviceInput(device: device) else { return }
        
        if captureSession.canAddInput(input) { captureSession.addInput(input) }
        
        let metadataOutput = AVCaptureMetadataOutput()
        if captureSession.canAddOutput(metadataOutput) {
            captureSession.addOutput(metadataOutput)
            metadataOutput.setMetadataObjectsDelegate(self, queue: DispatchQueue.main)
            metadataOutput.metadataObjectTypes = [.qr]
        }
        
        previewLayer = AVCaptureVideoPreviewLayer(session: captureSession)
        previewLayer?.videoGravity = .resizeAspectFill
        if let pl = previewLayer { view.layer.addSublayer(pl) }
    }
    
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        previewLayer?.frame = view.bounds
    }
    
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.captureSession.startRunning()
        }
    }
    
    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        captureSession.stopRunning()
    }
    
    func metadataOutput(_ output: AVCaptureMetadataOutput, didOutput metadataObjects: [AVMetadataObject], from connection: AVCaptureConnection) {
        guard let first = metadataObjects.first as? AVMetadataMachineReadableCodeObject,
              let stringVal = first.stringValue else { return }
        captureSession.stopRunning()
        AudioServicesPlaySystemSound(SystemSoundID(kSystemSoundID_Vibrate))
        onCodeScanned?(stringVal)
    }
}
