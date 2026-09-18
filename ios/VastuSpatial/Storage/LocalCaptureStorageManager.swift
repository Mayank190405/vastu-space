import Foundation
import CryptoKit

public struct LocalCaptureRecord: Codable, Identifiable {
    public let id: String // captureId
    public let projectId: String
    public let name: String
    public let sessionDirPath: String
    public let videoFilePath: String
    public let imuFilePath: String
    public let manifestFilePath: String
    public let metadataFilePath: String
    public let fileSizeBytes: Int64
    public let checksumSha256: String
    public var status: String // pending_upload, uploading, uploaded, failed
    public var totalChunks: Int
    public var uploadedChunks: Int
    public var retryCount: Int
    public var lastError: String?
    public let createdAt: Date
    public var updatedAt: Date
}

public class LocalCaptureStorageManager: ObservableObject {
    public static let shared = LocalCaptureStorageManager()
    
    public let chunkSize: Int64 = 5 * 1024 * 1024 // 5MB chunks
    @Published public var captureRecords: [String: LocalCaptureRecord] = [:]
    
    private let storeFileURL: URL
    private let capturesDirectoryURL: URL
    
    public init() {
        let fileManager = FileManager.default
        let appSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? fileManager.temporaryDirectory
        self.capturesDirectoryURL = appSupport.appendingPathComponent("captures", isDirectory: true)
        self.storeFileURL = appSupport.appendingPathComponent("vastu_captures_store.json")
        
        try? fileManager.createDirectory(at: capturesDirectoryURL, withIntermediateDirectories: true)
        loadRecords()
    }
    
    public func createCaptureDirectory(captureId: String = UUID().uuidString) -> URL {
        let dir = capturesDirectoryURL.appendingPathComponent(captureId, isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }
    
    public func packageAndIndexCapture(
        captureId: String,
        projectId: String,
        sessionName: String,
        sessionDir: URL,
        videoURL: URL,
        imuURL: URL,
        manifestURL: URL,
        metadata: [String: String]
    ) async throws -> LocalCaptureRecord {
        let fileManager = FileManager.default
        let attributes = try fileManager.attributesOfItem(atPath: videoURL.path)
        let totalBytes = (attributes[.size] as? NSNumber)?.int64Value ?? 0
        let totalChunks = Int((totalBytes + chunkSize - 1) / chunkSize)
        let wholeFileChecksum = try calculateSha256(fileURL: videoURL)
        
        // 1. Write metadata.json
        let metadataURL = sessionDir.appendingPathComponent("metadata.json")
        let metadataData = try JSONEncoder().encode(metadata)
        try metadataData.write(to: metadataURL)
        
        // 2. Build Record
        let record = LocalCaptureRecord(
            id: captureId,
            projectId: projectId,
            name: sessionName,
            sessionDirPath: sessionDir.path,
            videoFilePath: videoURL.path,
            imuFilePath: imuURL.path,
            manifestFilePath: manifestURL.path,
            metadataFilePath: metadataURL.path,
            fileSizeBytes: totalBytes,
            checksumSha256: wholeFileChecksum,
            status: "pending_upload",
            totalChunks: max(1, totalChunks),
            uploadedChunks: 0,
            retryCount: 0,
            lastError: nil,
            createdAt: Date(),
            updatedAt: Date()
        )
        
        await MainActor.run {
            self.captureRecords[captureId] = record
            self.saveRecords()
        }
        
        return record
    }
    
    public func recoverInterruptedCaptures() {
        Task {
            for (_, record) in captureRecords where record.status == "pending_upload" || record.status == "uploading" {
                let videoURL = URL(fileURLWithPath: record.videoFilePath)
                if FileManager.default.fileExists(atPath: videoURL.path) {
                    ResumableUploadManager.shared.startUpload(captureId: record.id, fileURL: videoURL)
                }
            }
        }
    }
    
    public func purgeUploadedLocalCaptures(keepLastN: Int = 3) {
        let uploaded = captureRecords.values.filter { $0.status == "uploaded" }.sorted { $0.createdAt < $1.createdAt }
        if uploaded.count > keepLastN {
            let toDelete = uploaded.prefix(uploaded.count - keepLastN)
            for item in toDelete {
                let dir = URL(fileURLWithPath: item.sessionDirPath)
                try? FileManager.default.removeItem(at: dir)
                self.captureRecords.removeValue(forKey: item.id)
            }
            saveRecords()
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
    
    private func saveRecords() {
        if let data = try? JSONEncoder().encode(captureRecords) {
            try? data.write(to: storeFileURL)
        }
    }
    
    private func loadRecords() {
        if let data = try? Data(contentsOf: storeFileURL),
           let records = try? JSONDecoder().decode([String: LocalCaptureRecord].self, from: data) {
            self.captureRecords = records
        }
    }
}
