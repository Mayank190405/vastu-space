import Foundation
import AVFoundation
import SwiftUI
import Combine

public class AVCameraManager: NSObject, ObservableObject, AVCaptureFileOutputRecordingDelegate {
    
    public let captureSession = AVCaptureSession()
    private let movieOutput = AVCaptureMovieFileOutput()
    private var activeDevice: AVCaptureDevice?
    
    @Published public var isRecording: Bool = false
    @Published public var recordedSeconds: Int = 0
    @Published public var isExposureLocked: Bool = false
    
    private var timer: AnyCancellable?
    private var completionHandler: ((Result<URL, Error>) -> Void)?
    
    public override init() {
        super.init()
        setupCaptureSession()
    }
    
    private func setupCaptureSession() {
        captureSession.beginConfiguration()
        captureSession.sessionPreset = .high
        
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
              let input = try? AVCaptureDeviceInput(device: device) else {
            captureSession.commitConfiguration()
            return
        }
        
        self.activeDevice = device
        
        // Optimize device settings for spatial photogrammetry / gaussian splatting
        do {
            try device.lockForConfiguration()
            if device.isFocusModeSupported(.continuousAutoFocus) {
                device.focusMode = .continuousAutoFocus
            }
            if device.isExposureModeSupported(.continuousAutoExposure) {
                device.exposureMode = .continuousAutoExposure
            }
            if device.isSmoothAutoFocusSupported {
                device.isSmoothAutoFocusEnabled = true
            }
            // Prefer 60fps if supported
            let formats = device.formats
            for format in formats {
                for range in format.videoSupportedFrameRateRanges {
                    if range.maxFrameRate >= 60.0 {
                        device.activeFormat = format
                        device.activeVideoMinFrameDuration = CMTime(value: 1, timescale: 60)
                        device.activeVideoMaxFrameDuration = CMTime(value: 1, timescale: 60)
                        break
                    }
                }
            }
            device.unlockForConfiguration()
        } catch {
            print("Failed to lock device configuration: \(error)")
        }
        
        if captureSession.canAddInput(input) {
            captureSession.addInput(input)
        }
        
        if let audioDevice = AVCaptureDevice.default(for: .audio),
           let audioInput = try? AVCaptureDeviceInput(device: audioDevice),
           captureSession.canAddInput(audioInput) {
            captureSession.addInput(audioInput)
        }
        
        if captureSession.canAddOutput(movieOutput) {
            captureSession.addOutput(movieOutput)
        }
        
        captureSession.commitConfiguration()
    }
    
    public func toggleExposureLock() {
        guard let device = activeDevice else { return }
        do {
            try device.lockForConfiguration()
            if isExposureLocked {
                // Unlock to continuous
                if device.isExposureModeSupported(.continuousAutoExposure) {
                    device.exposureMode = .continuousAutoExposure
                }
                if device.isFocusModeSupported(.continuousAutoFocus) {
                    device.focusMode = .continuousAutoFocus
                }
                isExposureLocked = false
            } else {
                // Lock current exposure and focus
                if device.isExposureModeSupported(.locked) {
                    device.exposureMode = .locked
                }
                if device.isFocusModeSupported(.locked) {
                    device.focusMode = .locked
                }
                isExposureLocked = true
            }
            device.unlockForConfiguration()
        } catch {
            print("Failed to toggle exposure lock: \(error)")
        }
    }
    
    public func startSession() {
        if captureSession.inputs.isEmpty {
            setupCaptureSession()
        }
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self, !self.captureSession.isRunning else { return }
            self.captureSession.startRunning()
        }
    }
    
    public func stopSession() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self, self.captureSession.isRunning else { return }
            self.captureSession.stopRunning()
        }
    }
    
    public func startRecording(to outputURL: URL, completion: @escaping (Result<URL, Error>) -> Void) {
        guard !isRecording else { return }
        
        // Verify disk storage
        guard StorageMonitor.hasSufficientStorage(minMB: 200) else {
            completion(.failure(NSError(domain: "AVCameraManager", code: 507, userInfo: [NSLocalizedDescriptionKey: "Insufficient storage (<200MB available)"])))
            return
        }
        
        self.completionHandler = completion
        
        if FileManager.default.fileExists(atPath: outputURL.path) {
            try? FileManager.default.removeItem(at: outputURL)
        }
        
        movieOutput.startRecording(to: outputURL, recordingDelegate: self)
        
        DispatchQueue.main.async {
            self.isRecording = true
            self.recordedSeconds = 0
            self.timer = Timer.publish(every: 1.0, on: .main, in: .common).autoconnect().sink { [weak self] _ in
                guard let self = self else { return }
                self.recordedSeconds += 1
                
                // Live storage safety guard
                if !StorageMonitor.hasSufficientStorage(minMB: 100) {
                    self.stopRecording()
                }
            }
        }
    }
    
    public func stopRecording() {
        guard isRecording else { return }
        movieOutput.stopRecording()
        timer?.cancel()
        timer = nil
    }
    
    public func stopRecordingAsync() async throws -> URL {
        guard isRecording else {
            throw NSError(domain: "AVCameraManager", code: 400, userInfo: [NSLocalizedDescriptionKey: "Camera is not currently recording"])
        }
        return try await withCheckedThrowingContinuation { continuation in
            self.completionHandler = { result in
                switch result {
                case .success(let url):
                    continuation.resume(returning: url)
                case .failure(let error):
                    continuation.resume(throwing: error)
                }
            }
            self.movieOutput.stopRecording()
            self.timer?.cancel()
            self.timer = nil
        }
    }
    
    public func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo outputFileURL: URL, from connections: [AVCaptureConnection], error: Error?) {
        DispatchQueue.main.async {
            self.isRecording = false
            if let error = error {
                self.completionHandler?(.failure(error))
            } else {
                self.completionHandler?(.success(outputFileURL))
            }
            self.completionHandler = nil
        }
    }
    
    public func extractCameraIntrinsics() -> CameraIntrinsics {
        guard let device = activeDevice else {
            return CameraIntrinsics(fx: 1500, fy: 1500, cx: 960, cy: 540, width: 1920, height: 1080, fps: 60)
        }
        
        let fovDegrees = Double(device.activeFormat.videoFieldOfView)
        let fovRadians = fovDegrees * .pi / 180.0
        let width = 1920.0
        let height = 1080.0
        
        let fx = (width / 2.0) / tan(fovRadians / 2.0)
        let fy = fx
        let cx = width / 2.0
        let cy = height / 2.0
        
        return CameraIntrinsics(
            fx: fx,
            fy: fy,
            cx: cx,
            cy: cy,
            width: Int(width),
            height: Int(height),
            fps: 60.0
        )
    }
}

// SwiftUI Camera Preview Bridge
public struct CameraPreviewView: UIViewRepresentable {
    public let session: AVCaptureSession
    
    public init(session: AVCaptureSession) {
        self.session = session
    }
    
    public func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)
        
        DispatchQueue.main.async {
            previewLayer.frame = view.bounds
        }
        return view
    }
    
    public func updateUIView(_ uiView: UIView, context: Context) {
        if let previewLayer = uiView.layer.sublayers?.first as? AVCaptureVideoPreviewLayer {
            previewLayer.frame = uiView.bounds
        }
    }
}
