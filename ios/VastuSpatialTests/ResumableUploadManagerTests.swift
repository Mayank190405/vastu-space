import XCTest
import CryptoKit
@testable import VastuSpatial

final class ResumableUploadManagerTests: XCTestCase {
    
    func testLocalChunkStateSerialization() throws {
        let chunk = LocalChunkState(
            chunkIndex: 0,
            startByte: 0,
            endByte: 5242879,
            sizeBytes: 5242880,
            checksumSha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            isUploaded: true,
            retryCount: 1,
            lastError: nil
        )
        
        let encoder = JSONEncoder()
        let data = try encoder.encode(chunk)
        
        let decoder = JSONDecoder()
        let decoded = try decoder.decode(LocalChunkState.self, from: data)
        
        XCTAssertEqual(decoded.chunkIndex, 0)
        XCTAssertEqual(decoded.startByte, 0)
        XCTAssertEqual(decoded.endByte, 5242879)
        XCTAssertEqual(decoded.sizeBytes, 5242880)
        XCTAssertEqual(decoded.checksumSha256, chunk.checksumSha256)
        XCTAssertTrue(decoded.isUploaded)
        XCTAssertEqual(decoded.retryCount, 1)
        XCTAssertNil(decoded.lastError)
    }
    
    func testLocalUploadTaskStateTransitions() throws {
        let chunks = [
            LocalChunkState(chunkIndex: 0, startByte: 0, endByte: 99, sizeBytes: 100, checksumSha256: "abc", isUploaded: true, retryCount: 0, lastError: nil),
            LocalChunkState(chunkIndex: 1, startByte: 100, endByte: 199, sizeBytes: 100, checksumSha256: "def", isUploaded: false, retryCount: 0, lastError: nil)
        ]
        
        var task = LocalUploadTask(
            id: "capture-uuid-1234",
            sessionId: "session-uuid-5678",
            filePath: "/tmp/sample.mp4",
            fileSizeBytes: 200,
            totalChunks: 2,
            chunks: chunks,
            status: "uploading",
            retryCount: 0,
            lastError: nil
        )
        
        XCTAssertEqual(task.status, "uploading")
        XCTAssertEqual(task.chunks.filter { $0.isUploaded }.count, 1)
        
        // Complete second chunk
        task.chunks[1].isUploaded = true
        task.status = "completed"
        
        let encoder = JSONEncoder()
        let data = try encoder.encode(task)
        let decoded = try JSONDecoder().decode(LocalUploadTask.self, from: data)
        
        XCTAssertEqual(decoded.status, "completed")
        XCTAssertEqual(decoded.chunks.filter { $0.isUploaded }.count, 2)
        XCTAssertEqual(decoded.sessionId, "session-uuid-5678")
    }
    
    func testChunkSizeAndCountCalculation() {
        let chunkSize: Int64 = 5 * 1024 * 1024 // 5MB
        
        // Exact multiple
        let exactSize: Int64 = 15 * 1024 * 1024 // 15MB
        let chunks1 = Int((exactSize + chunkSize - 1) / chunkSize)
        XCTAssertEqual(chunks1, 3)
        
        // Non-exact multiple
        let oddSize: Int64 = 16 * 1024 * 1024 // 16MB
        let chunks2 = Int((oddSize + chunkSize - 1) / chunkSize)
        XCTAssertEqual(chunks2, 4)
        
        // Small file < 1 chunk
        let smallSize: Int64 = 512 * 1024 // 512KB
        let chunks3 = Int((smallSize + chunkSize - 1) / chunkSize)
        XCTAssertEqual(chunks3, 1)
    }
}
