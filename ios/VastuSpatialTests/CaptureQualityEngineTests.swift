import XCTest
@testable import VastuSpatial

final class CaptureQualityEngineTests: XCTestCase {
    
    var engine: CaptureQualityEngine!
    
    override func setUp() {
        super.setUp()
        engine = CaptureQualityEngine()
    }
    
    override func tearDown() {
        engine = nil
        super.tearDown()
    }
    
    func testInitialState() {
        XCTAssertEqual(engine.currentSOPIndex, 0)
        XCTAssertEqual(engine.sopSteps.count, 12)
        XCTAssertEqual(engine.sopSteps.first?.title, "Start at Door")
        XCTAssertEqual(engine.sopSteps.last?.title, "Final Check")
        XCTAssertEqual(engine.getCoverageQualityScore(), 1.0)
    }
    
    func testSOPStepNavigation() {
        XCTAssertEqual(engine.currentSOPIndex, 0)
        
        // Cannot go below 0
        engine.previousSOPStep()
        XCTAssertEqual(engine.currentSOPIndex, 0)
        
        // Advance steps
        engine.nextSOPStep()
        XCTAssertEqual(engine.currentSOPIndex, 1)
        
        engine.nextSOPStep()
        XCTAssertEqual(engine.currentSOPIndex, 2)
        
        engine.previousSOPStep()
        XCTAssertEqual(engine.currentSOPIndex, 1)
        
        // Advance all the way to the end
        for _ in 0..<20 {
            engine.nextSOPStep()
        }
        XCTAssertEqual(engine.currentSOPIndex, engine.sopSteps.count - 1)
    }
    
    func testEvaluateMotion_MotionBlur() {
        // High rotational velocity: sqrt(1.5^2 + 1.0^2 + 0) = sqrt(3.25) ≈ 1.8 > 1.6
        engine.evaluateMotion(gyroX: 1.5, gyroY: 1.0, gyroZ: 0.0, accelX: 0.0, accelY: 0.0, accelZ: 1.0)
        
        let exp = expectation(description: "Wait for main queue update")
        DispatchQueue.main.async {
            XCTAssertEqual(self.engine.qualityFeedback.level, .motionBlur)
            XCTAssertTrue(self.engine.qualityFeedback.title.contains("MOTION BLUR"))
            exp.fulfill()
        }
        wait(for: [exp], timeout: 1.0)
        
        XCTAssertLessThan(engine.getCoverageQualityScore(), 1.0)
    }
    
    func testEvaluateMotion_InsufficientOverlap() {
        // High linear acceleration: linearAccel = sqrt(0^2 + 1.2^2 + 1.2^2) ≈ 1.69 > 1.4
        engine.evaluateMotion(gyroX: 0.1, gyroY: 0.1, gyroZ: 0.1, accelX: 0.0, accelY: 1.2, accelZ: 1.2)
        
        let exp = expectation(description: "Wait for main queue update")
        DispatchQueue.main.async {
            XCTAssertEqual(self.engine.qualityFeedback.level, .insufficientOverlap)
            XCTAssertTrue(self.engine.qualityFeedback.title.contains("INSUFFICIENT OVERLAP"))
            exp.fulfill()
        }
        wait(for: [exp], timeout: 1.0)
    }
    
    func testEvaluateMotion_LowFeatureDensity() {
        // Very low rotation and static gravity: rotationalVelocity < 0.02, linearAccel ≈ 1.0
        engine.evaluateMotion(gyroX: 0.005, gyroY: 0.005, gyroZ: 0.005, accelX: 0.0, accelY: 0.0, accelZ: 1.0)
        
        let exp = expectation(description: "Wait for main queue update")
        DispatchQueue.main.async {
            XCTAssertEqual(self.engine.qualityFeedback.level, .lowFeatureDensity)
            XCTAssertTrue(self.engine.qualityFeedback.title.contains("FEATURE POOR"))
            exp.fulfill()
        }
        wait(for: [exp], timeout: 1.0)
    }
    
    func testEvaluateMotion_Optimal() {
        // Moderate rotation and acceleration: walking pace
        engine.evaluateMotion(gyroX: 0.2, gyroY: 0.3, gyroZ: 0.1, accelX: 0.2, accelY: 0.3, accelZ: 0.95)
        
        let exp = expectation(description: "Wait for main queue update")
        DispatchQueue.main.async {
            XCTAssertEqual(self.engine.qualityFeedback.level, .optimal)
            XCTAssertTrue(self.engine.qualityFeedback.title.contains("EXCELLENT"))
            exp.fulfill()
        }
        wait(for: [exp], timeout: 1.0)
    }
}
