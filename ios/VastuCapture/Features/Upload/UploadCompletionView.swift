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
                            Text("Submitted")
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
                            Text("UPLOAD VERIFIED")
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
                        uploadCapture()
                    }
                    .buttonStyle(VastuPrimaryButtonStyle())
                    .padding(.horizontal, 20)
                    .padding(.bottom, 24)
                }
            }
            .background(VastuColors.brandParchment.ignoresSafeArea())
            .onAppear {
                uploadCapture()
            }
        }
    }
    
    private func uploadCapture() {
        isFailed = false
        isComplete = false
        progress = 0.0
        uploadStatusText = "Verifying cryptographic checksums.sha256..."
        
        Task {
            do {
                let jobID = try await SessionAPIClient.shared.uploadVideo(session: session, packageURL: packageURL) { value, message in
                    DispatchQueue.main.async { self.progress = value; self.uploadStatusText = message }
                }
                await MainActor.run {
                    self.serverJobId = jobID
                    self.progress = 1
                    self.isComplete = true
                    self.uploadStatusText = "Video verified in storage. Processing submitted. Monitor the dashboard for results."
                }
            } catch {
                await MainActor.run { self.isFailed = true; self.uploadStatusText = error.localizedDescription }
            }
        }
    }
}
