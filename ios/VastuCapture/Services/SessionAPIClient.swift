import Foundation
import Combine
#if canImport(UIKit)
import UIKit
#endif
import CryptoKit

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
        
        // A display code is not a redeemable challenge.
        guard trimmed.contains("://") else {
            throw SessionAuthError.invalidQRFormat("Scan the full server-issued QR code.")
        }

        // C. URL / Deep-Link Format (vastu://, vastuspatial://, or https://)
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
        
        #if canImport(UIKit)
        let deviceModel = UIDevice.current.model
        let deviceOS = "\(UIDevice.current.systemName) \(UIDevice.current.systemVersion)"
        #else
        let deviceModel = "iPhone (macOS Test Runner)"
        let deviceOS = "iOS 17.0"
        #endif
        
        let payload: [String: Any] = [
            "session_id": challenge.sessionId,
            "challenge_token": challenge.challengeToken,
            "nonce": challenge.nonce,
            "device_id": deviceUUID,
            "device_model": deviceModel,
            "device_os": deviceOS,
            "client_timestamp": ISO8601DateFormatter().string(from: Date())
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        
        do {
            let (data, response) = try await urlSession.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw SessionAuthError.networkUnavailable("Invalid server response")
            }
            
            if httpResponse.statusCode == 200 || httpResponse.statusCode == 201 {
                if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    let record = json["data"] as? [String: Any] ?? json
                    guard let grantToken = record["grant_token"] as? String, !grantToken.isEmpty,
                          let sessionID = record["session_id"] as? String, sessionID == challenge.sessionId,
                          let projectID = record["project_id"] as? String, UUID(uuidString: projectID) != nil else {
                        throw SessionAuthError.serverRejected("Invalid redemption contract")
                    }
                    return CaptureSession(
                        id: sessionID,
                        projectId: projectID,
                        projectName: record["project_name"] as? String ?? challenge.projectName,
                        roomId: record["room_id"] as? String ?? "",
                        roomName: record["room_name"] as? String ?? challenge.roomName,
                        operatorName: challenge.operatorName,
                        createdAt: Date(),
                        expiresAt: challenge.expiresAt,
                        state: .authorized,
                        grantToken: grantToken,
                        uploadURL: "\(challenge.endpoint)/api/v1/captures/upload",
                        maxDurationSeconds: 600
                    )
                }
            } else if httpResponse.statusCode == 409 {
                throw SessionAuthError.replayDetected("Challenge token already redeemed on server")
            }
            
            throw SessionAuthError.serverRejected("Redemption rejected (HTTP \(httpResponse.statusCode)); scan a server-issued QR code.")
        } catch let authErr as SessionAuthError {
            throw authErr
        } catch {
            throw SessionAuthError.networkUnavailable(error.localizedDescription)
        }
    }

    // MARK: - 3. Finalize Session with Backend
    public func finalizeSession(sessionId: String, capturePackageDir: URL) async throws -> Bool {
        guard let token = SecureSessionStore.shared.retrieveGrant(sessionId: sessionId)?.grantToken else {
            throw SessionAuthError.missingCredentials
        }
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
        guard let grantSessionID = sessionId as String?,
              let token = SecureSessionStore.shared.retrieveGrant(sessionId: grantSessionID)?.grantToken else { return false }
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.timeoutInterval = 4.0
        
        #if canImport(UIKit)
        let devModel = UIDevice.current.model
        let devOS = "\(UIDevice.current.systemName) \(UIDevice.current.systemVersion)"
        #else
        let devModel = "iPhone (macOS Test Runner)"
        let devOS = "iOS 17.0"
        #endif
        
        let body: [String: Any] = [
            "device_uuid": deviceUUID,
            "device_model": devModel,
            "device_os": devOS,
            "app_version": "1.0.0",
            "session_id": grantSessionID,
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
        guard let grantSessionID = sessionId as String?,
              let token = SecureSessionStore.shared.retrieveGrant(sessionId: grantSessionID)?.grantToken else { return false }
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
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


extension SessionAPIClient {
    public func uploadVideo(session: CaptureSession, packageURL: URL, progress: @escaping (Double, String) -> Void) async throws -> String {
        let token = session.grantToken
        guard !token.isEmpty else { throw SessionAuthError.missingCredentials }
        let video = packageURL.appendingPathComponent("capture.mp4")
        let size = (try FileManager.default.attributesOfItem(atPath: video.path)[.size] as? NSNumber)?.int64Value ?? 0
        guard size > 0 else { throw SessionAuthError.serverRejected("VIDEO_MISSING: Recorded video is empty") }
        let hashReader = try FileHandle(forReadingFrom: video)
        defer { try? hashReader.close() }
        var digest = SHA256()
        while let data = try hashReader.read(upToCount: 1 << 20), !data.isEmpty { digest.update(data: data) }
        let checksum = digest.finalize().map { String(format: "%02x", $0) }.joined()
        var endpoint = defaultBaseURL
        if let upload = session.uploadURL, let parts = URLComponents(string: upload), let scheme = parts.scheme, let host = parts.host {
            endpoint = "\(scheme)://\(host)" + (parts.port.map { ":\($0)" } ?? "")
        }
        let base = "\(endpoint)/api/v1/capture-sessions/\(session.id)"
        func call(_ suffix: String, method: String, body: Data? = nil, chunkHash: String? = nil) async throws -> [String: Any] {
            guard let url = URL(string: base + suffix) else { throw SessionAuthError.invalidQRFormat("Invalid upload endpoint") }
            var request = URLRequest(url: url)
            request.httpMethod = method
            request.timeoutInterval = 600
            request.httpBody = body
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            request.setValue(chunkHash == nil ? "application/json" : "application/octet-stream", forHTTPHeaderField: "Content-Type")
            if let hash = chunkHash { request.setValue(hash, forHTTPHeaderField: "X-Chunk-SHA256") }
            let (data, response) = try await urlSession.data(for: request)
            guard let http = response as? HTTPURLResponse else { throw SessionAuthError.networkUnavailable("Invalid response") }
            let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:]
            guard (200...299).contains(http.statusCode) else {
                throw NSError(domain: "CaptureUpload", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: json["error"] as? String ?? "Upload failed (HTTP \(http.statusCode))"])
            }
            return json["data"] as? [String: Any] ?? json
        }
        progress(0, "Initializing verified video upload...")
        let payload = try JSONSerialization.data(withJSONObject: ["file_name": "capture.mp4", "total_size_bytes": size, "sha256_checksum": checksum])
        let upload = try await call("/upload", method: "POST", body: payload)
        guard let chunkSize = (upload["chunk_size_bytes"] as? NSNumber)?.intValue, chunkSize > 0,
              let total = (upload["total_chunks"] as? NSNumber)?.intValue, total > 0 else { throw SessionAuthError.serverRejected("Invalid upload contract") }
        let state = try await call("/upload", method: "GET")
        let missing = (state["missing_chunks"] as? [Int]) ?? (state["status"] as? String == "completed" ? [] : Array(0..<total))
        let file = try FileHandle(forReadingFrom: video)
        defer { try? file.close() }
        var completed = total - missing.count
        for index in missing {
            try Task.checkCancellation()
            try file.seek(toOffset: UInt64(index * chunkSize))
            guard let data = try file.read(upToCount: chunkSize), !data.isEmpty else { throw SessionAuthError.serverRejected("VIDEO_READ_FAILED") }
            let hash = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
            for attempt in 0..<3 {
                do {
                    _ = try await call("/upload/chunks/\(index)", method: "PUT", body: data, chunkHash: hash)
                    break
                } catch {
                    let code = (error as NSError).code
                    if attempt == 2 || (400..<500).contains(code) && code != 408 && code != 429 { throw error }
                    try await Task.sleep(nanoseconds: UInt64(attempt + 1) * 1_000_000_000)
                }
            }
            completed += 1
            progress(Double(completed) / Double(total) * 0.95, "Uploaded \(completed) of \(total) video chunks")
        }
        progress(0.95, "Verifying video bytes in object storage and submitting processing...")
        let result = try await call("/finalize", method: "POST", body: Data("{}".utf8))
        guard let job = result["job_id"] as? String, UUID(uuidString: job) != nil,
              result["upload_verified_at"] as? String != nil else { throw SessionAuthError.serverRejected("UPLOAD_NOT_VERIFIED: Missing storage confirmation or job ID") }
        progress(1, "Video verified in storage. Processing submitted.")
        return job
    }
}
