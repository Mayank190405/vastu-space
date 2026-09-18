package com.vastu.spatial.sensor

import java.io.BufferedReader
import java.io.File
import java.io.FileReader

data class ImuValidationResult(
    val isValid: Boolean,
    val totalSamples: Long = 0L,
    val accelSamples: Long = 0L,
    val gyroSamples: Long = 0L,
    val durationSeconds: Double = 0.0,
    val averageFrequencyHz: Double = 0.0,
    val isMonotonic: Boolean = true,
    val duplicateTimestampCount: Int = 0,
    val largeGapCount: Int = 0,
    val errorMessage: String? = null
)

object ImuValidator {

    private const val MAX_ALLOWABLE_GAP_NS = 50_000_000L // 50ms (at 100Hz, normal interval is 10ms)
    private const val MIN_REQUIRED_SAMPLES = 50L // Min 0.5s of data

    fun validateImuFile(imuFile: File): ImuValidationResult {
        if (!imuFile.exists() || imuFile.length() == 0L) {
            return ImuValidationResult(
                isValid = false,
                errorMessage = "IMU stream file does not exist or is empty"
            )
        }

        var totalSamples = 0L
        var accelSamples = 0L
        var gyroSamples = 0L
        var firstTimestampNs = 0L
        var lastTimestampNs = 0L
        var prevTimestampNs = 0L

        var isMonotonic = true
        var duplicateCount = 0
        var gapCount = 0

        try {
            BufferedReader(FileReader(imuFile)).use { reader ->
                val header = reader.readLine()
                if (header == null || !header.contains("timestamp_ns")) {
                    return ImuValidationResult(
                        isValid = false,
                        errorMessage = "Invalid IMU CSV header format"
                    )
                }

                var line: String? = reader.readLine()
                while (line != null) {
                    val tokens = line.split(",")
                    if (tokens.size >= 5) {
                        val timestampNs = tokens[0].trim().toLongOrNull() ?: 0L
                        val sensorType = tokens[1].trim()

                        if (totalSamples == 0L) {
                            firstTimestampNs = timestampNs
                            prevTimestampNs = timestampNs
                        } else {
                            if (timestampNs <= prevTimestampNs) {
                                if (timestampNs == prevTimestampNs) {
                                    duplicateCount++
                                } else {
                                    isMonotonic = false
                                }
                            } else if (timestampNs - prevTimestampNs > MAX_ALLOWABLE_GAP_NS) {
                                gapCount++
                            }
                            prevTimestampNs = timestampNs
                        }

                        when {
                            sensorType.contains("ACCEL", ignoreCase = true) -> accelSamples++
                            sensorType.contains("GYRO", ignoreCase = true) -> gyroSamples++
                            sensorType.contains("COMBINED", ignoreCase = true) -> {
                                accelSamples++
                                gyroSamples++
                            }
                        }

                        lastTimestampNs = timestampNs
                        totalSamples++
                    }
                    line = reader.readLine()
                }
            }

            if (totalSamples < MIN_REQUIRED_SAMPLES) {
                return ImuValidationResult(
                    isValid = false,
                    totalSamples = totalSamples,
                    errorMessage = "Insufficient IMU samples ($totalSamples). At least $MIN_REQUIRED_SAMPLES required."
                )
            }

            val durationNs = lastTimestampNs - firstTimestampNs
            val durationSeconds = if (durationNs > 0) durationNs / 1_000_000_000.0 else 0.0
            val avgHz = if (durationSeconds > 0) totalSamples / durationSeconds else 0.0

            return ImuValidationResult(
                isValid = isMonotonic && totalSamples > 0,
                totalSamples = totalSamples,
                accelSamples = accelSamples,
                gyroSamples = gyroSamples,
                durationSeconds = durationSeconds,
                averageFrequencyHz = avgHz,
                isMonotonic = isMonotonic,
                duplicateTimestampCount = duplicateCount,
                largeGapCount = gapCount,
                errorMessage = if (!isMonotonic) "IMU stream contains non-monotonic timestamps" else null
            )
        } catch (e: Exception) {
            return ImuValidationResult(
                isValid = false,
                errorMessage = "Error validating IMU file: ${e.localizedMessage}"
            )
        }
    }
}
