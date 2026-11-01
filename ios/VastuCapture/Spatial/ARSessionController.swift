import Foundation
import Combine

#if os(iOS) || targetEnvironment(simulator)
import ARKit

public protocol ARSessionControllerDelegate: AnyObject {
    func sessionController(_ controller: ARSessionController, didUpdateFrame frame: ARFrame)
    func sessionController(_ controller: ARSessionController, didChangeTrackingState state: ARCamera.TrackingState, message: String, isWarning: Bool)
    func sessionControllerWasInterrupted(_ controller: ARSessionController)
    func sessionControllerInterruptionEnded(_ controller: ARSessionController)
}

public final class ARSessionController: NSObject, ObservableObject, ARSessionDelegate {
    public let session = ARSession()
    public weak var delegate: ARSessionControllerDelegate?
    
    @Published public private(set) var trackingStateText: String = "INITIALIZING"
    @Published public private(set) var isTrackingWarning: Bool = false
    @Published public private(set) var isSessionRunning: Bool = false
    
    public override init() {
        super.init()
        session.delegate = self
    }
    
    deinit {
        stopSession()
    }
    
    public func startSession() {
        guard ARWorldTrackingConfiguration.isSupported else {
            trackingStateText = "ARWorldTracking Not Supported"
            isTrackingWarning = true
            return
        }
        
        let config = ARWorldTrackingConfiguration()
        config.worldAlignment = .gravity // Aligns +Y strictly with physical gravity, meter metric units
        config.planeDetection = [.horizontal, .vertical]
        config.isAutoFocusEnabled = true
        // Explicitly zero-LiDAR: pure visual-inertial odometry
        
        session.run(config, options: [.resetTracking, .removeExistingAnchors])
        isSessionRunning = true
    }
    
    public func pauseSession() {
        session.pause()
        isSessionRunning = false
    }
    
    public func stopSession() {
        session.pause()
        isSessionRunning = false
    }
    
    // MARK: - ARSessionDelegate
    public func session(_ session: ARSession, didUpdate frame: ARFrame) {
        delegate?.sessionController(self, didUpdateFrame: frame)
    }
    
    public func session(_ session: ARSession, cameraDidChangeTrackingState camera: ARCamera) {
        let (text, isWarn) = parseTrackingState(camera.trackingState)
        DispatchQueue.main.async {
            self.trackingStateText = text
            self.isTrackingWarning = isWarn
        }
        delegate?.sessionController(self, didChangeTrackingState: camera.trackingState, message: text, isWarning: isWarn)
    }
    
    public func sessionWasInterrupted(_ session: ARSession) {
        DispatchQueue.main.async {
            self.trackingStateText = "TRACKING INTERRUPTED"
            self.isTrackingWarning = true
        }
        delegate?.sessionControllerWasInterrupted(self)
    }
    
    public func sessionInterruptionEnded(_ session: ARSession) {
        DispatchQueue.main.async {
            self.trackingStateText = "RECOVERING TRACKING..."
            self.isTrackingWarning = true
        }
        let config = ARWorldTrackingConfiguration()
        config.worldAlignment = .gravity
        config.isAutoFocusEnabled = true
        session.run(config, options: [])
        delegate?.sessionControllerInterruptionEnded(self)
    }
    
    public func session(_ session: ARSession, didFailWithError error: Error) {
        DispatchQueue.main.async {
            self.trackingStateText = "AR ERROR: \(error.localizedDescription)"
            self.isTrackingWarning = true
        }
    }
    
    private func parseTrackingState(_ state: ARCamera.TrackingState) -> (String, Bool) {
        switch state {
        case .normal:
            return ("NORMAL", false)
        case .notAvailable:
            return ("TRACKING UNAVAILABLE", true)
        case .limited(let reason):
            switch reason {
            case .initializing:
                return ("INITIALIZING", true)
            case .excessiveMotion:
                return ("EXCESSIVE MOTION", true)
            case .insufficientFeatures:
                return ("INSUFFICIENT FEATURES", true)
            case .relocalizing:
                return ("RELOCALIZING", true)
            @unknown default:
                return ("LIMITED TRACKING", true)
            }
        }
    }
}

#else

// MARK: - macOS Test Stub
public protocol ARSessionControllerDelegate: AnyObject {}

public final class ARSessionController: NSObject, ObservableObject {
    public weak var delegate: ARSessionControllerDelegate?
    @Published public private(set) var trackingStateText: String = "NORMAL"
    @Published public private(set) var isTrackingWarning: Bool = false
    @Published public private(set) var isSessionRunning: Bool = false
    
    public func startSession() { isSessionRunning = true }
    public func pauseSession() { isSessionRunning = false }
    public func stopSession() { isSessionRunning = false }
}

#endif
