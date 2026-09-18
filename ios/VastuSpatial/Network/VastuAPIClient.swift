import Foundation
import Security

// Secure Keychain Helper for JWT Token Storage
public class KeychainHelper {
    public static let shared = KeychainHelper()
    private let tokenKey = "com.vastu.spatial.jwt_token"
    
    public func saveToken(_ token: String) {
        guard let data = token.data(using: .utf8) else { return }
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: tokenKey,
            kSecValueData as String: data
        ]
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }
    
    public func getToken() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: tokenKey,
            kSecReturnData as String: kCFBooleanTrue!,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var dataTypeRef: AnyObject?
        let status: OSStatus = SecItemCopyMatching(query as CFDictionary, &dataTypeRef)
        if status == noErr, let data = dataTypeRef as? Data {
            return String(data: data, encoding: .utf8)
        }
        return nil
    }
    
    public func clearToken() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: tokenKey
        ]
        SecItemDelete(query as CFDictionary)
    }
}

// API Client for VĀSTU Control Plane
public class VastuAPIClient: ObservableObject {
    public static let shared = VastuAPIClient()
    
    // Default baseURL: localhost for simulator, Mac local IP for physical iPhone device
    #if targetEnvironment(simulator)
    private static let defaultBaseURL = "http://localhost:8080"
    #else
    private static let defaultBaseURL = "http://192.168.74.216:8080"
    #endif
    
    @Published public var baseURL: String = {
        if let saved = UserDefaults.standard.string(forKey: "vastu_api_base_url"), !saved.contains("192.168.163.216") {
            return saved
        }
        return defaultBaseURL
    }() {
        didSet {
            UserDefaults.standard.set(baseURL, forKey: "vastu_api_base_url")
        }
    }
    private let session = URLSession.shared
    
    @Published public var currentUser: UserDTO?
    @Published public var currentOrg: OrganizationDTO?
    @Published public var currentRole: String? = "Owner"
    @Published public var isAuthenticated: Bool = false
    
    public init() {
        self.isAuthenticated = KeychainHelper.shared.getToken() != nil
        if self.isAuthenticated {
            Task {
                try? await self.getMe()
            }
        }
    }
    
    // ==========================================
    // Auth & Profile Endpoints
    // ==========================================
    
    public func login(request: LoginRequest) async throws -> AuthResponse {
        let response: ApiResponse<AuthResponse> = try await post(path: "/api/v1/auth/login", body: request, requiresAuth: false)
        guard let data = response.data else {
            throw NSError(domain: "VastuAPI", code: 401, userInfo: [NSLocalizedDescriptionKey: response.error ?? "Login failed"])
        }
        KeychainHelper.shared.saveToken(data.token)
        await MainActor.run {
            self.currentUser = data.user
            self.isAuthenticated = true
        }
        _ = try? await self.getMe()
        return data
    }
    
    public func requestOtp(request: OtpRequest) async throws -> String {
        let response: ApiResponse<[String: String]> = try await post(path: "/api/v1/auth/request-otp", body: request, requiresAuth: false)
        return response.message ?? "OTP sent successfully"
    }
    
    public func verifyOtp(request: VerifyOtpRequest) async throws -> AuthResponse {
        let response: ApiResponse<AuthResponse> = try await post(path: "/api/v1/auth/verify-otp", body: request, requiresAuth: false)
        guard let data = response.data else {
            throw NSError(domain: "VastuAPI", code: 401, userInfo: [NSLocalizedDescriptionKey: response.error ?? "Invalid OTP"])
        }
        KeychainHelper.shared.saveToken(data.token)
        await MainActor.run {
            self.currentUser = data.user
            self.isAuthenticated = true
        }
        _ = try? await self.getMe()
        return data
    }
    
    public func getMe() async throws -> UserProfileResponse {
        let response: ApiResponse<UserProfileResponse> = try await get(path: "/api/v1/auth/me")
        if let data = response.data {
            await MainActor.run {
                if let u = data.user {
                    self.currentUser = u
                }
                if let org = data.active_org {
                    self.currentOrg = org
                }
                if let r = data.active_role {
                    self.currentRole = r
                }
            }
            return data
        }
        throw NSError(domain: "VastuAPI", code: 404, userInfo: [NSLocalizedDescriptionKey: "User profile not found"])
    }
    
    public func getMyOrg() async throws -> OrganizationDTO {
        let response: ApiResponse<OrganizationDTO> = try await get(path: "/api/v1/organizations/me")
        if let data = response.data {
            await MainActor.run {
                self.currentOrg = data
            }
            return data
        }
        throw NSError(domain: "VastuAPI", code: 404, userInfo: [NSLocalizedDescriptionKey: "Organization not found"])
    }
    
    public func signOut() {
        KeychainHelper.shared.clearToken()
        self.currentUser = nil
        self.currentOrg = nil
        self.currentRole = nil
        self.isAuthenticated = false
    }
    
    // ==========================================
    public func registerOrganization(request: OrgSignupRequest) async throws -> AuthResponse {
        let response: ApiResponse<AuthResponse> = try await post(path: "/api/v1/auth/signup/organization", body: request, requiresAuth: false)
        guard let data = response.data else {
            throw NSError(domain: "VastuAPI", code: 400, userInfo: [NSLocalizedDescriptionKey: response.error ?? "Organization registration failed"])
        }
        KeychainHelper.shared.saveToken(data.token)
        await MainActor.run {
            self.currentUser = data.user
            self.isAuthenticated = true
        }
        _ = try? await self.getMe()
        return data
    }
    
    public func joinOrganization(request: EmployeeJoinRequest) async throws -> AuthResponse {
        let response: ApiResponse<AuthResponse> = try await post(path: "/api/v1/auth/join/org", body: request, requiresAuth: false)
        guard let data = response.data else {
            throw NSError(domain: "VastuAPI", code: 400, userInfo: [NSLocalizedDescriptionKey: response.error ?? "Failed to join organization"])
        }
        KeychainHelper.shared.saveToken(data.token)
        await MainActor.run {
            self.currentUser = data.user
            self.isAuthenticated = true
        }
        _ = try? await self.getMe()
        return data
    }

    // ==========================================
    // Projects & Floors Endpoints
    // ==========================================
    
    public func getProjects() async throws -> [ProjectDTO] {
        let response: ApiResponse<[ProjectDTO]> = try await get(path: "/api/v1/projects")
        return response.data ?? []
    }
    
    public func createProject(request: CreateProjectRequest) async throws -> ProjectDTO {
        let response: ApiResponse<ProjectDTO> = try await post(path: "/api/v1/projects/create-full", body: request)
        guard let data = response.data else {
            throw NSError(domain: "VastuAPI", code: 400, userInfo: [NSLocalizedDescriptionKey: response.error ?? "Failed to create project"])
        }
        return data
    }
    
    public func getFloors(projectId: String) async throws -> [FloorDTO] {
        let response: ApiResponse<[FloorDTO]> = try await get(path: "/api/v1/projects/\(projectId)/floors")
        return response.data ?? []
    }
    
    public func getProjectMembers(projectId: String) async throws -> [ProjectMemberDTO] {
        let response: ApiResponse<[ProjectMemberDTO]> = try await get(path: "/api/v1/projects/\(projectId)/members")
        return response.data ?? []
    }
    
    public func addProjectMember(projectId: String, request: AddProjectMemberRequest) async throws -> ProjectMemberDTO {
        let response: ApiResponse<ProjectMemberDTO> = try await post(path: "/api/v1/projects/\(projectId)/members", body: request)
        guard let data = response.data else {
            throw NSError(domain: "VastuAPI", code: 400, userInfo: [NSLocalizedDescriptionKey: response.error ?? "Failed to add member"])
        }
        return data
    }
    
    public func removeProjectMember(projectId: String, userId: String) async throws {
        let _: ApiResponse<[String: String]> = try await delete(path: "/api/v1/projects/\(projectId)/members/\(userId)")
    }
    
    public func getOrganizationMembers() async throws -> [OrgMemberDTO] {
        let response: ApiResponse<[OrgMemberDTO]> = try await get(path: "/api/v1/organizations/me/members")
        return response.data ?? []
    }
    
    // ==========================================
    // Captures Endpoints
    // ==========================================
    
    public func createCapture(request: CreateCaptureRequest) async throws -> CaptureDTO {
        let response: ApiResponse<CaptureDTO> = try await post(path: "/api/v1/captures", body: request)
        guard let data = response.data else {
            throw NSError(domain: "VastuAPI", code: 400, userInfo: [NSLocalizedDescriptionKey: response.error ?? "Failed to create capture"])
        }
        return data
    }
    
    // ==========================================
    // Resumable Chunked Upload Endpoints
    // ==========================================
    
    public func initUploadSession(request: InitUploadRequest) async throws -> UploadSessionDTO {
        let response: ApiResponse<UploadSessionDTO> = try await post(path: "/api/v1/uploads/init", body: request)
        guard let data = response.data else {
            throw NSError(domain: "VastuAPI", code: 400, userInfo: [NSLocalizedDescriptionKey: response.error ?? "Failed to init upload"])
        }
        return data
    }
    
    public func uploadChunk(sessionId: String, chunkIndex: Int, contentRange: String, chunkChecksum: String, data: Data) async throws {
        guard let url = URL(string: "\(baseURL)/api/v1/uploads/\(sessionId)/chunk/\(chunkIndex)") else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        request.setValue(contentRange, forHTTPHeaderField: "Content-Range")
        request.setValue(chunkChecksum, forHTTPHeaderField: "X-Chunk-SHA256")
        if let token = KeychainHelper.shared.getToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        let (respData, response) = try await session.upload(for: request, from: data)
        guard let httpResp = response as? HTTPURLResponse, (200...299).contains(httpResp.statusCode) else {
            let errMsg = String(data: respData, encoding: .utf8) ?? "Upload chunk failed"
            throw NSError(domain: "VastuAPI", code: 500, userInfo: [NSLocalizedDescriptionKey: errMsg])
        }
    }
    
    public func completeUpload(sessionId: String, request: CompleteUploadRequest) async throws {
        let _: ApiResponse<[String: String]> = try await post(path: "/api/v1/uploads/\(sessionId)/complete", body: request)
    }
    
    // ==========================================
    // Private Network Helpers
    // ==========================================
    
    private func get<T: Codable>(path: String, requiresAuth: Bool = true) async throws -> T {
        guard let url = URL(string: "\(baseURL)\(path)") else { throw URLError(.badURL) }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if requiresAuth, let token = KeychainHelper.shared.getToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: request)
        guard let httpResp = response as? HTTPURLResponse, (200...299).contains(httpResp.statusCode) else {
            let errMsg = String(data: data, encoding: .utf8) ?? "HTTP Error"
            throw NSError(domain: "VastuAPI", code: (response as? HTTPURLResponse)?.statusCode ?? 500, userInfo: [NSLocalizedDescriptionKey: errMsg])
        }
        return try JSONDecoder().decode(T.self, from: data)
    }
    
    private func post<B: Codable, T: Codable>(path: String, body: B, requiresAuth: Bool = true) async throws -> T {
        guard let url = URL(string: "\(baseURL)\(path)") else { throw URLError(.badURL) }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if requiresAuth, let token = KeychainHelper.shared.getToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        request.httpBody = try JSONEncoder().encode(body)
        
        let (data, response) = try await session.data(for: request)
        guard let httpResp = response as? HTTPURLResponse, (200...299).contains(httpResp.statusCode) else {
            let errMsg = String(data: data, encoding: .utf8) ?? "HTTP Error"
            throw NSError(domain: "VastuAPI", code: (response as? HTTPURLResponse)?.statusCode ?? 500, userInfo: [NSLocalizedDescriptionKey: errMsg])
        }
        return try JSONDecoder().decode(T.self, from: data)
    }
    
    private func delete<T: Codable>(path: String, requiresAuth: Bool = true) async throws -> T {
        guard let url = URL(string: "\(baseURL)\(path)") else { throw URLError(.badURL) }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if requiresAuth, let token = KeychainHelper.shared.getToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: request)
        guard let httpResp = response as? HTTPURLResponse, (200...299).contains(httpResp.statusCode) else {
            let errMsg = String(data: data, encoding: .utf8) ?? "HTTP Error"
            throw NSError(domain: "VastuAPI", code: (response as? HTTPURLResponse)?.statusCode ?? 500, userInfo: [NSLocalizedDescriptionKey: errMsg])
        }
        return (try? JSONDecoder().decode(T.self, from: data)) ?? (ApiResponse<[String: String]>(success: true, message: "Deleted", data: nil, error: nil) as! T)
    }
}
