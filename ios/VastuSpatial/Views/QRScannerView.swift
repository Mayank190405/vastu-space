import SwiftUI
import AVFoundation
import Vision

struct QRScannerView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var scannerModel = QRScannerModel()
    
    let onCodeScanned: (String) -> Void
    
    var body: some View {
        ZStack {
            // Camera preview
            CameraPreview(session: scannerModel.captureSession)
                .ignoresSafeArea()
            
            // Scanning overlay
            VStack {
                // Top controls
                HStack {
                    Button(action: { dismiss() }) {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 32))
                            .foregroundColor(.white)
                            .shadow(radius: 4)
                    }
                    Spacer()
                    Text("Scan QR Code")
                        .font(.headline)
                        .foregroundColor(.white)
                    Spacer()
                    Button(action: {
                        scannerModel.toggleFlash()
                    }) {
                        Image(systemName: scannerModel.isFlashOn ? "flashlight.on.fill" : "flashlight.off.fill")
                            .font(.system(size: 24))
                            .foregroundColor(.white)
                            .shadow(radius: 4)
                    }
                }
                .padding()
                
                Spacer()
                
                // Scanning frame
                VStack {
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color.white, lineWidth: 2)
                        .frame(width: 280, height: 280)
                        .overlay(
                            VStack {
                                Text("Position QR code within frame")
                                    .font(.caption)
                                    .foregroundColor(.white)
                                    .padding(8)
                                    .background(Color.black.opacity(0.6))
                                    .cornerRadius(8)
                            }
                            .offset(y: 150)
                        )
                }
                
                Spacer()
                
                // Instructions
                VStack(spacing: 8) {
                    Text("Scan the QR code from the web dashboard")
                        .font(.subheadline)
                        .foregroundColor(.white)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                    
                    Text("Or enter session code manually")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.8))
                }
                .padding(.bottom, 32)
            }
        }
        .onAppear {
            scannerModel.startScanning { code in
                onCodeScanned(code)
                dismiss()
            }
        }
        .onDisappear {
            scannerModel.stopScanning()
        }
    }
}


class QRScannerModel: NSObject, ObservableObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    @Published var isFlashOn = false
    @Published var lastScannedCode: String?
    @Published var captureSession: AVCaptureSession?
    
    private var videoOutput: AVCaptureVideoDataOutput?
    private var previewLayer: AVCaptureVideoPreviewLayer?
    private var codeHandler: ((String) -> Void)?
    
    func startScanning(completion: @escaping (String) -> Void) {
        self.codeHandler = completion
        
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
            print("Failed to get camera device")
            return
        }
        
        do {
            let input = try AVCaptureDeviceInput(device: device)
            
            let captureSession = AVCaptureSession()
            captureSession.sessionPreset = .high
            
            if captureSession.canAddInput(input) {
                captureSession.addInput(input)
            }
            
            let output = AVCaptureVideoDataOutput()
            output.setSampleBufferDelegate(self, queue: DispatchQueue(label: "camera.queue"))
            
            if captureSession.canAddOutput(output) {
                captureSession.addOutput(output)
            }
            
            self.captureSession = captureSession
            self.videoOutput = output
            
            DispatchQueue.global(qos: .userInitiated).async {
                captureSession.startRunning()
            }
            
        } catch {
            print("Failed to setup camera: \(error)")
        }
    }
    
    func stopScanning() {
        captureSession?.stopRunning()
        captureSession = nil
        videoOutput = nil
    }
    
    func toggleFlash() {
        guard let device = AVCaptureDevice.default(for: .video), device.hasTorch else { return }
        
        do {
            try device.lockForConfiguration()
            if device.torchMode == .on {
                device.torchMode = .off
                isFlashOn = false
            } else {
                try device.setTorchModeOn(level: 1.0)
                isFlashOn = true
            }
            device.unlockForConfiguration()
        } catch {
            print("Failed to toggle flash: \(error)")
        }
    }
    
    // MARK: - AVCaptureVideoDataOutputSampleBufferDelegate
    
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer, from connection: AVCaptureConnection) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        
        let request = VNDetectBarcodesRequest { [weak self] request, error in
            guard let observations = request.results as? [VNBarcodeObservation],
                  let topCandidate = observations.first else { return }
            
            guard let payload = topCandidate.payloadStringValue else { return }
            
            DispatchQueue.main.async {
                self?.lastScannedCode = payload
                self?.codeHandler?(payload)
            }
        }
        
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .right, options: [:])
        
        do {
            try handler.perform([request])
        } catch {
            print("Failed to perform barcode detection: \(error)")
        }
    }
}

struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession?
    
    func makeUIView(context: Context) -> UIView {
        let view = UIView()
        
        guard let session = session else { return view }
        
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.frame = view.bounds
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)
        
        return view
    }
    
    func updateUIView(_ uiView: UIView, context: Context) {
        if let previewLayer = uiView.layer.sublayers?.first as? AVCaptureVideoPreviewLayer {
            previewLayer.frame = uiView.bounds
        }
    }
}