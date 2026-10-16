import SwiftUI

// ==========================================
// Screen 11: Home Dashboard (After Login)
// Matches the Exact Mockup Specification
// ==========================================

public struct DashboardView: View {
    @StateObject private var apiClient = VastuAPIClient.shared
    @State private var projects: [ProjectDTO] = []
    @State private var isLoading: Bool = true
    
    // Tab Navigation
    @State private var selectedTab: Int = 0 // 0: Home, 1: Projects, 2: Captures, 3: More
    
    // Org dropdown selector
    @State private var showOrgSelector: Bool = false
    
    // Navigation destinations
    @State private var showCreateProject: Bool = false
    @State private var selectedProjectForCapture: ProjectDTO?
    @State private var selectedFloorForCapture: FloorDTO?
    @State private var showFloorPicker: Bool = false
    @State private var availableFloors: [FloorDTO] = []
    @State private var isLoadingFloors: Bool = false
    
    // Team sheet
    @State private var activeTeamProject: ProjectDTO?
    @State private var projectMembers: [ProjectMemberDTO] = []
    @State private var orgMembers: [OrgMemberDTO] = []
    @State private var isLoadingTeam: Bool = false
    @State private var showTeamSheet: Bool = false
    @State private var showAddMemberSheet: Bool = false
    
    // QR Code Scanning
    @State private var showQRScanner: Bool = false
    
    public init() {}
    
    public var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Top App Bar
                HStack(spacing: 12) {
                    Button(action: {}) {
                        Image(systemName: "line.3.horizontal")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundColor(VastuColors.brandText)
                    }
                    
                    Spacer()
                    
                    // Org Switcher Pill
                    HStack(spacing: 6) {
                        Image(systemName: "building.2.fill")
                            .font(.system(size: 12))
                            .foregroundColor(VastuColors.brandBronze)
                        
                        Text(apiClient.currentOrg?.name ?? "Personal Workspace")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundColor(VastuColors.brandText)
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 7)
                    .background(VastuColors.brandIvory)
                    .cornerRadius(20)
                    .overlay(
                        RoundedRectangle(cornerRadius: 20)
                            .stroke(VastuColors.brandBorder, lineWidth: 1)
                    )
                    
                    Spacer()
                    
                    // QR Code Scanner Button
                    Button(action: { showQRScanner = true }) {
                        Image(systemName: "qrcode.viewfinder")
                            .font(.system(size: 17))
                            .foregroundColor(VastuColors.brandText)
                    }
                    
                    // Notification Bell with Badge
                    ZStack(alignment: .topTrailing) {
                        Button(action: {}) {
                            Image(systemName: "bell.fill")
                                .font(.system(size: 17))
                                .foregroundColor(VastuColors.brandText)
                        }
                        
                        Circle()
                            .fill(Color.red)
                            .frame(width: 14, height: 14)
                            .overlay(
                                Text("1")
                                    .font(.system(size: 8, weight: .bold))
                                    .foregroundColor(.white)
                            )
                            .offset(x: 4, y: -4)
                    }
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 12)
                .background(VastuColors.brandIvory)
                
                Divider().background(VastuColors.brandBorder)
                
                // Content Area
                if selectedTab == 3 {
                    ProfileView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    // Main Scrollable Body
                    ScrollView {
                        VStack(alignment: .leading, spacing: 18) {
                            // User Greeting
                            VStack(alignment: .leading, spacing: 2) {
                                Text("Good morning,")
                                    .font(.system(size: 13))
                                    .foregroundColor(VastuColors.brandTextMuted)
                                
                                Text(apiClient.currentUser?.full_name ?? "Architect")
                                    .font(.system(size: 22, weight: .bold, design: .serif))
                                    .foregroundColor(VastuColors.brandText)
                            }
                            .padding(.top, 8)
                            
                            // 4-Metric Grid (Dynamic Zero Fallback)
                            let totalProjects = projects.count
                            let totalFloors = projects.reduce(0) { $0 + ($1.total_floors_count ?? $1.floors?.count ?? 0) }
                            let processingCount = projects.filter { 
                                let st = ($0.status ?? "").lowercased()
                                return st == "processing" || st == "in_progress" || st == "capturing"
                            }.count
                            
                            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                                MetricBadgeCard(count: "\(totalProjects)", label: "Projects", icon: "doc.text.fill", color: VastuColors.brandBronze)
                                MetricBadgeCard(count: "\(totalFloors)", label: "Spaces", icon: "building.2.fill", color: VastuColors.brandBronze)
                                MetricBadgeCard(count: "\(totalFloors > 0 ? totalFloors : 0)", label: "Captures", icon: "video.fill", color: VastuColors.brandBronze)
                                MetricBadgeCard(count: "\(processingCount)", label: "Processing", icon: "person.2.fill", color: VastuColors.brandBronze)
                            }
                            
                            // Quick Action Hub
                            HStack(spacing: 12) {
                                Button(action: { showCreateProject = true }) {
                                    HStack(spacing: 6) {
                                        Image(systemName: "plus")
                                            .font(.system(size: 12, weight: .bold))
                                        Text("Create Project")
                                            .font(.system(size: 13, weight: .bold))
                                    }
                                    .foregroundColor(VastuColors.brandIvory)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 12)
                                    .background(VastuColors.brandBronze)
                                    .cornerRadius(12)
                                }
                                
                                Button(action: {
                                    if let p = projects.first {
                                        startCaptureForProject(p)
                                    } else {
                                        showCreateProject = true
                                    }
                                }) {
                                    HStack(spacing: 6) {
                                        Image(systemName: "video.fill")
                                            .font(.system(size: 12, weight: .bold))
                                        Text("Scan Space")
                                            .font(.system(size: 13, weight: .bold))
                                    }
                                    .foregroundColor(VastuColors.brandBronze)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 12)
                                    .background(VastuColors.brandIvory)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBronze, lineWidth: 1)
                                    )
                                    .cornerRadius(12)
                                }
                            }
                            
                            // Recent Projects Section Header
                            HStack {
                                Text("Recent Projects")
                                    .font(.system(size: 16, weight: .bold, design: .serif))
                                    .foregroundColor(VastuColors.brandText)
                                Spacer()
                                if !projects.isEmpty {
                                    Button("View All >") { }
                                        .font(.system(size: 12, weight: .bold))
                                        .foregroundColor(VastuColors.brandBronze)
                                }
                            }
                            .padding(.top, 4)
                            
                            // Live Real Projects (Zero Fallback)
                            if projects.isEmpty {
                                VStack(spacing: 12) {
                                    Image(systemName: "square.stack.3d.up.slash")
                                        .font(.system(size: 36))
                                        .foregroundColor(VastuColors.brandBronze.opacity(0.6))
                                    Text("No Spatial Projects Yet")
                                        .font(.system(size: 15, weight: .bold, design: .serif))
                                        .foregroundColor(VastuColors.brandText)
                                    Text("Create your first architectural project to upload floor plans and scan 3D spaces.")
                                        .font(.system(size: 12))
                                        .foregroundColor(VastuColors.brandTextMuted)
                                        .multilineTextAlignment(.center)
                                        .padding(.horizontal, 24)
                                    Button(action: { showCreateProject = true }) {
                                        Text("Create First Project")
                                            .font(.system(size: 12, weight: .bold))
                                            .foregroundColor(VastuColors.brandIvory)
                                            .padding(.horizontal, 16)
                                            .padding(.vertical, 8)
                                            .background(VastuColors.brandBronze)
                                            .cornerRadius(8)
                                    }
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 28)
                                .background(VastuColors.brandIvory)
                                .cornerRadius(14)
                                .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                            } else {
                                VStack(spacing: 12) {
                                    ForEach(projects) { p in
                                        ProjectListItemCard(
                                            title: p.name,
                                            location: p.project_type ?? "Commercial",
                                            status: p.status ?? "Ready",
                                            statusColor: VastuColors.brandBronze,
                                            icon: "square.stack.3d.up.fill",
                                            onTap: { startCaptureForProject(p) }
                                        )
                                    }
                                }
                            }
                        }
                        .padding(20)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
                
                // Bottom Tab Navigation Bar (Home, Projects, Captures, More)
                HStack(spacing: 0) {
                    BottomTabItem(title: "Home", icon: "house.fill", isSelected: selectedTab == 0) {
                        selectedTab = 0
                    }
                    BottomTabItem(title: "Projects", icon: "folder.fill", isSelected: selectedTab == 1) {
                        selectedTab = 1
                        showCreateProject = true
                    }
                    BottomTabItem(title: "Captures", icon: "camera.fill", isSelected: selectedTab == 2) {
                        selectedTab = 2
                        if let p = projects.first { startCaptureForProject(p) }
                    }
                    BottomTabItem(title: "More", icon: "ellipsis", isSelected: selectedTab == 3) {
                        selectedTab = 3
                    }
                }
                .padding(.top, 10)
                .padding(.bottom, 6)
                .frame(maxWidth: .infinity)
                .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
                .overlay(Rectangle().frame(height: 1).foregroundColor(VastuColors.brandBorder), alignment: .top)
            }
            .background(VastuColors.brandParchment.ignoresSafeArea())
            .navigationDestination(isPresented: $showCreateProject) {
                ProjectCreationWizardView(onProjectCreated: { created in
                    showCreateProject = false
                    Task { await loadProjects() }
                })
            }
            .navigationDestination(isPresented: Binding(
                get: { selectedProjectForCapture != nil },
                set: { if !$0 { selectedProjectForCapture = nil; selectedFloorForCapture = nil } }
            )) {
                if let proj = selectedProjectForCapture {
                    CaptureView(project: proj, floor: selectedFloorForCapture)
                }
            }
            .sheet(isPresented: $showFloorPicker) {
                FloorPickerSheet(
                    project: selectedProjectForCapture,
                    floors: availableFloors,
                    isLoading: isLoadingFloors,
                    onSelect: { floor in
                        selectedFloorForCapture = floor
                        showFloorPicker = false
                    }
                )
            }
            .sheet(isPresented: $showTeamSheet) {
                if let proj = activeTeamProject {
                    ProjectTeamSheet(
                        project: proj,
                        members: projectMembers,
                        orgMembers: orgMembers,
                        isLoading: isLoadingTeam,
                        onAddMember: { showAddMemberSheet = true },
                        onRemoveMember: { member in
                            Task {
                                try? await apiClient.removeProjectMember(projectId: proj.id, userId: member.user_id)
                                openTeamSheet(proj)
                            }
                        }
                    )
                }
            }
            .sheet(isPresented: $showAddMemberSheet) {
                if let proj = activeTeamProject {
                    AddMemberSheet(
                        project: proj,
                        orgMembers: orgMembers.filter { om in !projectMembers.contains { $0.user_id == om.user_id } },
                        onAssign: { userId, role in
                            Task {
                                try? await apiClient.addProjectMember(projectId: proj.id, request: AddProjectMemberRequest(userId: userId, projectRole: role))
                                showAddMemberSheet = false
                                openTeamSheet(proj)
                            }
                        }
                    )
                }
            }
            .sheet(isPresented: $showQRScanner) {
                QRScannerView { scannedCode in
                    handleQRCodeScanned(scannedCode)
                }
            }
        }
        .task {
            await loadProjects()
        }
    }
    
    private func loadProjects() async {
        isLoading = true
        do {
            projects = try await apiClient.getProjects()
        } catch {
            print("Failed to load projects: \(error)")
        }
        isLoading = false
    }
    
    private func startCaptureForProject(_ project: ProjectDTO) {
        selectedProjectForCapture = project
        availableFloors = []
        isLoadingFloors = true
        showFloorPicker = true
        Task {
            do {
                availableFloors = try await apiClient.getFloors(projectId: project.id)
            } catch {
                print("Failed to load floors: \(error)")
            }
            isLoadingFloors = false
        }
    }
    
    private func openTeamSheet(_ project: ProjectDTO) {
        activeTeamProject = project
        projectMembers = []
        isLoadingTeam = true
        showTeamSheet = true
        Task {
            do {
                projectMembers = try await apiClient.getProjectMembers(projectId: project.id)
                orgMembers = try await apiClient.getOrganizationMembers()
            } catch {
                print("Failed to load team: \(error)")
            }
            isLoadingTeam = false
        }
    }
    
    private func handleQRCodeScanned(_ code: String) {
        // Parse the QR code to extract session information
        // Expected format: "vastuspatial://capture/{sessionId}?projectId={projectId}"
        // Or session code: "V-{sessionId}"
        
        if code.hasPrefix("vastuspatial://capture/") {
            // Handle deep link format
            if let url = URL(string: code) {
                let sessionId = url.pathComponents.last
                let projectId = URLComponents(url: url, resolvingAgainstBaseURL: false)?
                    .queryItems?.first(where: { $0.name == "projectId" })?.value
                
                if let sessionId = sessionId, let projectId = projectId {
                    // Find the project and start capture
                    if let project = projects.first(where: { $0.id == projectId }) {
                        startCaptureForProject(project)
                    }
                }
            }
        } else if code.hasPrefix("V-") {
            // Handle session code format
            let sessionId = String(code.dropFirst(2))
            // In real implementation, validate session code with backend
            print("Session code scanned: \(sessionId)")
            // For now, just show alert
        }
    }
}

// ==========================================
// Dashboard Specific Subviews
// ==========================================

struct MetricBadgeCard: View {
    let count: String
    let label: String
    let icon: String
    let color: Color
    
    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 10)
                    .fill(VastuColors.brandParchment)
                    .frame(width: 40, height: 40)
                Image(systemName: icon)
                    .font(.system(size: 18))
                    .foregroundColor(color)
            }
            
            VStack(alignment: .leading, spacing: 1) {
                Text(count)
                    .font(.system(size: 18, weight: .bold, design: .serif))
                    .foregroundColor(VastuColors.brandText)
                Text(label)
                    .font(.system(size: 11))
                    .foregroundColor(VastuColors.brandTextMuted)
            }
            Spacer()
        }
        .padding(12)
        .background(VastuColors.brandIvory)
        .cornerRadius(12)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1))
    }
}

struct ProjectListItemCard: View {
    let title: String
    let location: String
    let status: String
    let statusColor: Color
    let icon: String
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                // Thumbnail image / icon
                ZStack {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(VastuColors.brandParchment)
                        .frame(width: 44, height: 44)
                    Image(systemName: icon)
                        .font(.system(size: 20))
                        .foregroundColor(VastuColors.brandBronze)
                }
                
                VStack(alignment: .leading, spacing: 3) {
                    Text(title)
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(VastuColors.brandText)
                    Text(location)
                        .font(.system(size: 11))
                        .foregroundColor(VastuColors.brandTextMuted)
                }
                
                Spacer()
                
                // Status pill
                HStack(spacing: 4) {
                    Circle().fill(statusColor).frame(width: 6, height: 6)
                    Text(status)
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(statusColor)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(statusColor.opacity(0.1))
                .cornerRadius(12)
            }
            .padding(12)
            .background(VastuColors.brandIvory)
            .cornerRadius(12)
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

struct BottomTabItem: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.system(size: 18))
                    .foregroundColor(isSelected ? VastuColors.brandBronze : VastuColors.brandTextMuted)
                Text(title)
                    .font(.system(size: 10, weight: isSelected ? .bold : .medium))
                    .foregroundColor(isSelected ? VastuColors.brandBronze : VastuColors.brandTextMuted)
            }
            .frame(maxWidth: .infinity)
        }
    }
}

// ==========================================
// Bottom Sheets
// ==========================================

struct FloorPickerSheet: View {
    let project: ProjectDTO?
    let floors: [FloorDTO]
    let isLoading: Bool
    let onSelect: (FloorDTO?) -> Void
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationStack {
            ZStack {
                VastuColors.brandParchment.ignoresSafeArea()
                
                VStack(spacing: 16) {
                    if isLoading {
                        ProgressView().tint(VastuColors.brandBronze)
                    } else if floors.isEmpty {
                        Text("No floors configured.")
                            .font(.system(size: 13))
                            .foregroundColor(VastuColors.brandTextMuted)
                        Button("Capture Default Space") { onSelect(nil) }
                            .buttonStyle(VastuGoldButtonStyle())
                    } else {
                        List(floors) { f in
                            Button(action: { onSelect(f) }) {
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(f.name)
                                            .font(.system(size: 14, weight: .bold))
                                            .foregroundColor(VastuColors.brandText)
                                        Text("\(f.floor_type) • \(Int(f.area_value ?? 2500)) SQFT")
                                            .font(.system(size: 11))
                                            .foregroundColor(VastuColors.brandTextMuted)
                                    }
                                    Spacer()
                                    Image(systemName: "video.fill")
                                        .foregroundColor(VastuColors.brandBronze)
                                }
                            }
                            .listRowBackground(VastuColors.brandIvory)
                        }
                        .scrollContentBackground(.hidden)
                    }
                }
                .padding(16)
            }
            .navigationTitle(project?.name ?? "Select Level")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .foregroundColor(VastuColors.brandTextMuted)
                }
            }
        }
    }
}

struct ProjectTeamSheet: View {
    let project: ProjectDTO
    let members: [ProjectMemberDTO]
    let orgMembers: [OrgMemberDTO]
    let isLoading: Bool
    let onAddMember: () -> Void
    let onRemoveMember: (ProjectMemberDTO) -> Void
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationStack {
            ZStack {
                VastuColors.brandParchment.ignoresSafeArea()
                
                VStack(spacing: 16) {
                    if isLoading {
                        ProgressView().tint(VastuColors.brandBronze)
                    } else if members.isEmpty {
                        VStack(spacing: 12) {
                            Text("No team members assigned.")
                                .font(.system(size: 13))
                                .foregroundColor(VastuColors.brandTextMuted)
                            Button("+ Assign First Member") { onAddMember() }
                                .buttonStyle(VastuGoldButtonStyle())
                        }
                        .padding(24)
                    } else {
                        List(members) { m in
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(m.user?.full_name ?? m.user?.email ?? "Collaborator")
                                        .font(.system(size: 13, weight: .bold))
                                        .foregroundColor(VastuColors.brandText)
                                    Text(m.user?.email ?? "")
                                        .font(.system(size: 11))
                                        .foregroundColor(VastuColors.brandTextMuted)
                                }
                                Spacer()
                                Text(m.project_role)
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(VastuColors.brandBronze)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(VastuColors.brandBronze.opacity(0.12))
                                    .cornerRadius(6)
                                
                                Button(action: { onRemoveMember(m) }) {
                                    Image(systemName: "xmark.circle.fill")
                                        .foregroundColor(.red.opacity(0.7))
                                        .font(.system(size: 16))
                                }
                                .buttonStyle(.plain)
                            }
                            .listRowBackground(VastuColors.brandIvory)
                        }
                        .scrollContentBackground(.hidden)
                    }
                }
            }
            .navigationTitle("\(project.name) — Team")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                        .foregroundColor(VastuColors.brandBronze)
                }
                ToolbarItem(placement: .primaryAction) {
                    Button(action: onAddMember) {
                        Image(systemName: "person.badge.plus")
                            .foregroundColor(VastuColors.brandBronze)
                    }
                }
            }
        }
    }
}

struct AddMemberSheet: View {
    let project: ProjectDTO
    let orgMembers: [OrgMemberDTO]
    let onAssign: (String, String) -> Void
    @Environment(\.dismiss) private var dismiss
    
    @State private var selectedUserId: String = ""
    @State private var selectedRole: String = "Member"
    
    var body: some View {
        NavigationStack {
            ZStack {
                VastuColors.brandParchment.ignoresSafeArea()
                
                Form {
                    Section("Select Organization Collaborator") {
                        if orgMembers.isEmpty {
                            Text("All organization members are assigned.")
                                .font(.system(size: 12))
                                .foregroundColor(VastuColors.brandTextMuted)
                        } else {
                            Picker("Collaborator", selection: $selectedUserId) {
                                Text("-- Choose Member --").tag("")
                                ForEach(orgMembers) { om in
                                    Text("\(om.user?.full_name ?? om.user?.email ?? "") (\(om.role))").tag(om.user_id)
                                }
                            }
                        }
                    }
                    
                    Section("Project Role") {
                        Picker("Role", selection: $selectedRole) {
                            Text("Manager").tag("Manager")
                            Text("Surveyor").tag("Surveyor")
                            Text("Member").tag("Member")
                            Text("Viewer").tag("Viewer")
                        }
                    }
                    
                    Section {
                        Button("Assign to Project") {
                            onAssign(selectedUserId, selectedRole)
                        }
                        .disabled(selectedUserId.isEmpty)
                        .buttonStyle(VastuGoldButtonStyle())
                    }
                    .listRowBackground(Color.clear)
                }
                .scrollContentBackground(.hidden)
            }
            .navigationTitle("Assign Team Member")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .foregroundColor(VastuColors.brandTextMuted)
                }
            }
        }
    }
}
