import Foundation

// ==========================================
// Authentication Models (Strict Email/Password & OTP - NO Apple / Google Auth)
// ==========================================

public struct LoginRequest: Codable {
    public let email: String
    public let password: String
    
    public init(email: String, password: String) {
        self.email = email
        self.password = password
    }
}

public struct OtpRequest: Codable {
    public let email: String
    public let purpose: String
    
    public init(email: String, purpose: String = "login") {
        self.email = email
        self.purpose = purpose
    }
}

public struct VerifyOtpRequest: Codable {
    public let email: String
    public let otp_code: String
    public let purpose: String
    
    public init(email: String, otpCode: String, purpose: String = "login") {
        self.email = email
        self.otp_code = otpCode
        self.purpose = purpose
    }
}

public struct OrgSignupRequest: Codable {
    public let orgName: String
    public let fullName: String
    public let email: String
    public let password: String?
    public let phone: String?
    public let legalName: String?
    public let orgType: String?
    public let industry: String?
    public let businessType: String?
    public let website: String?
    public let officialEmail: String?
    public let officialPhone: String?
    public let numberOfEmployees: String?
    public let yearEstablished: Int?
    public let description: String?
    public let identifierType: String?
    public let identifierValue: String?
    public let addressLine1: String?
    public let addressLine2: String?
    public let locality: String?
    public let city: String?
    public let state: String?
    public let pincode: String?
    public let country: String
    
    enum CodingKeys: String, CodingKey {
        case orgName = "org_name"
        case fullName = "full_name"
        case email
        case password
        case phone
        case legalName = "legal_name"
        case orgType = "organization_type"
        case industry
        case businessType = "business_type"
        case website
        case officialEmail = "official_email"
        case officialPhone = "official_phone"
        case numberOfEmployees = "number_of_employees"
        case yearEstablished = "year_established"
        case description
        case identifierType = "identifier_type"
        case identifierValue = "identifier_value"
        case addressLine1 = "address_line_1"
        case addressLine2 = "address_line_2"
        case locality
        case city
        case state
        case pincode
        case country
    }
    
    public init(
        orgName: String,
        fullName: String,
        email: String,
        password: String? = nil,
        phone: String? = nil,
        legalName: String? = nil,
        orgType: String? = "Enterprise",
        industry: String? = "Construction & Engineering",
        businessType: String? = "Enterprise",
        website: String? = nil,
        officialEmail: String? = nil,
        officialPhone: String? = nil,
        numberOfEmployees: String? = "11–50 Employees",
        yearEstablished: Int? = 2024,
        description: String? = nil,
        identifierType: String? = "PAN (10-char)",
        identifierValue: String? = nil,
        addressLine1: String? = nil,
        addressLine2: String? = nil,
        locality: String? = nil,
        city: String? = nil,
        state: String? = nil,
        pincode: String? = nil,
        country: String = "India"
    ) {
        self.orgName = orgName
        self.fullName = fullName
        self.email = email
        self.password = password
        self.phone = phone
        self.legalName = legalName
        self.orgType = orgType
        self.industry = industry
        self.businessType = businessType
        self.website = website
        self.officialEmail = officialEmail
        self.officialPhone = officialPhone
        self.numberOfEmployees = numberOfEmployees
        self.yearEstablished = yearEstablished
        self.description = description
        self.identifierType = identifierType
        self.identifierValue = identifierValue
        self.addressLine1 = addressLine1
        self.addressLine2 = addressLine2
        self.locality = locality
        self.city = city
        self.state = state
        self.pincode = pincode
        self.country = country
    }
}

public struct EmployeeJoinRequest: Codable {
    public let org_code: String
    public let full_name: String
    public let email: String
    public let password: String
    public let requested_role: String
    public let phone: String?
    
    public init(orgCode: String, fullName: String, email: String, password: String, requestedRole: String = "Site Manager", phone: String? = nil) {
        self.org_code = orgCode
        self.full_name = fullName
        self.email = email
        self.password = password
        self.requested_role = requestedRole
        self.phone = phone
    }
}

public struct UserDTO: Codable, Identifiable, Hashable, Equatable {
    public let id: String
    public let email: String
    public let full_name: String?
    public let role: String?
    public let phone: String?
    
    public init(id: String, email: String, full_name: String? = nil, role: String? = nil, phone: String? = nil) {
        self.id = id
        self.email = email
        self.full_name = full_name
        self.role = role
        self.phone = phone
    }
}

public struct OrganizationDTO: Codable, Identifiable, Hashable, Equatable {
    public let id: String
    public let name: String
    public let org_code: String?
    public let business_type: String?
    public let country: String?
}

public struct UserProfileResponse: Codable {
    public let user: UserDTO?
    public let active_org: OrganizationDTO?
    public let active_role: String?
}

public struct AuthResponse: Codable {
    public let token: String
    public let refresh_token: String?
    public let user: UserDTO?
    public let organization: OrganizationDTO?
}

public struct ApiResponse<T: Codable>: Codable {
    public let success: Bool?
    public let message: String?
    public let data: T?
    public let error: String?
}

// ==========================================
// Project Models & Multi-Floor Entities
// ==========================================

public struct FloorDTO: Codable, Identifiable, Hashable {
    public let id: String
    public let project_id: String
    public let name: String
    public let floor_number: Int
    public let floor_type: String
    public let area_value: Double?
    public let area_unit: String?
    public let height_value: Double?
    public let height_unit: String?
}

public struct CreateFloorDTO: Codable {
    public let name: String
    public let floor_number: Int
    public let floor_type: String
    public let area_value: Double
    public let area_unit: String
    public let height_value: Double
    public let height_unit: String
    public let sequence: Int
}

public struct ProjectDTO: Codable, Identifiable, Hashable {
    public let id: String
    public let name: String
    public let description: String?
    public let status: String?
    public let created_at: String?
    public let project_type: String?
    public let contact_name: String?
    public let contact_phone: String?
    public let contact_email: String?
    public let total_floors_count: Int?
    public let total_area_sqft: Double?
    public let cover_image_url: String?
    public let floors: [FloorDTO]?

    public var projectType: String? { project_type }
    public var createdAt: String { created_at ?? "" }
    public var location: String? { contact_name }
}

public struct CreateProjectRequest: Codable {
    public let name: String
    public let description: String?
    public let project_type: String?
    public let contact_name: String?
    public let contact_phone: String?
    public let contact_email: String?
    public let address: CreateAddressDTO?
    public let floors: [CreateFloorDTO]?
    
    public init(name: String, description: String? = nil, projectType: String = "Building", contactName: String = "Lead", contactPhone: String = "+910000000000", contactEmail: String = "contact@project.internal", address: CreateAddressDTO? = nil, floors: [CreateFloorDTO]? = nil) {
        self.name = name
        self.description = description
        self.project_type = projectType
        self.contact_name = contactName
        self.contact_phone = contactPhone
        self.contact_email = contactEmail
        self.address = address
        self.floors = floors
    }
}

public struct CreateAddressDTO: Codable {
    public let address_line_1: String
    public let city: String
    public let state: String
    public let pincode: String
    public let country: String
    
    public init(addressLine1: String, city: String, state: String, pincode: String, country: String = "India") {
        self.address_line_1 = addressLine1
        self.city = city
        self.state = state
        self.pincode = pincode
        self.country = country
    }
}

// ==========================================
// Capture & Sensor Models
// ==========================================

public struct CameraIntrinsics: Codable {
    public let fx: Double
    public let fy: Double
    public let cx: Double
    public let cy: Double
    public let width: Int
    public let height: Int
    public let fps: Double
}

public struct IMUDataPoint: Codable {
    public let timestamp_ns: Int64
    public let accel_x: Double
    public let accel_y: Double
    public let accel_z: Double
    public let gyro_x: Double
    public let gyro_y: Double
    public let gyro_z: Double
}

public struct CreateCaptureRequest: Codable {
    public let project_id: String
    public let name: String
    public let capture_type: String
    public let device_info: String
    public let metadata: [String: String]?
    
    public init(projectId: String, name: String, captureType: String = "video_rgb_imu", deviceInfo: String, metadata: [String: String]? = nil) {
        self.project_id = projectId
        self.name = name
        self.capture_type = captureType
        self.device_info = deviceInfo
        self.metadata = metadata
    }
}

public struct CaptureDTO: Codable, Identifiable {
    public let id: String
    public let project_id: String
    public let name: String
    public let status: String
    public let created_at: String?
}

// ==========================================
// Resumable Chunked Upload Models
// ==========================================

public struct InitUploadRequest: Codable {
    public let capture_id: String
    public let file_name: String
    public let file_type: String
    public let file_size_bytes: Int64
    public let total_size_bytes: Int64
    public let chunk_size_bytes: Int64
    public let total_chunks: Int
    public let checksum_sha256: String
    public let sha256_checksum: String
    
    public init(captureId: String, fileName: String, fileType: String = "video", fileSizeBytes: Int64, chunkSizeBytes: Int64 = 5242880, totalChunks: Int, checksumSha256: String) {
        self.capture_id = captureId
        self.file_name = fileName
        self.file_type = fileType
        self.file_size_bytes = fileSizeBytes
        self.total_size_bytes = fileSizeBytes
        self.chunk_size_bytes = chunkSizeBytes
        self.total_chunks = totalChunks
        self.checksum_sha256 = checksumSha256
        self.sha256_checksum = checksumSha256
    }
}

public struct UploadSessionDTO: Codable, Identifiable {
    public let id: String
    public let capture_id: String?
    public let file_name: String
    public let file_size_bytes: Int64?
    public let total_size_bytes: Int64?
    public let chunk_size_bytes: Int64
    public let total_chunks: Int
    public let uploaded_chunks: Int
    public let status: String
}

public struct CompleteUploadRequest: Codable {
    public let final_checksum_sha256: String
    public let sha256_checksum: String?
    
    public init(finalChecksumSha256: String) {
        self.final_checksum_sha256 = finalChecksumSha256
        self.sha256_checksum = finalChecksumSha256
    }
}

// ==========================================
// Project Team & Member Models
// ==========================================

public struct ProjectMemberDTO: Codable, Identifiable, Hashable {
    public let id: String
    public let project_id: String
    public let user_id: String
    public let project_role: String
    public let user: UserDTO?
}

public struct AddProjectMemberRequest: Codable {
    public let user_id: String
    public let project_role: String
    
    public init(userId: String, projectRole: String = "Member") {
        self.user_id = userId
        self.project_role = projectRole
    }
}

public struct OrgMemberDTO: Codable, Identifiable, Hashable {
    public let id: String
    public let organization_id: String
    public let user_id: String
    public let role: String
    public let user: UserDTO?
}

// ==========================================
// POI & Spatial Navigation Models
// ==========================================

public struct POIDTO: Codable, Identifiable {
    public let id: String
    public let project_id: String
    public let name: String
    public let category: String
    public let x: Double
    public let y: Double
    public let z: Double
    public let color: String?
    public let description: String?
    public let created_at: String?
}

public struct CreatePOIRequest: Codable {
    public let name: String
    public let category: String
    public let x: Double
    public let y: Double
    public let z: Double
    public let color: String?
    public let description: String?
    
    public init(name: String, category: String = "Custom", x: Double, y: Double, z: Double, color: String? = nil, description: String? = nil) {
        self.name = name
        self.category = category
        self.x = x
        self.y = y
        self.z = z
        self.color = color
        self.description = description
    }
}

public struct JobDTO: Codable, Identifiable {
    public let id: String
    public let capture_id: String?
    public let floor_id: String?
    public let status: String
    public let progress_percent: Double
    public let stage: String?
    public let error_message: String?
    public let created_at: String?
}

