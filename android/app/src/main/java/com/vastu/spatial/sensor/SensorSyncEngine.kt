package com.vastu.spatial.sensor

import com.squareup.moshi.JsonClass
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import com.vastu.spatial.camera.VideoValidationResult
import java.io.BufferedReader
import java.io.File
import java.io.FileReader
import java.io.FileWriter
import kotlin.math.abs

@JsonClass(generateAdapter = true)
data class FrameImuAssociation(
    val frameIndex: Int,
    val frameTimestampNs: Long,
    val nearestImuTimestampNs: Long,
    val timeDifferenceNs: Long,
    val imuSampleCountInWindow: Int
)

@JsonClass(generateAdapter = true)
data class SyncManifest(
    val sessionName: String,
    val videoDurationMs: Long,
    val imuDurationMs: Long,
    val clockOffsetNs: Long,
    val timestampDriftMs: Long,
    val totalFrames: Int,
    val totalImuSamples: Long,
    val estimatedFps: Float,
    val syncQuality: String, // "EXCELLENT", "GOOD", "ACCEPTABLE", "DEGRADED"
    val isMonotonic: Boolean,
    val frameAssociations: List<FrameImuAssociation>
)

object SensorSyncEngine {

    private const val ASSOCIATION_WINDOW_NS = 20_000_000L // 20ms window (+-10ms)

    fun generateSyncManifest(
        sessionName: String,
        videoValidation: VideoValidationResult,
        imuValidation: ImuValidationResult,
        videoStartTimestampNs: Long,
        imuFile: File,
        outputDir: File
    ): SyncManifest {
        // Read IMU timestamps from CSV
        val imuTimestamps = mutableListOf<Long>()
        try {
            BufferedReader(FileReader(imuFile)).use { reader ->
                reader.readLine() // skip header
                var line: String? = reader.readLine()
                while (line != null) {
                    val tokens = line.split(",")
                    if (tokens.isNotEmpty()) {
                        tokens[0].trim().toLongOrNull()?.let { ts ->
                            if (imuTimestamps.isEmpty() || ts != imuTimestamps.last()) {
                                imuTimestamps.add(ts)
                            }
                        }
                    }
                    line = reader.readLine()
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }

        val firstImuTimestampNs = imuTimestamps.firstOrNull() ?: videoStartTimestampNs
        val clockOffsetNs = videoStartTimestampNs - firstImuTimestampNs
        val imuDurationMs = (imuValidation.durationSeconds * 1000).toLong()
        val driftMs = abs(videoValidation.durationMs - imuDurationMs)

        val totalFrames = if (videoValidation.frameRate > 0) {
            ((videoValidation.durationMs * videoValidation.frameRate) / 1000.0).toInt().coerceAtLeast(1)
        } else {
            30
        }

        val frameIntervalNs = if (totalFrames > 1) {
            (videoValidation.durationMs * 1_000_000L) / totalFrames
        } else {
            33_333_333L // ~30fps default
        }

        val associations = mutableListOf<FrameImuAssociation>()

        for (frameIdx in 0 until totalFrames) {
            val frameTimeNs = videoStartTimestampNs + (frameIdx * frameIntervalNs)

            // Find nearest IMU timestamp and count within +-20ms window
            var nearestTs = firstImuTimestampNs
            var minDiff = Long.MAX_VALUE
            var windowCount = 0

            for (imuTs in imuTimestamps) {
                val diff = abs(imuTs - frameTimeNs)
                if (diff < minDiff) {
                    minDiff = diff
                    nearestTs = imuTs
                }
                if (diff <= ASSOCIATION_WINDOW_NS) {
                    windowCount++
                }
            }

            associations.add(
                FrameImuAssociation(
                    frameIndex = frameIdx,
                    frameTimestampNs = frameTimeNs,
                    nearestImuTimestampNs = nearestTs,
                    timeDifferenceNs = minDiff,
                    imuSampleCountInWindow = windowCount
                )
            )
        }

        val syncQuality = when {
            driftMs < 50 && imuValidation.isMonotonic && imuValidation.largeGapCount == 0 -> "EXCELLENT"
            driftMs < 150 && imuValidation.isMonotonic -> "GOOD"
            driftMs < 300 -> "ACCEPTABLE"
            else -> "DEGRADED"
        }

        val manifest = SyncManifest(
            sessionName = sessionName,
            videoDurationMs = videoValidation.durationMs,
            imuDurationMs = imuDurationMs,
            clockOffsetNs = clockOffsetNs,
            timestampDriftMs = driftMs,
            totalFrames = totalFrames,
            totalImuSamples = imuValidation.totalSamples,
            estimatedFps = videoValidation.frameRate,
            syncQuality = syncQuality,
            isMonotonic = imuValidation.isMonotonic,
            frameAssociations = associations
        )

        // Write to sync_manifest.json
        try {
            val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
            val json = moshi.adapter(SyncManifest::class.java).indent("  ").toJson(manifest)
            val manifestFile = File(outputDir, "sync_manifest.json")
            FileWriter(manifestFile).use { it.write(json) }
        } catch (e: Exception) {
            e.printStackTrace()
        }

        return manifest
    }
}
