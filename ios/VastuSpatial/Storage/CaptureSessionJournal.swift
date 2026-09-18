import Foundation

public struct JournalEntry: Codable {
    public let event: String
    public let timestampNs: Int64
    public let payload: [String: String]
    
    public init(event: String, timestampNs: Int64 = Int64(Date().timeIntervalSince1970 * 1_000_000_000), payload: [String: String]) {
        self.event = event
        self.timestampNs = timestampNs
        self.payload = payload
    }
}

public class CaptureSessionJournal {
    public static let journalFilename = "session_journal.jsonl"
    private let journalURL: URL
    private let fileHandle: FileHandle?
    private let queue = DispatchQueue(label: "com.vastu.journal.queue")
    
    public init(sessionDir: URL) {
        self.journalURL = sessionDir.appendingPathComponent(Self.journalFilename)
        if !FileManager.default.fileExists(atPath: journalURL.path) {
            FileManager.default.createFile(atPath: journalURL.path, contents: nil)
        }
        self.fileHandle = try? FileHandle(forWritingTo: journalURL)
        self.fileHandle?.seekToEndOfFile()
    }
    
    deinit {
        try? fileHandle?.close()
    }
    
    public func logEvent(event: String, payload: [String: String]) {
        queue.async { [weak self] in
            guard let self = self, let handle = self.fileHandle else { return }
            let entry = JournalEntry(event: event, payload: payload)
            if let data = try? JSONEncoder().encode(entry),
               let line = String(data: data, encoding: .utf8)?.appending("\n"),
               let lineData = line.data(using: .utf8) {
                handle.write(lineData)
                try? handle.synchronize() // Force fsync to guarantee durability across crash/kill
            }
        }
    }
    
    public func readEvents() -> [JournalEntry] {
        guard let content = try? String(contentsOf: journalURL, encoding: .utf8) else { return [] }
        var entries: [JournalEntry] = []
        let lines = content.components(separatedBy: .newlines)
        for line in lines where !line.trimmingCharacters(in: .whitespaces).isEmpty {
            if let data = line.data(using: .utf8),
               let entry = try? JSONDecoder().decode(JournalEntry.self, from: data) {
                entries.append(entry)
            }
        }
        return entries
    }
}
