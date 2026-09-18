package com.vastu.spatial.data.api

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import com.vastu.spatial.data.model.*
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.OkHttpClient
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.ResponseBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.*
import java.io.File
import java.util.concurrent.TimeUnit

interface VastuApiService {

    // ==========================================
    // Auth Endpoints (Strict Email/Password & OTP)
    // ==========================================

    @POST("api/v1/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<ApiResponse<AuthResponse>>

    @POST("api/v1/auth/signup/organization")
    suspend fun registerOrganization(@Body request: OrgSignupRequest): Response<ApiResponse<AuthResponse>>

    @POST("api/v1/auth/join/org")
    suspend fun joinOrganization(@Body request: EmployeeJoinRequest): Response<ApiResponse<AuthResponse>>

    @POST("api/v1/auth/request-otp")
    suspend fun requestOtp(@Body request: OtpRequest): Response<ApiResponse<Map<String, String>>>

    @POST("api/v1/auth/verify-otp")
    suspend fun verifyOtp(@Body request: VerifyOtpRequest): Response<ApiResponse<AuthResponse>>

    @GET("api/v1/auth/me")
    suspend fun getMe(): Response<ApiResponse<UserProfileResponse>>

    @GET("api/v1/organizations/me")
    suspend fun getMyOrg(): Response<ApiResponse<OrganizationDto>>

    // ==========================================
    // Projects & Floors Endpoints
    // ==========================================

    @GET("api/v1/projects")
    suspend fun getProjects(): Response<ApiResponse<List<ProjectDto>>>

    @POST("api/v1/projects/create-full")
    suspend fun createProject(@Body request: CreateProjectRequest): Response<ApiResponse<ProjectDto>>

    @GET("api/v1/projects/{projectId}/floors")
    suspend fun getFloors(@Path("projectId") projectId: String): Response<ApiResponse<List<FloorDto>>>

    @POST("api/v1/projects/{projectId}/floors")
    suspend fun createFloor(@Path("projectId") projectId: String, @Body request: CreateFloorDto): Response<ApiResponse<FloorDto>>

    @GET("api/v1/projects/{projectId}/members")
    suspend fun getProjectMembers(@Path("projectId") projectId: String): Response<ApiResponse<List<ProjectMemberDto>>>

    @POST("api/v1/projects/{projectId}/members")
    suspend fun addProjectMember(@Path("projectId") projectId: String, @Body request: AddProjectMemberRequest): Response<ApiResponse<ProjectMemberDto>>

    @DELETE("api/v1/projects/{projectId}/members/{userId}")
    suspend fun removeProjectMember(@Path("projectId") projectId: String, @Path("userId") userId: String): Response<ApiResponse<Unit>>

    @GET("api/v1/organizations/me/members")
    suspend fun getOrganizationMembers(): Response<ApiResponse<List<OrgMemberDto>>>

    // ==========================================
    // Captures Endpoints
    // ==========================================

    @GET("api/v1/captures")
    suspend fun getCaptures(@Query("project_id") projectId: String): Response<ApiResponse<List<CaptureDto>>>

    @POST("api/v1/captures")
    suspend fun createCapture(@Body request: CreateCaptureRequest): Response<ApiResponse<CaptureDto>>

    @GET("api/v1/captures/{id}")
    suspend fun getCaptureById(@Path("id") captureId: String): Response<ApiResponse<CaptureDto>>

    // ==========================================
    // Resumable Chunked Uploads Endpoints
    // ==========================================

    @POST("api/v1/uploads/init")
    suspend fun initUploadSession(@Body request: InitUploadRequest): Response<ApiResponse<UploadSessionDto>>

    @PUT("api/v1/uploads/{sessionId}/chunk/{chunkIndex}")
    suspend fun uploadChunk(
        @Path("sessionId") sessionId: String,
        @Path("chunkIndex") chunkIndex: Int,
        @Header("Content-Range") contentRange: String,
        @Header("X-Chunk-SHA256") chunkChecksum: String,
        @Body chunkBody: RequestBody
    ): Response<ApiResponse<Map<String, Any>>>

    @POST("api/v1/uploads/{sessionId}/complete")
    suspend fun completeUpload(
        @Path("sessionId") sessionId: String,
        @Body request: CompleteUploadRequest
    ): Response<ApiResponse<Map<String, Any>>>

    @GET("api/v1/uploads/{sessionId}/status")
    suspend fun getUploadStatus(@Path("sessionId") sessionId: String): Response<ApiResponse<UploadSessionDto>>
}

// Session Token Storage with Hardware-Backed Encryption
class AuthTokenManager(context: Context) {
    private val masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
    private val prefs = EncryptedSharedPreferences.create(
        "vastu_secure_prefs",
        masterKeyAlias,
        context,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    fun saveToken(token: String) {
        prefs.edit().putString("jwt_token", token).apply()
    }

    fun getToken(): String? {
        return prefs.getString("jwt_token", null)
    }

    fun saveUser(user: UserDto) {
        val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
        val json = moshi.adapter(UserDto::class.java).toJson(user)
        prefs.edit().putString("current_user", json).apply()
    }

    fun getUser(): UserDto? {
        val json = prefs.getString("current_user", null) ?: return null
        val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
        return runCatching { moshi.adapter(UserDto::class.java).fromJson(json) }.getOrNull()
    }

    fun clear() {
        prefs.edit().clear().apply()
    }
}

// Singleton API Provider
object ApiClient {
    private var tokenManager: AuthTokenManager? = null
    
    // Auto-detect emulator (10.0.2.2) vs physical phone (Mac Wi-Fi IP 192.168.74.216)
    val defaultBaseUrl: String
        get() = if (isEmulator()) "http://10.0.2.2:8080/" else "http://192.168.74.216:8080/"

    var baseUrl: String = defaultBaseUrl

    fun isEmulator(): Boolean {
        return (android.os.Build.BRAND.startsWith("generic") && android.os.Build.DEVICE.startsWith("generic"))
                || android.os.Build.FINGERPRINT.startsWith("generic")
                || android.os.Build.FINGERPRINT.startsWith("unknown")
                || android.os.Build.HARDWARE.contains("goldfish")
                || android.os.Build.HARDWARE.contains("ranchu")
                || android.os.Build.MODEL.contains("google_sdk")
                || android.os.Build.MODEL.contains("Emulator")
                || android.os.Build.MODEL.contains("Android SDK built for x86")
                || android.os.Build.MANUFACTURER.contains("Genymotion")
                || android.os.Build.PRODUCT.contains("sdk")
                || android.os.Build.PRODUCT.contains("emulator")
    }

    fun init(context: Context) {
        tokenManager = AuthTokenManager(context)
    }

    val service: VastuApiService by lazy {
        val authInterceptor = Interceptor { chain ->
            val requestBuilder = chain.request().newBuilder()
            tokenManager?.getToken()?.let { token ->
                if (token.isNotBlank()) {
                    requestBuilder.addHeader("Authorization", "Bearer $token")
                }
            }
            requestBuilder.addHeader("Accept", "application/json")
            chain.proceed(requestBuilder.build())
        }

        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        val okHttpClient = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(loggingInterceptor)
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .build()

        val moshi = Moshi.Builder()
            .add(KotlinJsonAdapterFactory())
            .build()

        Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(VastuApiService::class.java)
    }

    fun getTokenManager(): AuthTokenManager? = tokenManager
}
