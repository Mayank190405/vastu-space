package com.vastu.spatial.camera

import android.media.MediaMetadataRetriever
import java.io.File

data class VideoValidationResult(
    val isValid: Boolean,
    val width: Int = 0,
    val height: Int = 0,
    val durationMs: Long = 0L,
    val bitrate: Long = 0L,
    val frameRate: Float = 0f,
    val fileSizeBytes: Long = 0L,
    val errorMessage: String? = null
)

object VideoValidator {

    private const val MIN_RECORDING_DURATION_MS = 1000L // Min 1 second
    private const val MIN_FILE_SIZE_BYTES = 100 * 1024L // Min 100KB

    fun validateVideo(videoFile: File): VideoValidationResult {
        if (!videoFile.exists()) {
            return VideoValidationResult(
                isValid = false,
                errorMessage = "Video file does not exist on disk"
            )
        }

        val fileSize = videoFile.length()
        if (fileSize < MIN_FILE_SIZE_BYTES) {
            return VideoValidationResult(
                isValid = false,
                fileSizeBytes = fileSize,
                errorMessage = "Video file size is too small (${fileSize} bytes) - likely corrupted or aborted prematurely"
            )
        }

        val retriever = MediaMetadataRetriever()
        return try {
            retriever.setDataSource(videoFile.absolutePath)

            val hasVideo = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_HAS_VIDEO)
            if (hasVideo != "yes") {
                return VideoValidationResult(
                    isValid = false,
                    fileSizeBytes = fileSize,
                    errorMessage = "File does not contain a readable video track"
                )
            }

            val durationStr = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
            val durationMs = durationStr?.toLongOrNull() ?: 0L

            if (durationMs < MIN_RECORDING_DURATION_MS) {
                return VideoValidationResult(
                    isValid = false,
                    durationMs = durationMs,
                    fileSizeBytes = fileSize,
                    errorMessage = "Recording duration is too short (${durationMs}ms). Minimum 1 second required."
                )
            }

            val width = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toIntOrNull() ?: 0
            val height = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)?.toIntOrNull() ?: 0
            val bitrate = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_BITRATE)?.toLongOrNull() ?: 0L
            val frameCountStr = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_FRAME_COUNT)
            val frameCount = frameCountStr?.toIntOrNull() ?: 0

            val frameRate = if (durationMs > 0 && frameCount > 0) {
                (frameCount * 1000f) / durationMs
            } else {
                30.0f
            }

            VideoValidationResult(
                isValid = true,
                width = width,
                height = height,
                durationMs = durationMs,
                bitrate = bitrate,
                frameRate = frameRate,
                fileSizeBytes = fileSize
            )
        } catch (e: Exception) {
            VideoValidationResult(
                isValid = false,
                fileSizeBytes = fileSize,
                errorMessage = "Failed to parse video container / moov atom: ${e.localizedMessage}"
            )
        } finally {
            try {
                retriever.release()
            } catch (e: Exception) {
                // Ignore
            }
        }
    }
}
