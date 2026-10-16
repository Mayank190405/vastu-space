package com.vastu.spatial.data.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

// ==========================================
// Authentication DTOs (Strict Email/Password & OTP - NO Apple / Google Auth)
// ==========================================

@JsonClass(generateAdapter = true)
data class LoginRequest(
    @Json(name = "email") val email: String,
    @Json(name = "password") val password: String
)

@JsonClass(generateAdapter = true)
data class OrgSignupRequest(
    @Json(name = "org_name") val orgName: String,
    @Json(name = "full_name") val fullName: String,
    @Json(name = "email") val email: String,
    @Json(name = "password") val password: String? = null,
    @Json(name = "phone") val phone: String? = null,
    @Json(name = "legal_name") val legalName: String? = null,
    @Json(name = "organization_type") val organizationType: String? = "Enterprise",
    @Json(name = "industry") val industry: String? = "Construction & Engineering",
    @Json(name = "business_type") val businessType: String? = "Enterprise",
    @Json(name = "website") val website: String? = null,
    @Json(name = "official_email") val officialEmail: String? = null,
    @Json(name = "official_phone") val officialPhone: String? = null,
    @Json(name = "number_of_employees") val numberOfEmployees: String? = "11–50 Employees",
    @Json(name = "year_established") val yearEstablished: Int? = 2024,
    @Json(name = "description") val description: String? = null,
    @Json(name = "identifier_type") val identifierType: String? = "PAN (10-char)",
    @Json(name = "identifier_value") val identifierValue: String? = null,
    @Json(name = "address_line_1") val addressLine1: String? = null,
    @Json(name = "address_line_2") val addressLine2: String? = null,
    @Json(name = "locality") val locality: String? = null,
    @Json(name = "city") val city: String? = null,
    @Json(name = "state") val state: String? = null,
    @Json(name = "pincode") val pincode: String? = null,
    @Json(name = "country") val country: String = "India"
)

@JsonClass(generateAdapter = true)
data class EmployeeJoinRequest(
    @Json(name = "org_code") val orgCode: String,
    @Json(name = "full_name") val fullName: String,
    @Json(name = "email") val email: String,
    @Json(name = "password") val password: String,
    @Json(name = "requested_role") val requestedRole: String = "Site Manager",
    @Json(name = "phone") val phone: String? = null
)

@JsonClass(generateAdapter = true)
data class OtpRequest(
    @Json(name = "email") val email: String,
    @Json(name = "purpose") val purpose: String = "login"
)

@JsonClass(generateAdapter = true)
data class VerifyOtpRequest(
    @Json(name = "email") val email: String,
    @Json(name = "otp_code") val otpCode: String,
    @Json(name = "purpose") val purpose: String = "login"
)

@JsonClass(generateAdapter = true)
data class AuthResponse(
    @Json(name = "token") val token: String,
    @Json(name = "refresh_token") val refreshToken: String? = null,
    @Json(name = "user") val user: UserDto,
    @Json(name = "organization") val organization: OrganizationDto? = null
)

@JsonClass(generateAdapter = true)
data class UserDto(
    @Json(name = "id") val id: String,
    @Json(name = "email") val email: String,
    @Json(name = "full_name") val fullName: String? = null,
    @Json(name = "role") val role: String? = "viewer",
    @Json(name = "phone") val phone: String? = null
)

@JsonClass(generateAdapter = true)
data class OrganizationDto(
    @Json(name = "id") val id: String,
    @Json(name = "name") val name: String,
    @Json(name = "org_code") val orgCode: String? = null,
    @Json(name = "business_type") val businessType: String? = null,
    @Json(name = "country") val country: String? = "India"
)

@JsonClass(generateAdapter = true)
data class UserProfileResponse(
    @Json(name = "user") val user: UserDto? = null,
    @Json(name = "active_org") val activeOrg: OrganizationDto? = null,
    @Json(name = "active_role") val activeRole: String? = null
)

@JsonClass(generateAdapter = true)
data class ApiResponse<T>(
    @Json(name = "success") val success: Boolean = true,
    @Json(name = "message") val message: String? = null,
    @Json(name = "data") val data: T? = null,
    @Json(name = "error") val error: String? = null
)

// ==========================================
// Project & Multi-Floor DTOs
// ==========================================

@JsonClass(generateAdapter = true)
data class FloorDto(
    @Json(name = "id") val id: String,
    @Json(name = "project_id") val projectId: String,
    @Json(name = "name") val name: String,
    @Json(name = "floor_number") val floorNumber: Int,
    @Json(name = "floor_type") val floorType: String,
    @Json(name = "area_value") val areaValue: Double? = null,
    @Json(name = "area_unit") val areaUnit: String? = null,
    @Json(name = "height_value") val heightValue: Double? = null,
    @Json(name = "height_unit") val heightUnit: String? = null
)

@JsonClass(generateAdapter = true)
data class CreateFloorDto(
    @Json(name = "name") val name: String,
    @Json(name = "floor_number") val floorNumber: Int,
    @Json(name = "floor_type") val floorType: String = "Standard",
    @Json(name = "area_value") val areaValue: Double,
    @Json(name = "area_unit") val areaUnit: String = "SQFT",
    @Json(name = "height_value") val heightValue: Double = 10.5,
    @Json(name = "height_unit") val heightUnit: String = "FT",
    @Json(name = "sequence") val sequence: Int = 0
)

@JsonClass(generateAdapter = true)
data class CreateAddressDto(
    @Json(name = "address_line_1") val addressLine1: String,
    @Json(name = "city") val city: String,
    @Json(name = "state") val state: String,
    @Json(name = "pincode") val pincode: String,
    @Json(name = "country") val country: String = "India"
)

@JsonClass(generateAdapter = true)
data class CreateProjectRequest(
    @Json(name = "name") val name: String,
    @Json(name = "description") val description: String? = null,
    @Json(name = "project_type") val projectType: String = "Building",
    @Json(name = "contact_name") val contactName: String = "Lead",
    @Json(name = "contact_phone") val contactPhone: String = "+910000000000",
    @Json(name = "contact_email") val contactEmail: String = "contact@project.internal",
    @Json(name = "address") val address: CreateAddressDto? = null,
    @Json(name = "floors") val floors: List<CreateFloorDto>? = null
)

@JsonClass(generateAdapter = true)
data class ProjectDto(
    @Json(name = "id") val id: String,
    @Json(name = "name") val name: String,
    @Json(name = "description") val description: String? = null,
    @Json(name = "status") val status: String? = "active",
    @Json(name = "created_at") val createdAt: String? = null,
    @Json(name = "project_type") val projectType: String? = null,
    @Json(name = "contact_name") val contactName: String? = null,
    @Json(name = "contact_phone") val contactPhone: String? = null,
    @Json(name = "contact_email") val contactEmail: String? = null,
    @Json(name = "total_floors_count") val totalFloorsCount: Int? = null,
    @Json(name = "total_area_sqft") val totalAreaSqft: Double? = null,
    @Json(name = "cover_image_url") val coverImageUrl: String? = null,
    @Json(name = "floors") val floors: List<FloorDto>? = null
)

// ==========================================
// Capture & Sensor DTOs
// ==========================================

@JsonClass(generateAdapter = true)
data class CameraIntrinsics(
    @Json(name = "fx") val fx: Double,
    @Json(name = "fy") val fy: Double,
    @Json(name = "cx") val cx: Double,
    @Json(name = "cy") val cy: Double,
    @Json(name = "width") val width: Int,
    @Json(name = "height") val height: Int,
    @Json(name = "fps") val fps: Double
)

@JsonClass(generateAdapter = true)
data class ImuDataPoint(
    @Json(name = "timestamp_ns") val timestampNs: Long,
    @Json(name = "accel_x") val accelX: Float,
    @Json(name = "accel_y") val accelY: Float,
    @Json(name = "accel_z") val accelZ: Float,
    @Json(name = "gyro_x") val gyroX: Float,
    @Json(name = "gyro_y") val gyroY: Float,
    @Json(name = "gyro_z") val gyroZ: Float
)

@JsonClass(generateAdapter = true)
data class CaptureMetadata(
    @Json(name = "device_model") val deviceModel: String,
    @Json(name = "os_version") val osVersion: String,
    @Json(name = "camera_intrinsics") val cameraIntrinsics: CameraIntrinsics,
    @Json(name = "imu_rate_hz") val imuRateHz: Int = 100,
    @Json(name = "total_frames") val totalFrames: Long,
    @Json(name = "duration_seconds") val durationSeconds: Double
)

@JsonClass(generateAdapter = true)
data class CreateCaptureRequest(
    @Json(name = "project_id") val projectId: String,
    @Json(name = "name") val name: String,
    @Json(name = "capture_type") val captureType: String = "video_rgb_imu",
    @Json(name = "device_info") val deviceInfo: String,
    @Json(name = "metadata") val metadata: Map<String, Any>? = null
)

@JsonClass(generateAdapter = true)
data class CaptureDto(
    @Json(name = "id") val id: String,
    @Json(name = "project_id") val projectId: String,
    @Json(name = "name") val name: String,
    @Json(name = "status") val status: String,
    @Json(name = "created_at") val createdAt: String? = null
)

// ==========================================
// Resumable Chunked Upload DTOs
// ==========================================

@JsonClass(generateAdapter = true)
data class InitUploadRequest(
    @Json(name = "capture_id") val captureId: String,
    @Json(name = "file_name") val fileName: String,
    @Json(name = "file_size_bytes") val fileSizeBytes: Long,
    @Json(name = "chunk_size_bytes") val chunkSizeBytes: Long = 5242880, // 5MB chunks
    @Json(name = "total_chunks") val totalChunks: Int,
    @Json(name = "checksum_sha256") val checksumSha256: String
)

@JsonClass(generateAdapter = true)
data class UploadSessionDto(
    @Json(name = "id") val id: String,
    @Json(name = "capture_id") val captureId: String,
    @Json(name = "file_name") val fileName: String,
    @Json(name = "file_size_bytes") val fileSizeBytes: Long,
    @Json(name = "chunk_size_bytes") val chunkSizeBytes: Long,
    @Json(name = "total_chunks") val totalChunks: Int,
    @Json(name = "uploaded_chunks") val uploadedChunks: Int,
    @Json(name = "status") val status: String
)

@JsonClass(generateAdapter = true)
data class CompleteUploadRequest(
    @Json(name = "final_checksum_sha256") val finalChecksumSha256: String
)

// ==========================================
// Team & Project Member DTOs
// ==========================================

@JsonClass(generateAdapter = true)
data class ProjectMemberDto(
    @Json(name = "id") val id: String,
    @Json(name = "project_id") val projectId: String,
    @Json(name = "user_id") val userId: String,
    @Json(name = "project_role") val projectRole: String,
    @Json(name = "user") val user: UserDto? = null
)

@JsonClass(generateAdapter = true)
data class AddProjectMemberRequest(
    @Json(name = "user_id") val userId: String,
    @Json(name = "project_role") val projectRole: String = "Member"
)

@JsonClass(generateAdapter = true)
data class OrgMemberDto(
    @Json(name = "id") val id: String,
    @Json(name = "organization_id") val organizationId: String,
    @Json(name = "user_id") val userId: String,
    @Json(name = "role") val role: String,
    @Json(name = "user") val user: UserDto? = null
)

// ==========================================
// POI & Spatial Navigation Models
// ==========================================

@JsonClass(generateAdapter = true)
data class PoiDto(
    @Json(name = "id") val id: String,
    @Json(name = "project_id") val projectId: String,
    @Json(name = "name") val name: String,
    @Json(name = "category") val category: String,
    @Json(name = "x") val x: Double,
    @Json(name = "y") val y: Double,
    @Json(name = "z") val z: Double,
    @Json(name = "color") val color: String? = null,
    @Json(name = "description") val description: String? = null,
    @Json(name = "created_at") val createdAt: String? = null
)

@JsonClass(generateAdapter = true)
data class CreatePoiDto(
    @Json(name = "name") val name: String,
    @Json(name = "category") val category: String = "Custom",
    @Json(name = "x") val x: Double,
    @Json(name = "y") val y: Double,
    @Json(name = "z") val z: Double,
    @Json(name = "color") val color: String? = null,
    @Json(name = "description") val description: String? = null
)

@JsonClass(generateAdapter = true)
data class JobDto(
    @Json(name = "id") val id: String,
    @Json(name = "capture_id") val captureId: String? = null,
    @Json(name = "floor_id") val floorId: String? = null,
    @Json(name = "status") val status: String,
    @Json(name = "progress_percent") val progressPercent: Double = 0.0,
    @Json(name = "stage") val stage: String? = null,
    @Json(name = "error_message") val errorMessage: String? = null,
    @Json(name = "created_at") val createdAt: String? = null
)

