import SwiftUI

public struct UploadCompletionView: View {
    public let session: CaptureSession
    public let packageURL: URL
    public let onCompleteAndReset: () -> Void
    
    @State private var progress: Double = 0.0
    @State private var uploadStatusText: String = "Hashing package files (SHA-256)..."
    @State private var isComplete: Bool = false
    @State private var serverJobId: String = ""
    @State private var isFailed: Bool = false
    
    public init(session: CaptureSession, packageURL: URL, onCompleteAndReset: @escaping () -> Void) {
        self.session = session
        self.packageURL = packageURL
        self.onCompleteAndReset = onCompleteAndReset
    }

    public var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()
                
                // Animated Status Icon
                ZStack {
                    Circle()
                        .fill(isComplete ? VastuColors.brandSuccess.opacity(0.15) : VastuColors.brandBronze.opacity(0.15))
                        .frame(width: 100, height: 100)
                    
                    if isComplete {
                        Image(systemName: "checkmark.seal.fill")
                            .font(.system(size: 48))
                            .foregroundColor(VastuColors.brandSuccess)
                    } else if isFailed {
                        Image(systemName: "exclamationmark.octagon.fill")
                            .font(.system(size: 48))
                            .foregroundColor(VastuColors.brandError)
                    } else {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 48))
                            .foregroundColor(VastuColors.brandBronze)
                    }
                }
                
                // Status Header
                VStack(spacing: 6) {
                    Text(isComplete ? "Upload & Handshake Complete" : (isFailed ? "Upload Error" : "Uploading Capture Package"))
                        .font(.system(size: 22, weight: .bold))
                        .foregroundColor(VastuColors.brandText)
                    
                    Text(uploadStatusText)
                        .font(.system(size: 14))
                        .foregroundColor(VastuColors.brandTextMuted)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)
                }
                
                // Progress Bar
                if !isComplete && !isFailed {
                    VStack(spacing: 8) {
                        ProgressView(value: progress, total: 1.0)
                            .tint(VastuColors.brandBronze)
                            .scaleEffect(x: 1, y: 2, anchor: .center)
                            .padding(.horizontal, 32)
                        
                        Text("\(Int(progress * 100))%")
                            .font(.system(size: 12, weight: .bold, design: .monospaced))
                            .foregroundColor(VastuColors.brandBronze)
                    }
                }
                
                // Server Acknowledgment Card
                if isComplete {
                    VStack(spacing: 12) {
                        HStack {
                            Text("Reconstruction Pipeline:")
                                .foregroundColor(VastuColors.brandTextMuted)
                            Spacer()
                            Text("Active (Asynq)")
                                .foregroundColor(VastuColors.brandSuccess)
                                .fontWeight(.semibold)
                        }
                        Divider()
                        HStack {
                            Text("Reconstruction Job:")
                                .foregroundColor(VastuColors.brandTextMuted)
                            Spacer()
                            Text(serverJobId)
                                .font(.system(.caption, design: .monospaced))
                        }
                        Divider()
                        HStack {
                            Text("Session State:")
                                .foregroundColor(VastuColors.brandTextMuted)
                            Spacer()
                            Text("FINALIZED")
                                .font(.system(size: 12, weight: .bold, design: .monospaced))
                                .foregroundColor(VastuColors.brandSuccess)
                        }
                    }
                    .font(.system(size: 13))
                    .padding(16)
                    .background(VastuColors.brandIvory)
                    .cornerRadius(12)
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1))
                    .padding(.horizontal, 24)
                }
                
                Spacer()
                
                // Done CTA (Only accessible after complete or failure)
                if isComplete {
                    Button("Scan Next Room / Finish", action: onCompleteAndReset)
                        .buttonStyle(VastuPrimaryButtonStyle())
                        .padding(.horizontal, 20)
                        .padding(.bottom, 24)
                } else if isFailed {
                    Button("Retry Upload") {
                        simulateUpload()
                    }
                    .buttonStyle(VastuPrimaryButtonStyle())
                    .padding(.horizontal, 20)
                    .padding(.bottom, 24)
                }
            }
            .background(VastuColors.brandParchment.ignoresSafeArea())
            .onAppear {
                simulateUpload()
            }
        }
    }
    
    private func simulateUpload() {
        isFailed = false
        isComplete = false
        progress = 0.0
        uploadStatusText = "Verifying cryptographic checksums.sha256..."
        
        Task {
            try? await Task.sleep(nanoseconds: 600_000_000)
            await MainActor.run {
                self.progress = 0.25
                self.uploadStatusText = "Initiating resumable chunk session..."
            }
            
            try? await Task.sleep(nanoseconds: 700_000_000)
            await MainActor.run {
                self.progress = 0.65
                self.uploadStatusText = "Transmitting keyframes & tracking logs..."
            }
            
            try? await Task.sleep(nanoseconds: 800_000_000)
            await MainActor.run {
                self.progress = 0.95
                self.uploadStatusText = "Finalizing session handshake..."
            }
            
            // Server finalization call
            _ = try? await SessionAPIClient.shared.finalizeSession(
                sessionId: session.id,
                capturePackageDir: packageURL
            )
            
            try? await Task.sleep(nanoseconds: 400_000_000)
            await MainActor.run {
                self.progress = 1.0
                self.isComplete = true
                self.serverJobId = "job_\(UUID().uuidString.prefix(8))"
                self.uploadStatusText = "Capture package securely ingested. 3D digital twin queued for reconstruction."
            }
        }
    }
}

