import Foundation

// In-Memory test double for SecureSessionStore
public final class MockSecureSessionStore: SecureSessionStoreProtocol {
    public var storedGrants: [String: SessionGrantRecord] = [:]
    public var activeSessionId: String?
    public var redeemedNonces: Set<String> = []
    
    public init() {}
    
    public func saveGrant(_ record: SessionGrantRecord) -> Bool {
        storedGrants[record.sessionId] = record
        activeSessionId = record.sessionId
        return true
    }
    
    public func retrieveGrant(sessionId: String) -> SessionGrantRecord? {
        return storedGrants[sessionId]
    }
    
    public func retrieveActiveGrant() -> SessionGrantRecord? {
        guard let activeId = activeSessionId else { return nil }
        return retrieveGrant(sessionId: activeId)
    }
    
    public func deleteGrant(sessionId: String) -> Bool {
        storedGrants.removeValue(forKey: sessionId)
        if activeSessionId == sessionId {
            activeSessionId = nil
        }
        return true
    }
    
    public func clearAllGrants() -> Bool {
        storedGrants.removeAll()
        activeSessionId = nil
        redeemedNonces.removeAll()
        return true
    }
    
    public func recordRedeemedNonce(_ nonce: String) {
        redeemedNonces.insert(nonce)
    }
    
    public func isNonceRedeemed(_ nonce: String) -> Bool {
        return redeemedNonces.contains(nonce)
    }
}

// Mock API Client to test redemption logic without external network dependencies
public final class MockSessionAPIClient: SessionAPIClientProtocol {
    public var shouldFailRedemption = false
    public var failureError: SessionAuthError = .serverRejected("Mock server rejection")
    private let realParser = SessionAPIClient()
    
    public init() {}
    
    public func parseQRChallenge(rawPayload: String) throws -> ParsedQRChallenge {
        return try realParser.parseQRChallenge(rawPayload: rawPayload)
    }
    
    public func redeemChallenge(_ challenge: ParsedQRChallenge, deviceUUID: String) async throws -> CaptureSession {
        if shouldFailRedemption {
            throw failureError
        }
        
        return CaptureSession(
            id: challenge.sessionId,
            projectId: challenge.projectId,
            projectName: challenge.projectName,
            roomId: challenge.roomId,
            roomName: challenge.roomName,
            operatorName: challenge.operatorName,
            createdAt: Date(),
            expiresAt: challenge.expiresAt,
            state: .authorized,
            grantToken: "mock_jwt_grant_\(challenge.sessionId)",
            uploadURL: "https://vastu.krads.co.in/api/v1/captures/upload",
            maxDurationSeconds: 600
        )
    }
    
    public func finalizeSession(sessionId: String, grantToken: String, endpoint: String) async throws -> Bool {
        return true
    }
}

public class SessionAuthorizationManagerTests {
    public static func runPhase2Tests(report: TestReport) async {
        print("\n==================================================")
        print("🔐 Phase 2: QR Authentication & Session Tests")
        print("==================================================")
        
        await testValidQRAuthorizationFlow(report)
        await testReplayPrevention(report)
        await testExpiredQRRejection(report)
        await testMalformedQRRejection(report)
        testRecordingLockEnforcement(report)
        testSessionRestorationOnRestart(report)
        testRevokeAndCompleteLifecycle(report)
    }
    
    // 1. Valid QR Authorization Flow
    private static func testValidQRAuthorizationFlow(_ report: TestReport) async {
        print("\n[Phase 2 - Test 1/7] Valid QR Authorization Flow")
        let store = MockSecureSessionStore()
        let api = MockSessionAPIClient()
        let manager = SessionAuthorizationManager(secureStore: store, apiClient: api, deviceUUID: "dev_iphone_17")
        
        await MainActor.run {
            report.check(manager.state == .unauthorized, "Initial state is UNAUTHORIZED")
            report.check(manager.canStartRecording == false, "Recording disabled initially")
        }
        
        let validPayload = "vastu://capture-session?endpoint=https%3A%2F%2Fvastu.krads.co.in&challenge=chal_pass_1&nonce=nonce_pass_1&session_id=sess_penthouse_9&project_id=proj_77&project_name=Sky%20Penthouse&room_id=room_2&room_name=Master%20Suite"
        
        let result = await manager.redeemQR(rawCode: validPayload)
        switch result {
        case .success(let session):
            report.check(session.id == "sess_penthouse_9", "Session ID correctly extracted")
            report.check(session.projectName == "Sky Penthouse", "Project name correctly bound")
            report.check(session.roomName == "Master Suite", "Room name correctly bound")
            await MainActor.run {
                report.check(manager.state == .ready, "Manager state advanced to READY")
                report.check(manager.canStartRecording == true, "Recording unlocked upon valid authorization")
            }
            report.check(store.retrieveGrant(sessionId: "sess_penthouse_9") != nil, "Grant token saved in SecureSessionStore")
            report.check(store.isNonceRedeemed("nonce_pass_1"), "Nonce registered as redeemed")
        case .failure(let err):
            report.check(false, "Expected success but got: \(err)")
        }
    }
    
    // 2. Anti-Replay Security Test
    private static func testReplayPrevention(_ report: TestReport) async {
        print("\n[Phase 2 - Test 2/7] Anti-Replay Challenge Protection")
        let store = MockSecureSessionStore()
        let api = MockSessionAPIClient()
        let manager = SessionAuthorizationManager(secureStore: store, apiClient: api, deviceUUID: "dev_iphone_17")
        
        let reusablePayload = "vastu://capture-session?endpoint=https%3A%2F%2Fvastu.krads.co.in&challenge=chal_reuse&nonce=single_use_nonce_123&session_id=sess_once"
        
        let res1 = await manager.redeemQR(rawCode: reusablePayload)
        switch res1 {
        case .success:
            report.check(true, "First redemption of single-use QR succeeded")
        case .failure:
            report.check(false, "First redemption should succeed")
        }
        
        // Second attempt with identical challenge/nonce must be rejected
        let res2 = await manager.redeemQR(rawCode: reusablePayload)
        switch res2 {
        case .success:
            report.check(false, "Replay attack was NOT blocked!")
        case .failure(let err):
            report.check(err == .replayDetected("QR Challenge 'single_use_nonce_123' has already been redeemed. Single-use QR codes cannot be reused."), "Replayed QR code strictly blocked with .replayDetected")
            await MainActor.run {
                report.check(manager.state == .unauthorized, "State reset to UNAUTHORIZED on replay attempt")
                report.check(manager.canStartRecording == false, "Recording remains locked on replay attempt")
            }
        }
    }
    
    // 3. Expired QR Rejection Test
    private static func testExpiredQRRejection(_ report: TestReport) async {
        print("\n[Phase 2 - Test 3/7] Expired QR Challenge Rejection")
        let store = MockSecureSessionStore()
        let api = MockSessionAPIClient()
        let manager = SessionAuthorizationManager(secureStore: store, apiClient: api, deviceUUID: "dev_iphone_17")
        
        let pastTimestamp = Date().addingTimeInterval(-120).timeIntervalSince1970 // Expired 2 minutes ago
        let expiredPayload = "vastu://capture-session?endpoint=https%3A%2F%2Fvastu.krads.co.in&challenge=chal_old&nonce=nonce_old&session_id=sess_expired&expires_at=\(pastTimestamp)"
        
        let res = await manager.redeemQR(rawCode: expiredPayload)
        switch res {
        case .success:
            report.check(false, "Expired QR code was accepted when it should be rejected!")
        case .failure(let err):
            report.check(err == .challengeExpired, "Expired QR rejected with .challengeExpired")
            await MainActor.run {
                report.check(manager.state == .expired, "Manager state transitioned to EXPIRED")
                report.check(manager.canStartRecording == false, "Recording strictly locked on expired QR")
            }
        }
    }
    
    // 4. Malformed QR Rejection Test
    private static func testMalformedQRRejection(_ report: TestReport) async {
        print("\n[Phase 2 - Test 4/7] Malformed QR Code Handling")
        let store = MockSecureSessionStore()
        let api = MockSessionAPIClient()
        let manager = SessionAuthorizationManager(secureStore: store, apiClient: api)
        
        let invalidPayloads = [
            "",
            "ftp://invalid.com/file",
            "not_a_valid_url_or_json",
            "https://randomsite.com/hello",
            "{\"broken_json\": 123"
        ]
        
        for payload in invalidPayloads {
            let res = await manager.redeemQR(rawCode: payload)
            switch res {
            case .success:
                report.check(false, "Malformed payload '\(payload)' was unexpectedly accepted")
            case .failure:
                report.check(true, "Malformed payload correctly rejected")
            }
        }
    }
    
    // 5. Strict Recording Lock Enforcement
    private static func testRecordingLockEnforcement(_ report: TestReport) {
        print("\n[Phase 2 - Test 5/7] Recording Lock Enforcement")
        let store = MockSecureSessionStore()
        let api = MockSessionAPIClient()
        let manager = SessionAuthorizationManager(secureStore: store, apiClient: api)
        
        // When UNAUTHORIZED
        report.check(manager.canStartRecording == false, "canStartRecording is FALSE when unauthorized")
        do {
            try manager.beginRecording()
            report.check(false, "beginRecording() succeeded when unauthorized!")
        } catch {
            report.check(true, "beginRecording() correctly threw recordingForbidden when unauthorized")
        }
        
        // Simulate recording without valid Keychain grant
        do {
            try manager.assertRecordingAuthorized()
            report.check(false, "assertRecordingAuthorized() succeeded with empty session!")
        } catch {
            report.check(true, "assertRecordingAuthorized() threw without valid credentials")
        }
    }
    
    // 6. Session Restoration on App Restart
    private static func testSessionRestorationOnRestart(_ report: TestReport) {
        print("\n[Phase 2 - Test 6/7] Session Restoration Across Restarts")
        let store = MockSecureSessionStore()
        let api = MockSessionAPIClient()
        
        // Pre-populate store with an unexpired active grant
        let validGrant = SessionGrantRecord(
            sessionId: "sess_persisted_1",
            grantToken: "jwt_token_persisted",
            createdAt: Date(),
            expiresAt: Date().addingTimeInterval(1800), // Valid for 30 more minutes
            deviceUUID: "dev_iphone_17",
            projectId: "proj_persisted",
            roomName: "Dining Room"
        )
        _ = store.saveGrant(validGrant)
        
        // Create a fresh manager instance (simulating app relaunch)
        let freshManager = SessionAuthorizationManager(secureStore: store, apiClient: api)
        report.check(freshManager.state == .ready, "Valid grant restored to READY on launch")
        report.check(freshManager.currentSession?.id == "sess_persisted_1", "Restored session ID matches")
        report.check(freshManager.canStartRecording == true, "Recording unlocked on restored unexpired session")
        
        // Now test launch with an EXPIRED grant in store
        let expiredGrant = SessionGrantRecord(
            sessionId: "sess_expired_saved",
            grantToken: "jwt_token_expired",
            createdAt: Date().addingTimeInterval(-7200),
            expiresAt: Date().addingTimeInterval(-3600), // Expired 1 hour ago
            deviceUUID: "dev_iphone_17",
            projectId: "proj_expired",
            roomName: "Balcony"
        )
        _ = store.saveGrant(expiredGrant)
        
        let expiredLaunchManager = SessionAuthorizationManager(secureStore: store, apiClient: api)
        report.check(expiredLaunchManager.state == .expired, "Expired saved grant transitions to EXPIRED on launch")
        report.check(expiredLaunchManager.canStartRecording == false, "Recording remains locked on expired relaunch")
        report.check(store.retrieveGrant(sessionId: "sess_expired_saved") == nil, "Expired grant automatically purged from store")
    }
    
    // 7. Revocation and Completion Lifecycle
    private static func testRevokeAndCompleteLifecycle(_ report: TestReport) {
        print("\n[Phase 2 - Test 7/7] Revoke and Complete Lifecycle")
        let store = MockSecureSessionStore()
        let api = MockSessionAPIClient()
        let manager = SessionAuthorizationManager(secureStore: store, apiClient: api)
        
        let grant = SessionGrantRecord(
            sessionId: "sess_lifecycle",
            grantToken: "jwt_token",
            expiresAt: Date().addingTimeInterval(3600),
            deviceUUID: "dev_iphone_17",
            projectId: "proj_1",
            roomName: "Library"
        )
        _ = store.saveGrant(grant)
        manager.restoreActiveSessionIfValid()
        
        report.check(manager.state == .ready, "State ready before completion")
        
        // Complete session
        manager.completeSession()
        report.check(manager.state == .completed, "State transitioned to COMPLETED")
        report.check(manager.canStartRecording == false, "Recording disabled once session completed")
        report.check(store.retrieveGrant(sessionId: "sess_lifecycle") == nil, "Grant purged from Keychain on completion")
        
        // Revoke session
        let grant2 = SessionGrantRecord(
            sessionId: "sess_to_revoke",
            grantToken: "jwt_token_2",
            expiresAt: Date().addingTimeInterval(3600),
            deviceUUID: "dev_iphone_17",
            projectId: "proj_2",
            roomName: "Garage"
        )
        _ = store.saveGrant(grant2)
        manager.restoreActiveSessionIfValid()
        
        manager.revokeSession(reason: "Operator security token revoked by administrator")
        report.check(manager.state == .revoked, "State transitioned to REVOKED")
        report.check(manager.canStartRecording == false, "Recording disabled once revoked")
        report.check(store.retrieveGrant(sessionId: "sess_to_revoke") == nil, "Grant purged on revocation")
    }
    
    // MARK: - Phase 7 Telemetry & Device Heartbeat Tests
    public static func runPhase7Tests(report: TestReport) async {
        print("\n==================================================")
        print("📡 Phase 7: Real-Time Heartbeat & Stage Telemetry Tests")
        print("==================================================")
        
        testDeviceUUIDPersistence(report)
        await testHeartbeatTransmission(report)
        await testPipelineStageReporting(report)
    }
    
    private static func testDeviceUUIDPersistence(_ report: TestReport) {
        print("\n[Phase 7 - Test 1/3] Device UUID Persistence in Secure Store")
        let store = SecureSessionStore.shared
        let uuid1 = store.deviceUUID
        let uuid2 = store.deviceUUID
        report.check(!uuid1.isEmpty, "Device UUID is not empty")
        report.check(uuid1 == uuid2, "Device UUID is consistent across reads on same device")
    }
    
    private static func testHeartbeatTransmission(_ report: TestReport) async {
        print("\n[Phase 7 - Test 2/3] Heartbeat Non-Blocking Dispatch & Failure Grace")
        let client = SessionAPIClient.shared
        
        // Test heartbeat with local dummy endpoint (fails gracefully without crashing or throwing)
        let sent = await client.sendHeartbeat(
            sessionId: "sess_test_hb",
            deviceUUID: "mock_device_uuid_15",
            battery: 0.92,
            trackingState: "NORMAL",
            localAIReady: true,
            recordingState: "RECORDING",
            endpoint: "http://127.0.0.1:9" // unreachable port
        )
        report.check(sent == false, "Heartbeat gracefully handles network offline without crashing")
    }
    
    private static func testPipelineStageReporting(_ report: TestReport) async {
        print("\n[Phase 7 - Test 3/3] Real Pipeline Stage Reporting Telemetry")
        let client = SessionAPIClient.shared
        
        let reported = await client.reportPipelineStage(
            sessionId: "sess_test_hb",
            stageName: "LOCAL_AI_ANALYSIS",
            status: "RUNNING",
            progress: 45,
            worker: "iPhone 15 Engine",
            errorDetails: nil,
            endpoint: "http://127.0.0.1:9" // unreachable port
        )
        report.check(reported == false, "Pipeline stage telemetry gracefully handles offline endpoint")
    }
}
