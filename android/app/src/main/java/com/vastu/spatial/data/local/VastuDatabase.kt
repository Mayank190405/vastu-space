package com.vastu.spatial.data.local

import android.content.Context
import androidx.room.*
import kotlinx.coroutines.flow.Flow

// ==========================================
// Room Entities
// ==========================================

@Entity(tableName = "projects")
data class ProjectEntity(
    @PrimaryKey val id: String,
    val name: String,
    val description: String?,
    val status: String,
    val createdAt: Long = System.currentTimeMillis()
)

@Entity(
    tableName = "captures",
    foreignKeys = [
        ForeignKey(
            entity = ProjectEntity::class,
            parentColumns = ["id"],
            childColumns = ["projectId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index(value = ["projectId"])]
)
data class CaptureEntity(
    @PrimaryKey val id: String,
    val projectId: String,
    val name: String,
    val sessionDir: String,
    val videoFilePath: String,
    val imuFilePath: String,
    val metadataFilePath: String,
    val fileSizeBytes: Long = 0L,
    val checksumSha256: String = "",
    val status: String, // "pending_upload", "uploading", "uploaded", "failed", "paused"
    val isReadyForUpload: Boolean = true,
    val totalChunks: Int = 0,
    val uploadedChunks: Int = 0,
    val uploadSessionId: String? = null,
    val retryCount: Int = 0,
    val lastError: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)

@Entity(
    tableName = "upload_chunks",
    foreignKeys = [
        ForeignKey(
            entity = CaptureEntity::class,
            parentColumns = ["id"],
            childColumns = ["captureId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index(value = ["captureId"])]
)
data class UploadChunkEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val captureId: String,
    val chunkIndex: Int,
    val startByte: Long,
    val endByte: Long,
    val sizeBytes: Long,
    val checksumSha256: String,
    val isUploaded: Boolean = false,
    val retryCount: Int = 0,
    val lastError: String? = null
)

// ==========================================
// DAOs
// ==========================================

@Dao
interface ProjectDao {
    @Query("SELECT * FROM projects ORDER BY createdAt DESC")
    fun getAllProjectsFlow(): Flow<List<ProjectEntity>>

    @Query("SELECT * FROM projects ORDER BY createdAt DESC")
    suspend fun getAllProjects(): List<ProjectEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProjects(projects: List<ProjectEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProject(project: ProjectEntity)

    @Query("DELETE FROM projects WHERE id = :id")
    suspend fun deleteProject(id: String)
}

@Dao
interface CaptureDao {
    @Query("SELECT * FROM captures WHERE projectId = :projectId ORDER BY createdAt DESC")
    fun getCapturesForProject(projectId: String): Flow<List<CaptureEntity>>

    @Query("SELECT * FROM captures WHERE status IN ('pending_upload', 'uploading', 'failed') ORDER BY createdAt ASC")
    suspend fun getPendingOrInterruptedCaptures(): List<CaptureEntity>

    @Query("SELECT * FROM captures WHERE status = 'uploaded' ORDER BY createdAt ASC")
    suspend fun getUploadedCaptures(): List<CaptureEntity>

    @Query("SELECT * FROM captures WHERE id = :id")
    suspend fun getCaptureById(id: String): CaptureEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertCapture(capture: CaptureEntity)

    @Update
    suspend fun updateCapture(capture: CaptureEntity)

    @Query("UPDATE captures SET status = :status, uploadedChunks = :uploadedChunks, updatedAt = :timestamp WHERE id = :id")
    suspend fun updateProgress(id: String, status: String, uploadedChunks: Int, timestamp: Long = System.currentTimeMillis())

    @Query("UPDATE captures SET status = :status, lastError = :error, retryCount = retryCount + 1, updatedAt = :timestamp WHERE id = :id")
    suspend fun recordError(id: String, status: String, error: String, timestamp: Long = System.currentTimeMillis())

    @Query("DELETE FROM captures WHERE id = :id")
    suspend fun deleteCapture(id: String)
}

@Dao
interface UploadChunkDao {
    @Query("SELECT * FROM upload_chunks WHERE captureId = :captureId ORDER BY chunkIndex ASC")
    suspend fun getChunksForCapture(captureId: String): List<UploadChunkEntity>

    @Query("SELECT COUNT(*) FROM upload_chunks WHERE captureId = :captureId AND isUploaded = 1")
    suspend fun getUploadedChunkCount(captureId: String): Int

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertChunks(chunks: List<UploadChunkEntity>)

    @Query("UPDATE upload_chunks SET isUploaded = 1 WHERE captureId = :captureId AND chunkIndex = :chunkIndex")
    suspend fun markChunkUploaded(captureId: String, chunkIndex: Int)

    @Query("UPDATE upload_chunks SET retryCount = retryCount + 1, lastError = :error WHERE captureId = :captureId AND chunkIndex = :chunkIndex")
    suspend fun recordChunkError(captureId: String, chunkIndex: Int, error: String)

    @Query("DELETE FROM upload_chunks WHERE captureId = :captureId")
    suspend fun deleteChunksForCapture(captureId: String)
}

// ==========================================
// Database
// ==========================================

@Database(
    entities = [ProjectEntity::class, CaptureEntity::class, UploadChunkEntity::class],
    version = 2,
    exportSchema = false
)
abstract class VastuDatabase : RoomDatabase() {
    abstract fun projectDao(): ProjectDao
    abstract fun captureDao(): CaptureDao
    abstract fun uploadChunkDao(): UploadChunkDao

    companion object {
        @Volatile
        private var INSTANCE: VastuDatabase? = null

        fun getDatabase(context: Context): VastuDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    VastuDatabase::class.java,
                    "vastu_spatial.db"
                )
                .fallbackToDestructiveMigration()
                .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
