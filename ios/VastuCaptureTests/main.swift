import Foundation
import Darwin

let report = await VastuCaptureTestRunner.runAllTests()
if report.failed > 0 {
    Darwin.exit(1)
} else {
    Darwin.exit(0)
}
