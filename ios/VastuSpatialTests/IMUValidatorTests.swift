import XCTest
@testable import VastuSpatial

final class IMUValidatorTests: XCTestCase {
    
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
    
    private func createTestIMUFile(named name: String, rows: [(timestampNs: Int64, ax: Double, ay: Double, az: Double, gx: Double, gy: Double, gz: Double)]) throws -> URL {
        let fileURL = tempDirectory.appendingPathComponent(name)
        var content = "timestamp_ns,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z\n"
        for row in rows {
            content += "\(row.timestampNs),\(row.ax),\(row.ay),\(row.az),\(row.gx),\(row.gy),\(row.gz)\n"
        }
        try content.write(to: fileURL, atomically: true, encoding: .utf8)
        return fileURL
    }
    
    func testValidateIMUFile_NonExistentFile() async {
        let dummyURL = tempDirectory.appendingPathComponent("non_existent.csv")
        let result = await IMUValidator.validateIMUFile(at: dummyURL)
        
        XCTAssertFalse(result.isValid)
        XCTAssertNotNil(result.errorMessage)
        XCTAssertTrue(result.errorMessage?.contains("does not exist") == true)
    }
    
    func testValidateIMUFile_EmptyFile() async throws {
        let fileURL = tempDirectory.appendingPathComponent("empty.csv")
        try "timestamp_ns,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z\n".write(to: fileURL, atomically: true, encoding: .utf8)
        
        let result = await IMUValidator.validateIMUFile(at: fileURL)
        XCTAssertFalse(result.isValid)
        XCTAssertTrue(result.errorMessage?.contains("empty") == true)
    }
    
    func testValidateIMUFile_ValidSamples() async throws {
        var rows: [(timestampNs: Int64, ax: Double, ay: Double, az: Double, gx: Double, gy: Double, gz: Double)] = []
        let baseTime: Int64 = 1_000_000_000
        let intervalNs: Int64 = 10_000_000 // 10ms = 100Hz
        
        for i in 0..<100 {
            let t = baseTime + Int64(i) * intervalNs
            rows.append((t, 0.0, 0.0, 9.81, 0.01, 0.02, -0.01))
        }
        
        let fileURL = try createTestIMUFile(named: "valid.csv", rows: rows)
        let result = await IMUValidator.validateIMUFile(at: fileURL)
        
        XCTAssertTrue(result.isValid)
        XCTAssertEqual(result.totalSamples, 100)
        XCTAssertTrue(result.isMonotonic)
        XCTAssertEqual(result.duplicateTimestampCount, 0)
        XCTAssertEqual(result.largeGapCount, 0)
        XCTAssertNil(result.errorMessage)
        XCTAssertGreaterThan(result.durationSeconds, 0.9)
        XCTAssertLessThan(result.durationSeconds, 1.1)
        XCTAssertGreaterThan(result.averageFrequencyHz, 90.0)
    }
    
    func testValidateIMUFile_InsufficientSamples() async throws {
        var rows: [(timestampNs: Int64, ax: Double, ay: Double, az: Double, gx: Double, gy: Double, gz: Double)] = []
        let baseTime: Int64 = 1_000_000_000
        for i in 0..<20 {
            rows.append((baseTime + Int64(i) * 10_000_000, 0, 0, 9.8, 0, 0, 0))
        }
        
        let fileURL = try createTestIMUFile(named: "short.csv", rows: rows)
        let result = await IMUValidator.validateIMUFile(at: fileURL)
        
        XCTAssertFalse(result.isValid)
        XCTAssertEqual(result.totalSamples, 20)
        XCTAssertTrue(result.errorMessage?.contains("Insufficient IMU samples") == true)
    }
    
    func testValidateIMUFile_NonMonotonicTimestamps() async throws {
        var rows: [(timestampNs: Int64, ax: Double, ay: Double, az: Double, gx: Double, gy: Double, gz: Double)] = []
        let baseTime: Int64 = 1_000_000_000
        for i in 0..<60 {
            var t = baseTime + Int64(i) * 10_000_000
            if i == 30 {
                t = baseTime + Int64(i - 5) * 10_000_000 // backward jump
            }
            rows.append((t, 0, 0, 9.8, 0, 0, 0))
        }
        
        let fileURL = try createTestIMUFile(named: "non_monotonic.csv", rows: rows)
        let result = await IMUValidator.validateIMUFile(at: fileURL)
        
        XCTAssertFalse(result.isValid)
        XCTAssertFalse(result.isMonotonic)
        XCTAssertTrue(result.errorMessage?.contains("non-monotonic") == true)
    }
    
    func testValidateIMUFile_WithDuplicateAndLargeGaps() async throws {
        var rows: [(timestampNs: Int64, ax: Double, ay: Double, az: Double, gx: Double, gy: Double, gz: Double)] = []
        var currentTime: Int64 = 1_000_000_000
        
        for i in 0..<60 {
            if i == 20 {
                // duplicate timestamp
            } else if i == 40 {
                currentTime += 60_000_000 // 60ms gap (> 50ms max allowable)
            } else {
                currentTime += 10_000_000
            }
            rows.append((currentTime, 0, 0, 9.8, 0, 0, 0))
        }
        
        let fileURL = try createTestIMUFile(named: "gaps.csv", rows: rows)
        let result = await IMUValidator.validateIMUFile(at: fileURL)
        
        XCTAssertTrue(result.isValid) // Still valid monotonic, but flags recorded
        XCTAssertEqual(result.duplicateTimestampCount, 1)
        XCTAssertEqual(result.largeGapCount, 1)
    }
}
