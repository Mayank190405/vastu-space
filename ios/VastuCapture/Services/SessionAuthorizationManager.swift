import Foundation
import Combine

public final class SessionAuthorizationManager: ObservableObject {
    public static let shared = SessionAuthorizationManager()
    
    @Published public private(set) var state: SessionState = .unauthorized
    @Published public private(set) var currentSession: CaptureSession?
    @Published public private(set) var errorMessage: String?
    @Published public private(set) var canStartRecording: Bool = false
    
    private let secureStore: SecureSessionStoreProtocol
    private let apiClient: SessionAPIClientProtocol
    private let deviceUUID: String
    private var expirationTimer: Timer?
    
    public init(
        secureStore: SecureSessionStoreProtocol = SecureSessionStore.shared,
        apiClient: SessionAPIClientProtocol = SessionAPIClient.shared,
        deviceUUID: String = UUID().uuidString
    ) {
        self.secureStore = secureStore
        self.apiClient = apiClient
        self.deviceUUID = deviceUUID
        restoreActiveSessionIfValid()
    }
    
    deinit {
        expirationTimer?.invalidate()
    }
    
    // MARK: - Startup Session Restoration
    public func restoreActiveSessionIfValid() {
        guard let grantRecord = secureStore.retrieveActiveGrant() else {
            transitionTo(state: .unauthorized)
            return
        }
        
        if grantRecord.isExpired {
            _ = secureStore.deleteGrant(sessionId: grantRecord.sessionId)
            transitionTo(state: .expired, error: "Previous capture session has expired.")
            return
        }
        
        // Restore active session
        let session = CaptureSession(
            id: grantRecord.sessionId,
            projectId: grantRecord.projectId,
            projectName: "Restored Project",
            roomId: "restored_room",
            roomName: grantRecord.roomName,
            operatorName: nil,
            createdAt: grantRecord.createdAt,
            expiresAt: grantRecord.expiresAt,
            state: .ready,
            grantToken: grantRecord.grantToken,
            uploadURL: nil,
            maxDurationSeconds: 600
        )
        
        self.currentSession = session
        transitionTo(state: .ready)
        startExpirationWatcher(expiresAt: grantRecord.expiresAt)
    }
    
    // MARK: - QR Challenge Redemption Flow
    @MainActor
    public func redeemQR(rawCode: String) async -> Result<CaptureSession, SessionAuthError> {
        self.errorMessage = nil
        transitionTo(state: .qrScanning)
        
        // 1. Parse and validate syntax
        let challenge: ParsedQRChallenge
        do {
            challenge = try apiClient.parseQRChallenge(rawPayload: rawCode)
        } catch let authErr as SessionAuthError {
            if authErr == .challengeExpired {
                transitionTo(state: .expired, error: authErr.localizedDescription)
            } else {
                transitionTo(state: .unauthorized, error: authErr.localizedDescription)
            }
            return .failure(authErr)
        } catch {
            let err = SessionAuthError.invalidQRFormat(error.localizedDescription)
            transitionTo(state: .unauthorized, error: err.localizedDescription)
            return .failure(err)
        }
        
        // 2. Anti-Replay: Verify challenge nonce has not already been redeemed
        if secureStore.isNonceRedeemed(challenge.nonce) {
            let replayErr = SessionAuthError.replayDetected("QR Challenge '\(challenge.nonce)' has already been redeemed. Single-use QR codes cannot be reused.")
            transitionTo(state: .unauthorized, error: replayErr.localizedDescription)
            return .failure(replayErr)
        }
        
        // 3. TTL Check: Verify not expired
        if challenge.expiresAt < Date() {
            let expErr = SessionAuthError.challengeExpired
            transitionTo(state: .expired, error: expErr.localizedDescription)
            return .failure(expErr)
        }
        
        // 4. State transition: QR Validating
        transitionTo(state: .qrValidating)
        
        // 5. Server Redemption via TLS
        do {
            let authorizedSession = try await apiClient.redeemChallenge(challenge, deviceUUID: deviceUUID)
            
            // Mark challenge nonce as redeemed to prevent replay
            secureStore.recordRedeemedNonce(challenge.nonce)
            
            // Persist scoped grant in Keychain
            let grantRecord = SessionGrantRecord(
                sessionId: authorizedSession.id,
                grantToken: authorizedSession.grantToken,
                createdAt: authorizedSession.createdAt,
                expiresAt: authorizedSession.expiresAt,
                deviceUUID: deviceUUID,
                projectId: authorizedSession.projectId,
                roomName: authorizedSession.roomName
            )
            _ = secureStore.saveGrant(grantRecord)
            
            self.currentSession = authorizedSession
            
            // Step through lifecycle
            transitionTo(state: .authorized)
            transitionTo(state: .deviceCheck)
            transitionTo(state: .ready)
            
            startExpirationWatcher(expiresAt: authorizedSession.expiresAt)
            return .success(authorizedSession)
        } catch let authErr as SessionAuthError {
            transitionTo(state: .unauthorized, error: authErr.localizedDescription)
            return .failure(authErr)
        } catch {
            let networkErr = SessionAuthError.networkUnavailable(error.localizedDescription)
            transitionTo(state: .unauthorized, error: networkErr.localizedDescription)
            return .failure(networkErr)
        }
    }
    
    // MARK: - Strict Recording Lock Enforcement
    public func assertRecordingAuthorized() throws {
        guard let session = currentSession, !session.isExpired else {
            throw SessionAuthError.recordingForbidden("No active session exists or session has expired.")
        }
        
        guard state == .ready || state == .recording || state == .paused || state == .trackingRecovery else {
            throw SessionAuthError.recordingForbidden("Cannot record in state '\(state.rawValue)'. Valid authorization is required.")
        }
        
        guard let grant = secureStore.retrieveGrant(sessionId: session.id), !grant.isExpired else {
            throw SessionAuthError.recordingForbidden("Keychain credentials expired or missing.")
        }
    }
    
    // MARK: - State Transitions
    public func beginRecording() throws {
        try assertRecordingAuthorized()
        transitionTo(state: .recording)
    }
    
    public func pauseRecording() {
        if state == .recording {
            transitionTo(state: .paused)
        }
    }
    
    public func resumeRecording() throws {
        try assertRecordingAuthorized()
        transitionTo(state: .recording)
    }
    
    public func stopRecordingForReview() {
        if state == .recording || state == .paused {
            transitionTo(state: .validatingCapture)
        }
    }
    
    public func markUploading() {
        transitionTo(state: .uploading)
    }
    
    public func completeSession() {
        if let s = currentSession {
            _ = secureStore.deleteGrant(sessionId: s.id)
        }
        transitionTo(state: .completed)
    }
    
    public func revokeSession(reason: String) {
        if let s = currentSession {
            _ = secureStore.deleteGrant(sessionId: s.id)
        }
        transitionTo(state: .revoked, error: reason)
    }
    
    public func resetToScanner() {
        expirationTimer?.invalidate()
        currentSession = nil
        errorMessage = nil
        transitionTo(state: .unauthorized)
    }
    
    // MARK: - Private Helpers
    private func transitionTo(state: SessionState, error: String? = nil) {
        self.state = state
        self.errorMessage = error
        
        // Lock recording unless strictly in READY state with non-expired session
        let isSessionValid = currentSession != nil && !(currentSession?.isExpired ?? true)
        self.canStartRecording = (state == .ready) && isSessionValid
        
        if state == .expired || state == .revoked || state == .unauthorized {
            self.canStartRecording = false
        }
    }
    
    private func startExpirationWatcher(expiresAt: Date) {
        expirationTimer?.invalidate()
        let interval = max(1.0, expiresAt.timeIntervalSince(Date()))
        
        expirationTimer = Timer.scheduledTimer(withTimeInterval: interval, repeats: false) { [weak self] _ in
            DispatchQueue.main.async {
                self?.handleSessionExpired()
            }
        }
    }
    
    private func handleSessionExpired() {
        if let s = currentSession {
            _ = secureStore.deleteGrant(sessionId: s.id)
        }
        transitionTo(state: .expired, error: "Session grant expired. Please scan a newly authorized session QR code.")
    }
}
