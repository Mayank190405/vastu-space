package com.vastu.spatial.camera

import android.content.Context
import android.speech.tts.TextToSpeech
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.util.Locale

enum class QualityLevel {
    OPTIMAL,
    WARNING_MOTION_BLUR,
    WARNING_INSUFFICIENT_OVERLAP,
    WARNING_LOW_FEATURE_DENSITY,
    WARNING_LOW_LIGHT,
    RESCAN_REQUIRED
}

data class QualityFeedback(
    val level: QualityLevel,
    val title: String,
    val correctiveAction: String
)

data class SOPStep(
    val id: Int,
    val index: Int,
    val title: String,
    val description: String
)

enum class AndroidSOPStage {
    ROOM_ENTRY,
    PERIMETER_COVERAGE,
    WALL_COVERAGE,
    CORNERS,
    DOORWAY,
    WINDOWS,
    FLOOR,
    CEILING,
    CENTER_TRAVERSAL,
    RETURN_LOOP_CLOSURE,
    COMPLETION_VERIFICATION
}

enum class AndroidTTSPriority(val level: Int) {
    CRITICAL(1),
    WARNING(2),
    GUIDANCE(3),
    CONFIRMATION(4)
}

data class AndroidSOPStageInfo(
    val id: Int,
    val stage: AndroidSOPStage,
    val title: String,
    val guidance: String,
    val completionNotice: String
)

class CaptureQualityEngine(context: Context? = null) : TextToSpeech.OnInitListener {

    val sopSteps = listOf(
        SOPStep(1, 1, "Start at the Door", "Stand at the room entrance and hold your phone steady for a few seconds"),
        SOPStep(2, 2, "Walk Room Outline", "Walk slowly around the room walls in a circle. Take steady, calm steps"),
        SOPStep(3, 3, "Point at Walls", "Point your phone at the walls while walking about 6 feet away"),
        SOPStep(4, 4, "Check Room Corners", "At each corner, tilt your phone slowly up and down from floor to ceiling"),
        SOPStep(5, 5, "Scan Doorways", "Frame each doorway clearly from top to bottom"),
        SOPStep(6, 6, "Scan Windows", "Point at window frames without aiming directly into bright sunlight"),
        SOPStep(7, 7, "Scan the Floor", "Tilt your phone down slightly to capture the floor and baseboards"),
        SOPStep(8, 8, "Scan the Ceiling", "Tilt your phone up to capture the ceiling, lights, and fans"),
        SOPStep(9, 9, "Walk Across Room", "Walk across the middle of the room to capture central tables and furniture"),
        SOPStep(10, 10, "Walk Back to Start", "Return to the door where you started to finish the circle"),
        SOPStep(11, 11, "Final Check", "Hold your phone still while we verify your complete scan")
    )

    val sopStages = listOf(
        AndroidSOPStageInfo(1, AndroidSOPStage.ROOM_ENTRY, "Start at the Door", "Stand at the room entrance and hold your phone steady for a few seconds", "Great start! Now start walking slowly"),
        AndroidSOPStageInfo(2, AndroidSOPStage.PERIMETER_COVERAGE, "Walk Room Outline", "Walk slowly around the room walls in a circle. Take steady steps", "Room outline captured. Now focus on the walls"),
        AndroidSOPStageInfo(3, AndroidSOPStage.WALL_COVERAGE, "Point at Walls", "Point your phone at the walls while walking about 6 feet away", "Walls recorded. Now move to the corners"),
        AndroidSOPStageInfo(4, AndroidSOPStage.CORNERS, "Check Room Corners", "At each corner, tilt your phone slowly up and down from floor to ceiling", "Corners saved. Now scan the doorways"),
        AndroidSOPStageInfo(5, AndroidSOPStage.DOORWAY, "Scan Doorways", "Frame each doorway clearly from top to bottom", "Doors captured. Next are the windows"),
        AndroidSOPStageInfo(6, AndroidSOPStage.WINDOWS, "Scan Windows", "Point at window frames without aiming directly into bright sunlight", "Windows recorded. Now aim toward the floor"),
        AndroidSOPStageInfo(7, AndroidSOPStage.FLOOR, "Scan the Floor", "Tilt your phone down slightly to capture the floor and baseboards", "Floor captured. Now tilt up toward the ceiling"),
        AndroidSOPStageInfo(8, AndroidSOPStage.CEILING, "Scan the Ceiling", "Tilt your phone up to capture the ceiling, lights, and fans", "Ceiling verified. Now walk across the room"),
        AndroidSOPStageInfo(9, AndroidSOPStage.CENTER_TRAVERSAL, "Walk Across Room", "Walk across the middle of the room to capture central furniture", "Center covered. Now head back to the start"),
        AndroidSOPStageInfo(10, AndroidSOPStage.RETURN_LOOP_CLOSURE, "Walk Back to Start", "Return to the door where you started to finish the circle", "Circle closed! Hold still for the final check"),
        AndroidSOPStageInfo(11, AndroidSOPStage.COMPLETION_VERIFICATION, "Final Check", "Hold your phone still while we verify your complete scan", "Scan complete! Space captured successfully")
    )

    private val _currentStageIndex = MutableStateFlow(0)
    val currentStageIndex: StateFlow<Int> = _currentStageIndex
    val currentSopIndex: StateFlow<Int> = _currentStageIndex

    private val _qualityFeedback = MutableStateFlow(
        QualityFeedback(QualityLevel.OPTIMAL, "Optimal Coverage", "Maintain steady movement and 70% overlap")
    )
    val qualityFeedback: StateFlow<QualityFeedback> = _qualityFeedback

    private val _activeWarning = MutableStateFlow<String?>(null)
    val activeWarning: StateFlow<String?> = _activeWarning

    private var tts: TextToSpeech? = context?.let { TextToSpeech(it.applicationContext, this) }
    private var isTtsReady = false

    private val lastSpokenTimestamps = mutableMapOf<String, Long>()
    private var lastAnySpeechTime: Long = 0L

    private val cooldownMs = 6000L
    private val minSilenceMs = 2500L

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale.US
            isTtsReady = true
        }
    }

    fun nextSopStep() {
        if (_currentStageIndex.value < sopSteps.size - 1) {
            _currentStageIndex.value += 1
            val nextStep = sopSteps[_currentStageIndex.value]
            speakInstruction(nextStep.description, AndroidTTSPriority.GUIDANCE, "STAGE_GUIDE")
        }
    }

    fun previousSopStep() {
        if (_currentStageIndex.value > 0) {
            _currentStageIndex.value -= 1
        }
    }

    fun getCoverageQualityScore(): Double {
        val completedRatio = (_currentStageIndex.value + 1).toDouble() / sopSteps.size.toDouble()
        return Math.min(1.0, Math.max(0.0, completedRatio * 0.95))
    }

    fun speakInstruction(text: String, priority: AndroidTTSPriority, category: String) {
        val engine = tts ?: return
        if (!isTtsReady) return
        val now = System.currentTimeMillis()

        // Check cooldown and silence
        if (priority != AndroidTTSPriority.CRITICAL) {
            val lastCatTime = lastSpokenTimestamps[category] ?: 0L
            if ((now - lastCatTime) < cooldownMs) {
                return // Suppress repetitive prompt
            }
            if ((now - lastAnySpeechTime) < minSilenceMs) {
                return // Enforce pacing gap
            }
        }

        lastSpokenTimestamps[category] = now
        lastAnySpeechTime = now

        if (priority == AndroidTTSPriority.CRITICAL) {
            engine.stop()
            engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, category)
        } else {
            engine.speak(text, TextToSpeech.QUEUE_ADD, null, category)
        }
    }

    private val _overallCoverageScore = MutableStateFlow(0.0f)
    val overallCoverageScore: StateFlow<Float> = _overallCoverageScore

    private val _floorCoverageScore = MutableStateFlow(0.0f)
    val floorCoverageScore: StateFlow<Float> = _floorCoverageScore

    private val _wallCoverageScore = MutableStateFlow(0.0f)
    val wallCoverageScore: StateFlow<Float> = _wallCoverageScore

    private val _isGatedComplete = MutableStateFlow(false)
    val isGatedComplete: StateFlow<Boolean> = _isGatedComplete

    fun updateCoverage(overall: Float, floor: Float, walls: Float) {
        _overallCoverageScore.value = Math.min(1.0f, Math.max(0.0f, overall))
        _floorCoverageScore.value = Math.min(1.0f, Math.max(0.0f, floor))
        _wallCoverageScore.value = Math.min(1.0f, Math.max(0.0f, walls))
        _isGatedComplete.value = (_overallCoverageScore.value >= 0.85f &&
                                 _floorCoverageScore.value >= 0.80f &&
                                 _wallCoverageScore.value >= 0.70f)
    }

    fun verifyCompletionGate(): Pair<Boolean, String?> {
        if (_overallCoverageScore.value < 0.85f) {
            val pct = (_overallCoverageScore.value * 100).toInt()
            val msg = "Capture incomplete. Overall coverage is $pct%, required 85%."
            speakInstruction("$msg Sweep unobserved areas before completing.", AndroidTTSPriority.WARNING, "GATE_INCOMPLETE")
            _activeWarning.value = "COVERAGE < 85%"
            return Pair(false, msg)
        }
        if (_floorCoverageScore.value < 0.80f) {
            val pct = (_floorCoverageScore.value * 100).toInt()
            val msg = "Floor coverage is $pct%, required 80%. Tilt phone downward to scan floor."
            speakInstruction(msg, AndroidTTSPriority.WARNING, "GATE_FLOOR")
            _activeWarning.value = "SCAN FLOOR SURFACE"
            return Pair(false, msg)
        }
        if (_wallCoverageScore.value < 0.70f) {
            val pct = (_wallCoverageScore.value * 100).toInt()
            val msg = "Wall coverage is $pct%, required 70%. Sweep perimeter walls."
            speakInstruction(msg, AndroidTTSPriority.WARNING, "GATE_WALLS")
            _activeWarning.value = "SCAN WALL SURFACES"
            return Pair(false, msg)
        }
        return Pair(true, null)
    }

    fun evaluateTelemetry(
        velocityMps: Float,
        angularVelocityRadps: Float,
        blurScore: Float,
        ambientLux: Float,
        featureCount: Int,
        trackingLost: Boolean
    ) {
        if (trackingLost) {
            speakInstruction("Tracking lost. Aim camera toward previously scanned areas.", AndroidTTSPriority.CRITICAL, "TRACKING_LOST")
            _activeWarning.value = "TRACKING DEGRADED"
            _qualityFeedback.value = QualityFeedback(
                QualityLevel.RESCAN_REQUIRED,
                "Tracking Degraded",
                "Re-aim camera at features already scanned to recover tracking"
            )
            return
        }

        // Translation baseline check: alert if user twists in place without translation baseline
        if (velocityMps < 0.15f && angularVelocityRadps > 0.26f) { // > 15 deg/s
            speakInstruction("Walk sideways along room perimeter! Do not twist in place without translation baseline.", AndroidTTSPriority.WARNING, "PURE_ROTATION")
            _activeWarning.value = "TWISTING IN PLACE — WALK SIDEWAYS"
            _qualityFeedback.value = QualityFeedback(
                QualityLevel.WARNING_INSUFFICIENT_OVERLAP,
                "Translation Baseline Required",
                "Step sideways along perimeter instead of rotating in place"
            )
            return
        }

        if (velocityMps > 0.8f || angularVelocityRadps > 1.2f) {
            speakInstruction("Slow down. Move camera more steadily.", AndroidTTSPriority.WARNING, "EXCESSIVE_MOTION")
            _activeWarning.value = "EXCESSIVE MOTION"
            _qualityFeedback.value = QualityFeedback(
                QualityLevel.WARNING_MOTION_BLUR,
                "Excessive Motion",
                "Slow down walking pace and pan camera steadily"
            )
            return
        }

        if (blurScore > 0.4f) {
            speakInstruction("Image blur detected. Hold camera steady.", AndroidTTSPriority.WARNING, "BLUR")
            _activeWarning.value = "BLUR DETECTED"
            _qualityFeedback.value = QualityFeedback(
                QualityLevel.WARNING_MOTION_BLUR,
                "Motion Blur Detected",
                "Hold phone steady and minimize sudden panning"
            )
            return
        }

        if (ambientLux < 30f) {
            speakInstruction("Lighting too low. Turn on room lights.", AndroidTTSPriority.WARNING, "LOW_LIGHT")
            _activeWarning.value = "LOW LIGHT"
            _qualityFeedback.value = QualityFeedback(
                QualityLevel.WARNING_LOW_LIGHT,
                "Insufficient Light",
                "Turn on room lighting or avoid dark shadow areas"
            )
            return
        }

        if (featureCount < 80) {
            speakInstruction("Low texture area. Frame more furniture or doorways.", AndroidTTSPriority.GUIDANCE, "LOW_FEATURES")
            _activeWarning.value = "LOW FEATURES"
            _qualityFeedback.value = QualityFeedback(
                QualityLevel.WARNING_LOW_FEATURE_DENSITY,
                "Low Feature Density",
                "Point toward patterned surfaces, door frames, or furniture"
            )
            return
        }

        _activeWarning.value = null
        _qualityFeedback.value = QualityFeedback(
            QualityLevel.OPTIMAL,
            "Optimal Quality",
            "Maintain steady movement and 70% overlap"
        )
    }

    fun advanceStage() {
        if (_currentStageIndex.value == sopStages.size - 1) {
            // Final stage: verify 85% completion gate
            val gate = verifyCompletionGate()
            if (!gate.first) {
                return // Block completion until gate passes
            }
            speakInstruction("Scan complete! Space captured successfully.", AndroidTTSPriority.CONFIRMATION, "STAGE_CONFIRM")
            return
        }

        if (_currentStageIndex.value < sopStages.size - 1) {
            val current = sopStages[_currentStageIndex.value]
            speakInstruction(current.completionNotice, AndroidTTSPriority.CONFIRMATION, "STAGE_CONFIRM")

            _currentStageIndex.value += 1
            val next = sopStages[_currentStageIndex.value]
            speakInstruction(next.guidance, AndroidTTSPriority.GUIDANCE, "STAGE_GUIDE")
        }
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
    }
}

