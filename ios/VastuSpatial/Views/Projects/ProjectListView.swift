import SwiftUI

enum ProjectSortOption: String, CaseIterable {
    case recent = "Recent"
    case name = "Name"
    case status = "Status"
    case type = "Type"
}

public struct ProjectListView: View {
    @ObservedObject var apiClient = VastuAPIClient.shared
    @State private var projects: [ProjectDTO] = []
    @State private var isLoading: Bool = true
    
    // Project Creation State
    @State private var showCreateModal: Bool = false
    @State private var newProjectName: String = ""
    @State private var newProjectType: String = "Building"
    @State private var newProjectDesc: String = ""
    @State private var contactName: String = ""
    @State private var contactEmail: String = ""
    @State private var contactPhone: String = ""
    @State private var addressLine: String = ""
    @State private var city: String = ""
    @State private var state: String = ""
    @State private var pincode: String = ""
    @State private var floorConfigs: [CreateFloorDTO] = [
        CreateFloorDTO(name: "Ground Floor", floor_number: 0, floor_type: "Standard", area_value: 2400, area_unit: "SQFT", height_value: 10.5, height_unit: "FT", sequence: 0)
    ]
    @State private var createError: String?
    @State private var isSubmittingProject: Bool = false
    
    // Floor Selection State for Capture
    @State private var projectForCapture: ProjectDTO?
    @State private var availableFloors: [FloorDTO] = []
    @State private var isLoadingFloors: Bool = false
    @State private var showFloorPickerSheet: Bool = false
    @State private var activeCaptureSession: CaptureLaunchTarget?
    
    // Add Floor on the fly state
    @State private var showQuickAddFloor: Bool = false
    @State private var quickFloorName: String = ""
    
    // Enhanced Project Selection
    @State private var searchText: String = ""
    @State private var selectedProjectType: String = "All"
    @State private var selectedStatus: String = "All"
    @State private var sortBy: ProjectSortOption = .recent
    
    let supportedTypes = [
        "Building", "Mall", "Office", "Warehouse", "Hospital",
        "Hotel", "Campus", "Convention Centre", "Villa", "Apartment Complex"
    ]
    
    // Computed properties for filtering and sorting
    var filteredProjects: [ProjectDTO] {
        var result = projects
        
        // Filter by search text
        if !searchText.isEmpty {
            result = result.filter { project in
                project.name.localizedCaseInsensitiveContains(searchText) ||
                (project.projectType?.localizedCaseInsensitiveContains(searchText) ?? false) ||
                (project.location?.localizedCaseInsensitiveContains(searchText) ?? false)
            }
        }
        
        // Filter by project type
        if selectedProjectType != "All" {
            result = result.filter { $0.projectType == selectedProjectType }
        }
        
        // Filter by status
        if selectedStatus != "All" {
            result = result.filter { $0.status == selectedStatus }
        }
        
        // Sort
        switch sortBy {
        case .recent:
            result = result.sorted { $0.createdAt > $1.createdAt }
        case .name:
            result = result.sorted { $0.name < $1.name }
        case .status:
            result = result.sorted { $0.status ?? "" < $1.status ?? "" }
        case .type:
            result = result.sorted { $0.projectType ?? "" < $1.projectType ?? "" }
        }
        
        return result
    }
    
    public init() {}
    
    public var body: some View {
        NavigationView {
            ZStack {
                VastuColors.brandParchment.ignoresSafeArea()
                
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: VastuColors.brandBronze))
                        .scaleEffect(1.3)
                } else if filteredProjects.isEmpty && !searchText.isEmpty {
                    emptySearchStateView
                } else if projects.isEmpty {
                    emptyStateView
                } else {
                    VStack(spacing: 0) {
                        // Search and Filter Bar
                        searchAndFilterBar
                        
                        // Project List
                        ScrollView {
                            LazyVStack(spacing: 14) {
                                ForEach(filteredProjects) { project in
                                    ProjectCardView(project: project) {
                                        handleStartCapture(for: project)
                                    }
                                }
                            }
                            .padding(.horizontal, 16)
                            .padding(.top, 16)
                            .padding(.bottom, 30)
                        }
                    }
                }
            }
            .navigationTitle("Spatial Projects")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { showCreateModal = true }) {
                        HStack(spacing: 4) {
                            Image(systemName: "plus.circle.fill")
                            Text("New Project")
                                .font(.system(size: 13, weight: .semibold))
                        }
                        .foregroundColor(VastuColors.brandBronze)
                    }
                }
                
                ToolbarItem(placement: .navigationBarLeading) {
                    Button(action: { apiClient.signOut() }) {
                        Image(systemName: "rectangle.portrait.and.arrow.right")
                            .font(.system(size: 15))
                            .foregroundColor(VastuColors.brandTextMuted)
                    }
                }
            }
            .sheet(isPresented: $showCreateModal) {
                createProjectSheet
            }
            .sheet(isPresented: $showFloorPickerSheet) {
                floorSelectionSheet
            }
            .fullScreenCover(item: $activeCaptureSession) { target in
                CaptureView(project: target.project, floor: target.floor)
            }
            .onAppear(perform: loadProjects)
        }
    }
    
    // MARK: - Empty State View
    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "building.2.crop.circle")
                .font(.system(size: 56))
                .foregroundColor(VastuColors.brandBronze)
            
            Text("No Projects Yet")
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(VastuColors.brandText)
            
            Text("Create your first architectural project to begin scanning floors and spatial structures.")
                .font(.system(size: 14))
                .foregroundColor(VastuColors.brandTextMuted)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 36)
            
            Button(action: { showCreateModal = true }) {
                Text("Create First Project")
            }
            .buttonStyle(VastuGoldButtonStyle())
            .frame(width: 220)
            .padding(.top, 8)
        }
    }
    
    // MARK: - Floor Selection Sheet
    private var floorSelectionSheet: some View {
        NavigationView {
            ZStack {
                VastuColors.brandParchment.ignoresSafeArea()
                
                if isLoadingFloors {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: VastuColors.brandBronze))
                } else {
                    VStack(spacing: 16) {
                        if let proj = projectForCapture {
                            VStack(spacing: 4) {
                                Text(proj.name)
                                    .font(.system(size: 18, weight: .bold))
                                    .foregroundColor(VastuColors.brandText)
                                Text("Select the floor level you are scanning")
                                    .font(.system(size: 13))
                                    .foregroundColor(VastuColors.brandTextMuted)
                            }
                            .padding(.top, 16)
                        }
                        
                        if availableFloors.isEmpty {
                            VStack(spacing: 12) {
                                Text("No floors configured for this project.")
                                    .font(.system(size: 14))
                                    .foregroundColor(VastuColors.brandTextMuted)
                                
                                Button("Start Capture on Default Level") {
                                    if let p = projectForCapture {
                                        showFloorPickerSheet = false
                                        activeCaptureSession = CaptureLaunchTarget(project: p, floor: nil)
                                    }
                                }
                                .buttonStyle(VastuGoldButtonStyle())
                                .padding(.horizontal, 40)
                            }
                            .frame(maxHeight: .infinity)
                        } else {
                            List {
                                ForEach(availableFloors) { floor in
                                    Button(action: {
                                        if let p = projectForCapture {
                                            showFloorPickerSheet = false
                                            activeCaptureSession = CaptureLaunchTarget(project: p, floor: floor)
                                        }
                                    }) {
                                        HStack {
                                            VStack(alignment: .leading, spacing: 4) {
                                                Text(floor.name)
                                                    .font(.system(size: 16, weight: .bold))
                                                    .foregroundColor(VastuColors.brandText)
                                                HStack(spacing: 8) {
                                                    Text(floor.floor_type)
                                                        .font(.system(size: 11, weight: .semibold))
                                                        .foregroundColor(VastuColors.brandBronze)
                                                    if let area = floor.area_value {
                                                        Text("• \(Int(area)) \(floor.area_unit ?? "SQFT")")
                                                            .font(.system(size: 12))
                                                            .foregroundColor(VastuColors.brandTextMuted)
                                                    }
                                                }
                                            }
                                            Spacer()
                                            Image(systemName: "chevron.right")
                                                .font(.system(size: 14, weight: .semibold))
                                                .foregroundColor(VastuColors.brandBronze)
                                        }
                                        .padding(.vertical, 8)
                                    }
                                    .listRowBackground(VastuColors.brandIvory)
                                }
                            }
                            .listStyle(InsetGroupedListStyle())
                        }
                    }
                }
            }
            .navigationTitle("Select Floor")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Close") { showFloorPickerSheet = false }
                        .foregroundColor(VastuColors.brandBronze)
                }
            }
        }
    }
    
    // MARK: - Create Project Sheet
    private var createProjectSheet: some View {
        NavigationView {
            ZStack {
                VastuColors.brandParchment.ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: 16) {
                        VStack(spacing: 14) {
                            Text("Project Specifications")
                                .font(.system(size: 15, weight: .bold))
                                .foregroundColor(VastuColors.brandText)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            
                            customInput(label: "Project Name *", placeholder: "e.g. Prestige Tech Hub - Tower A", text: $newProjectName)
                            
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Structure / Project Type")
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundColor(VastuColors.brandText)
                                Picker("Project Type", selection: $newProjectType) {
                                    ForEach(supportedTypes, id: \.self) { t in
                                        Text(t).tag(t)
                                    }
                                }
                                .pickerStyle(MenuPickerStyle())
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color.white)
                                .cornerRadius(8)
                                .overlay(RoundedRectangle(cornerRadius: 8).stroke(VastuColors.brandBorder, lineWidth: 1))
                            }
                            
                            customInput(label: "Description (Optional)", placeholder: "Details regarding site & scope", text: $newProjectDesc)
                        }
                        .padding(18)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(14)
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                        
                        // Contact & Location Card
                        VStack(spacing: 14) {
                            Text("Location & Site Contact")
                                .font(.system(size: 15, weight: .bold))
                                .foregroundColor(VastuColors.brandText)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            
                            customInput(label: "Contact Person", placeholder: "Site Engineer / Lead", text: $contactName)
                            customInput(label: "Contact Mobile", placeholder: "+91 9876543210", text: $contactPhone, keyboardType: .phonePad)
                            customInput(label: "Contact Email", placeholder: "lead@acme.com", text: $contactEmail, keyboardType: .emailAddress)
                            customInput(label: "Street Address", placeholder: "Outer Ring Road, Kadubeesanahalli", text: $addressLine)
                            
                            HStack(spacing: 10) {
                                customInput(label: "City", placeholder: "Bengaluru", text: $city)
                                customInput(label: "State", placeholder: "Karnataka", text: $state)
                            }
                            customInput(label: "PIN Code", placeholder: "560103", text: $pincode, keyboardType: .numberPad)
                        }
                        .padding(18)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(14)
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                        
                        // Floors Configuration Card
                        VStack(spacing: 14) {
                            HStack {
                                Text("Floors / Levels (\(floorConfigs.count))")
                                    .font(.system(size: 15, weight: .bold))
                                    .foregroundColor(VastuColors.brandText)
                                Spacer()
                                Button(action: addFloorRow) {
                                    HStack(spacing: 4) {
                                        Image(systemName: "plus.circle.fill")
                                        Text("Add Floor")
                                            .font(.system(size: 12, weight: .bold))
                                    }
                                    .foregroundColor(VastuColors.brandBronze)
                                }
                            }
                            
                            ForEach(floorConfigs.indices, id: \.self) { idx in
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(floorConfigs[idx].name)
                                            .font(.system(size: 14, weight: .semibold))
                                            .foregroundColor(VastuColors.brandText)
                                        Text("\(floorConfigs[idx].floor_type) • \(Int(floorConfigs[idx].area_value)) \(floorConfigs[idx].area_unit)")
                                            .font(.system(size: 12))
                                            .foregroundColor(VastuColors.brandTextMuted)
                                    }
                                    Spacer()
                                    if floorConfigs.count > 1 {
                                        Button(action: { floorConfigs.remove(at: idx) }) {
                                            Image(systemName: "trash")
                                                .font(.system(size: 13))
                                                .foregroundColor(VastuColors.brandError)
                                        }
                                    }
                                }
                                .padding(10)
                                .background(Color.white)
                                .cornerRadius(8)
                                .overlay(RoundedRectangle(cornerRadius: 8).stroke(VastuColors.brandBorderSubtle, lineWidth: 1))
                            }
                        }
                        .padding(18)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(14)
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                        
                        if let err = createError {
                            Text(err)
                                .font(.system(size: 13))
                                .foregroundColor(VastuColors.brandError)
                                .multilineTextAlignment(.center)
                        }
                    }
                    .padding(16)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                
                // Pinned Bottom Action Footer
                VStack(spacing: 0) {
                    Divider().background(VastuColors.brandBorder)
                    
                    Button(action: handleCreateProject) {
                        if isSubmittingProject {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: VastuColors.brandIvory))
                        } else {
                            Text("Publish Project to Cloud")
                        }
                    }
                    .buttonStyle(VastuGoldButtonStyle())
                    .disabled(isSubmittingProject || newProjectName.trimmingCharacters(in: .whitespaces).isEmpty)
                    .padding(.horizontal, 20)
                    .padding(.top, 12)
                    .padding(.bottom, 6)
                }
                .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
            }
            .navigationTitle("New Project")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") { showCreateModal = false }
                        .foregroundColor(VastuColors.brandTextMuted)
                }
            }
        }
    }
    
    private func customInput(label: String, placeholder: String, text: Binding<String>, keyboardType: UIKeyboardType = .default) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(VastuColors.brandText)
            TextField(placeholder, text: text)
                .keyboardType(keyboardType)
                .autocapitalization(.none)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(Color.white)
                .foregroundColor(VastuColors.brandText)
                .cornerRadius(8)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(VastuColors.brandBorder, lineWidth: 1))
        }
    }
    
    private func addFloorRow() {
        let count = floorConfigs.count
        floorConfigs.append(
            CreateFloorDTO(
                name: "Floor \(count)",
                floor_number: count,
                floor_type: "Standard",
                area_value: 2400,
                area_unit: "SQFT",
                height_value: 10.5,
                height_unit: "FT",
                sequence: count
            )
        )
    }
    
    private func handleStartCapture(for project: ProjectDTO) {
        self.projectForCapture = project
        self.availableFloors = []
        self.isLoadingFloors = true
        self.showFloorPickerSheet = true
        
        Task {
            do {
                let floors = try await apiClient.getFloors(projectId: project.id)
                await MainActor.run {
                    self.availableFloors = floors
                    self.isLoadingFloors = false
                }
            } catch {
                await MainActor.run {
                    self.isLoadingFloors = false
                }
            }
        }
    }
    
    private func handleCreateProject() {
        createError = nil
        isSubmittingProject = true
        
        let addr = CreateAddressDTO(
            addressLine1: addressLine.isEmpty ? "Site Location" : addressLine,
            city: city.isEmpty ? "Bengaluru" : city,
            state: state.isEmpty ? "Karnataka" : state,
            pincode: pincode.isEmpty ? "560001" : pincode,
            country: "India"
        )
        
        let req = CreateProjectRequest(
            name: newProjectName.trimmingCharacters(in: .whitespaces),
            description: newProjectDesc.isEmpty ? nil : newProjectDesc,
            projectType: newProjectType,
            contactName: contactName.isEmpty ? "Site Lead" : contactName,
            contactPhone: contactPhone.isEmpty ? "+910000000000" : contactPhone,
            contactEmail: contactEmail.isEmpty ? "lead@project.internal" : contactEmail,
            address: addr,
            floors: floorConfigs
        )
        
        Task {
            do {
                _ = try await apiClient.createProject(request: req)
                await MainActor.run {
                    self.isSubmittingProject = false
                    self.showCreateModal = false
                    self.newProjectName = ""
                    self.newProjectDesc = ""
                    loadProjects()
                }
            } catch {
                await MainActor.run {
                    self.createError = error.localizedDescription
                    self.isSubmittingProject = false
                }
            }
        }
    }
    
    private func loadProjects() {
        isLoading = true
        Task {
            do {
                let list = try await apiClient.getProjects()
                await MainActor.run {
                    self.projects = list
                    self.isLoading = false
                }
            } catch {
                await MainActor.run {
                    self.isLoading = false
                }
            }
        }
    }
}

// Wrapper to pass both project & floor to CaptureView fullScreenCover
public struct CaptureLaunchTarget: Identifiable {
    public var id: String { "\(project.id)_\(floor?.id ?? "nofloor")" }
    public let project: ProjectDTO
    public let floor: FloorDTO?
}

// MARK: - Project Card View
struct ProjectCardView: View {
    let project: ProjectDTO
    let onCaptureTap: () -> Void
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(project.name)
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(VastuColors.brandText)
                    
                    if let pType = project.project_type {
                        Text(pType.uppercased())
                            .font(.system(size: 10, weight: .bold))
                            .tracking(1)
                            .foregroundColor(VastuColors.brandBronze)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(VastuColors.brandBronzeLight)
                            .cornerRadius(4)
                    }
                }
                
                Spacer()
                
                Button(action: onCaptureTap) {
                    HStack(spacing: 6) {
                        Image(systemName: "video.fill")
                            .font(.system(size: 12))
                        Text("Capture")
                            .font(.system(size: 13, weight: .bold))
                    }
                    .foregroundColor(VastuColors.brandIvory)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 8)
                    .background(VastuColors.brandBronze)
                    .cornerRadius(8)
                    .shadow(color: VastuColors.brandBronze.opacity(0.3), radius: 4, x: 0, y: 2)
                }
            }
            
            if let desc = project.description, !desc.isEmpty {
                Text(desc)
                    .font(.system(size: 13))
                    .foregroundColor(VastuColors.brandTextMuted)
                    .lineLimit(2)
            }
            
            HStack(spacing: 16) {
                if let floorCount = project.total_floors_count, floorCount > 0 {
                    HStack(spacing: 4) {
                        Image(systemName: "square.3.layers.3d")
                            .font(.system(size: 11))
                        Text("\(floorCount) Floors")
                            .font(.system(size: 12, weight: .medium))
                    }
                    .foregroundColor(VastuColors.brandTextMuted)
                }
                
                if let area = project.total_area_sqft, area > 0 {
                    HStack(spacing: 4) {
                        Image(systemName: "ruler")
                            .font(.system(size: 11))
                        Text("\(Int(area)) SQFT")
                            .font(.system(size: 12, weight: .medium))
                    }
                    .foregroundColor(VastuColors.brandTextMuted)
                }
            }
        }
        .padding(16)
        .background(VastuColors.brandIvory)
        .cornerRadius(14)
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(VastuColors.brandBorder, lineWidth: 1)
        )
        .shadow(color: Color.black.opacity(0.04), radius: 6, x: 0, y: 2)
    }
}

// MARK: - Enhanced Search and Filter Bar

extension ProjectListView {
    var searchAndFilterBar: some View {
        VStack(spacing: 12) {
            // Search Bar
            HStack {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 14))
                    .foregroundColor(VastuColors.brandTextMuted)
                
                TextField("Search projects...", text: $searchText)
                    .font(.system(size: 14))
                    .foregroundColor(VastuColors.brandText)
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
                
                if !searchText.isEmpty {
                    Button(action: { searchText = "" }) {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 16))
                            .foregroundColor(VastuColors.brandTextMuted)
                    }
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(VastuColors.brandIvory)
            .cornerRadius(10)
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(VastuColors.brandBorder, lineWidth: 1)
            )
            
            // Filter Chips
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    // Project Type Filter
                    FilterChip(
                        title: selectedProjectType,
                        options: ["All"] + supportedTypes,
                        onSelect: { selectedProjectType = $0 }
                    )
                    
                    // Status Filter
                    FilterChip(
                        title: selectedStatus,
                        options: ["All", "Ready", "Processing", "Completed"],
                        onSelect: { selectedStatus = $0 }
                    )
                    
                    // Sort Option
                    Menu {
                        ForEach(ProjectSortOption.allCases, id: \.self) { option in
                            Button(action: { sortBy = option }) {
                                HStack {
                                    Text(option.rawValue)
                                    if sortBy == option {
                                        Image(systemName: "checkmark")
                                    }
                                }
                            }
                        }
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "arrow.up.arrow.down")
                                .font(.system(size: 12))
                            Text(sortBy.rawValue)
                                .font(.system(size: 12, weight: .medium))
                        }
                        .foregroundColor(VastuColors.brandText)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(8)
                    }
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 8)
        .padding(.bottom, 12)
        .background(VastuColors.brandParchment)
    }
    
    var emptySearchStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 48))
                .foregroundColor(VastuColors.brandTextMuted.opacity(0.5))
            
            Text("No projects found")
                .font(.system(size: 18, weight: .semibold))
                .foregroundColor(VastuColors.brandText)
            
            Text("Try adjusting your search or filters")
                .font(.system(size: 14))
                .foregroundColor(VastuColors.brandTextMuted)
                .multilineTextAlignment(.center)
            
            Button(action: { 
                searchText = ""
                selectedProjectType = "All"
                selectedStatus = "All"
            }) {
                Text("Clear Filters")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(.white)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 10)
                    .background(VastuColors.brandBronze)
                    .cornerRadius(8)
            }
        }
        .padding(32)
    }
}

// MARK: - Filter Chip Component

struct FilterChip: View {
    let title: String
    let options: [String]
    let onSelect: (String) -> Void
    
    @State private var showMenu = false
    
    var body: some View {
        Menu {
            ForEach(options, id: \.self) { option in
                Button(action: { onSelect(option) }) {
                    HStack {
                        Text(option)
                        if title == option {
                            Image(systemName: "checkmark")
                        }
                    }
                }
            }
        } label: {
            HStack(spacing: 4) {
                Text(title)
                    .font(.system(size: 12, weight: .medium))
                Image(systemName: "chevron.down")
                    .font(.system(size: 10))
            }
            .foregroundColor(VastuColors.brandText)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(VastuColors.brandIvory)
            .cornerRadius(8)
        }
    }
}
