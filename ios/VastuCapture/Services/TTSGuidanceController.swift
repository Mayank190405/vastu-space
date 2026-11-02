import Foundation
import AVFoundation

/// Offline-capable Text-to-Speech voice guidance assistant using Apple's AVSpeechSynthesizer (IOS-010)
public final class TTSGuidanceController: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {
    public static let shared = TTSGuidanceController()
    
    @Published public var isMuted: Bool = false
    @Published public var speechVolume: Float = 0.85
    @Published public var currentSpokenText: String = ""
    @Published public var isSpeaking: Bool = false
    
    private let synthesizer = AVSpeechSynthesizer()
    private var lastSpokenText: String = ""
    private var lastSpokenTime: Date = Date.distantPast
    
    // Cooldown intervals
    private let nonCriticalCooldownSeconds: TimeInterval = 6.0
    private let duplicateCooldownSeconds: TimeInterval = 12.0
    
    public override init() {
        super.init()
        synthesizer.delegate = self
        configureAudioSession()
    }
    
    private func configureAudioSession() {
        #if os(iOS)
        do {
            let session = AVAudioSession.sharedInstance()
            // .ambient allows speech to mix without stopping background processes or interrupting camera
            try session.setCategory(.ambient, options: [.duckOthers])
            try session.setActive(true)
        } catch {
            print("⚠️ TTS AudioSession configuration warning: \(error.localizedDescription)")
        }
        #endif
    }
    
    /// Schedules or immediately speaks an instruction according to priority rules
    public func speakInstruction(_ instruction: GuidanceInstruction) {
        guard !isMuted else { return }
        
        let now = Date()
        let isCritical = (instruction.severity == .alert)
        let isSameText = (instruction.text == lastSpokenText)
        let timeSinceLast = now.timeIntervalSince(lastSpokenTime)
        
        // Priority Rule: Critical tracking alerts interrupt immediately
        if isCritical {
            if isSpeaking {
                synthesizer.stopSpeaking(at: .immediate)
            }
            performSpeech(text: instruction.text, volume: speechVolume, rate: 0.52)
            lastSpokenText = instruction.text
            lastSpokenTime = now
            return
        }
        
        // Non-critical scheduling: check duplicate suppression and cooldown
        if isSameText && timeSinceLast < duplicateCooldownSeconds {
            return
        }
        if !isSameText && timeSinceLast < nonCriticalCooldownSeconds {
            return
        }
        if isSpeaking {
            return // Do not talk over an ongoing non-critical instruction
        }
        
        performSpeech(text: instruction.text, volume: speechVolume, rate: 0.50)
        lastSpokenText = instruction.text
        lastSpokenTime = now
    }
    
    private func performSpeech(text: String, volume: Float, rate: Float) {
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US") ?? AVSpeechSynthesisVoice(language: Locale.current.identifier)
        utterance.rate = rate
        utterance.volume = volume
        utterance.pitchMultiplier = 1.05
        
        self.currentSpokenText = text
        self.isSpeaking = true
        synthesizer.speak(utterance)
    }
    
    public func resetState() {
        stopSpeaking()
        lastSpokenText = ""
        lastSpokenTime = Date.distantPast
        isMuted = false
    }
    
    public func stopSpeaking() {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
        DispatchQueue.main.async {
            self.isSpeaking = false
            self.currentSpokenText = ""
        }
    }
    
    public func toggleMute() {
        isMuted.toggle()
        if isMuted {
            stopSpeaking()
        }
    }
    
    // MARK: - AVSpeechSynthesizerDelegate
    public func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        DispatchQueue.main.async {
            self.isSpeaking = false
        }
    }
    
    public func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didCancel utterance: AVSpeechUtterance) {
        DispatchQueue.main.async {
            self.isSpeaking = false
        }
    }
}
