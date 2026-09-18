import XCTest
import AVFoundation
@testable import VastuSpatial

final class VideoValidatorTests: XCTestCase {
    
    private var tempDirectory: URL!
    
    override func setUp() {
        super.setUp()
        tempDirectory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try? FileManager.default.createDirectory(at: tempDirectory, withIntermediateDirectories: true)
    }
    
    override func tearDown() {
        if let tempDirectory = tempDirectory {
            try? FileManager.default.removeItem(at: tempDirectory)
        }
        super.tearDown()
    }
    
    func testValidateVideo_NonExistentFile() async {
        let dummyURL = tempDirectory.appendingPathComponent("missing_video.mp4")
        let result = await VideoValidator.validateVideo(fileURL: dummyURL)
        
        XCTAssertFalse(result.isValid)
        XCTAssertNotNil(result.errorMessage)
        XCTAssertTrue(result.errorMessage?.contains("does not exist") == true)
    }
    
    func testValidateVideo_TooSmallFile() async throws {
        let smallFileURL = tempDirectory.appendingPathComponent("tiny.mp4")
        let smallData = Data(repeating: 0x00, count: 1024) // 1KB < 100KB min
        try smallData.write(to: smallFileURL)
        
        let result = await VideoValidator.validateVideo(fileURL: smallFileURL)
        XCTAssertFalse(result.isValid)
        XCTAssertEqual(result.fileSizeBytes, 1024)
        XCTAssertTrue(result.errorMessage?.contains("too small") == true)
    }
    
    func testValidateVideo_CorruptedContainer() async throws {
        let corruptedURL = tempDirectory.appendingPathComponent("corrupted.mp4")
        // Size exceeds 100KB, but data is invalid video container
        let garbageData = Data(repeating: 0xFF, count: 150 * 1024)
        try garbageData.write(to: corruptedURL)
        
        let result = await VideoValidator.validateVideo(fileURL: corruptedURL)
        XCTAssertFalse(result.isValid)
        XCTAssertNotNil(result.errorMessage)
    }
}
