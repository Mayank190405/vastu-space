package com.vastu.spatial.worker

import android.content.Context
import androidx.work.*
import com.vastu.spatial.data.api.ApiClient
import com.vastu.spatial.data.local.UploadChunkEntity
import com.vastu.spatial.data.local.VastuDatabase
import com.vastu.spatial.data.model.CompleteUploadRequest
import com.vastu.spatial.data.model.InitUploadRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.RandomAccessFile
import java.security.MessageDigest

class ResumableUploadWorker(
    context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    private val db = VastuDatabase.getDatabase(context)
    private val api = ApiClient.service

    companion object {
        const val KEY_CAPTURE_ID = "capture_id"
        const val KEY_FILE_PATH = "file_path"
        const val CHUNK_SIZE_BYTES = 5 * 1024 * 1024L // 5MB

        fun enqueue(context: Context, captureId: String, filePath: String) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val workRequest = OneTimeWorkRequestBuilder<ResumableUploadWorker>()
                .setConstraints(constraints)
                .setInputData(
                    workDataOf(
                        KEY_CAPTURE_ID to captureId,
                        KEY_FILE_PATH to filePath
                    )
                )
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 5, java.util.concurrent.TimeUnit.SECONDS)
                .build()

            WorkManager.getInstance(context).enqueueUniqueWork(
                "upload_$captureId",
                ExistingWorkPolicy.REPLACE,
                workRequest
            )
        }
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val captureId = inputData.getString(KEY_CAPTURE_ID) ?: return@withContext Result.failure()
        val filePath = inputData.getString(KEY_FILE_PATH) ?: return@withContext Result.failure()
        val file = File(filePath)

        if (!file.exists() || file.length() == 0L) {
            db.captureDao().recordError(captureId, "failed", "File does not exist: $filePath")
            return@withContext Result.failure()
        }

        val totalBytes = file.length()
        val totalChunks = ((totalBytes + CHUNK_SIZE_BYTES - 1) / CHUNK_SIZE_BYTES).toInt().coerceAtLeast(1)
        val wholeFileChecksum = calculateSha256(file)

        // 1. Initialize or query active upload session
        val capture = db.captureDao().getCaptureById(captureId) ?: return@withContext Result.failure()
        var sessionId = capture.uploadSessionId

        if (sessionId == null) {
            val initReq = InitUploadRequest(
                captureId = captureId,
                fileName = file.name,
                fileSizeBytes = totalBytes,
                chunkSizeBytes = CHUNK_SIZE_BYTES,
                totalChunks = totalChunks,
                checksumSha256 = wholeFileChecksum
            )

            val initResp = try {
                api.initUploadSession(initReq)
            } catch (e: Exception) {
                db.captureDao().recordError(captureId, "uploading", "Network error initializing upload: ${e.localizedMessage}")
                return@withContext Result.retry()
            }

            if (!initResp.isSuccessful || initResp.body()?.data == null) {
                val err = initResp.body()?.error ?: "HTTP ${initResp.code()} failed to init upload session"
                db.captureDao().recordError(captureId, "uploading", err)
                return@withContext Result.retry()
            }

            sessionId = initResp.body()!!.data!!.id
            db.captureDao().updateCapture(
                capture.copy(
                    uploadSessionId = sessionId,
                    totalChunks = totalChunks,
                    fileSizeBytes = totalBytes,
                    checksumSha256 = wholeFileChecksum,
                    status = "uploading"
                )
            )

            // Prepare chunk entities in local DB
            val chunks = mutableListOf<UploadChunkEntity>()
            for (i in 0 until totalChunks) {
                val start = i * CHUNK_SIZE_BYTES
                val end = minOf(start + CHUNK_SIZE_BYTES - 1, totalBytes - 1)
                val size = (end - start + 1).coerceAtLeast(0)
                val chunkHash = calculateChunkSha256(file, start, size)

                chunks.add(
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
            db.uploadChunkDao().deleteChunksForCapture(captureId)
            db.uploadChunkDao().insertChunks(chunks)
        }

        // 2. Fetch remote progress to reconcile missing chunks
        val statusResp = try {
            api.getUploadStatus(sessionId)
        } catch (e: Exception) {
            null
        }

        val localChunks = db.uploadChunkDao().getChunksForCapture(captureId)
        val raf = RandomAccessFile(file, "r")

        try {
            var uploadedCount = localChunks.count { it.isUploaded }

            for (chunk in localChunks) {
                if (chunk.isUploaded) continue

                val buffer = ByteArray(chunk.sizeBytes.toInt())
                raf.seek(chunk.startByte)
                raf.readFully(buffer)

                val contentRange = "bytes ${chunk.startByte}-${chunk.endByte}/$totalBytes"
                val requestBody = buffer.toRequestBody("application/octet-stream".toMediaTypeOrNull())

                var chunkSuccess = false
                var attempts = 0
                val maxChunkRetries = 3

                while (!chunkSuccess && attempts < maxChunkRetries) {
                    attempts++
                    try {
                        val chunkResp = api.uploadChunk(
                            sessionId = sessionId,
                            chunkIndex = chunk.chunkIndex,
                            contentRange = contentRange,
                            chunkChecksum = chunk.checksumSha256,
                            chunkBody = requestBody
                        )

                        if (chunkResp.isSuccessful) {
                            chunkSuccess = true
                            db.uploadChunkDao().markChunkUploaded(captureId, chunk.chunkIndex)
                            uploadedCount++
                            db.captureDao().updateProgress(captureId, "uploading", uploadedCount)
                            setProgress(workDataOf("progress" to (uploadedCount.toFloat() / totalChunks)))
                        } else {
                            val err = chunkResp.body()?.error ?: "HTTP ${chunkResp.code()}"
                            db.uploadChunkDao().recordChunkError(captureId, chunk.chunkIndex, err)
                            delay(1000L * attempts)
                        }
                    } catch (e: Exception) {
                        db.uploadChunkDao().recordChunkError(captureId, chunk.chunkIndex, e.localizedMessage ?: "Connection reset")
                        delay(1000L * attempts)
                    }
                }

                if (!chunkSuccess) {
                    return@withContext Result.retry()
                }
            }

            // 3. Finalize upload session with final SHA256 verification
            val completeResp = try {
                api.completeUpload(sessionId, CompleteUploadRequest(finalChecksumSha256 = wholeFileChecksum))
            } catch (e: Exception) {
                db.captureDao().recordError(captureId, "uploading", "Error finalizing upload: ${e.localizedMessage}")
                return@withContext Result.retry()
            }

            if (completeResp.isSuccessful) {
                db.captureDao().updateProgress(captureId, "uploaded", totalChunks)
                return@withContext Result.success()
            } else {
                val err = completeResp.body()?.error ?: "Finalize error (code ${completeResp.code()})"
                db.captureDao().recordError(captureId, "uploading", err)
                return@withContext Result.retry()
            }
        } catch (e: Exception) {
            db.captureDao().recordError(captureId, "uploading", e.localizedMessage ?: "IO Exception during upload")
            return@withContext Result.retry()
        } finally {
            raf.close()
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
