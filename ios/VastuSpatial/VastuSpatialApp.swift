import SwiftUI

@main
public struct VastuSpatialApp: App {
    @StateObject private var apiClient = VastuAPIClient.shared
    @StateObject private var storageManager = LocalCaptureStorageManager.shared
    
    public init() {
        // Recover interrupted / pending uploads on app launch
        LocalCaptureStorageManager.shared.recoverInterruptedCaptures()
        LocalCaptureStorageManager.shared.purgeUploadedLocalCaptures(keepLastN: 3)
        
        // Proactively request iOS sensor permissions on app launch
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            PermissionManager.shared.requestAllPermissions()
        }
    }
    
    @State private var showPreloader: Bool = true
    
    public var body: some Scene {
        WindowGroup {
            ZStack {
                VastuColors.brandParchment.ignoresSafeArea()
                
                if showPreloader {
                    VastuPreloaderView {
                        showPreloader = false
                    }
                } else if apiClient.isAuthenticated {
                    DashboardView()
                } else {
                    AuthView()
                }
            }
            .preferredColorScheme(.light)
            .onChange(of: apiClient.isAuthenticated) { _, isAuth in
                if isAuth {
                    showPreloader = true
                }
            }
        }
    }
}
