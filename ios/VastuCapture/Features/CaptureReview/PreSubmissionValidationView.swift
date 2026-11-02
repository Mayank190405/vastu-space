import SwiftUI

/// Pre-Submission Validation Screen enforcing mandatory 90% Quality Gate and Region Rescan Controls (IOS-014)
public struct PreSubmissionValidationView: View {
    public let audit: ComprehensiveCaptureAudit
    public let sessionId: String
    public let onProceedToUpload: () -> Void
    public let onTriggerRescan: (String) -> Void
    public let onCancel: () -> Void
    
    public init(
        audit: ComprehensiveCaptureAudit,
        sessionId: String,
        onProceedToUpload: @escaping () -> Void,
        onTriggerRescan: @escaping (String) -> Void,
        onCancel: @escaping () -> Void
    ) {
        self.audit = audit
        self.sessionId = sessionId
        self.onProceedToUpload = onProceedToUpload
        self.onTriggerRescan = onTriggerRescan
        self.onCancel = onCancel
    }
    
    public var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollView {
                    VStack(spacing: 20) {
                        // 1. Mandatory 90% Quality Gauge Header
                        qualityGaugeHeader
                        
                        // 2. Six-Factor Weighted Quality Scorecard (IOS-008)
                        weightedScorecard
                        
                        // 3. Actionable Region Issues & Targeted Rescan Actions (IOS-014)
                        if !audit.issues.isEmpty {
                            issuesSection
                        }
                        
                        // 4. Session Integrity & Dimensional Accuracy Disclaimer
                        integrityDisclaimer
                    }
                    .padding(20)
                }
                
                // Bottom CTAs
                bottomActionFooter
            }
            .background(Color(red: 0.04, green: 0.06, blue: 0.08).ignoresSafeArea())
            .navigationTitle("Quality Gate Audit")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close", action: onCancel)
                        .foregroundColor(.white)
                }
            }
        }
    }
    
    // MARK: - 1. Gauge Header
    private var qualityGaugeHeader: some View {
        let isPass = audit.submissionAllowed
        let color: Color = isPass ? .green : (audit.overallScore >= 70 ? .orange : .red)
        
        return VStack(spacing: 12) {
            ZStack {
                Circle()
                    .stroke(lineWidth: 12)
                    .opacity(0.15)
                    .foregroundColor(color)
                
                Circle()
                    .trim(from: 0.0, to: CGFloat(audit.overallScore / 100.0))
                    .stroke(style: StrokeStyle(lineWidth: 12, lineCap: .round))
                    .foregroundColor(color)
                    .rotationEffect(.degrees(-90))
                
                VStack(spacing: 2) {
                    Text("\(Int(audit.overallScore))%")
                        .font(.system(size: 32, weight: .black, design: .monospaced))
                        .foregroundColor(.white)
                    Text(isPass ? "VALIDATED (≥90%)" : "THRESHOLD: 90%")
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .foregroundColor(color)
                }
            }
            .frame(width: 140, height: 140)
            .padding(.top, 10)
            
            Text(isPass ? "Mandatory Quality Gate Passed" : "Capture Quality Below Mandatory 90%")
                .font(.system(size: 18, weight: .bold))
                .foregroundColor(.white)
            
            Text(audit.auditSummary)
                .font(.system(size: 13, weight: .medium))
                .foregroundColor(.white.opacity(0.75))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 16)
        }
        .padding(16)
        .frame(maxWidth: .infinity)
        .background(Color.white.opacity(0.04))
        .cornerRadius(16)
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(color.opacity(0.35), lineWidth: 1))
    }
    
    // MARK: - 2. Six-Factor Scorecard
    private var weightedScorecard: some View {
        VStack(spacing: 12) {
            HStack {
                Text("WEIGHTED AUDIT BREAKDOWN")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundColor(Color(red: 0.87, green: 0.72, blue: 0.45))
                Spacer()
                Text("TARGET ≥ 90%")
                    .font(.system(size: 10, weight: .heavy, design: .monospaced))
                    .foregroundColor(.white.opacity(0.6))
            }
            
            Divider().background(Color.white.opacity(0.12))
            
            categoryRow(
                title: "Spatial Surface Coverage",
                weight: "25%",
                score: audit.categoryScores.spatialSurfaceCoverage,
                targetMin: 80.0
            )
            categoryRow(
                title: "Camera Tracking Reliability",
                weight: "20%",
                score: audit.categoryScores.cameraTrackingReliability,
                targetMin: 85.0
            )
            categoryRow(
                title: "Multi-View Observation Quality",
                weight: "20%",
                score: audit.categoryScores.multiViewObservationQuality,
                targetMin: 80.0
            )
            categoryRow(
                title: "Depth & Geometry Consistency",
                weight: "20%",
                score: audit.categoryScores.depthAndGeometryConsistency,
                targetMin: 80.0
            )
            categoryRow(
                title: "Capture Sharpness & Exposure",
                weight: "10%",
                score: audit.categoryScores.captureSharpnessAndExposure,
                targetMin: 70.0
            )
            categoryRow(
                title: "Session Data Integrity",
                weight: "5%",
                score: audit.categoryScores.sessionDataIntegrity,
                targetMin: 90.0
            )
        }
        .padding(16)
        .background(Color.white.opacity(0.04))
        .cornerRadius(16)
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.white.opacity(0.10), lineWidth: 1))
    }
    
    // MARK: - 3. Issues & Rescan Actions
    private var issuesSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundColor(.orange)
                Text("IDENTIFIED REGION DEFECTS (\(audit.issues.count))")
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundColor(.white)
            }
            
            ForEach(audit.issues) { issue in
                HStack(alignment: .top, spacing: 12) {
                    Circle()
                        .fill(issue.severity == "high" ? Color.red : Color.orange)
                        .frame(width: 8, height: 8)
                        .padding(.top, 5)
                    
                    VStack(alignment: .leading, spacing: 3) {
                        HStack {
                            Text(issue.regionId.uppercased())
                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                .foregroundColor(.white)
                            Spacer()
                            Text(issue.severity.uppercased())
                                .font(.system(size: 9, weight: .bold, design: .monospaced))
                                .foregroundColor(issue.severity == "high" ? .red : .orange)
                        }
                        Text(issue.recommendedAction)
                            .font(.system(size: 12))
                            .foregroundColor(.white.opacity(0.8))
                    }
                    
                    Spacer()
                    
                    Button(action: {
                        onTriggerRescan(issue.regionId)
                    }) {
                        Text("Rescan")
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundColor(.black)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 5)
                            .background(Color.cyan)
                            .cornerRadius(6)
                    }
                }
                .padding(12)
                .background(Color.white.opacity(0.03))
                .cornerRadius(10)
            }
        }
        .padding(16)
        .background(Color.white.opacity(0.04))
        .cornerRadius(16)
    }
    
    // MARK: - 4. Disclaimer
    private var integrityDisclaimer: some View {
        HStack(spacing: 8) {
            Image(systemName: "info.circle")
                .foregroundColor(.white.opacity(0.5))
            Text("A descriptive quality score of 90% certifies capture completeness and multi-view coverage, not 90% geometric accuracy. Local capture files are preserved safely on device.")
                .font(.system(size: 10))
                .foregroundColor(.white.opacity(0.55))
        }
        .padding(.horizontal, 8)
    }
    
    // MARK: - 5. Bottom Action Footer
    private var bottomActionFooter: some View {
        VStack(spacing: 10) {
            // Submit Button: STRICTLY DISABLED IF BELOW 90% (IOS-008, IOS-014)
            Button(action: onProceedToUpload) {
                HStack(spacing: 8) {
                    Image(systemName: audit.submissionAllowed ? "arrow.up.circle.fill" : "lock.fill")
                        .font(.system(size: 16))
                    Text(audit.submissionAllowed ? "Upload & Reconstruct Room (Gate Passed)" : "Submit Locked — Score < 90/100")
                        .font(.system(size: 13, weight: .bold, design: .monospaced))
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(audit.submissionAllowed ? Color.green : Color.white.opacity(0.12))
                .foregroundColor(audit.submissionAllowed ? .black : .white.opacity(0.4))
                .cornerRadius(12)
            }
            .disabled(!audit.submissionAllowed)
            
            Button("Return to Capture & Rescan", action: onCancel)
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(.white.opacity(0.7))
        }
        .padding(16)
        .background(Color.black.opacity(0.92))
    }
    
    private func categoryRow(title: String, weight: String, score: Double, targetMin: Double) -> some View {
        let isPass = score >= targetMin
        return HStack {
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(title)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.white)
                    Text("(\(weight))")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(.white.opacity(0.5))
                }
            }
            Spacer()
            HStack(spacing: 8) {
                Text("\(Int(score))%")
                    .font(.system(size: 13, weight: .bold, design: .monospaced))
                    .foregroundColor(isPass ? .green : (score >= 60 ? .orange : .red))
                Image(systemName: isPass ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                    .foregroundColor(isPass ? .green : .orange)
                    .font(.system(size: 12))
            }
        }
    }
}

