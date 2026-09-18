import Foundation
import CoreMotion
import Combine

public enum MotionScanQuality: String {
    case optimal = "OPTIMAL (GOOD PACE)"
    case tooFast = "SLOW DOWN: MOVING TOO FAST"
    case shaky = "STABILIZE: EXCESSIVE JITTER"
    case stationary = "MOVE STEADILY THROUGH ROOM"
}

public class MotionSensorManager: ObservableObject {
    private let motionManager = CMMotionManager()
    private let queue = OperationQueue()
    
    @Published public var scanQuality: MotionScanQuality = .optimal
    @Published public var recordedSampleCount: Int64 = 0
    @Published public var isRecording: Bool = false
    
    private var fileHandle: FileHandle?
    private var lastRecordedNs: Int64 = 0
    private let targetIntervalNs: Int64 = 10_000_000 // 10ms = 100Hz
    
    public init() {
        queue.qualityOfService = .userInteractive
        queue.maxConcurrentOperationCount = 1
    }
    
    public var isAvailable: Bool {
        return motionManager.isDeviceMotionAvailable || (motionManager.isAccelerometerAvailable && motionManager.isGyroAvailable)
    }
    
    public func startRecording(outputURL: URL) {
        guard !isRecording else { return }
        
        let fileManager = FileManager.default
        if !fileManager.fileExists(atPath: outputURL.path) {
            fileManager.createFile(atPath: outputURL.path, contents: nil)
        }
        
        do {
            fileHandle = try FileHandle(forWritingTo: outputURL)
            // Header with sensor_type and accuracy
            let header = "timestamp_ns,sensor_type,x,y,z,accuracy\n"
            if let data = header.data(using: .utf8) {
                fileHandle?.write(data)
            }
        } catch {
            print("Error initializing IMU file handle: \(error)")
            return
        }
        
        DispatchQueue.main.async {
            self.recordedSampleCount = 0
            self.isRecording = true
        }
        
        lastRecordedNs = 0
        
        if motionManager.isDeviceMotionAvailable {
            motionManager.deviceMotionUpdateInterval = 0.01 // 100 Hz
            motionManager.startDeviceMotionUpdates(using: .xArbitraryZVertical, to: queue) { [weak self] motion, error in
                guard let self = self, let motion = motion else { return }
                self.processDeviceMotion(motion)
            }
        }
    }
    
    public func stopRecording() {
        guard isRecording else { return }
        motionManager.stopDeviceMotionUpdates()
        
        do {
            try fileHandle?.synchronize()
            try fileHandle?.close()
        } catch {
            print("Error closing IMU file: \(error)")
        }
        fileHandle = nil
        
        DispatchQueue.main.async {
            self.isRecording = false
        }
    }
    
    private func processDeviceMotion(_ motion: CMDeviceMotion) {
        let currentNs = Int64(motion.timestamp * 1_000_000_000)
        guard currentNs - lastRecordedNs >= targetIntervalNs else { return }
        lastRecordedNs = currentNs
        
        let ax = motion.userAcceleration.x + motion.gravity.x
        let ay = motion.userAcceleration.y + motion.gravity.y
        let az = motion.userAcceleration.z + motion.gravity.z
        
        let gx = motion.rotationRate.x
        let gy = motion.rotationRate.y
        let gz = motion.rotationRate.z
        
        let gyroMag = sqrt(gx * gx + gy * gy + gz * gz)
        
        let quality: MotionScanQuality
        if gyroMag > 1.8 {
            quality = .shaky
        } else if gyroMag > 0.8 {
            quality = .tooFast
        } else if gyroMag < 0.02 {
            quality = .stationary
        } else {
            quality = .optimal
        }
        
        // Log individual sensor telemetry rows
        let accelLine = "\(currentNs),ACCELEROMETER,\(ax),\(ay),\(az),3\n"
        let gyroLine = "\(currentNs),GYROSCOPE,\(gx),\(gy),\(gz),3\n"
        
        if let accelData = accelLine.data(using: .utf8),
           let gyroData = gyroLine.data(using: .utf8) {
            fileHandle?.write(accelData)
            fileHandle?.write(gyroData)
        }
        
        DispatchQueue.main.async {
            self.scanQuality = quality
            self.recordedSampleCount += 2
        }
    }
}
