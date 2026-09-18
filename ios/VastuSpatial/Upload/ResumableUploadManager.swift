import Foundation
import CryptoKit
import Combine

public struct LocalChunkState: Codable {
    public let chunkIndex: Int
    public let startByte: Int64
    public let endByte: Int64
    public let sizeBytes: Int64
    public let checksumSha256: String
    public var isUploaded: Bool
    public var retryCount: Int
    public var lastError: String?
}

public struct LocalUploadTask: Codable, Identifiable {
    public let id: String // captureId
    public var sessionId: String?
    public let filePath: String
    public let fileSizeBytes: Int64
    public let totalChunks: Int
    public var chunks: [LocalChunkState]
    public var status: String // pending, uploading, completed, failed
    public var retryCount: Int
    public var lastError: String?
}

public class ResumableUploadManager: ObservableObject {
    public static let shared = ResumableUploadManager()
    
    public let chunkSize: Int64 = 5 * 1024 * 1024 // 5MB chunks
    @Published public var activeTasks: [String: LocalUploadTask] = [:]
    @Published public var uploadProgress: [String: Double] = [:]
    
    private let apiClient = VastuAPIClient.shared
    private let tasksFileURL: URL
    
    public init() {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory
        self.tasksFileURL = appSupport.appendingPathComponent("vastu_upload_tasks.json")
        loadTasks()
    }
    
    public func startUpload(captureId: String, fileURL: URL) {
        Task {
            do {
                guard FileManager.default.fileExists(atPath: fileURL.path) else { return }
                let attributes = try FileManager.default.attributesOfItem(atPath: fileURL.path)
                let fileSize = (attributes[.size] as? NSNumber)?.int64Value ?? 0
                guard fileSize > 0 else { return }
                
                let totalChunks = Int((fileSize + chunkSize - 1) / chunkSize)
                let wholeFileChecksum = try calculateSha256(fileURL: fileURL)
                
                // 1. Prepare Chunks
                var chunks: [LocalChunkState] = []
                for i in 0..<totalChunks {
                    let start = Int64(i) * chunkSize
                    let end = min(start + chunkSize - 1, fileSize - 1)
                    let size = end - start + 1
                    let chunkHash = try calculateChunkSha256(fileURL: fileURL, start: start, size: size)
                    chunks.append(LocalChunkState(
                        chunkIndex: i,
                        startByte: start,
                        endByte: end,
                        sizeBytes: size,
                        checksumSha256: chunkHash,
                        isUploaded: false,
                        retryCount: 0,
                        lastError: nil
                    ))
                }
                
                var task = LocalUploadTask(
                    id: captureId,
                    sessionId: nil,
                    filePath: fileURL.path,
                    fileSizeBytes: fileSize,
                    totalChunks: totalChunks,
                    chunks: chunks,
                    status: "pending",
                    retryCount: 0,
                    lastError: nil
                )
                
                // 2. Initialize Session
                let initReq = InitUploadRequest(
                    captureId: captureId,
                    fileName: fileURL.lastPathComponent,
                    fileType: "video",
                    fileSizeBytes: fileSize,
                    chunkSizeBytes: chunkSize,
                    totalChunks: totalChunks,
                    checksumSha256: wholeFileChecksum
                )
                
                let sessionDto = try await apiClient.initUploadSession(request: initReq)
                task.sessionId = sessionDto.id
                task.status = "uploading"
                
                await MainActor.run {
                    self.activeTasks[captureId] = task
                    self.saveTasks()
                }
                
                // 3. Upload Missing Chunks
                let fileHandle = try FileHandle(forReadingFrom: fileURL)
                defer { try? fileHandle.close() }
                
                var uploadedCount = 0
                for index in 0..<task.chunks.count {
                    if task.chunks[index].isUploaded {
                        uploadedCount += 1
                        continue
                    }
                    
                    let chunk = task.chunks[index]
                    try fileHandle.seek(toOffset: UInt64(chunk.startByte))
                    let chunkData = fileHandle.readData(ofLength: Int(chunk.sizeBytes))
                    let dynamicHash = SHA256.hash(data: chunkData).compactMap { String(format: "%02x", $0) }.joined()
                    
                    let contentRange = "bytes \(chunk.startByte)-\(chunk.endByte)/\(fileSize)"
                    
                    var chunkSuccess = false
                    var attempts = 0
                    let maxAttempts = 3
                    
                    while !chunkSuccess && attempts < maxAttempts {
                        attempts += 1
                        do {
                            try await apiClient.uploadChunk(
                                sessionId: sessionDto.id,
                                chunkIndex: chunk.chunkIndex,
                                contentRange: contentRange,
                                chunkChecksum: dynamicHash,
                                data: chunkData
                            )
                            chunkSuccess = true
                        } catch {
                            task.chunks[index].retryCount += 1
                            task.chunks[index].lastError = error.localizedDescription
                            try? await Task.sleep(nanoseconds: UInt64(attempts) * 1_000_000_000)
                        }
                    }
                    
                    if !chunkSuccess {
                        throw NSError(domain: "ResumableUpload", code: 500, userInfo: [NSLocalizedDescriptionKey: "Failed chunk \(chunk.chunkIndex) after \(maxAttempts) retries"])
                    }
                    
                    task.chunks[index].isUploaded = true
                    uploadedCount += 1
                    
                    let progress = Double(uploadedCount) / Double(totalChunks)
                    await MainActor.run {
                        self.activeTasks[captureId] = task
                        self.uploadProgress[captureId] = progress
                        self.saveTasks()
                    }
                }
                
                // 4. Finalize with Whole-File Checksum
                try await apiClient.completeUpload(
                    sessionId: sessionDto.id,
                    request: CompleteUploadRequest(finalChecksumSha256: wholeFileChecksum)
                )
                
                task.status = "completed"
                await MainActor.run {
                    self.activeTasks[captureId] = task
                    self.uploadProgress[captureId] = 1.0
                    self.saveTasks()
                }
                
            } catch {
                print("Error during resumable upload: \(error)")
                await MainActor.run {
                    if var t = self.activeTasks[captureId] {
                        t.status = "failed"
                        t.retryCount += 1
                        t.lastError = error.localizedDescription
                        self.activeTasks[captureId] = t
                        self.saveTasks()
                    }
                }
            }
        }
    }
    
    private func calculateSha256(fileURL: URL) throws -> String {
        let fileHandle = try FileHandle(forReadingFrom: fileURL)
        defer { try? fileHandle.close() }
        var hasher = SHA256()
        while autoreleasepool(invoking: {
            let nextChunk = fileHandle.readData(ofLength: 64 * 1024)
            guard !nextChunk.isEmpty else { return false }
            hasher.update(data: nextChunk)
            return true
        }) {}
        return hasher.finalize().compactMap { String(format: "%02x", $0) }.joined()
    }
    
    private func calculateChunkSha256(fileURL: URL, start: Int64, size: Int64) throws -> String {
        let fileHandle = try FileHandle(forReadingFrom: fileURL)
        defer { try? fileHandle.close() }
        try fileHandle.seek(toOffset: UInt64(start))
        var hasher = SHA256()
        var remaining = size
        while remaining > 0 {
            let toRead = min(Int(remaining), 64 * 1024)
            let data = fileHandle.readData(ofLength: toRead)
            if data.isEmpty { break }
            hasher.update(data: data)
            remaining -= Int64(data.count)
        }
        return hasher.finalize().compactMap { String(format: "%02x", $0) }.joined()
    }
    
    private func saveTasks() {
        if let data = try? JSONEncoder().encode(activeTasks) {
            try? data.write(to: tasksFileURL)
        }
    }
    
    private func loadTasks() {
        if let data = try? Data(contentsOf: tasksFileURL),
           let tasks = try? JSONDecoder().decode([String: LocalUploadTask].self, from: data) {
            self.activeTasks = tasks
        }
    }
}
