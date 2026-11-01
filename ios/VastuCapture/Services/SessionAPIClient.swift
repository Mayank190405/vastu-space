import Foundation
import Combine

public enum SessionAuthError: LocalizedError, Equatable {
    case invalidQRFormat(String)
    case challengeExpired
    case replayDetected(String)
    case serverRejected(String)
    case networkUnavailable(String)
    case unauthorizedDevice
    case missingCredentials
    case recordingForbidden(String)
    
    public var errorDescription: String? {
        switch self {
        case .invalidQRFormat(let msg):
            return "Invalid QR Code: \(msg)"
        case .challengeExpired:
            return "Session QR code has expired. Please scan an active session."
        case .replayDetected(let msg):
            return "Security Alert: \(msg)"
        case .serverRejected(let msg):
            return "Server Authorization Failed: \(msg)"
        case .networkUnavailable(let msg):
            return "Network Error: \(msg)"
        case .unauthorizedDevice:
            return "Device verification failed. Only authorized devices can capture."
        case .missingCredentials:
            return "Missing session authorization credentials."
        case .recordingForbidden(let msg):
            return "Recording Locked: \(msg)"
        }
    }
}

public struct ParsedQRChallenge {
    public let sessionId: String
    public let challengeToken: String
    public let nonce: String
    public let endpoint: String
    public let projectId: String
    public let projectName: String
    public let roomId: String
    public let roomName: String
    public let operatorName: String?
    public let expiresAt: Date
    public let offlineVerifiableGrant: String?
}

public protocol SessionAPIClientProtocol: AnyObject {
    func parseQRChallenge(rawPayload: String) throws -> ParsedQRChallenge
    func redeemChallenge(_ challenge: ParsedQRChallenge, deviceUUID: String) async throws -> CaptureSession
    func finalizeSession(sessionId: String, grantToken: String, endpoint: String) async throws -> Bool
}

public final class SessionAPIClient: ObservableObject, SessionAPIClientProtocol {
    public static let shared = SessionAPIClient()
    
    public var defaultBaseURL: String = "https://vastu.krads.co.in"
    private let urlSession: URLSession
    
    public init(urlSession: URLSession = .shared) {
        self.urlSession = urlSession
    }
    
    // MARK: - 1. QR Payload Parsing & Validation
    public func parseQRChallenge(rawPayload: String) throws -> ParsedQRChallenge {
        let trimmed = rawPayload.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            throw SessionAuthError.invalidQRFormat("Empty QR payload")
        }
        
        // A. JSON Payload Format
        if trimmed.hasPrefix("{") && trimmed.hasSuffix("}") {
            guard let data = trimmed.data(using: .utf8),
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                throw SessionAuthError.invalidQRFormat("Malformed JSON structure")
            }
            
            guard let sessionId = json["session_id"] as? String, !sessionId.isEmpty,
                  let challenge = json["challenge_token"] as? String ?? json["challenge"] as? String, !challenge.isEmpty else {
                throw SessionAuthError.invalidQRFormat("Missing session_id or challenge in JSON")
            }
            
            let endpoint = json["endpoint"] as? String ?? defaultBaseURL
            let nonce = json["nonce"] as? String ?? challenge
            let projectId = json["project_id"] as? String ?? "proj_\(sessionId.prefix(8))"
            let projectName = json["project_name"] as? String ?? "VĀSTU Space"
            let roomId = json["room_id"] as? String ?? "room_\(sessionId.suffix(6))"
            let roomName = json["room_name"] as? String ?? "Room Scan"
            let operatorName = json["operator_name"] as? String
            
            let expTimestamp = json["expires_at"] as? TimeInterval ?? (Date().timeIntervalSince1970 + 3600)
            let expiresAt = Date(timeIntervalSince1970: expTimestamp)
            
            if Date() > expiresAt {
                throw SessionAuthError.challengeExpired
            }
            
            return ParsedQRChallenge(
                sessionId: sessionId,
                challengeToken: challenge,
                nonce: nonce,
                endpoint: endpoint,
                projectId: projectId,
                projectName: projectName,
                roomId: roomId,
                roomName: roomName,
                operatorName: operatorName,
                expiresAt: expiresAt,
                offlineVerifiableGrant: json["offline_grant"] as? String
            )
        }
        
        // B. URL / Deep-Link Format (vastu://, vastuspatial://, or https://)
        guard let url = URL(string: trimmed) else {
            throw SessionAuthError.invalidQRFormat("Payload is not a valid URI: \(trimmed)")
        }
        
        let scheme = url.scheme?.lowercased() ?? ""
        guard ["vastu", "vastuspatial", "https", "http"].contains(scheme) else {
            throw SessionAuthError.invalidQRFormat("Unsupported protocol scheme '\(scheme)'. Must be vastu:// or https://")
        }
        
        let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        let queryMap = Dictionary(uniqueKeysWithValues: components?.queryItems?.compactMap { item in
            item.value.map { (item.name, $0) }
        } ?? [])
        
        if ["https", "http"].contains(scheme) {
            let isVastuHost = (url.host ?? "").lowercased().contains("vastu")
            let hasCapturePath = url.path.contains("/capture")
            let hasSessionParam = queryMap["session_id"] != nil
            guard isVastuHost || hasCapturePath || hasSessionParam else {
                throw SessionAuthError.invalidQRFormat("URL does not originate from a recognized VĀSTU domain or capture endpoint")
            }
        }
        
        var sessionId = queryMap["session_id"] ?? ""
        if sessionId.isEmpty {
            // Extract from URL path (e.g., vastuspatial://capture/{session_id} or https://.../capture/{session_id})
            let pathSegments = url.pathComponents.filter { $0 != "/" && !$0.isEmpty }
            if let last = pathSegments.last, last != "capture" {
                sessionId = last
            } else if let host = url.host, host != "capture-session" && host != "capture" && !host.contains(".") {
                sessionId = host
            }
        }
        
        guard !sessionId.isEmpty else {
            throw SessionAuthError.invalidQRFormat("Session ID could not be identified in QR URI")
        }
        
        let challenge = queryMap["challenge"] ?? queryMap["challenge_token"] ?? "chal_\(sessionId)"
        let nonce = queryMap["nonce"] ?? challenge
        let endpoint = queryMap["endpoint"] ?? defaultBaseURL
        let projectId = queryMap["project_id"] ?? queryMap["projectId"] ?? "proj_\(sessionId.prefix(8))"
        let projectName = queryMap["project_name"] ?? "VĀSTU Residence"
        let roomId = queryMap["room_id"] ?? "room_\(sessionId.suffix(6))"
        let roomName = queryMap["room_name"] ?? queryMap["floor"] ?? "Living Space"
        let operatorName = queryMap["operator"] ?? queryMap["operator_name"]
        
        var expiresAt = Date().addingTimeInterval(3600) // Default 1 hour TTL
        if let expStr = queryMap["expires_at"], let expSec = Double(expStr) {
            expiresAt = Date(timeIntervalSince1970: expSec)
        }
        
        if Date() > expiresAt {
            throw SessionAuthError.challengeExpired
        }
        
        return ParsedQRChallenge(
            sessionId: sessionId,
            challengeToken: challenge,
            nonce: nonce,
            endpoint: endpoint,
            projectId: projectId,
            projectName: projectName,
            roomId: roomId,
            roomName: roomName,
            operatorName: operatorName,
            expiresAt: expiresAt,
            offlineVerifiableGrant: queryMap["grant"]
        )
    }
    
    // MARK: - 2. Server-Side Challenge Redemption
    public func redeemChallenge(_ challenge: ParsedQRChallenge, deviceUUID: String) async throws -> CaptureSession {
        // Enforce challenge expiration
        if Date() > challenge.expiresAt {
            throw SessionAuthError.challengeExpired
        }
        
        let redeemUrlString = "\(challenge.endpoint)/api/v1/capture-sessions/redeem"
        guard let url = URL(string: redeemUrlString) else {
            throw SessionAuthError.invalidQRFormat("Invalid endpoint URL: \(redeemUrlString)")
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 8.0
        
        let payload: [String: Any] = [
            "session_id": challenge.sessionId,
            "challenge_token": challenge.challengeToken,
            "nonce": challenge.nonce,
            "device_id": deviceUUID,
            "device_model": "iPhone",
            "device_os": "iOS 17+",
            "client_timestamp": ISO8601DateFormatter().string(from: Date())
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        
        do {
            let (data, response) = try await urlSession.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw SessionAuthError.networkUnavailable("Invalid server response")
            }
            
            if httpResponse.statusCode == 200 || httpResponse.statusCode == 201 {
                if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let grantToken = (json["grant_token"] as? String) ?? (json["data"] as? [String: Any])?["grant_token"] as? String {
                    
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
                        grantToken: grantToken,
                        uploadURL: "\(challenge.endpoint)/api/v1/captures/upload",
                        maxDurationSeconds: 600
                    )
                }
            } else if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
                throw SessionAuthError.serverRejected("Server rejected challenge redemption (HTTP \(httpResponse.statusCode))")
            } else if httpResponse.statusCode == 409 {
                throw SessionAuthError.replayDetected("Challenge token already redeemed on server")
            }
        } catch let authErr as SessionAuthError {
            throw authErr
        } catch {
            // Network fallback: if offline but valid grant provided in challenge
            if let offlineGrant = challenge.offlineVerifiableGrant, !offlineGrant.isEmpty {
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
                    grantToken: offlineGrant,
                    uploadURL: "\(challenge.endpoint)/api/v1/captures/upload",
                    maxDurationSeconds: 600
                )
            }
            
            // Check if local connection error or unreachable host
            let nsError = error as NSError
            if nsError.domain == NSURLErrorDomain {
                // If offline and within valid TTL, issue locally scoped grant
                let fallbackGrant = "local_grant_\(challenge.sessionId)_\(UUID().uuidString.prefix(8))"
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
                    grantToken: fallbackGrant,
                    uploadURL: "\(challenge.endpoint)/api/v1/captures/upload",
                    maxDurationSeconds: 600
                )
            }
            throw SessionAuthError.networkUnavailable(error.localizedDescription)
        }
        
        throw SessionAuthError.serverRejected("Redemption failed")
    }
    
    // MARK: - 3. Finalize Session with Backend
    public func finalizeSession(sessionId: String, capturePackageDir: URL) async throws -> Bool {
        let token = SecureSessionStore.shared.retrieveGrant(sessionId: sessionId)?.grantToken ?? "local_grant"
        return try await finalizeSession(sessionId: sessionId, grantToken: token, endpoint: defaultBaseURL)
    }
    
    public func finalizeSession(sessionId: String, grantToken: String, endpoint: String) async throws -> Bool {
        guard let url = URL(string: "\(endpoint)/api/v1/capture-sessions/\(sessionId)/finalize") else {
            return false
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(grantToken)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "session_id": sessionId,
            "finalized_at": ISO8601DateFormatter().string(from: Date())
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        let (_, response) = try await urlSession.data(for: request)
        if let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) {
            return true
        }
        return false
    }
    
    // MARK: - 4. Phase 7 Real-Time Telemetry & Heartbeats
    public func sendHeartbeat(
        sessionId: String?,
        deviceUUID: String,
        battery: Double = 0.85,
        trackingState: String = "NORMAL",
        localAIReady: Bool = true,
        recordingState: String = "IDLE",
        endpoint: String? = nil
    ) async -> Bool {
        let targetEndpoint = endpoint ?? defaultBaseURL
        guard let url = URL(string: "\(targetEndpoint)/api/v1/devices/heartbeat") else {
            return false
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 4.0
        
        let body: [String: Any] = [
            "device_uuid": deviceUUID,
            "device_model": "iPhone",
            "device_os": "iOS 17+",
            "app_version": "1.0.0",
            "session_id": sessionId as Any,
            "battery_level": battery,
            "arkit_tracking_status": trackingState,
            "local_ai_status": localAIReady ? "READY" : "INITIALIZING",
            "recording_state": recordingState,
            "network_type": "WIFI",
            "storage_free_mb": StorageMonitor.getAvailableStorageMB()
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        do {
            let (_, response) = try await urlSession.data(for: request)
            if let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) {
                return true
            }
        } catch {
            // Heartbeat drops fail gracefully without crashing or interrupting capture
        }
        return false
    }
    
    public func reportPipelineStage(
        sessionId: String,
        stageName: String,
        status: String,
        progress: Int = 0,
        worker: String = "iPhone Capture Engine",
        errorDetails: String? = nil,
        endpoint: String? = nil
    ) async -> Bool {
        let targetEndpoint = endpoint ?? defaultBaseURL
        guard let url = URL(string: "\(targetEndpoint)/api/v1/capture-sessions/\(sessionId)/stages/\(stageName)") else {
            return false
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 4.0
        
        var body: [String: Any] = [
            "status": status,
            "progress_percentage": progress,
            "responsible_worker": worker
        ]
        if let err = errorDetails {
            body["error_details"] = err
        }
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        do {
            let (_, response) = try await urlSession.data(for: request)
            if let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) {
                return true
            }
        } catch {
            // Telemetry reporting drops fail gracefully
        }
        return false
    }
}
