import SwiftUI

public struct CaptureValidationView: View {
    public let audit: CaptureQualityAudit
    public let packageURL: URL
    public let onProceedToUpload: () -> Void
    public let onRetake: () -> Void
    
    public init(
        audit: CaptureQualityAudit,
        packageURL: URL,
        onProceedToUpload: @escaping () -> Void,
        onRetake: @escaping () -> Void
    ) {
        self.audit = audit
        self.packageURL = packageURL
        self.onProceedToUpload = onProceedToUpload
        self.onRetake = onRetake
    }

    public var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollView {
                    VStack(spacing: 20) {
                        // Quality Gauge Header
                        VStack(spacing: 8) {
                            ZStack {
                                Circle()
                                    .stroke(lineWidth: 10)
                                    .opacity(0.2)
                                    .foregroundColor(audit.isAcceptableForReconstruction ? VastuColors.brandSuccess : VastuColors.brandWarning)
                                
                                Circle()
                                    .trim(from: 0.0, to: CGFloat(audit.overallScore))
                                    .stroke(style: StrokeStyle(lineWidth: 10, lineCap: .round, lineJoin: .round))
                                    .foregroundColor(audit.isAcceptableForReconstruction ? VastuColors.brandSuccess : VastuColors.brandWarning)
                                    .rotationEffect(.degrees(-90))
                                
                                VStack {
                                    Text("\(Int(audit.overallScore * 100))%")
                                        .font(.system(size: 28, weight: .bold, design: .monospaced))
                                        .foregroundColor(VastuColors.brandText)
                                    Text("QUALITY SCORE")
                                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                                        .foregroundColor(VastuColors.brandTextMuted)
                                }
                            }
                            .frame(width: 120, height: 120)
                            .padding(.top, 16)
                            
                            Text(audit.isAcceptableForReconstruction ? "Capture Validation Passed" : "Suboptimal Scan Quality")
                                .font(.system(size: 20, weight: .bold))
                                .foregroundColor(VastuColors.brandText)
                            
                            Text(audit.recommendationPrompt)
                                .font(.system(size: 13, weight: .medium))
                                .foregroundColor(VastuColors.brandTextMuted)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 20)
                        }
                        
                        // Verification Metrics Matrix Card
                        VStack(spacing: 12) {
                            metricRow(
                                title: "Camera Translation Baseline",
                                value: String(format: "%.2f m", audit.translationalBaselineM),
                                target: "Target ≥ 0.80 m",
                                isPass: audit.translationalBaselineM >= 0.40
                            )
                            Divider()
                            metricRow(
                                title: "Keyframes Recorded",
                                value: "\(audit.keyframeCount)",
                                target: "Target ≥ 16 frames",
                                isPass: audit.keyframeCount >= 12
                            )
                            Divider()
                            metricRow(
                                title: "Room Boundary Coverage",
                                value: "\(Int(audit.wallBoundaryCoveragePct))%",
                                target: "Target ≥ 70%",
                                isPass: audit.wallBoundaryCoveragePct >= 50.0
                            )
                            Divider()
                            metricRow(
                                title: "Hardware VIO Tracking Stability",
                                value: "\(Int(audit.trackingStabilityPct))%",
                                target: "Target ≥ 80%",
                                isPass: audit.trackingStabilityPct >= 75.0
                            )
                        }
                        .padding(16)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(14)
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                        
                        // Package Location & AirDrop Share
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Local Package Verified")
                                    .font(.system(size: 13, weight: .semibold))
                                    .foregroundColor(VastuColors.brandText)
                                Text(packageURL.lastPathComponent)
                                    .font(.system(size: 11, design: .monospaced))
                                    .foregroundColor(VastuColors.brandTextMuted)
                                    .lineLimit(1)
                            }
                            Spacer()
                            ShareLink(item: packageURL) {
                                Image(systemName: "square.and.arrow.up")
                                    .font(.system(size: 16))
                                    .foregroundColor(VastuColors.brandBronze)
                                    .padding(8)
                                    .background(VastuColors.brandBronze.opacity(0.12))
                                    .clipShape(Circle())
                            }
                        }
                        .padding(14)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(12)
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorderSubtle, lineWidth: 1))
                    }
                    .padding(.horizontal, 20)
                    .padding(.bottom, 20)
                }
                
                // Bottom CTAs
                VStack(spacing: 12) {
                    Button(action: onProceedToUpload) {
                        HStack(spacing: 8) {
                            Image(systemName: "arrow.up.circle.fill")
                                .font(.system(size: 18))
                            Text("Upload & Reconstruct 3D Room")
                        }
                    }
                    .buttonStyle(VastuPrimaryButtonStyle())
                    
                    Button("Retake / Rescan Room", action: onRetake)
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundColor(VastuColors.brandTextMuted)
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 16)
                .background(VastuColors.brandParchment)
            }
            .background(VastuColors.brandParchment.ignoresSafeArea())
            .navigationBarTitleDisplayMode(.inline)
        }
    }
    
    private func metricRow(title: String, value: String, target: String, isPass: Bool) -> some View {
        HStack {
            Image(systemName: isPass ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                .foregroundColor(isPass ? VastuColors.brandSuccess : VastuColors.brandWarning)
                .font(.system(size: 16))
            
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(VastuColors.brandText)
                Text(target)
                    .font(.system(size: 11))
                    .foregroundColor(VastuColors.brandTextMuted)
            }
            Spacer()
            Text(value)
                .font(.system(size: 14, weight: .bold, design: .monospaced))
                .foregroundColor(isPass ? VastuColors.brandText : VastuColors.brandWarning)
        }
    }
}

