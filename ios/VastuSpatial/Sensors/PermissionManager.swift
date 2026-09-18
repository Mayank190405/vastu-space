import Foundation
import AVFoundation
import CoreLocation
import CoreMotion
import Combine
import UIKit

public class PermissionManager: NSObject, ObservableObject, CLLocationManagerDelegate {
    public static let shared = PermissionManager()
    
    @Published public var cameraAuthorized: Bool = false
    @Published public var microphoneAuthorized: Bool = false
    @Published public var locationAuthorized: Bool = false
    @Published public var motionAuthorized: Bool = false
    
    @Published public var cameraDenied: Bool = false
    @Published public var microphoneDenied: Bool = false
    @Published public var locationDenied: Bool = false
    
    @Published public var isChecking: Bool = false
    
    private let locationManager = CLLocationManager()
    private var cancellables = Set<AnyCancellable>()
    
    public var allPermissionsGranted: Bool {
        return cameraAuthorized && microphoneAuthorized && locationAuthorized
    }
    
    public var isAnyPermissionDenied: Bool {
        return cameraDenied || microphoneDenied || locationDenied
    }
    
    public override init() {
        super.init()
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyBest
        checkCurrentPermissions()
        
        // Automatically re-check permissions when returning from Settings or background
        NotificationCenter.default.publisher(for: UIApplication.didBecomeActiveNotification)
            .sink { [weak self] _ in
                self?.checkCurrentPermissions()
            }
            .store(in: &cancellables)
    }
    
    public func checkCurrentPermissions() {
        DispatchQueue.main.async {
            // Camera
            let camStatus = AVCaptureDevice.authorizationStatus(for: .video)
            self.cameraAuthorized = (camStatus == .authorized)
            self.cameraDenied = (camStatus == .denied || camStatus == .restricted)
            
            // Microphone
            if #available(iOS 17.0, *) {
                let micStatus = AVAudioApplication.shared.recordPermission
                self.microphoneAuthorized = (micStatus == .granted)
                self.microphoneDenied = (micStatus == .denied)
            } else {
                let micStatus = AVAudioSession.sharedInstance().recordPermission
                self.microphoneAuthorized = (micStatus == .granted)
                self.microphoneDenied = (micStatus == .denied)
            }
            
            // Location
            let locStatus = self.locationManager.authorizationStatus
            self.locationAuthorized = (locStatus == .authorizedWhenInUse || locStatus == .authorizedAlways)
            self.locationDenied = (locStatus == .denied || locStatus == .restricted)
            
            // Motion
            self.motionAuthorized = CMMotionManager().isDeviceMotionAvailable
        }
    }
    
    public func requestAllPermissions(completion: ((Bool) -> Void)? = nil) {
        checkCurrentPermissions()
        
        // If any permission is permanently denied, direct user to iOS Settings
        if isAnyPermissionDenied {
            openAppSettings()
            completion?(false)
            return
        }
        
        DispatchQueue.main.async {
            self.isChecking = true
        }
        
        // 1. Request Camera Access
        requestCameraPermission { [weak self] _ in
            guard let self = self else { return }
            
            // 2. Request Microphone Access
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                self.requestMicrophonePermission { [weak self] _ in
                    guard let self = self else { return }
                    
                    // 3. Request Location Access
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
                        self.requestLocationPermission()
                        
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                            self.checkCurrentPermissions()
                            self.isChecking = false
                            completion?(self.allPermissionsGranted)
                        }
                    }
                }
            }
        }
    }
    
    public func requestCameraPermission(completion: ((Bool) -> Void)? = nil) {
        let status = AVCaptureDevice.authorizationStatus(for: .video)
        switch status {
        case .authorized:
            DispatchQueue.main.async {
                self.cameraAuthorized = true
                self.cameraDenied = false
                completion?(true)
            }
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { granted in
                DispatchQueue.main.async {
                    self.cameraAuthorized = granted
                    self.cameraDenied = !granted
                    completion?(granted)
                }
            }
        case .denied, .restricted:
            DispatchQueue.main.async {
                self.cameraAuthorized = false
                self.cameraDenied = true
                self.openAppSettings()
                completion?(false)
            }
        @unknown default:
            break
        }
    }
    
    public func requestMicrophonePermission(completion: ((Bool) -> Void)? = nil) {
        if #available(iOS 17.0, *) {
            let status = AVAudioApplication.shared.recordPermission
            if status == .undetermined {
                AVAudioApplication.requestRecordPermission { granted in
                    DispatchQueue.main.async {
                        self.microphoneAuthorized = granted
                        self.microphoneDenied = !granted
                        completion?(granted)
                    }
                }
            } else if status == .granted {
                DispatchQueue.main.async {
                    self.microphoneAuthorized = true
                    self.microphoneDenied = false
                    completion?(true)
                }
            } else {
                DispatchQueue.main.async {
                    self.microphoneAuthorized = false
                    self.microphoneDenied = true
                    self.openAppSettings()
                    completion?(false)
                }
            }
        } else {
            let status = AVAudioSession.sharedInstance().recordPermission
            if status == .undetermined {
                AVAudioSession.sharedInstance().requestRecordPermission { granted in
                    DispatchQueue.main.async {
                        self.microphoneAuthorized = granted
                        self.microphoneDenied = !granted
                        completion?(granted)
                    }
                }
            } else if status == .granted {
                DispatchQueue.main.async {
                    self.microphoneAuthorized = true
                    self.microphoneDenied = false
                    completion?(true)
                }
            } else {
                DispatchQueue.main.async {
                    self.microphoneAuthorized = false
                    self.microphoneDenied = true
                    self.openAppSettings()
                    completion?(false)
                }
            }
        }
    }
    
    public func requestLocationPermission() {
        DispatchQueue.main.async {
            let status = self.locationManager.authorizationStatus
            if status == .notDetermined {
                self.locationManager.requestWhenInUseAuthorization()
            } else if status == .authorizedWhenInUse || status == .authorizedAlways {
                self.locationAuthorized = true
                self.locationDenied = false
            } else if status == .denied || status == .restricted {
                self.locationAuthorized = false
                self.locationDenied = true
                self.openAppSettings()
            }
        }
    }
    
    public func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        DispatchQueue.main.async {
            let status = manager.authorizationStatus
            self.locationAuthorized = (status == .authorizedWhenInUse || status == .authorizedAlways)
            self.locationDenied = (status == .denied || status == .restricted)
        }
    }
    
    public func openAppSettings() {
        DispatchQueue.main.async {
            if let url = URL(string: UIApplication.openSettingsURLString), UIApplication.shared.canOpenURL(url) {
                UIApplication.shared.open(url)
            }
        }
    }
}
