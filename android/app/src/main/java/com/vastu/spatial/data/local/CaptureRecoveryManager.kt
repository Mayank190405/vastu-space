package com.vastu.spatial.data.local

import java.io.File

data class AndroidRecoveryStatus(
    val isInterrupted: Boolean,
    val canResume: Boolean,
    val lastSegmentIndex: Int,
    val lastFrameIndex: Int,
    val recordedEventsCount: Int
)

object CaptureRecoveryManager {

    fun analyzeSession(sessionDir: File): AndroidRecoveryStatus {
        val journal = CaptureSessionJournal(sessionDir)
        val events = journal.readEvents()

        val hasStart = events.any { it.event == "SESSION_START" }
        val hasEnd = events.any { it.event == "SESSION_END" }

        var maxSegment = 0
        var maxFrame = 0

        for (e in events) {
            if (e.event == "SEGMENT_START" || e.event == "SEGMENT_END") {
                e.payload["segment_index"]?.toIntOrNull()?.let {
                    maxSegment = maxOf(maxSegment, it)
                }
            }
            if (e.event == "TELEMETRY_CHECKPOINT") {
                e.payload["last_frame_index"]?.toIntOrNull()?.let {
                    maxFrame = maxOf(maxFrame, it)
                }
            }
        }

        val isInterrupted = hasStart && !hasEnd
        return AndroidRecoveryStatus(
            isInterrupted = isInterrupted,
            canResume = isInterrupted,
            lastSegmentIndex = maxSegment,
            lastFrameIndex = maxFrame,
            recordedEventsCount = events.size
        )
    }

    fun prepareResumption(sessionDir: File): Pair<Int, Int> {
        val status = analyzeSession(sessionDir)
        val journal = CaptureSessionJournal(sessionDir)

        val nextSeg = status.lastSegmentIndex + 1
        val nextFrame = status.lastFrameIndex + 1

        journal.logEvent(
            "RESUMPTION",
            mapOf(
                "next_segment_index" to nextSeg.toString(),
                "start_frame_index" to nextFrame.toString()
            )
        )

        return Pair(nextSeg, nextFrame)
    }
}
