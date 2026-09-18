package com.vastu.spatial.data.local

import android.content.Context
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import com.vastu.spatial.worker.ResumableUploadWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileWriter
import java.io.RandomAccessFile
import java.security.MessageDigest
import java.util.UUID

data class CapturePackageResult(
    val captureId: String,
    val sessionDir: File,
    val videoFile: File,
    val imuFile: File,
    val manifestFile: File,
    val metadataFile: File,
    val totalChunks: Int,
    val totalBytes: Long,
    val wholeFileChecksumSha256: String
)

class LocalCaptureStorageManager(private val context: Context) {

    private val db = VastuDatabase.getDatabase(context)
    val chunkSize: Long = 5 * 1024 * 1024L // 5MB chunks

    fun createCaptureDirectory(captureId: String = UUID.randomUUID().toString()): File {
        val root = File(context.filesDir, "captures")
        val dir = File(root, captureId)
        dir.mkdirs()
        return dir
    }

    suspend fun packageAndIndexCapture(
        captureId: String,
        projectId: String,
        sessionName: String,
        sessionDir: File,
        videoFile: File,
        imuFile: File,
        manifestFile: File,
        metadataMap: Map<String, Any>
    ): CapturePackageResult = withContext(Dispatchers.IO) {
        val totalBytes = videoFile.length()
        val totalChunks = ((totalBytes + chunkSize - 1) / chunkSize).toInt().coerceAtLeast(1)
        val wholeFileChecksum = calculateSha256(videoFile)

        // 1. Write metadata.json in session folder
        val metadataFile = File(sessionDir, "metadata.json")
        val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
        val jsonAdapter = moshi.adapter(Map::class.java)
        FileWriter(metadataFile).use { writer ->
            writer.write(jsonAdapter.indent("  ").toJson(metadataMap))
        }

        // 2. Build local chunk entities with SHA256 checksums
        val chunkEntities = mutableListOf<UploadChunkEntity>()
        for (i in 0 until totalChunks) {
            val start = i * chunkSize
            val end = minOf(start + chunkSize - 1, totalBytes - 1)
            val size = (end - start + 1).coerceAtLeast(0)
            val chunkHash = calculateChunkSha256(videoFile, start, size)

            chunkEntities.add(
                UploadChunkEntity(
                    captureId = captureId,
                    chunkIndex = i,
                    startByte = start,
                    endByte = end,
                    sizeBytes = size,
                    checksumSha256 = chunkHash,
                    isUploaded = false
                )
            )
        }

        // 3. Persist CaptureEntity & UploadChunkEntities into Room DB
        val captureEntity = CaptureEntity(
            id = captureId,
            projectId = projectId,
            name = sessionName,
            sessionDir = sessionDir.absolutePath,
            videoFilePath = videoFile.absolutePath,
            imuFilePath = imuFile.absolutePath,
            metadataFilePath = metadataFile.absolutePath,
            fileSizeBytes = totalBytes,
            checksumSha256 = wholeFileChecksum,
            status = "pending_upload",
            isReadyForUpload = true,
            totalChunks = totalChunks,
            uploadedChunks = 0
        )

        db.captureDao().insertCapture(captureEntity)
        db.uploadChunkDao().deleteChunksForCapture(captureId)
        db.uploadChunkDao().insertChunks(chunkEntities)

        CapturePackageResult(
            captureId = captureId,
            sessionDir = sessionDir,
            videoFile = videoFile,
            imuFile = imuFile,
            manifestFile = manifestFile,
            metadataFile = metadataFile,
            totalChunks = totalChunks,
            totalBytes = totalBytes,
            wholeFileChecksumSha256 = wholeFileChecksum
        )
    }

    suspend fun recoverInterruptedCaptures() = withContext(Dispatchers.IO) {
        val pendingCaptures = db.captureDao().getPendingOrInterruptedCaptures()
        for (capture in pendingCaptures) {
            val file = File(capture.videoFilePath)
            if (file.exists() && file.length() > 0) {
                // Re-enqueue in WorkManager with network constraint
                ResumableUploadWorker.enqueue(
                    context = context,
                    captureId = capture.id,
                    filePath = capture.videoFilePath
                )
            } else {
                db.captureDao().recordError(capture.id, "failed", "Local capture files missing after reboot")
            }
        }
    }

    suspend fun purgeUploadedLocalCaptures(keepLastN: Int = 3) = withContext(Dispatchers.IO) {
        val uploaded = db.captureDao().getUploadedCaptures()
        if (uploaded.size > keepLastN) {
            val toDelete = uploaded.take(uploaded.size - keepLastN)
            for (item in toDelete) {
                val dir = File(item.sessionDir)
                if (dir.exists()) {
                    dir.deleteRecursively()
                }
            }
        }
    }

    private fun calculateSha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { isStream ->
            val buffer = ByteArray(8192)
            var bytesRead: Int
            while (isStream.read(buffer).also { bytesRead = it } != -1) {
                digest.update(buffer, 0, bytesRead)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun calculateChunkSha256(file: File, start: Long, size: Long): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val raf = RandomAccessFile(file, "r")
        raf.seek(start)
        val buffer = ByteArray(8192)
        var remaining = size
        while (remaining > 0) {
            val toRead = minOf(buffer.size.toLong(), remaining).toInt()
            val read = raf.read(buffer, 0, toRead)
            if (read == -1) break
            digest.update(buffer, 0, read)
            remaining -= read
        }
        raf.close()
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
