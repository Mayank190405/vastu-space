import Foundation
import Security

public struct SessionGrantRecord: Codable {
    public let sessionId: String
    public let grantToken: String
    public let createdAt: Date
    public let expiresAt: Date
    public let deviceUUID: String
    public let projectId: String
    public let roomName: String
    
    public var isExpired: Bool {
        return Date() > expiresAt
    }
    
    public init(
        sessionId: String,
        grantToken: String,
        createdAt: Date = Date(),
        expiresAt: Date,
        deviceUUID: String,
        projectId: String,
        roomName: String
    ) {
        self.sessionId = sessionId
        self.grantToken = grantToken
        self.createdAt = createdAt
        self.expiresAt = expiresAt
        self.deviceUUID = deviceUUID
        self.projectId = projectId
        self.roomName = roomName
    }
}

public protocol SecureSessionStoreProtocol: AnyObject {
    func saveGrant(_ record: SessionGrantRecord) -> Bool
    func retrieveGrant(sessionId: String) -> SessionGrantRecord?
    func retrieveActiveGrant() -> SessionGrantRecord?
    func deleteGrant(sessionId: String) -> Bool
    func clearAllGrants() -> Bool
    func recordRedeemedNonce(_ nonce: String)
    func isNonceRedeemed(_ nonce: String) -> Bool
}

public final class SecureSessionStore: SecureSessionStoreProtocol {
    public static let shared = SecureSessionStore()
    private let serviceName = "com.vastu.capture.keychain"
    private let activeSessionKey = "com.vastu.capture.active_session_id"
    private let redeemedNoncesKey = "com.vastu.capture.redeemed_nonces"
    private let deviceUUIDKey = "com.vastu.capture.device_uuid"
    
    private let userDefaults: UserDefaults
    
    public var deviceUUID: String {
        if let stored = userDefaults.string(forKey: deviceUUIDKey) {
            return stored
        }
        let newUUID = UUID().uuidString
        userDefaults.set(newUUID, forKey: deviceUUIDKey)
        return newUUID
    }
    
    public init(userDefaults: UserDefaults = .standard) {
        self.userDefaults = userDefaults
    }
    
    // MARK: - Save Grant to Keychain
    public func saveGrant(_ record: SessionGrantRecord) -> Bool {
        do {
            let data = try JSONEncoder().encode(record)
            
            // Delete existing item if present
            _ = deleteGrant(sessionId: record.sessionId)
            
            let query: [String: Any] = [
                kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: serviceName,
                kSecAttrAccount as String: "session_\(record.sessionId)",
                kSecValueData as String: data,
                kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            ]
            
            let status = SecItemAdd(query as CFDictionary, nil)
            if status == errSecSuccess {
                userDefaults.set(record.sessionId, forKey: activeSessionKey)
                return true
            }
            return false
        } catch {
            return false
        }
    }
    
    // MARK: - Retrieve Specific Grant
    public func retrieveGrant(sessionId: String) -> SessionGrantRecord? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: "session_\(sessionId)",
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        
        if status == errSecSuccess, let data = result as? Data {
            if let record = try? JSONDecoder().decode(SessionGrantRecord.self, from: data) {
                return record
            }
        }
        return nil
    }
    
    // MARK: - Retrieve Active Grant (Survives App Restarts)
    public func retrieveActiveGrant() -> SessionGrantRecord? {
        guard let activeId = userDefaults.string(forKey: activeSessionKey) else {
            return nil
        }
        guard let record = retrieveGrant(sessionId: activeId) else {
            userDefaults.removeObject(forKey: activeSessionKey)
            return nil
        }
        return record
    }
    
    // MARK: - Delete Grant
    @discardableResult
    public func deleteGrant(sessionId: String) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: "session_\(sessionId)"
        ]
        let status = SecItemDelete(query as CFDictionary)
        if userDefaults.string(forKey: activeSessionKey) == sessionId {
            userDefaults.removeObject(forKey: activeSessionKey)
        }
        return status == errSecSuccess || status == errSecItemNotFound
    }
    
    // MARK: - Clear All Grants
    @discardableResult
    public func clearAllGrants() -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName
        ]
        let status = SecItemDelete(query as CFDictionary)
        userDefaults.removeObject(forKey: activeSessionKey)
        return status == errSecSuccess || status == errSecItemNotFound
    }
    
    // MARK: - Replay Attack Nonce Management
    public func recordRedeemedNonce(_ nonce: String) {
        var nonces = Set(userDefaults.stringArray(forKey: redeemedNoncesKey) ?? [])
        nonces.insert(nonce)
        // Bound set size to last 500 nonces to avoid unbounded growth
        if nonces.count > 500 {
            nonces.remove(nonces.first!)
        }
        userDefaults.set(Array(nonces), forKey: redeemedNoncesKey)
    }
    
    public func isNonceRedeemed(_ nonce: String) -> Bool {
        let nonces = Set(userDefaults.stringArray(forKey: redeemedNoncesKey) ?? [])
        return nonces.contains(nonce)
    }
}

// Backward compatibility alias for existing code
public typealias SecureCredentialStore = SecureSessionStore
