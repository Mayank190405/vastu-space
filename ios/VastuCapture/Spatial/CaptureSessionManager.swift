import Foundation
import Combine
import simd

#if os(iOS) || targetEnvironment(simulator)
import ARKit
#endif

public protocol CaptureSessionManagerDelegate: AnyObject {
    func captureManager(_ manager: CaptureSessionManager, didUpdatePose pose: CameraPose, headingDeg: Double)
    func captureManager(_ manager: CaptureSessionManager, didRecordKeyframe index: Int, total: Int)
    func captureManager(_ manager: CaptureSessionManager, didChangeTrackingStatus text: String, isWarning: Bool)
}

public final class CaptureSessionManager: NSObject, ObservableObject, ARSessionControllerDelegate {
    public let arController = ARSessionController()
    public let keyframeSelector = KeyframeSelector()
    public weak var delegate: CaptureSessionManagerDelegate?
    
    @Published public private(set) var isRecording: Bool = false
    @Published public private(set) var isPaused: Bool = false
    @Published public private(set) var keyframeCount: Int = 0
    @Published public private(set) var droppedFrameCount: Int = 0
    @Published public private(set) var translationBaselineMeters: Double = 0.0
    @Published public private(set) var activeTrackingText: String = "INITIALIZING"
    @Published public private(set) var isTrackingDegraded: Bool = false
    @Published public private(set) var completedPackageURL: URL?
    
    private var packageWriter: CapturePackageWriter?
    private var activeSessionId: String = ""
    private var sessionStartTime: TimeInterval = 0
    private var initialCameraPosition: simd_float3?
    private var minCameraPosition: simd_float3?
    private var maxCameraPosition: simd_float3?
    private var recordedKeyframePositions: [simd_float3] = []
    private var maxBaselineDisplacement: Double = 0.0
    private var frameIndexCounter: Int = 0
    private let processingQueue = DispatchQueue(label: "com.vastu.capture.session_processor", qos: .userInitiated)
    
    public override init() {
        super.init()
        arController.delegate = self
    }
    
    public func startLiveCamera() {
        arController.startSession()
    }
    
    public func pauseLiveCamera() {
        arController.pauseSession()
    }
    
    // MARK: - Recording Lifecycle
    public func startRecording(session: CaptureSession) throws {
        // Enforce Phase 2 Authorization check
        try SessionAuthorizationManager.shared.assertRecordingAuthorized()
        
        guard !isRecording else { return }
        self.activeSessionId = session.id
        self.frameIndexCounter = 0
        self.keyframeCount = 0
        self.droppedFrameCount = 0
        self.translationBaselineMeters = 0.0
        self.maxBaselineDisplacement = 0.0
        self.initialCameraPosition = nil
        self.minCameraPosition = nil
        self.maxCameraPosition = nil
        self.recordedKeyframePositions.removeAll()
        self.completedPackageURL = nil
        self.sessionStartTime = ProcessInfo.processInfo.systemUptime
        
        keyframeSelector.reset()
        
        let docsDir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        self.packageWriter = try CapturePackageWriter(
            parentDirectory: docsDir,
            sessionId: session.id,
            projectName: session.projectName,
            roomName: session.roomName
        )
        
        self.packageWriter?.recordTrackingEvent(
            type: "RECORDING_STARTED",
            timestampSec: ProcessInfo.processInfo.systemUptime,
            details: ["session_id": session.id, "project": session.projectName, "room": session.roomName]
        )
        
        if let writer = self.packageWriter {
            SceneUnderstandingManager.shared.configureLogging(packageDirectory: writer.packageDirectoryURL)
        }
        
        self.isRecording = true
        self.isPaused = false
        
        // Phase 7 Real-Time Pipeline Telemetry Reporting
        let sid = session.id
        Task {
            _ = await SessionAPIClient.shared.reportPipelineStage(
                sessionId: sid,
                stageName: "ARKIT_CAPTURE_RUNNING",
                status: "RUNNING",
                progress: 10,
                worker: "iPhone ARKit Odometry"
            )
            _ = await SessionAPIClient.shared.reportPipelineStage(
                sessionId: sid,
                stageName: "LOCAL_AI_ANALYSIS",
                status: "RUNNING",
                progress: 15,
                worker: "Core ML On-Device"
            )
        }
    }
    
    public func pauseRecording() {
        guard isRecording && !isPaused else { return }
        isPaused = true
        packageWriter?.recordTrackingEvent(type: "RECORDING_PAUSED", timestampSec: ProcessInfo.processInfo.systemUptime)
        let sid = activeSessionId
        Task {
            _ = await SessionAPIClient.shared.sendHeartbeat(
                sessionId: sid,
                deviceUUID: SecureSessionStore.shared.deviceUUID,
                trackingState: activeTrackingText,
                localAIReady: true,
                recordingState: "PAUSED"
            )
        }
    }
    
    public func resumeRecording() throws {
        try SessionAuthorizationManager.shared.assertRecordingAuthorized()
        guard isRecording && isPaused else { return }
        isPaused = false
        packageWriter?.recordTrackingEvent(type: "RECORDING_RESUMED", timestampSec: ProcessInfo.processInfo.systemUptime)
        let sid = activeSessionId
        Task {
            _ = await SessionAPIClient.shared.sendHeartbeat(
                sessionId: sid,
                deviceUUID: SecureSessionStore.shared.deviceUUID,
                trackingState: activeTrackingText,
                localAIReady: true,
                recordingState: "RECORDING"
            )
        }
    }
    
    public func finishRecording() throws -> URL {
        guard isRecording else {
            throw SessionAuthError.recordingForbidden("No active recording to finish")
        }
        
        isRecording = false
        isPaused = false
        
        let duration = ProcessInfo.processInfo.systemUptime - sessionStartTime
        SceneUnderstandingManager.shared.observationWriter?.close()
        packageWriter?.recordTrackingEvent(
            type: "RECORDING_FINISHED",
            timestampSec: ProcessInfo.processInfo.systemUptime,
            details: [
                "total_keyframes": keyframeCount,
                "duration_sec": duration,
                "translation_baseline_m": translationBaselineMeters
            ]
        )
        
        guard let writer = packageWriter else {
            throw SessionAuthError.recordingForbidden("Package writer was deallocated")
        }
        
        let finalPkgURL = try writer.finalizePackage(totalFrames: keyframeCount, durationSeconds: duration)
        self.completedPackageURL = finalPkgURL
        
        // Phase 7 Real-Time Pipeline Telemetry Reporting
        let sid = activeSessionId
        Task {
            _ = await SessionAPIClient.shared.reportPipelineStage(
                sessionId: sid,
                stageName: "ARKIT_CAPTURE_RUNNING",
                status: "COMPLETED",
                progress: 100
            )
            _ = await SessionAPIClient.shared.reportPipelineStage(
                sessionId: sid,
                stageName: "LOCAL_AI_ANALYSIS",
                status: "COMPLETED",
                progress: 100
            )
            _ = await SessionAPIClient.shared.reportPipelineStage(
                sessionId: sid,
                stageName: "CAPTURE_VALIDATION",
                status: "COMPLETED",
                progress: 100
            )
            _ = await SessionAPIClient.shared.reportPipelineStage(
                sessionId: sid,
                stageName: "UPLOADING",
                status: "RUNNING",
                progress: 25
            )
        }
        
        return finalPkgURL
    }
    
#if os(iOS) || targetEnvironment(simulator)
    // MARK: - ARSessionControllerDelegate
    public func sessionController(_ controller: ARSessionController, didUpdateFrame frame: ARFrame) {
        let trackingState = arController.trackingStateText
        let cameraTransform = frame.camera.transform
        let timestamp = frame.timestamp
        let pixelBuffer = frame.capturedImage
        let currentPos = simd_make_float3(cameraTransform.columns.3.x, cameraTransform.columns.3.y, cameraTransform.columns.3.z)
        
        // 1. Update calibration from frame
        _ = packageWriter?.calibrationManager.updateCalibration(
            intrinsics: frame.camera.intrinsics,
            resolution: frame.camera.imageResolution
        )
        
        // 2. Track real camera translation baseline during active recording
        if isRecording && !isPaused {
            if initialCameraPosition == nil {
                initialCameraPosition = currentPos
                minCameraPosition = currentPos
                maxCameraPosition = currentPos
                recordedKeyframePositions.append(currentPos)
            } else {
                let distFromStart = Double(simd_distance(currentPos, initialCameraPosition!))
                if distFromStart > maxBaselineDisplacement {
                    maxBaselineDisplacement = distFromStart
                }
                
                if let minP = minCameraPosition, let maxP = maxCameraPosition {
                    let newMin = simd_min(minP, currentPos)
                    let newMax = simd_max(maxP, currentPos)
                    minCameraPosition = newMin
                    maxCameraPosition = newMax
                    let boxDiag = Double(simd_distance(newMin, newMax))
                    if boxDiag > maxBaselineDisplacement {
                        maxBaselineDisplacement = boxDiag
                    }
                }
            }
            
            let updatedBaseline = round(maxBaselineDisplacement * 100.0) / 100.0
            if updatedBaseline != translationBaselineMeters {
                DispatchQueue.main.async { [weak self] in
                    self?.translationBaselineMeters = updatedBaseline
                }
            }
        }
        
        // 3. Notify delegate of current camera pose & heading
        let headingDeg = Double(atan2(-cameraTransform.columns.2.x, cameraTransform.columns.2.z)) * (180.0 / .pi)
        let poseObj = CameraPose(
            frameId: String(format: "frame_%06d.jpg", frameIndexCounter),
            timestampNs: Int64(timestamp * 1_000_000_000.0),
            transformMatrix: cameraTransform,
            trackingState: trackingState
        )
        delegate?.captureManager(self, didUpdatePose: poseObj, headingDeg: headingDeg)
        
        // 1b. Asynchronously submit frame to on-device AI inference engine (5-10 Hz throttled)
        let intrinsics = packageWriter?.calibrationManager.currentIntrinsics ?? CameraIntrinsics.defaultFallback()
        InferenceScheduler.shared.submitFrame(
            pixelBuffer: pixelBuffer,
            timestamp: timestamp,
            intrinsics: intrinsics,
            cameraPose: poseObj
        )
        
        // 4. If recording and not paused, evaluate keyframe selection
        guard isRecording && !isPaused else { return }
        
        processingQueue.async { [weak self] in
            guard let self = self, let writer = self.packageWriter else { return }
            
            let decision = self.keyframeSelector.evaluate(
                transform: cameraTransform,
                timestamp: timestamp,
                trackingState: trackingState
            )
            
            guard decision.shouldRecord else { return }
            
            self.frameIndexCounter += 1
            let frameIdx = self.frameIndexCounter
            let frameId = String(format: "frame_%06d.jpg", frameIdx)
            
            // Check pairwise baseline across recorded keyframes
            for kPos in self.recordedKeyframePositions {
                let d = Double(simd_distance(currentPos, kPos))
                if d > self.maxBaselineDisplacement {
                    self.maxBaselineDisplacement = d
                }
            }
            if self.recordedKeyframePositions.count < 400 {
                self.recordedKeyframePositions.append(currentPos)
            }
            let updatedBaseline = round(self.maxBaselineDisplacement * 100.0) / 100.0
            DispatchQueue.main.async { [weak self] in
                self?.translationBaselineMeters = updatedBaseline
            }
            
            // Asynchronously record frame JPEG
            writer.frameRecorder.recordFrame(pixelBuffer: pixelBuffer, frameIndex: frameIdx) { [weak self] _, success in
                if success {
                    DispatchQueue.main.async {
                        self?.keyframeCount = frameIdx
                        self?.delegate?.captureManager(self!, didRecordKeyframe: frameIdx, total: frameIdx)
                    }
                } else {
                    DispatchQueue.main.async {
                        self?.droppedFrameCount += 1
                    }
                }
            }
            
            // Log matching pose to camera_poses.jsonl
            writer.poseLogger.logPose(
                frameId: frameId,
                timestampSec: timestamp,
                transform: cameraTransform,
                trackingState: trackingState
            )
            
            // Record timestamped boundary observations to capture package
            let stablePts = WallBoundaryMapper.shared.getStableBoundaryPoints(minHits: 1)
            if !stablePts.isEmpty {
                writer.recordBoundaryObservations(points: stablePts, timestampSec: timestamp)
            }
        }
    }
    
    public func sessionController(_ controller: ARSessionController, didChangeTrackingState state: ARCamera.TrackingState, message: String, isWarning: Bool) {
        activeTrackingText = message
        isTrackingDegraded = isWarning
        
        if isRecording {
            packageWriter?.recordTrackingEvent(
                type: "TRACKING_STATE_CHANGED",
                timestampSec: ProcessInfo.processInfo.systemUptime,
                details: ["state": message, "is_warning": isWarning]
            )
        }
        delegate?.captureManager(self, didChangeTrackingStatus: message, isWarning: isWarning)
    }
    
    public func sessionControllerWasInterrupted(_ controller: ARSessionController) {
        activeTrackingText = "TRACKING INTERRUPTED"
        isTrackingDegraded = true
        
        if isRecording {
            packageWriter?.recordTrackingEvent(type: "SESSION_INTERRUPTED", timestampSec: ProcessInfo.processInfo.systemUptime)
        }
    }
    
    public func sessionControllerInterruptionEnded(_ controller: ARSessionController) {
        activeTrackingText = "TRACKING RESUMED"
        isTrackingDegraded = false
        
        if isRecording {
            packageWriter?.recordTrackingEvent(type: "SESSION_INTERRUPTION_ENDED", timestampSec: ProcessInfo.processInfo.systemUptime)
        }
    }
#endif

    public func updateBaselineForTesting(distanceMeters: Double) {
        self.maxBaselineDisplacement = distanceMeters
        self.translationBaselineMeters = round(distanceMeters * 100.0) / 100.0
    }
}

// Backward compatibility alias for existing code
public typealias ARCaptureEngine = CaptureSessionManager
public typealias ARCaptureEngineDelegate = CaptureSessionManagerDelegate
