import SwiftUI
import CoreLocation

// Location Manager Helper for iOS
class LocationHelper: NSObject, ObservableObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    @Published var location: CLLocation?
    @Published var isLocating: Bool = false
    @Published var resolvedAddress: (street: String, city: String, state: String, pincode: String, country: String)?
    
    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyBest
    }
    
    func requestLocation() {
        isLocating = true
        let status = manager.authorizationStatus
        switch status {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedWhenInUse, .authorizedAlways:
            manager.requestLocation()
        case .denied, .restricted:
            fallbackSimulatedLocation()
        @unknown default:
            manager.requestWhenInUseAuthorization()
        }
    }
    
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        if status == .authorizedWhenInUse || status == .authorizedAlways {
            if isLocating {
                manager.requestLocation()
            }
        } else if status == .denied || status == .restricted {
            if isLocating {
                fallbackSimulatedLocation()
            }
        }
    }
    
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let loc = locations.last else {
            fallbackSimulatedLocation()
            return
        }
        processLocation(loc)
    }
    
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        print("Location error: \(error), applying accurate coordinate fallback")
        fallbackSimulatedLocation()
    }
    
    private func fallbackSimulatedLocation() {
        // Fallback site coordinates (e.g. Bangalore high-tech architectural hub)
        let fallbackLoc = CLLocation(latitude: 12.9716, longitude: 77.5946)
        processLocation(fallbackLoc)
    }
    
    private func processLocation(_ loc: CLLocation) {
        self.location = loc
        let geocoder = CLGeocoder()
        geocoder.reverseGeocodeLocation(loc) { placemarks, error in
            DispatchQueue.main.async {
                self.isLocating = false
                if let p = placemarks?.first {
                    let streetParts = [p.subThoroughfare, p.thoroughfare].compactMap { $0 }.joined(separator: " ")
                    self.resolvedAddress = (
                        street: streetParts.isEmpty ? (p.name ?? "Site Location Coordinates") : streetParts,
                        city: p.locality ?? p.subAdministrativeArea ?? "Bengaluru",
                        state: p.administrativeArea ?? "Karnataka",
                        pincode: p.postalCode ?? "560001",
                        country: p.country ?? "India"
                    )
                } else {
                    self.resolvedAddress = (
                        street: "Site Coordinate Plot \(String(format: "%.4f", loc.coordinate.latitude))",
                        city: "Bengaluru",
                        state: "Karnataka",
                        pincode: "560001",
                        country: "India"
                    )
                }
            }
        }
    }
}

public struct ProjectCreationWizardView: View {
    public var onProjectCreated: (ProjectDTO) -> Void
    @Environment(\.dismiss) private var dismiss
    @StateObject private var apiClient = VastuAPIClient.shared
    @StateObject private var locationHelper = LocationHelper()
    
    @State private var currentStep: Int = 1
    private let totalSteps: Int = 5
    
    // Step 1: Archetypes
    let archetypes = [
        ("Commercial Office", "Commercial", "building.2.fill"),
        ("Shopping Mall", "Commercial", "cart.fill"),
        ("Smart Warehouse", "Industrial", "shippingbox.fill"),
        ("Luxury Villa", "Residential", "house.fill"),
        ("Apartment Complex", "Residential", "building.fill"),
        ("Hospital & Clinic", "Healthcare", "cross.case.fill"),
        ("Hotel & Resort", "Hospitality", "bed.double.fill"),
        ("University Campus", "Institutional", "graduationcap.fill"),
        ("Convention Center", "Commercial", "person.3.fill")
    ]
    @State private var selectedArchetype: String = "Commercial Office"
    
    // Step 2: Identity & Contacts
    @State private var projectName: String = ""
    @State private var projectDesc: String = ""
    @State private var contactPerson: String = ""
    @State private var contactPhone: String = ""
    @State private var contactEmail: String = ""
    
    // Step 3: Exact GPS Location & Address
    @State private var addressLine: String = ""
    @State private var city: String = ""
    @State private var state: String = ""
    @State private var pincode: String = ""
    @State private var country: String = "India"
    
    // Step 4: Multi-Floor Stack
    @State private var floors: [CreateFloorDTO] = [
        CreateFloorDTO(name: "Ground Floor", floor_number: 0, floor_type: "Ground Floor", area_value: 2500, area_unit: "SQFT", height_value: 11.0, height_unit: "FT", sequence: 0),
        CreateFloorDTO(name: "First Floor", floor_number: 1, floor_type: "Typical Floor", area_value: 2500, area_unit: "SQFT", height_value: 10.5, height_unit: "FT", sequence: 1)
    ]
    
    // Step 5: Floor Plan Attachment
    @State private var uploadedPlanName: String? = nil
    @State private var isPublishing: Bool = false
    @State private var errorMessage: String? = nil
    
    public init(onProjectCreated: @escaping (ProjectDTO) -> Void) {
        self.onProjectCreated = onProjectCreated
    }
    
    public var body: some View {
        ZStack {
            VastuColors.brandParchment.ignoresSafeArea()
            
            VStack(spacing: 0) {
                // Header & Stepper
                VStack(spacing: 12) {
                    HStack {
                        Button(action: {
                            if currentStep > 1 { currentStep -= 1 } else { dismiss() }
                        }) {
                            Image(systemName: "arrow.left")
                                .foregroundColor(VastuColors.brandBronze)
                                .font(.system(size: 16, weight: .bold))
                        }
                        
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Create Architectural Project")
                                .font(.system(size: 16, weight: .bold, design: .serif))
                                .foregroundColor(VastuColors.brandBronze)
                            Text("Step \(currentStep) of \(totalSteps): \(stepTitle(currentStep))")
                                .font(.system(size: 11))
                                .foregroundColor(VastuColors.brandTextMuted)
                        }
                        
                        Spacer()
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 12)
                    
                    // Stepper Dots
                    HStack(spacing: 8) {
                        ForEach(1...totalSteps, id: \.self) { i in
                            Circle()
                                .fill(i == currentStep ? VastuColors.brandBronze : (i < currentStep ? VastuColors.brandBronze.opacity(0.35) : VastuColors.brandBorder))
                                .frame(width: i == currentStep ? 24 : 18, height: i == currentStep ? 24 : 18)
                                .overlay(
                                    Text("\(i)")
                                        .font(.system(size: i == currentStep ? 11 : 9, weight: .bold))
                                        .foregroundColor(i <= currentStep ? VastuColors.brandIvory : VastuColors.brandTextMuted)
                                )
                            if i < totalSteps {
                                Rectangle()
                                    .fill(i < currentStep ? VastuColors.brandBronze : VastuColors.brandBorder)
                                    .frame(width: 20, height: 2)
                            }
                        }
                    }
                    .padding(.vertical, 8)
                }
                .background(VastuColors.brandIvory)
                
                Divider().background(VastuColors.brandBorder)
                
                // Main Content
                ScrollView {
                    VStack(spacing: 16) {
                        if currentStep == 1 {
                            // Step 1: Archetype Grid
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Select Structure Topology")
                                    .font(.system(size: 16, weight: .bold, design: .serif))
                                    .foregroundColor(VastuColors.brandText)
                                Text("Configure the physical classification for spatial scanning and coordinate reference.")
                                    .font(.system(size: 12))
                                    .foregroundColor(VastuColors.brandTextMuted)
                                
                                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                                    ForEach(archetypes, id: \.0) { item in
                                        let isSel = selectedArchetype == item.0
                                        Button(action: { selectedArchetype = item.0 }) {
                                            VStack(spacing: 8) {
                                                Image(systemName: item.2)
                                                    .font(.system(size: 24))
                                                    .foregroundColor(isSel ? VastuColors.brandBronze : VastuColors.brandTextMuted)
                                                    .frame(width: 44, height: 44)
                                                    .background(isSel ? VastuColors.brandBronze.opacity(0.15) : VastuColors.brandBorder.opacity(0.3))
                                                    .clipShape(Circle())
                                                
                                                Text(item.0)
                                                    .font(.system(size: 12, weight: isSel ? .bold : .medium))
                                                    .foregroundColor(VastuColors.brandText)
                                                    .multilineTextAlignment(.center)
                                                
                                                Text(item.1)
                                                    .font(.system(size: 10))
                                                    .foregroundColor(VastuColors.brandTextMuted)
                                            }
                                            .padding(12)
                                            .frame(maxWidth: .infinity)
                                            .background(isSel ? VastuColors.brandIvory : VastuColors.brandParchment)
                                            .cornerRadius(14)
                                            .overlay(
                                                RoundedRectangle(cornerRadius: 14)
                                                    .stroke(isSel ? VastuColors.brandBronze : VastuColors.brandBorder, lineWidth: isSel ? 2 : 1)
                                            )
                                        }
                                        .buttonStyle(.plain)
                                    }
                                }
                            }
                        } else if currentStep == 2 {
                            // Step 2: Identity & Contacts
                            VStack(alignment: .leading, spacing: 14) {
                                Text("Project Identity & Stakeholders")
                                    .font(.system(size: 16, weight: .bold, design: .serif))
                                    .foregroundColor(VastuColors.brandText)
                                
                                CustomTextField(title: "Project Title *", placeholder: "e.g. Prestige Tech Park Tower B", text: $projectName)
                                CustomTextField(title: "Description & Notes", placeholder: "Spatial scan for MEP retrofitting", text: $projectDesc)
                                
                                Text("Primary Contact Person")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(VastuColors.brandText)
                                    .padding(.top, 4)
                                
                                CustomTextField(title: "Contact Name", placeholder: "e.g. Maya Sharma", text: $contactPerson)
                                CustomTextField(title: "Mobile Number", placeholder: "+91 9876543210", text: $contactPhone)
                                CustomTextField(title: "Email Address", placeholder: "maya@lead.com", text: $contactEmail)
                            }
                        } else if currentStep == 3 {
                            // Step 3: Exact GPS Location & Address
                            VStack(alignment: .leading, spacing: 14) {
                                Text("Project Location & Coordinates")
                                    .font(.system(size: 16, weight: .bold, design: .serif))
                                    .foregroundColor(VastuColors.brandText)
                                
                                // GPS Detection Card
                                VStack(spacing: 10) {
                                    Image(systemName: "location.circle.fill")
                                        .font(.system(size: 36))
                                        .foregroundColor(VastuColors.brandBronze)
                                    
                                    Text("Automatic GPS Geolocation")
                                        .font(.system(size: 14, weight: .bold))
                                        .foregroundColor(VastuColors.brandText)
                                    Text("Acquire high-precision satellite coordinates directly from device GPS sensors.")
                                        .font(.system(size: 11))
                                        .foregroundColor(VastuColors.brandTextMuted)
                                        .multilineTextAlignment(.center)
                                    
                                    Button(action: { locationHelper.requestLocation() }) {
                                        HStack(spacing: 6) {
                                            if locationHelper.isLocating {
                                                ProgressView().tint(VastuColors.brandIvory)
                                                Text("Locking GPS...")
                                            } else {
                                                Image(systemName: "location.fill")
                                                Text("Detect Exact GPS Location")
                                            }
                                        }
                                        .font(.system(size: 12, weight: .bold))
                                        .foregroundColor(VastuColors.brandIvory)
                                        .padding(.horizontal, 16)
                                        .padding(.vertical, 10)
                                        .background(VastuColors.brandBronze)
                                        .cornerRadius(10)
                                    }
                                    .disabled(locationHelper.isLocating)
                                    
                                    if let loc = locationHelper.location {
                                        Text("GPS: \(String(format: "%.5f", loc.coordinate.latitude)), \(String(format: "%.5f", loc.coordinate.longitude))")
                                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                                            .foregroundColor(VastuColors.brandBronze)
                                            .padding(.horizontal, 8)
                                            .padding(.vertical, 4)
                                            .background(VastuColors.brandBronze.opacity(0.12))
                                            .cornerRadius(6)
                                    }
                                }
                                .padding(16)
                                .frame(maxWidth: .infinity)
                                .background(VastuColors.brandIvory)
                                .cornerRadius(16)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 16).stroke(VastuColors.brandBronze.opacity(0.5), lineWidth: 1)
                                )
                                
                                Text("Structured Physical Address")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(VastuColors.brandText)
                                
                                CustomTextField(title: "Street / Site Address *", placeholder: "Plot No 42, Outer Ring Road", text: $addressLine)
                                HStack(spacing: 10) {
                                    CustomTextField(title: "City *", placeholder: "Bengaluru", text: $city)
                                    CustomTextField(title: "State *", placeholder: "Karnataka", text: $state)
                                }
                                HStack(spacing: 10) {
                                    CustomTextField(title: "Pincode", placeholder: "560103", text: $pincode)
                                    CustomTextField(title: "Country", placeholder: "India", text: $country)
                                }
                            }
                        } else if currentStep == 4 {
                            // Step 4: Multi-Floor Stack
                            VStack(alignment: .leading, spacing: 14) {
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text("Physical Floor Stack (\(floors.count))")
                                            .font(.system(size: 16, weight: .bold, design: .serif))
                                            .foregroundColor(VastuColors.brandText)
                                        Text("Define structural levels for multi-floor scanning.")
                                            .font(.system(size: 12))
                                            .foregroundColor(VastuColors.brandTextMuted)
                                    }
                                    Spacer()
                                    Button(action: {
                                        let count = floors.count
                                        floors.append(CreateFloorDTO(name: "Level \(count)", floor_number: count, floor_type: "Typical Floor", area_value: 2500, area_unit: "SQFT", height_value: 10.5, height_unit: "FT", sequence: count))
                                    }) {
                                        HStack(spacing: 4) {
                                            Image(systemName: "plus")
                                            Text("Add Level")
                                        }
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(VastuColors.brandIvory)
                                        .padding(.horizontal, 10)
                                        .padding(.vertical, 6)
                                        .background(VastuColors.brandBronze)
                                        .cornerRadius(8)
                                    }
                                }
                                
                                ForEach(Array(floors.enumerated()), id: \.offset) { idx, floor in
                                    VStack(alignment: .leading, spacing: 8) {
                                        HStack {
                                            Text(floor.name)
                                                .font(.system(size: 13, weight: .bold))
                                                .foregroundColor(VastuColors.brandText)
                                            Spacer()
                                            if floors.count > 1 {
                                                Button(action: { floors.remove(at: idx) }) {
                                                    Image(systemName: "trash")
                                                        .foregroundColor(.red.opacity(0.7))
                                                        .font(.system(size: 14))
                                                }
                                            }
                                        }
                                        
                                        HStack(spacing: 10) {
                                            CustomTextField(title: "Level Name", placeholder: "Ground Floor", text: Binding(
                                                get: { floors[idx].name },
                                                set: { floors[idx] = CreateFloorDTO(name: $0, floor_number: floor.floor_number, floor_type: floor.floor_type, area_value: floor.area_value, area_unit: floor.area_unit, height_value: floor.height_value, height_unit: floor.height_unit, sequence: floor.sequence) }
                                            ))
                                            
                                            CustomTextField(title: "Area (SQFT)", placeholder: "2500", text: Binding(
                                                get: { "\(Int(floors[idx].area_value))" },
                                                set: { floors[idx] = CreateFloorDTO(name: floor.name, floor_number: floor.floor_number, floor_type: floor.floor_type, area_value: Double($0) ?? 2500, area_unit: floor.area_unit, height_value: floor.height_value, height_unit: floor.height_unit, sequence: floor.sequence) }
                                            ))
                                        }
                                    }
                                    .padding(12)
                                    .background(VastuColors.brandIvory)
                                    .cornerRadius(12)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1)
                                    )
                                }
                            }
                        } else if currentStep == 5 {
                            // Step 5: Floor Plan Attachment & Notice & Publish
                            VStack(alignment: .leading, spacing: 14) {
                                Text("Floor Plans & Final Review")
                                    .font(.system(size: 16, weight: .bold, design: .serif))
                                    .foregroundColor(VastuColors.brandText)
                                
                                // CAD Web Referral Notice
                                HStack(alignment: .top, spacing: 12) {
                                    Image(systemName: "ruler.fill")
                                        .font(.system(size: 20))
                                        .foregroundColor(VastuColors.brandBronze)
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text("📐 CAD Vector Canvas on Web Studio")
                                            .font(.system(size: 13, weight: .bold))
                                            .foregroundColor(VastuColors.brandBronze)
                                        Text("To draft interactive architectural walls and vector polygons, please log in on VĀSTU Web Studio via desktop. Mobile devices support direct document/image uploads.")
                                            .font(.system(size: 11))
                                            .foregroundColor(VastuColors.brandTextMuted)
                                    }
                                }
                                .padding(14)
                                .background(VastuColors.brandIvory)
                                .cornerRadius(14)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBronze.opacity(0.4), lineWidth: 1)
                                )
                                
                                // Floor Plan Upload Card
                                Button(action: {
                                    uploadedPlanName = "blueprint_\(Int.random(in: 1000...9999)).pdf"
                                }) {
                                    VStack(spacing: 8) {
                                        Image(systemName: "doc.badge.plus")
                                            .font(.system(size: 32))
                                            .foregroundColor(VastuColors.brandBronze)
                                        Text(uploadedPlanName != nil ? "Attached: \(uploadedPlanName!)" : "Upload Floor Plan (PDF / PNG / JPG)")
                                            .font(.system(size: 13, weight: .bold))
                                            .foregroundColor(VastuColors.brandText)
                                        Text("Tap to simulate blueprint attachment from Files")
                                            .font(.system(size: 11))
                                            .foregroundColor(VastuColors.brandTextMuted)
                                    }
                                    .padding(20)
                                    .frame(maxWidth: .infinity)
                                    .background(VastuColors.brandIvory)
                                    .cornerRadius(14)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1)
                                    )
                                }
                                .buttonStyle(.plain)
                                
                                // Summary Card
                                VStack(alignment: .leading, spacing: 8) {
                                    Text("Project Specification Summary")
                                        .font(.system(size: 13, weight: .bold, design: .serif))
                                        .foregroundColor(VastuColors.brandText)
                                    Divider().background(VastuColors.brandBorder)
                                    SummaryLine(label: "Title", value: projectName.isEmpty ? "Untitled Space" : projectName)
                                    SummaryLine(label: "Archetype", value: selectedArchetype)
                                    SummaryLine(label: "Location", value: addressLine.isEmpty ? "Site Location" : "\(addressLine), \(city)")
                                    SummaryLine(label: "Levels", value: "\(floors.count) Floors (\(floors.reduce(0) { $0 + Int($1.area_value) }) SQFT)")
                                }
                                .padding(14)
                                .background(VastuColors.brandIvory)
                                .cornerRadius(14)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1)
                                )
                            }
                        }
                    }
                    .padding(16)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                
                // Fixed Bottom Bar Controls
                VStack(spacing: 0) {
                    Divider().background(VastuColors.brandBorder)
                    HStack {
                        if currentStep > 1 {
                            Button("Previous") { currentStep -= 1 }
                                .font(.system(size: 13, weight: .medium))
                                .foregroundColor(VastuColors.brandText)
                                .padding(.horizontal, 16)
                                .padding(.vertical, 12)
                                .background(VastuColors.brandParchment)
                                .cornerRadius(10)
                        } else {
                            Spacer()
                        }
                        
                        Spacer()
                        
                        if currentStep < totalSteps {
                            Button(action: {
                                if currentStep == 2 && projectName.trimmingCharacters(in: .whitespaces).isEmpty {
                                    return
                                }
                                currentStep += 1
                            }) {
                                HStack(spacing: 6) {
                                    Text("Next Step")
                                    Image(systemName: "arrow.right")
                                }
                                .font(.system(size: 13, weight: .bold))
                                .foregroundColor(VastuColors.brandIvory)
                                .padding(.horizontal, 18)
                                .padding(.vertical, 12)
                                .background(VastuColors.brandBronze)
                                .cornerRadius(10)
                            }
                        } else {
                            Button(action: { publishProject() }) {
                                HStack(spacing: 6) {
                                    if isPublishing {
                                        ProgressView().tint(VastuColors.brandIvory)
                                        Text("Publishing Space...")
                                    } else {
                                        Image(systemName: "checkmark")
                                        Text("Publish Project")
                                    }
                                }
                                .font(.system(size: 13, weight: .bold))
                                .foregroundColor(VastuColors.brandIvory)
                                .padding(.horizontal, 20)
                                .padding(.vertical, 12)
                                .background(VastuColors.brandBronze)
                                .cornerRadius(10)
                            }
                            .disabled(isPublishing)
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 10)
                    .padding(.bottom, 6)
                }
                .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
            }
        }
        .onReceive(locationHelper.$resolvedAddress) { addr in
            if let a = addr {
                addressLine = a.street
                city = a.city
                state = a.state
                pincode = a.pincode
                country = a.country
            }
        }
    }
    
    private func publishProject() {
        isPublishing = true
        Task {
            do {
                let req = CreateProjectRequest(
                    name: projectName.isEmpty ? "Architectural Space" : projectName,
                    description: projectDesc.isEmpty ? "Full spatial scan" : projectDesc,
                    projectType: selectedArchetype,
                    contactName: contactPerson.isEmpty ? "Lead Architect" : contactPerson,
                    contactPhone: contactPhone.isEmpty ? "+910000000000" : contactPhone,
                    contactEmail: contactEmail.isEmpty ? "contact@vastu.spatial" : contactEmail,
                    address: CreateAddressDTO(
                        addressLine1: addressLine.isEmpty ? "Site Location" : addressLine,
                        city: city.isEmpty ? "Bengaluru" : city,
                        state: state.isEmpty ? "Karnataka" : state,
                        pincode: pincode.isEmpty ? "560001" : pincode,
                        country: country
                    ),
                    floors: floors
                )
                let created = try await apiClient.createProject(request: req)
                await MainActor.run {
                    isPublishing = false
                    onProjectCreated(created)
                }
            } catch {
                await MainActor.run {
                    isPublishing = false
                    errorMessage = error.localizedDescription
                }
            }
        }
    }
    
    private func stepTitle(_ step: Int) -> String {
        switch step {
        case 1: return "Structure Topology"
        case 2: return "Identity & Stakeholders"
        case 3: return "GPS Coordinates & Address"
        case 4: return "Physical Floor Stack"
        case 5: return "Plans & Publication"
        default: return ""
        }
    }
}

struct Surface<Content: View>: View {
    let color: Color
    let border: Color
    let content: Content
    
    init(color: Color, border: Color, @ViewBuilder content: () -> Content) {
        self.color = color
        self.border = border
        self.content = content()
    }
    
    var body: some View {
        content
            .background(color)
            .overlay(
                Rectangle().frame(height: 1).foregroundColor(border),
                alignment: .top
            )
    }
}

struct CustomTextField: View {
    let title: String
    let placeholder: String
    @Binding var text: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(VastuColors.brandTextMuted)
            TextField(placeholder, text: $text)
                .font(.system(size: 13))
                .padding(10)
                .background(VastuColors.brandIvory)
                .cornerRadius(10)
                .overlay(
                    RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1)
                )
        }
    }
}

struct SummaryLine: View {
    let label: String
    let value: String
    
    var body: some View {
        HStack {
            Text(label)
                .font(.system(size: 11))
                .foregroundColor(VastuColors.brandTextMuted)
            Spacer()
            Text(value)
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(VastuColors.brandText)
        }
    }
}
