import SwiftUI

public enum NavigationStep {
    case qrScanner
    case sessionDetails(CaptureSession)
    case liveCapture(CaptureSession)
    case captureValidation(CaptureSession, URL, CaptureQualityAudit)
    case uploadCompletion(CaptureSession, URL)
}

public final class AppCoordinator: ObservableObject {
    @Published public var currentStep: NavigationStep = .qrScanner
    
    public init() {}
    
    public func resetToScanner() {
        SessionAuthorizationManager.shared.resetToScanner()
        currentStep = .qrScanner
    }
}

public struct AppCoordinatorView: View {
    @StateObject private var coordinator = AppCoordinator()
    @ObservedObject private var authManager = SessionAuthorizationManager.shared

    public init() {}

    public var body: some View {
        ZStack {
            VastuColors.brandParchment.ignoresSafeArea()
            
            switch coordinator.currentStep {
            case .qrScanner:
                QRScannerView { session in
                    withAnimation {
                        coordinator.currentStep = .sessionDetails(session)
                    }
                }
                
            case .sessionDetails(let session):
                SessionDetailsView(
                    session: session,
                    onStartCapture: {
                        withAnimation {
                            coordinator.currentStep = .liveCapture(session)
                        }
                    },
                    onCancel: {
                        withAnimation {
                            coordinator.resetToScanner()
                        }
                    }
                )
                
            case .liveCapture(let session):
                LiveSpatialCaptureView(
                    session: session,
                    onFinishCapture: { packageURL, audit in
                        authManager.stopRecordingForReview()
                        withAnimation {
                            coordinator.currentStep = .captureValidation(session, packageURL, audit)
                        }
                    },
                    onCancel: {
                        authManager.resetToScanner()
                        withAnimation {
                            coordinator.currentStep = .sessionDetails(session)
                        }
                    }
                )
                
            case .captureValidation(let session, let packageURL, let audit):
                CaptureValidationView(
                    audit: audit,
                    packageURL: packageURL,
                    onProceedToUpload: {
                        authManager.markUploading()
                        withAnimation {
                            coordinator.currentStep = .uploadCompletion(session, packageURL)
                        }
                    },
                    onRetake: {
                        withAnimation {
                            coordinator.currentStep = .liveCapture(session)
                        }
                    }
                )
                
            case .uploadCompletion(let session, let packageURL):
                UploadCompletionView(
                    session: session,
                    packageURL: packageURL,
                    onCompleteAndReset: {
                        authManager.completeSession()
                        withAnimation {
                            coordinator.resetToScanner()
                        }
                    }
                )
            }
        }
        .preferredColorScheme(.light)
        .onChange(of: authManager.state) { _, newState in
            if newState == .expired || newState == .revoked {
                withAnimation {
                    coordinator.currentStep = .qrScanner
                }
            }
        }
    }
}
