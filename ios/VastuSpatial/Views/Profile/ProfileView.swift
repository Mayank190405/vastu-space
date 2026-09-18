import SwiftUI
import ARKit
import CoreLocation

public struct ProfileView: View {
    @ObservedObject private var apiClient = VastuAPIClient.shared
    @Environment(\.presentationMode) var presentationMode
    
    @State private var copiedOrgCode: Bool = false
    @State private var isRefreshing: Bool = false
    @State private var showSignOutAlert: Bool = false
    
    // LiDAR & ARKit Hardware Detection
    private var isLidarAvailable: Bool {
        if #available(iOS 13.4, *) {
            return ARWorldTrackingConfiguration.supportsSceneReconstruction(.mesh)
        }
        return false
    }
    
    public init() {}
    
    public var body: some View {
        ZStack {
            VastuColors.brandParchment.ignoresSafeArea()
            
            VStack(spacing: 0) {
                // Header Bar
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("ACCOUNT & PROFILE")
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .tracking(2)
                            .foregroundColor(VastuColors.brandBronze)
                        Text("Spatial Identity")
                            .font(.system(size: 20, weight: .bold, design: .serif))
                            .foregroundColor(VastuColors.brandText)
                    }
                    
                    Spacer()
                    
                    Button(action: {
                        Task {
                            isRefreshing = true
                            _ = try? await apiClient.getMe()
                            _ = try? await apiClient.getMyOrg()
                            isRefreshing = false
                        }
                    }) {
                        Image(systemName: isRefreshing ? "arrow.triangle.2.circlepath" : "arrow.clockwise")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(VastuColors.brandBronze)
                            .padding(8)
                            .background(VastuColors.brandIvory)
                            .clipShape(Circle())
                            .overlay(Circle().stroke(VastuColors.brandBorder, lineWidth: 1))
                            .rotationEffect(.degrees(isRefreshing ? 360 : 0))
                            .animation(isRefreshing ? Animation.linear(duration: 1).repeatForever(autoreverses: false) : .default, value: isRefreshing)
                    }
                }
                .padding(.horizontal, 20)
                .padding(.top, 14)
                .padding(.bottom, 12)
                .background(VastuColors.brandIvory)
                
                Divider().background(VastuColors.brandBorder)
                
                ScrollView {
                    VStack(spacing: 16) {
                        
                        // User Profile Hero Card
                        VStack(spacing: 14) {
                            HStack(spacing: 16) {
                                // Monogram Avatar with Gold Glow
                                ZStack {
                                    Circle()
                                        .fill(VastuColors.brandParchment)
                                        .frame(width: 64, height: 64)
                                        .overlay(
                                            Circle()
                                                .stroke(VastuColors.brandBronze, lineWidth: 2)
                                        )
                                        .shadow(color: VastuColors.brandBronze.opacity(0.2), radius: 6, x: 0, y: 3)
                                    
                                    let initials = (apiClient.currentUser?.full_name?.split(separator: " ").compactMap { $0.first }.prefix(2).map(String.init).joined()) ?? "V"
                                    Text(initials.uppercased())
                                        .font(.system(size: 22, weight: .bold, design: .serif))
                                        .foregroundColor(VastuColors.brandBronze)
                                }
                                
                                VStack(alignment: .leading, spacing: 4) {
                                    HStack {
                                        Text(apiClient.currentUser?.full_name ?? "Authenticated User")
                                            .font(.system(size: 18, weight: .bold, design: .serif))
                                            .foregroundColor(VastuColors.brandText)
                                        
                                        Spacer()
                                        
                                        Text(apiClient.currentRole?.uppercased() ?? apiClient.currentUser?.role?.uppercased() ?? "ADMIN")
                                            .font(.system(size: 9, weight: .bold, design: .monospaced))
                                            .padding(.horizontal, 8)
                                            .padding(.vertical, 3)
                                            .background(VastuColors.brandBronze.opacity(0.12))
                                            .foregroundColor(VastuColors.brandBronze)
                                            .cornerRadius(6)
                                    }
                                    
                                    Text(apiClient.currentUser?.email ?? "No email linked")
                                        .font(.system(size: 13))
                                        .foregroundColor(VastuColors.brandTextMuted)
                                    
                                    if let phone = apiClient.currentUser?.phone, !phone.isEmpty {
                                        Text(phone)
                                            .font(.system(size: 12))
                                            .foregroundColor(VastuColors.brandTextMuted)
                                    }
                                }
                            }
                        }
                        .padding(18)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(16)
                        .overlay(
                            RoundedRectangle(cornerRadius: 16).stroke(VastuColors.brandBorder, lineWidth: 1)
                        )
                        .shadow(color: Color.black.opacity(0.02), radius: 6, x: 0, y: 3)
                        
                        // Active Organization Card
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Image(systemName: "building.2.fill")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(VastuColors.brandBronze)
                                Text("ACTIVE ORGANIZATION")
                                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                                    .tracking(1.5)
                                    .foregroundColor(VastuColors.brandTextMuted)
                                Spacer()
                            }
                            
                            if let org = apiClient.currentOrg {
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(org.name)
                                            .font(.system(size: 16, weight: .bold, design: .serif))
                                            .foregroundColor(VastuColors.brandText)
                                        if let businessType = org.business_type, !businessType.isEmpty {
                                            Text(businessType)
                                                .font(.system(size: 12))
                                                .foregroundColor(VastuColors.brandTextMuted)
                                        }
                                    }
                                    Spacer()
                                }
                                
                                if let orgCode = org.org_code, !orgCode.isEmpty {
                                    Divider().background(VastuColors.brandBorder)
                                    
                                    HStack {
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text("ORGANIZATION CODE")
                                                .font(.system(size: 9, weight: .bold, design: .monospaced))
                                                .foregroundColor(VastuColors.brandTextMuted)
                                            Text(orgCode)
                                                .font(.system(size: 13, weight: .bold, design: .monospaced))
                                                .foregroundColor(VastuColors.brandBronze)
                                        }
                                        
                                        Spacer()
                                        
                                        Button(action: {
                                            UIPasteboard.general.string = orgCode
                                            copiedOrgCode = true
                                            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                                copiedOrgCode = false
                                            }
                                        }) {
                                            HStack(spacing: 4) {
                                                Image(systemName: copiedOrgCode ? "checkmark" : "doc.on.doc")
                                                    .font(.system(size: 11, weight: .bold))
                                                Text(copiedOrgCode ? "Copied" : "Copy Code")
                                                    .font(.system(size: 11, weight: .bold))
                                            }
                                            .foregroundColor(VastuColors.brandBronze)
                                            .padding(.horizontal, 10)
                                            .padding(.vertical, 6)
                                            .background(VastuColors.brandParchment)
                                            .cornerRadius(8)
                                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(VastuColors.brandBorder, lineWidth: 1))
                                        }
                                    }
                                }
                            } else {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("Personal Workspace")
                                        .font(.system(size: 15, weight: .semibold, design: .serif))
                                        .foregroundColor(VastuColors.brandText)
                                    Text("Individual spatial mapping account")
                                        .font(.system(size: 12))
                                        .foregroundColor(VastuColors.brandTextMuted)
                                }
                                .padding(.vertical, 4)
                            }
                        }
                        .padding(18)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(16)
                        .overlay(
                            RoundedRectangle(cornerRadius: 16).stroke(VastuColors.brandBorder, lineWidth: 1)
                        )
                        
                        // Hardware & Spatial Capabilities
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Image(systemName: "sensor.tag.radiowaves.forward.fill")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(VastuColors.brandBronze)
                                Text("DEVICE SPATIAL HARDWARE")
                                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                                    .tracking(1.5)
                                    .foregroundColor(VastuColors.brandTextMuted)
                                Spacer()
                            }
                            
                            VStack(spacing: 10) {
                                CapabilityRow(
                                    icon: "dot.radiowaves.left.and.right",
                                    title: "LiDAR Depth Sensor",
                                    subtitle: isLidarAvailable ? "High-precision active optical time-of-flight" : "Standard visual odometry mode",
                                    isActive: isLidarAvailable
                                )
                                
                                Divider().background(VastuColors.brandBorder)
                                
                                CapabilityRow(
                                    icon: "cube.transparent",
                                    title: "ARKit 3D Mesh Engine",
                                    subtitle: "Sub-centimeter structural point cloud fusion",
                                    isActive: ARWorldTrackingConfiguration.isSupported
                                )
                                
                                Divider().background(VastuColors.brandBorder)
                                
                                CapabilityRow(
                                    icon: "location.fill",
                                    title: "GPS Geolocation Precision",
                                    subtitle: "WGS-84 real-world site anchor coordinates",
                                    isActive: CLLocationManager.locationServicesEnabled()
                                )
                                
                                Divider().background(VastuColors.brandBorder)
                                
                                CapabilityRow(
                                    icon: "gyroscope",
                                    title: "6-DOF IMU Motion Fusion",
                                    subtitle: "Hardware calibrated accelerometer & gyroscope",
                                    isActive: true
                                )
                            }
                        }
                        .padding(18)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(16)
                        .overlay(
                            RoundedRectangle(cornerRadius: 16).stroke(VastuColors.brandBorder, lineWidth: 1)
                        )
                        
                        // Cloud Sync & Control Plane
                        VStack(alignment: .leading, spacing: 10) {
                            HStack {
                                Image(systemName: "server.rack")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(VastuColors.brandBronze)
                                Text("CONTROL PLANE")
                                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                                    .tracking(1.5)
                                    .foregroundColor(VastuColors.brandTextMuted)
                                Spacer()
                                
                                HStack(spacing: 4) {
                                    Circle().fill(Color.green).frame(width: 6, height: 6)
                                    Text("Connected")
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(Color.green)
                                }
                            }
                            
                            Text(apiClient.baseURL)
                                .font(.system(size: 12, weight: .medium, design: .monospaced))
                                .foregroundColor(VastuColors.brandTextMuted)
                        }
                        .padding(16)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(14)
                        .overlay(
                            RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1)
                        )
                        
                        // Sign Out Button
                        Button(action: { showSignOutAlert = true }) {
                            HStack(spacing: 8) {
                                Image(systemName: "rectangle.portrait.and.arrow.right")
                                    .font(.system(size: 14, weight: .bold))
                                Text("Sign Out of VĀSTU Spatial")
                                    .font(.system(size: 14, weight: .bold))
                            }
                            .foregroundColor(Color.red.opacity(0.85))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(VastuColors.brandIvory)
                            .cornerRadius(12)
                            .overlay(
                                RoundedRectangle(cornerRadius: 12).stroke(Color.red.opacity(0.25), lineWidth: 1)
                            )
                        }
                        .padding(.top, 8)
                        
                        Spacer().frame(height: 40)
                    }
                    .padding(20)
                }
            }
        }
        .alert(isPresented: $showSignOutAlert) {
            Alert(
                title: Text("Sign Out"),
                message: Text("Are you sure you want to sign out? Your spatial scans saved locally will remain secure."),
                primaryButton: .destructive(Text("Sign Out")) {
                    apiClient.signOut()
                },
                secondaryButton: .cancel()
            )
        }
        .onAppear {
            Task {
                _ = try? await apiClient.getMe()
                _ = try? await apiClient.getMyOrg()
            }
        }
    }
}

// Supporting Capability Row
private struct CapabilityRow: View {
    let icon: String
    let title: String
    let subtitle: String
    let isActive: Bool
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 16))
                .foregroundColor(isActive ? VastuColors.brandBronze : VastuColors.brandTextMuted)
                .frame(width: 24)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(VastuColors.brandText)
                Text(subtitle)
                    .font(.system(size: 11))
                    .foregroundColor(VastuColors.brandTextMuted)
            }
            
            Spacer()
            
            Text(isActive ? "Active" : "N/A")
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundColor(isActive ? Color.green : VastuColors.brandTextMuted)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background((isActive ? Color.green : Color.gray).opacity(0.12))
                .cornerRadius(4)
        }
    }
}
