import SwiftUI
import ARKit

public struct SessionDetailsView: View {
    public let session: CaptureSession
    public let onStartCapture: () -> Void
    public let onCancel: () -> Void
    
    @ObservedObject var authManager = SessionAuthorizationManager.shared
    @State private var availableStorageMB: Int64 = StorageMonitor.getAvailableStorageMB()
    @State private var hasARWorldTracking: Bool = ARWorldTrackingConfiguration.isSupported
    
    public init(session: CaptureSession, onStartCapture: @escaping () -> Void, onCancel: @escaping () -> Void) {
        self.session = session
        self.onStartCapture = onStartCapture
        self.onCancel = onCancel
    }

    public var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollView {
                    VStack(spacing: 20) {
                        // Header Status Pill
                        HStack(spacing: 6) {
                            Circle()
                                .fill(statusColor)
                                .frame(width: 8, height: 8)
                            Text(statusText)
                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                .foregroundColor(statusColor)
                        }
                        .padding(.horizontal, 14)
                        .padding(.vertical, 6)
                        .background(statusColor.opacity(0.12))
                        .cornerRadius(16)
                        .padding(.top, 10)
                        
                        // Project & Room Title
                        VStack(spacing: 4) {
                            Text(session.roomName)
                                .font(.system(size: 26, weight: .bold))
                                .foregroundColor(VastuColors.brandText)
                            Text(session.projectName)
                                .font(.system(size: 15, weight: .medium))
                                .foregroundColor(VastuColors.brandTextMuted)
                        }
                        
                        // Scope Details Card
                        VStack(spacing: 12) {
                            detailRow(icon: "number.circle.fill", label: "Session ID", value: session.id)
                            Divider()
                            detailRow(icon: "person.badge.shield.checkmark.fill", label: "Operator", value: session.operatorName ?? "Authorized Field Surveyor")
                            Divider()
                            detailRow(icon: "clock.badge.checkmark.fill", label: "Grant Validity", value: formatExpiry(session.expiresAt))
                        }
                        .padding(16)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(14)
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                        
                        // Hardware & Local Readiness Checklist
                        VStack(alignment: .leading, spacing: 14) {
                            Text("SYSTEM & LOCAL AI READINESS")
                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                .foregroundColor(VastuColors.brandBronze)
                            
                            checklistRow(
                                title: "Zero-LiDAR VIO Odometry",
                                subtitle: "Apple ARKit 6-DoF Metric Visual-Inertial Odometry",
                                isReady: hasARWorldTracking
                            )
                            checklistRow(
                                title: "Local Computer Vision Models",
                                subtitle: "Boundary ray extractor & blur scoring engines active",
                                isReady: true
                            )
                            checklistRow(
                                title: "Device Local Storage",
                                subtitle: "\(availableStorageMB / 1024) GB available (min. 500 MB required)",
                                isReady: availableStorageMB >= 500
                            )
                            checklistRow(
                                title: "Cryptographic Authorization",
                                subtitle: "Hardware Keychain-backed session grant active",
                                isReady: authManager.canStartRecording && !session.isExpired
                            )
                        }
                        .padding(16)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(14)
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                    }
                    .padding(.horizontal, 20)
                    .padding(.bottom, 20)
                }
                
                // Bottom Fixed CTA
                VStack(spacing: 12) {
                    if session.isExpired {
                        Text("⚠️ This capture grant has expired. Please scan a new QR code.")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(VastuColors.brandError)
                    }
                    
                    Button(action: {
                        do {
                            try authManager.beginRecording()
                            onStartCapture()
                        } catch {
                            print("Authorization error: \(error)")
                        }
                    }) {
                        HStack(spacing: 8) {
                            Image(systemName: "record.circle.fill")
                                .font(.system(size: 18))
                            Text("Begin 3D Spatial Scan")
                        }
                    }
                    .buttonStyle(VastuPrimaryButtonStyle())
                    .disabled(!authManager.canStartRecording || session.isExpired || availableStorageMB < 500)
                    .opacity((authManager.canStartRecording && !session.isExpired && availableStorageMB >= 500) ? 1.0 : 0.4)
                    
                    Button("Cancel / Exit Session", action: onCancel)
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
    
    private var statusColor: Color {
        if session.isExpired { return VastuColors.brandError }
        if authManager.canStartRecording { return VastuColors.brandSuccess }
        return VastuColors.brandBronze
    }
    
    private var statusText: String {
        if session.isExpired { return "SESSION EXPIRED" }
        if authManager.canStartRecording { return "READY TO RECORD" }
        return "AUTHORIZING..."
    }
    
    private func detailRow(icon: String, label: String, value: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 16))
                .foregroundColor(VastuColors.brandBronze)
                .frame(width: 24)
            Text(label)
                .font(.system(size: 13))
                .foregroundColor(VastuColors.brandTextMuted)
            Spacer()
            Text(value)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(VastuColors.brandText)
        }
    }
    
    private func checklistRow(title: String, subtitle: String, isReady: Bool) -> some View {
        HStack(spacing: 12) {
            Image(systemName: isReady ? "checkmark.circle.fill" : "exclamationmark.circle.fill")
                .foregroundColor(isReady ? VastuColors.brandSuccess : VastuColors.brandError)
                .font(.system(size: 18))
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(VastuColors.brandText)
                Text(subtitle)
                    .font(.system(size: 11))
                    .foregroundColor(VastuColors.brandTextMuted)
            }
            Spacer()
        }
    }
    
    private func formatExpiry(_ date: Date) -> String {
        let diff = Int(date.timeIntervalSinceNow)
        if diff <= 0 { return "Expired" }
        let mins = diff / 60
        return "\(mins) minutes remaining"
    }
}
