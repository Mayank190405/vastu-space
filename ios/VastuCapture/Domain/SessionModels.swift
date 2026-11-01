import Foundation

public enum SessionState: String, Codable, CaseIterable {
    case unauthorized = "UNAUTHORIZED"
    case qrScanning = "QR_SCANNING"
    case qrValidating = "QR_VALIDATING"
    case authorized = "AUTHORIZED"
    case deviceCheck = "DEVICE_CHECK"
    case ready = "READY"
    case recording = "RECORDING"
    case paused = "PAUSED"
    case trackingRecovery = "TRACKING_RECOVERY"
    case validatingCapture = "VALIDATING_CAPTURE"
    case rescanRequired = "RESCAN_REQUIRED"
    case finalizing = "FINALIZING"
    case uploadPending = "UPLOAD_PENDING"
    case uploading = "UPLOADING"
    case uploadFailed = "UPLOAD_FAILED"
    case completed = "COMPLETED"
    case expired = "EXPIRED"
    case revoked = "REVOKED"
    
    public var isRecordingActive: Bool {
        return self == .recording || self == .paused || self == .trackingRecovery
    }
}

public struct CaptureSession: Codable, Identifiable {
    public let id: String
    public let projectId: String
    public let projectName: String
    public let roomId: String
    public let roomName: String
    public let operatorName: String?
    public let createdAt: Date
    public let expiresAt: Date
    public var state: SessionState
    public let grantToken: String
    public let uploadURL: String?
    public let maxDurationSeconds: Int
    
    public var isExpired: Bool {
        return Date() > expiresAt
    }
    
    public init(
        id: String,
        projectId: String,
        projectName: String,
        roomId: String,
        roomName: String,
        operatorName: String? = nil,
        createdAt: Date = Date(),
        expiresAt: Date = Date().addingTimeInterval(3600),
        state: SessionState = .authorized,
        grantToken: String,
        uploadURL: String? = nil,
        maxDurationSeconds: Int = 180
    ) {
        self.id = id
        self.projectId = projectId
        self.projectName = projectName
        self.roomId = roomId
        self.roomName = roomName
        self.operatorName = operatorName
        self.createdAt = createdAt
        self.expiresAt = expiresAt
        self.state = state
        self.grantToken = grantToken
        self.uploadURL = uploadURL
        self.maxDurationSeconds = maxDurationSeconds
    }
}

public struct SessionAuthorization: Codable {
    public let sessionId: String
    public let grantToken: String
    public let issuedAt: Date
    public let expiresAt: Date
    public let signature: String
    
    public var isValid: Bool {
        return Date() < expiresAt && !grantToken.isEmpty
    }
}

public struct DeviceReadinessStatus {
    public var hasCameraPermission: Bool = false
    public var hasARWorldTracking: Bool = false
    public var availableStorageMB: Int64 = 0
    public var batteryLevel: Float = 1.0
    public var thermalStateNominal: Bool = true
    
    public var isReadyToCapture: Bool {
        return hasCameraPermission && hasARWorldTracking && availableStorageMB >= 500
    }
}

