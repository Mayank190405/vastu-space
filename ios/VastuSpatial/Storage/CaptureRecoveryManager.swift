import Foundation

public struct RecoveryStatus {
    public let isInterrupted: Bool
    public let canResume: Bool
    public let lastSegmentIndex: Int
    public let lastFrameIndex: Int
    public let recordedEventsCount: Int
}

public class CaptureRecoveryManager {
    
    public static func analyzeSession(sessionDir: URL) -> RecoveryStatus {
        let journal = CaptureSessionJournal(sessionDir: sessionDir)
        let events = journal.readEvents()
        
        let hasStart = events.contains(where: { $0.event == "SESSION_START" })
        let hasEnd = events.contains(where: { $0.event == "SESSION_END" })
        
        var maxSegment = 0
        var maxFrame = 0
        
        for e in events {
            if e.event == "SEGMENT_START" || e.event == "SEGMENT_END" {
                if let segStr = e.payload["segment_index"], let seg = Int(segStr) {
                    maxSegment = max(maxSegment, seg)
                }
            }
            if e.event == "TELEMETRY_CHECKPOINT" {
                if let fStr = e.payload["last_frame_index"], let f = Int(fStr) {
                    maxFrame = max(maxFrame, f)
                }
            }
        }
        
        let isInterrupted = hasStart && !hasEnd
        return RecoveryStatus(
            isInterrupted: isInterrupted,
            canResume: isInterrupted,
            lastSegmentIndex: maxSegment,
            lastFrameIndex: maxFrame,
            recordedEventsCount: events.count
        )
    }
    
    public static func prepareResumption(sessionDir: URL) -> (nextSegmentIndex: Int, startFrameIndex: Int) {
        let status = analyzeSession(sessionDir: sessionDir)
        let journal = CaptureSessionJournal(sessionDir: sessionDir)
        
        let nextSeg = status.lastSegmentIndex + 1
        let nextFrame = status.lastFrameIndex + 1
        
        journal.logEvent(event: "RESUMPTION", payload: [
            "next_segment_index": String(nextSeg),
            "start_frame_index": String(nextFrame)
        ])
        
        return (nextSeg, nextFrame)
    }
}
