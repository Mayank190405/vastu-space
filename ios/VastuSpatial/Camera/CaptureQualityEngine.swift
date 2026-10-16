import Foundation
import CoreMotion
import AVFoundation
import Combine

public enum QualityLevel: String, CaseIterable {
    case optimal
    case motionBlur
    case insufficientOverlap
    case lowFeatureDensity
    case lowLight
    case rescanRequired
}

public struct QualityFeedback {
    public let level: QualityLevel
    public let title: String
    public let correctiveAction: String
    
    public init(level: QualityLevel, title: String, correctiveAction: String) {
        self.level = level
        self.title = title
        self.correctiveAction = correctiveAction
    }
}

public struct SOPStep: Identifiable {
    public let id: Int
    public let title: String
    public let description: String
    
    public init(id: Int, title: String, description: String) {
        self.id = id
        self.title = title
        self.description = description
    }
}

public enum SOPStage: String, CaseIterable {
    case roomEntry = "ROOM_ENTRY"
    case perimeterCoverage = "PERIMETER_COVERAGE"
    case wallCoverage = "WALL_COVERAGE"
    case corners = "CORNERS"
    case doorway = "DOORWAY"
    case windows = "WINDOWS"
    case floor = "FLOOR"
    case ceiling = "CEILING"
    case centerTraversal = "CENTER_TRAVERSAL"
    case returnLoopClosure = "RETURN_LOOP_CLOSURE"
    case completionVerification = "COMPLETION_VERIFICATION"
}

public enum TTSPriority: Int {
    case critical = 1
    case warning = 2
    case guidance = 3
    case confirmation = 4
}

public struct SOPStageInfo: Identifiable {
    public let id: Int
    public let stage: SOPStage
    public let title: String
    public let guidance: String
    public let completionNotice: String
}

public class CaptureQualityEngine: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {
    
    public let sopSteps: [SOPStep] = [
        SOPStep(id: 1, title: "Start at Door", description: "Stand at the room entrance and hold your phone steady for a few seconds"),
        SOPStep(id: 2, title: "Walk Room Outline", description: "Walk slowly in a circle around the room. Take calm, steady steps"),
        SOPStep(id: 3, title: "Point at Walls", description: "Point your phone at the walls while walking about 6 feet away"),
        SOPStep(id: 4, title: "Check Corners", description: "At each corner, tilt your phone slowly up and down from floor to ceiling"),
        SOPStep(id: 5, title: "Scan Doors", description: "Frame each doorway clearly from top to bottom"),
        SOPStep(id: 6, title: "Scan Windows", description: "Point at window frames without aiming directly into bright sunlight"),
        SOPStep(id: 7, title: "Scan the Floor", description: "Tilt your phone down slightly to capture the floor and baseboards"),
        SOPStep(id: 8, title: "Scan the Ceiling", description: "Tilt your phone up to capture the ceiling, lights, and fans"),
        SOPStep(id: 9, title: "Center Furniture", description: "Walk around tables, islands, and key furniture in the room"),
        SOPStep(id: 10, title: "Walk Across Room", description: "Walk straight across the middle of the room to connect both sides"),
        SOPStep(id: 11, title: "Walk Back to Start", description: "Return to the door where you started to finish the circle"),
        SOPStep(id: 12, title: "Final Check", description: "Hold your phone still while we verify your complete scan")
    ]
    
    public let sopStages: [SOPStageInfo] = [
        SOPStageInfo(id: 1, stage: .roomEntry, title: "Start at Door", guidance: "Stand at the room entrance and hold your phone steady for a few seconds", completionNotice: "Great start! Now start walking slowly"),
        SOPStageInfo(id: 2, stage: .perimeterCoverage, title: "Walk Room Outline", guidance: "Walk slowly around the room walls in a circle. Take steady steps", completionNotice: "Room outline captured. Now focus on the walls"),
        SOPStageInfo(id: 3, stage: .wallCoverage, title: "Point at Walls", guidance: "Point your phone at the walls while walking about 6 feet away", completionNotice: "Walls recorded. Now move to the corners"),
        SOPStageInfo(id: 4, stage: .corners, title: "Check Corners", guidance: "At each corner, tilt your phone slowly up and down from floor to ceiling", completionNotice: "Corners saved. Now scan the doorways"),
        SOPStageInfo(id: 5, stage: .doorway, title: "Scan Doors", guidance: "Frame each doorway clearly from top to bottom", completionNotice: "Doors captured. Next are the windows"),
        SOPStageInfo(id: 6, stage: .windows, title: "Scan Windows", guidance: "Point at window frames without aiming directly into bright sunlight", completionNotice: "Windows recorded. Now aim toward the floor"),
        SOPStageInfo(id: 7, stage: .floor, title: "Scan the Floor", guidance: "Tilt your phone down slightly to capture the floor and baseboards", completionNotice: "Floor captured. Now tilt up toward the ceiling"),
        SOPStageInfo(id: 8, stage: .ceiling, title: "Scan the Ceiling", guidance: "Tilt your phone up to capture the ceiling, lights, and fans", completionNotice: "Ceiling verified. Now walk across the room"),
        SOPStageInfo(id: 9, stage: .centerTraversal, title: "Walk Across Room", guidance: "Walk across the middle of the room to capture central furniture", completionNotice: "Center covered. Now head back to the start"),
        SOPStageInfo(id: 10, stage: .returnLoopClosure, title: "Walk Back to Start", guidance: "Return to the door where you started to finish the circle", completionNotice: "Circle closed! Hold still for the final check"),
        SOPStageInfo(id: 11, stage: .completionVerification, title: "Final Check", guidance: "Hold your phone still while we verify your complete scan", completionNotice: "Scan complete! Space captured successfully")
    ]
    
    @Published public var currentSOPIndex: Int = 0
    @Published public var currentStageIndex: Int = 0
    @Published public var activeWarning: String? = nil
    @Published public var qualityFeedback: QualityFeedback = QualityFeedback(
        level: .optimal,
        title: "EXCELLENT QUALITY",
        correctiveAction: "Maintain steady movement"
    )
    
    private let speechSynthesizer = AVSpeechSynthesizer()
    private var lastSpokenTimestamps: [String: TimeInterval] = [:]
    private var lastAnySpeechTime: TimeInterval = 0
    
    private let cooldownSeconds: TimeInterval = 6.0
    private let minSilenceSeconds: TimeInterval = 2.5
    
    public override init() {
        super.init()
        speechSynthesizer.delegate = self
    }
    
    public func nextSOPStep() {
        if currentSOPIndex < sopSteps.count - 1 {
            currentSOPIndex += 1
        }
    }
    
    public func previousSOPStep() {
        if currentSOPIndex > 0 {
            currentSOPIndex -= 1
        }
    }
    
    public func evaluateMotion(gyroX: Float, gyroY: Float, gyroZ: Float, accelX: Float, accelY: Float, accelZ: Float) {
        let rotationalVelocity = sqrt(gyroX * gyroX + gyroY * gyroY + gyroZ * gyroZ)
        let linearAccel = sqrt(accelX * accelX + accelY * accelY + accelZ * accelZ)
        
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            
            if rotationalVelocity > 1.6 {
                self.qualityFeedback = QualityFeedback(
                    level: .motionBlur,
                    title: "MOTION BLUR WARNING",
                    correctiveAction: "Slow down camera panning to avoid motion blur"
                )
                self.activeWarning = "MOTION BLUR DETECTED"
            } else if linearAccel > 1.4 {
                self.qualityFeedback = QualityFeedback(
                    level: .insufficientOverlap,
                    title: "INSUFFICIENT OVERLAP WARNING",
                    correctiveAction: "Move more steadily to ensure 70% frame overlap"
                )
                self.activeWarning = "EXCESSIVE SPEED"
            } else if rotationalVelocity < 0.02 && abs(linearAccel - 1.0) < 0.05 {
                self.qualityFeedback = QualityFeedback(
                    level: .lowFeatureDensity,
                    title: "FEATURE POOR WARNING",
                    correctiveAction: "Aim toward areas with distinct visual features"
                )
                self.activeWarning = "LOW TEXTURE AREA"
            } else {
                self.qualityFeedback = QualityFeedback(
                    level: .optimal,
                    title: "EXCELLENT QUALITY",
                    correctiveAction: "Maintain steady movement"
                )
                self.activeWarning = nil
            }
        }
    }
    
    public func getCoverageQualityScore() -> Float {
        switch qualityFeedback.level {
        case .optimal: return 1.0
        case .insufficientOverlap, .lowFeatureDensity, .lowLight: return 0.8
        case .motionBlur: return 0.6
        case .rescanRequired: return 0.3
        }
    }
    
    public func speakInstruction(text: String, priority: TTSPriority, category: String) {
        let now = Date().timeIntervalSince1970
        
        // Check cooldown
        if priority != .critical {
            if let lastTime = lastSpokenTimestamps[category], (now - lastTime) < cooldownSeconds {
                return // Suppress repetitive speech
            }
            if (now - lastAnySpeechTime) < minSilenceSeconds {
                return // Enforce pacing silence
            }
        }
        
        lastSpokenTimestamps[category] = now
        lastAnySpeechTime = now
        
        if priority == .critical && speechSynthesizer.isSpeaking {
            speechSynthesizer.stopSpeaking(at: .immediate)
        }
        
        let utterance = AVSpeechUtterance(string: text)
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        speechSynthesizer.speak(utterance)
    }
    
    @Published public var overallCoverageScore: Float = 0.0
    @Published public var floorCoverageScore: Float = 0.0
    @Published public var wallCoverageScore: Float = 0.0
    @Published public var isGatedComplete: Bool = false
    
    public func updateCoverage(overall: Float, floor: Float, walls: Float) {
        self.overallCoverageScore = min(1.0, max(0.0, overall))
        self.floorCoverageScore = min(1.0, max(0.0, floor))
        self.wallCoverageScore = min(1.0, max(0.0, walls))
        self.isGatedComplete = (overallCoverageScore >= 0.85 && floorCoverageScore >= 0.80 && wallCoverageScore >= 0.70)
    }
    
    public func verifyCompletionGate() -> (canComplete: Bool, defectMessage: String?) {
        if overallCoverageScore < 0.85 {
            let pct = Int(overallCoverageScore * 100)
            let msg = "Capture incomplete. Overall coverage is \(pct)%, required 85%."
            speakInstruction(text: "\(msg) Sweep unobserved areas before completing.", priority: .warning, category: "GATE_INCOMPLETE")
            activeWarning = "COVERAGE < 85%"
            return (false, msg)
        }
        if floorCoverageScore < 0.80 {
            let pct = Int(floorCoverageScore * 100)
            let msg = "Floor coverage is \(pct)%, required 80%. Tilt phone downward to scan floor."
            speakInstruction(text: msg, priority: .warning, category: "GATE_FLOOR")
            activeWarning = "SCAN FLOOR SURFACE"
            return (false, msg)
        }
        if wallCoverageScore < 0.70 {
            let pct = Int(wallCoverageScore * 100)
            let msg = "Wall coverage is \(pct)%, required 70%. Sweep perimeter walls."
            speakInstruction(text: msg, priority: .warning, category: "GATE_WALLS")
            activeWarning = "SCAN WALL SURFACES"
            return (false, msg)
        }
        return (true, nil)
    }

    public func evaluateTelemetry(
        velocityMps: Float,
        angularVelocityRadps: Float,
        blurScore: Float,
        ambientLux: Float,
        featureCount: Int,
        trackingLost: Bool
    ) {
        if trackingLost {
            speakInstruction(text: "Tracking lost. Aim camera toward previously scanned areas.", priority: .critical, category: "TRACKING_LOST")
            activeWarning = "TRACKING DEGRADED"
            return
        }
        
        // Translation baseline check: alert if user twists in place without translation baseline
        if velocityMps < 0.15 && angularVelocityRadps > 0.26 { // > 15 deg/s
            speakInstruction(text: "Walk sideways along room perimeter! Do not twist in place without translation baseline.", priority: .warning, category: "PURE_ROTATION")
            activeWarning = "TWISTING IN PLACE — WALK SIDEWAYS"
            qualityFeedback = QualityFeedback(
                level: .insufficientOverlap,
                title: "TRANSLATION BASELINE REQUIRED",
                correctiveAction: "Step sideways along perimeter instead of rotating in place"
            )
            return
        }
        
        if velocityMps > 0.8 || angularVelocityRadps > 1.2 {
            speakInstruction(text: "Slow down. Move camera more steadily.", priority: .warning, category: "EXCESSIVE_MOTION")
            activeWarning = "EXCESSIVE MOTION"
            return
        }
        
        if blurScore > 0.4 {
            speakInstruction(text: "Image blur detected. Hold camera steady.", priority: .warning, category: "BLUR")
            activeWarning = "BLUR DETECTED"
            return
        }
        
        if ambientLux < 30 {
            speakInstruction(text: "Lighting too low. Turn on room lights.", priority: .warning, category: "LOW_LIGHT")
            activeWarning = "LOW LIGHT"
            return
        }
        
        if featureCount < 80 {
            speakInstruction(text: "Low texture area. Frame more furniture or doorways.", priority: .guidance, category: "LOW_FEATURES")
            activeWarning = "LOW FEATURES"
            return
        }
        
        activeWarning = nil
    }
    
    public func advanceStage() {
        if currentStageIndex == sopStages.count - 1 {
            // Final stage: gate completion
            let gate = verifyCompletionGate()
            if !gate.canComplete {
                return // Block completion until gate passes
            }
            speakInstruction(text: "Scan complete! Space captured successfully.", priority: .confirmation, category: "STAGE_CONFIRM")
            return
        }
        
        if currentStageIndex < sopStages.count - 1 {
            let current = sopStages[currentStageIndex]
            speakInstruction(text: current.completionNotice, priority: .confirmation, category: "STAGE_CONFIRM")
            
            currentStageIndex += 1
            let next = sopStages[currentStageIndex]
            speakInstruction(text: next.guidance, priority: .guidance, category: "STAGE_GUIDE")
        }
    }
}

