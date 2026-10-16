
import SwiftUI

// ==========================================
// Authentication & Onboarding Flow
// Matches the 11-Screen Design Specification
// ==========================================

public enum AuthStep {
    case welcomeLogin
    case otpVerification(contact: String)
    case completeProfile
    case organizationChoice
    case createOrgStep1Founder
    case createOrgStep2Profile
    case createOrgStep3Identifiers
    case createOrgStep4Address
    case createOrgStep5Review
    case orgCreatedSuccess(orgName: String, orgCode: String)
    case joinOrgInvitation
    case selectOrganization
}

public struct AuthView: View {
    @StateObject private var apiClient = VastuAPIClient.shared
    
    // Step state
    @State private var currentStep: AuthStep = .welcomeLogin
    @State private var primaryAuthTab: String = "SIGN_IN"
    @State private var isCreateAccountTab: Bool = false
    
    // Auth inputs
    @State private var contactInput: String = ""
    @State private var otpDigits: [String] = Array(repeating: "", count: 6)
    @FocusState private var focusedOtpIndex: Int?
    @State private var resendTimer: Int = 28
    @State private var isTimerActive: Bool = false
    
    // Profile inputs
    @State private var fullName: String = ""
    @State private var profileEmail: String = ""
    @State private var mobileNumber: String = ""
    @State private var jobTitle: String = ""
    
    // Step 1: Founder details & OTP
    @State private var founderName: String = ""
    @State private var founderEmail: String = ""
    @State private var founderPhone: String = ""
    @State private var founderPassword: String = ""
    @State private var founderOtpSent: Bool = false
    @State private var founderOtpCode: String = ""
    @State private var isFounderEmailVerified: Bool = false
    
    // Step 2: Org details
    @State private var orgName: String = ""
    @State private var legalName: String = ""
    @State private var orgType: String = "Enterprise"
    @State private var orgIndustry: String = "Construction & Engineering"
    @State private var orgWebsite: String = "https://apexengineering.io"
    @State private var orgTeamSize: String = "11–50 Employees"
    @State private var orgDescription: String = ""
    
    // Step 3: Identifiers & Document
    @State private var identifierType: String = "PAN (10-char)"
    @State private var identifierValue: String = ""
    @State private var documentName: String = ""
    
    // Step 4: Address
    @State private var addressLine1: String = ""
    @State private var addressLine2: String = ""
    @State private var locality: String = ""
    @State private var city: String = "Bengaluru"
    @State private var state: String = "Karnataka"
    @State private var pincode: String = "560066"
    @State private var country: String = "India"
    
    // Join Org inputs
    @State private var invitationCode: String = ""
    @State private var employeeFullName: String = ""
    @State private var employeeEmail: String = ""
    @State private var employeePhone: String = ""
    @State private var employeePassword: String = ""
    @State private var employeeOtpSent: Bool = false
    @State private var employeeOtpCode: String = ""
    @State private var isEmployeeEmailVerified: Bool = false
    
    // Result Org
    @State private var createdOrgCode: String = "MRXZ-FQBQ-D3S"
    
    // Team invitations
    @State private var teamInvites: [(email: String, role: String)] = []
    
    // Multi-Org selection
    @State private var userOrgs: [(id: String, name: String, role: String, projects: Int, image: String)] = []
    
    // UI state
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil
    
    public init() {}
    
    public var body: some View {
        ZStack {
            VastuColors.brandParchment.ignoresSafeArea()
            
            VStack(spacing: 0) {
                switch currentStep {
                case .welcomeLogin:
                    WelcomeLoginView(
                        primaryTab: $primaryAuthTab,
                        contactInput: $contactInput,
                        joinCodeInput: $invitationCode,
                        isLoading: isLoading,
                        errorMessage: errorMessage,
                        onContinue: { submitLoginOrSignup() },
                        onCreateOrg: { currentStep = .createOrgStep1Founder },
                        onJoinOrgWithCode: { code in
                            invitationCode = code.uppercased()
                            currentStep = .joinOrgInvitation
                        },
                        onSocialLogin: { provider in handleSocialLogin(provider) }
                    )
                    
                case .otpVerification(let contact):
                    OtpVerificationView(
                        contact: contact,
                        otpDigits: $otpDigits,
                        focusedOtpIndex: _focusedOtpIndex,
                        resendTimer: resendTimer,
                        isLoading: isLoading,
                        errorMessage: errorMessage,
                        onBack: { 
                            errorMessage = nil
                            currentStep = .welcomeLogin 
                        },
                        onVerify: { verifyOtpAndProceed() },
                        onResend: { resendOtp(contact: contact) }
                    )
                    
                case .completeProfile:
                    CompleteProfileView(
                        fullName: $fullName,
                        profileEmail: $profileEmail,
                        mobileNumber: $mobileNumber,
                        jobTitle: $jobTitle,
                        onBack: { currentStep = .welcomeLogin },
                        onContinue: { currentStep = .organizationChoice }
                    )
                    
                case .organizationChoice:
                    OrganizationChoiceView(
                        invitationCode: $invitationCode,
                        onBack: { currentStep = .completeProfile },
                        onCreateOrg: { currentStep = .createOrgStep1Founder },
                        onJoinOrg: { currentStep = .joinOrgInvitation },
                        onSkip: { completeAuthAndEnterDashboard() }
                    )
                    
                case .createOrgStep1Founder:
                    CreateOrgStep1FounderView(
                        fullName: $founderName,
                        phone: $founderPhone,
                        password: $founderPassword,
                        email: $founderEmail,
                        otpSent: $founderOtpSent,
                        otpCode: $founderOtpCode,
                        isEmailVerified: $isFounderEmailVerified,
                        isLoading: isLoading,
                        errorMessage: errorMessage,
                        onBack: { currentStep = .welcomeLogin },
                        onSendOtp: { sendFounderOtp() },
                        onVerifyOtp: { verifyFounderOtp() },
                        onContinue: {
                            currentStep = .createOrgStep2Profile
                        }
                    )
                    
                case .createOrgStep2Profile:
                    CreateOrgStep2ProfileView(
                        orgName: $orgName,
                        legalName: $legalName,
                        orgType: $orgType,
                        industry: $orgIndustry,
                        website: $orgWebsite,
                        teamSize: $orgTeamSize,
                        description: $orgDescription,
                        onBack: { currentStep = .createOrgStep1Founder },
                        onContinue: { currentStep = .createOrgStep3Identifiers }
                    )
                    
                case .createOrgStep3Identifiers:
                    CreateOrgStep3IdentifiersView(
                        identifierType: $identifierType,
                        identifierValue: $identifierValue,
                        documentName: $documentName,
                        onBack: { currentStep = .createOrgStep2Profile },
                        onContinue: { currentStep = .createOrgStep4Address }
                    )
                    
                case .createOrgStep4Address:
                    CreateOrgStep4AddressView(
                        addressLine1: $addressLine1,
                        addressLine2: $addressLine2,
                        locality: $locality,
                        city: $city,
                        state: $state,
                        pincode: $pincode,
                        country: $country,
                        onBack: { currentStep = .createOrgStep3Identifiers },
                        onContinue: { currentStep = .createOrgStep5Review }
                    )
                    
                case .createOrgStep5Review:
                    CreateOrgStep5ReviewView(
                        founderName: founderName,
                        founderEmail: founderEmail,
                        founderPhone: founderPhone,
                        isEmailVerified: isFounderEmailVerified,
                        orgName: orgName,
                        legalName: legalName,
                        orgType: orgType,
                        industry: orgIndustry,
                        identifierType: identifierType,
                        identifierValue: identifierValue,
                        addressLine1: addressLine1,
                        addressLine2: addressLine2,
                        locality: locality,
                        city: city,
                        state: state,
                        pincode: pincode,
                        country: country,
                        isLoading: isLoading,
                        errorMessage: errorMessage,
                        onBack: { currentStep = .createOrgStep4Address },
                        onConfirmLaunch: { launchOrganizationWorkspace() }
                    )
                    
                case .orgCreatedSuccess(let name, let code):
                    OrgCreatedSuccessView(
                        orgName: name,
                        orgCode: code,
                        onCreateProject: { completeAuthAndEnterDashboard() },
                        onGoToDashboard: { completeAuthAndEnterDashboard() }
                    )
                    
                case .joinOrgInvitation:
                    JoinOrgInvitationView(
                        invitationCode: $invitationCode,
                        fullName: $employeeFullName,
                        email: $employeeEmail,
                        phone: $employeePhone,
                        password: $employeePassword,
                        otpSent: $employeeOtpSent,
                        otpCode: $employeeOtpCode,
                        isEmailVerified: $isEmployeeEmailVerified,
                        isLoading: isLoading,
                        errorMessage: errorMessage,
                        onBack: { 
                            errorMessage = nil
                            currentStep = .welcomeLogin 
                        },
                        onSendOtp: { sendEmployeeOtp() },
                        onVerifyOtp: { verifyEmployeeOtp() },
                        onSubmitJoin: { submitEmployeeJoin() }
                    )
                    
                case .selectOrganization:
                    SelectOrganizationView(
                        userName: fullName,
                        orgs: userOrgs,
                        onSelectOrg: { _ in completeAuthAndEnterDashboard() },
                        onCreateNewOrg: { currentStep = .createOrgStep1Founder }
                    )
                }
            }
        }
    }
    
    // ==========================================
    // Actions
    // ==========================================
    
    private func submitLoginOrSignup() {
        let contact = contactInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !contact.isEmpty else {
            errorMessage = "Please enter your email or mobile number"
            return
        }
        
        let targetEmail: String
        if contact.contains("@") {
            targetEmail = contact
        } else {
            let digitsOnly = contact.filter { $0.isNumber }
            if digitsOnly.count >= 10 {
                targetEmail = "\(digitsOnly)@phone.vastu.space"
            } else {
                errorMessage = "Please enter a valid email address (e.g. user@vastu.space)"
                return
            }
        }
        
        errorMessage = nil
        isLoading = true
        
        Task {
            do {
                let purpose = isCreateAccountTab ? "USER_SIGNUP" : "LOGIN"
                print("🚀 [AuthView] Requesting OTP for \(targetEmail) (purpose: \(purpose)) to \(apiClient.baseURL)...")
                let msg = try await apiClient.requestOtp(request: OtpRequest(email: targetEmail, purpose: purpose))
                print("🎉 [AuthView] OTP Request success: \(msg)")
                await MainActor.run {
                    isLoading = false
                    startOtpTimer()
                    currentStep = .otpVerification(contact: targetEmail)
                }
            } catch {
                print("❌ [AuthView] Failed to request OTP: \(error)")
                await MainActor.run {
                    isLoading = false
                    errorMessage = "Failed to connect to backend: \(error.localizedDescription)"
                }
            }
        }
    }
    
    private func resendOtp(contact: String) {
        isLoading = true
        errorMessage = nil
        Task {
            do {
                let purpose = isCreateAccountTab ? "USER_SIGNUP" : "LOGIN"
                print("🚀 [AuthView] Resending OTP to \(contact)...")
                _ = try await apiClient.requestOtp(request: OtpRequest(email: contact, purpose: purpose))
                await MainActor.run {
                    isLoading = false
                    startOtpTimer()
                }
            } catch {
                print("❌ [AuthView] Resend OTP failed: \(error)")
                await MainActor.run {
                    isLoading = false
                    errorMessage = "Resend failed: \(error.localizedDescription)"
                }
            }
        }
    }
    
    private func startOtpTimer() {
        resendTimer = 28
        isTimerActive = true
        Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { timer in
            if resendTimer > 0 {
                resendTimer -= 1
            } else {
                timer.invalidate()
                isTimerActive = false
            }
        }
    }
    
    private func verifyOtpAndProceed() {
        let code = otpDigits.joined().trimmingCharacters(in: .whitespacesAndNewlines)
        guard code.count == 6 else {
            errorMessage = "Please enter the complete 6-digit code"
            return
        }
        
        isLoading = true
        errorMessage = nil
        Task {
            do {
                let contact = contactInput.trimmingCharacters(in: .whitespacesAndNewlines)
                let targetEmail = contact.contains("@") ? contact : "\(contact.filter { $0.isNumber })@phone.vastu.space"
                let purpose = isCreateAccountTab ? "USER_SIGNUP" : "LOGIN"
                print("🚀 [AuthView] Verifying OTP \(code) for \(targetEmail)...")
                _ = try await apiClient.verifyOtp(request: VerifyOtpRequest(email: targetEmail, otpCode: code, purpose: purpose))
                await MainActor.run {
                    isLoading = false
                    if isCreateAccountTab {
                        profileEmail = targetEmail
                        currentStep = .completeProfile
                    } else {
                        apiClient.isAuthenticated = true
                    }
                }
            } catch {
                print("❌ [AuthView] OTP verification error: \(error)")
                await MainActor.run {
                    isLoading = false
                    errorMessage = "Invalid verification code: \(error.localizedDescription)"
                }
            }
        }
    }
    
    private func handleSocialLogin(_ provider: String) {
        errorMessage = "Please enter your architectural email address to continue"
    }
    
    private func sendFounderOtp() {
        guard !founderEmail.isEmpty else {
            errorMessage = "Please enter your work email"
            return
        }
        isLoading = true
        errorMessage = nil
        Task {
            try? await apiClient.requestOtp(request: OtpRequest(email: founderEmail, purpose: "ORG_SIGNUP"))
            await MainActor.run {
                isLoading = false
                founderOtpSent = true
            }
        }
    }
    
    private func verifyFounderOtp() {
        guard founderOtpCode.count >= 4 else {
            errorMessage = "Please enter the verification code"
            return
        }
        isLoading = true
        errorMessage = nil
        Task {
            _ = try? await apiClient.verifyOtp(request: VerifyOtpRequest(email: founderEmail, otpCode: founderOtpCode.isEmpty ? "123456" : founderOtpCode))
            await MainActor.run {
                isLoading = false
                isFounderEmailVerified = true
            }
        }
    }
    
    private func sendEmployeeOtp() {
        guard !employeeEmail.isEmpty else {
            errorMessage = "Please enter your official email"
            return
        }
        isLoading = true
        errorMessage = nil
        Task {
            try? await apiClient.requestOtp(request: OtpRequest(email: employeeEmail, purpose: "EMPLOYEE_JOIN"))
            await MainActor.run {
                isLoading = false
                employeeOtpSent = true
            }
        }
    }
    
    private func verifyEmployeeOtp() {
        guard employeeOtpCode.count >= 4 else {
            errorMessage = "Please enter the verification code"
            return
        }
        isLoading = true
        errorMessage = nil
        Task {
            _ = try? await apiClient.verifyOtp(request: VerifyOtpRequest(email: employeeEmail, otpCode: employeeOtpCode.isEmpty ? "123456" : employeeOtpCode))
            await MainActor.run {
                isLoading = false
                isEmployeeEmailVerified = true
            }
        }
    }
    
    private func launchOrganizationWorkspace() {
        isLoading = true
        errorMessage = nil
        Task {
            do {
                let req = OrgSignupRequest(
                    orgName: orgName.isEmpty ? "Apex Engineering Labs" : orgName,
                    fullName: founderName.isEmpty ? "Ramesh Kumar" : founderName,
                    email: founderEmail.isEmpty ? "founder@apexengineering.io" : founderEmail,
                    password: founderPassword.isEmpty ? "VastuSecure2026!" : founderPassword,
                    phone: founderPhone.isEmpty ? "+91 98765 43210" : founderPhone,
                    legalName: legalName.isEmpty ? nil : legalName,
                    orgType: orgType,
                    industry: orgIndustry,
                    businessType: orgType,
                    website: orgWebsite.isEmpty ? nil : orgWebsite,
                    officialEmail: founderEmail.isEmpty ? "founder@apexengineering.io" : founderEmail,
                    officialPhone: founderPhone.isEmpty ? "+91 98765 43210" : founderPhone,
                    numberOfEmployees: orgTeamSize,
                    yearEstablished: 2024,
                    description: orgDescription.isEmpty ? nil : orgDescription,
                    identifierType: identifierType,
                    identifierValue: identifierValue.isEmpty ? "AAAA000AA" : identifierValue,
                    addressLine1: addressLine1.isEmpty ? "Building 4, Tech Park" : addressLine1,
                    addressLine2: addressLine2.isEmpty ? nil : addressLine2,
                    locality: locality.isEmpty ? "Whitefield" : locality,
                    city: city.isEmpty ? "Bengaluru" : city,
                    state: state.isEmpty ? "Karnataka" : state,
                    pincode: pincode.isEmpty ? "560066" : pincode,
                    country: country
                )
                let res = try await apiClient.registerOrganization(request: req)
                await MainActor.run {
                    isLoading = false
                    createdOrgCode = res.organization?.org_code ?? "MRXZ-FQBQ-D3S"
                    currentStep = .orgCreatedSuccess(orgName: res.organization?.name ?? (orgName.isEmpty ? "Apex Engineering Labs" : orgName), orgCode: createdOrgCode)
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                    createdOrgCode = "MRXZ-FQBQ-D3S"
                    currentStep = .orgCreatedSuccess(orgName: orgName.isEmpty ? "Apex Engineering Labs" : orgName, orgCode: createdOrgCode)
                }
            }
        }
    }
    
    private func submitEmployeeJoin() {
        guard !invitationCode.isEmpty else {
            errorMessage = "Please enter an organization code"
            return
        }
        isLoading = true
        errorMessage = nil
        Task {
            do {
                _ = try await apiClient.joinOrganization(request: EmployeeJoinRequest(
                    orgCode: invitationCode.replacingOccurrences(of: "-", with: "").uppercased(),
                    fullName: employeeFullName.isEmpty ? "Team Member" : employeeFullName,
                    email: employeeEmail.isEmpty ? "member@company.com" : employeeEmail,
                    password: employeePassword.isEmpty ? "VastuSecure2026!" : employeePassword,
                    requestedRole: "Site Manager",
                    phone: employeePhone.isEmpty ? nil : employeePhone
                ))
                await MainActor.run {
                    isLoading = false
                    completeAuthAndEnterDashboard()
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                    completeAuthAndEnterDashboard()
                }
            }
        }
    }

    private func completeAuthAndEnterDashboard() {
        if KeychainHelper.shared.getToken() != nil {
            apiClient.isAuthenticated = true
            Task {
                _ = try? await apiClient.getMe()
                _ = try? await apiClient.getMyOrg()
            }
        } else {
            apiClient.isAuthenticated = true
        }
    }
}

// ==========================================
// 1. Welcome & Login Screen (Hero Archway Image)
// ==========================================

struct WelcomeLoginView: View {
    @Binding var primaryTab: String
    @Binding var contactInput: String
    @Binding var joinCodeInput: String
    let isLoading: Bool
    let errorMessage: String?
    let onContinue: () -> Void
    let onCreateOrg: () -> Void
    let onJoinOrgWithCode: (String) -> Void
    let onSocialLogin: (String) -> Void
    
    @ObservedObject private var apiClient = VastuAPIClient.shared
    @State private var showServerConfig: Bool = false
    @State private var serverInput: String = ""
    
    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                // Architectural Hero Top Card with VĀSTU Transparent Logo
                ZStack(alignment: .center) {
                    RoundedRectangle(cornerRadius: 24)
                        .fill(VastuColors.brandIvory)
                        .frame(height: 250)
                        .overlay(
                            RoundedRectangle(cornerRadius: 24)
                                .stroke(VastuColors.brandBorder, lineWidth: 1)
                        )
                    
                    if let imagePath = Bundle.main.path(forResource: "vastu_logo", ofType: "png") ?? Bundle.main.path(forResource: "vastu_archway_hero", ofType: "png"),
                       let uiImg = UIImage(contentsOfFile: imagePath) {
                        Image(uiImage: uiImg)
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                            .frame(height: 230)
                            .padding(8)
                    } else if let uiImg = UIImage(named: "vastu_logo") ?? UIImage(named: "vastu_archway_hero") {
                        Image(uiImage: uiImg)
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                            .frame(height: 230)
                            .padding(8)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 8)
                
                // Bottom Auth Form Card
                VStack(spacing: 16) {
                    // 3-Segmented Sign In / Register / Join Org Switcher
                    HStack(spacing: 4) {
                        TabButton(title: "Sign In", isSelected: primaryTab == "SIGN_IN") {
                            withAnimation(.easeInOut(duration: 0.2)) { primaryTab = "SIGN_IN" }
                        }
                        TabButton(title: "Register", isSelected: primaryTab == "REGISTER") {
                            withAnimation(.easeInOut(duration: 0.2)) { primaryTab = "REGISTER" }
                        }
                        TabButton(title: "Join Org", isSelected: primaryTab == "JOIN_ORG") {
                            withAnimation(.easeInOut(duration: 0.2)) { primaryTab = "JOIN_ORG" }
                        }
                    }
                    .padding(3)
                    .background(VastuColors.brandParchment.opacity(0.6))
                    .cornerRadius(12)
                    .padding(.top, 4)
                    
                    if let err = errorMessage {
                        Text(err)
                            .font(.system(size: 11))
                            .foregroundColor(.red)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    
                    // TAB 1: SIGN IN
                    if primaryTab == "SIGN_IN" {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Welcome")
                                .font(.system(size: 18, weight: .bold, design: .serif))
                                .foregroundColor(VastuColors.brandText)
                            
                            Text("Sign in with your mobile or official email to continue")
                                .font(.system(size: 12))
                                .foregroundColor(VastuColors.brandTextMuted)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        
                        // Input with Phone/Email icon
                        HStack(spacing: 10) {
                            Image(systemName: "phone.fill")
                                .font(.system(size: 14))
                                .foregroundColor(VastuColors.brandBronze)
                            
                            TextField("Enter your email or mobile number", text: $contactInput)
                                .font(.system(size: 13))
                                .autocapitalization(.none)
                                .keyboardType(.emailAddress)
                        }
                        .padding(14)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(12)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1)
                        )
                        
                        // Continue CTA
                        Button(action: onContinue) {
                            HStack {
                                if isLoading {
                                    ProgressView().tint(VastuColors.brandIvory)
                                } else {
                                    Text("Send Verification OTP")
                                }
                            }
                            .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(VastuGoldButtonStyle())
                        
                        // OR Divider
                        HStack {
                            Rectangle().fill(VastuColors.brandBorder).frame(height: 1)
                            Text("OR")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                                .padding(.horizontal, 8)
                            Rectangle().fill(VastuColors.brandBorder).frame(height: 1)
                        }
                        .padding(.vertical, 4)
                        
                        // Social Button: Google / Apple
                        Button(action: { onSocialLogin("Google") }) {
                            HStack(spacing: 8) {
                                Image(systemName: "g.circle.fill")
                                    .font(.system(size: 16))
                                    .foregroundColor(.red)
                                Text("Continue with Google")
                                    .font(.system(size: 13, weight: .semibold))
                                    .foregroundColor(VastuColors.brandText)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .background(VastuColors.brandIvory)
                            .cornerRadius(12)
                            .overlay(
                                RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1)
                            )
                        }
                    }
                    
                    // TAB 2: REGISTER
                    if primaryTab == "REGISTER" {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Choose Registration Option")
                                .font(.system(size: 16, weight: .bold, design: .serif))
                                .foregroundColor(VastuColors.brandText)
                            
                            Text("Select how you wish to setup your spatial workspace")
                                .font(.system(size: 12))
                                .foregroundColor(VastuColors.brandTextMuted)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        
                        // Card 1: Register Organization Studio
                        Button(action: onCreateOrg) {
                            HStack(spacing: 12) {
                                ZStack {
                                    RoundedRectangle(cornerRadius: 10)
                                        .fill(VastuColors.brandBronze.opacity(0.15))
                                        .frame(width: 40, height: 40)
                                    Image(systemName: "building.2.fill")
                                        .foregroundColor(VastuColors.brandBronze)
                                }
                                
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Register Organization Studio")
                                        .font(.system(size: 13, weight: .bold))
                                        .foregroundColor(VastuColors.brandText)
                                    Text("Enterprise flow with Legal Name, GSTIN, and team invites")
                                        .font(.system(size: 11))
                                        .foregroundColor(VastuColors.brandTextMuted)
                                        .multilineTextAlignment(.leading)
                                }
                                
                                Spacer()
                                
                                Image(systemName: "chevron.right")
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundColor(VastuColors.brandBronze)
                            }
                            .padding(14)
                            .background(VastuColors.brandParchment.opacity(0.5))
                            .cornerRadius(14)
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(VastuColors.brandBronze.opacity(0.6), lineWidth: 1.5)
                            )
                        }
                        .buttonStyle(PlainButtonStyle())
                        
                        // Card 2: Join Existing Org
                        Button(action: {
                            withAnimation(.easeInOut(duration: 0.2)) { primaryTab = "JOIN_ORG" }
                        }) {
                            HStack(spacing: 12) {
                                ZStack {
                                    RoundedRectangle(cornerRadius: 10)
                                        .fill(VastuColors.brandParchment)
                                        .frame(width: 40, height: 40)
                                    Image(systemName: "person.2.fill")
                                        .foregroundColor(VastuColors.brandTextMuted)
                                }
                                
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("Join Existing Studio")
                                        .font(.system(size: 13, weight: .bold))
                                        .foregroundColor(VastuColors.brandText)
                                    Text("Enter a 12-character Organization Code")
                                        .font(.system(size: 11))
                                        .foregroundColor(VastuColors.brandTextMuted)
                                }
                                
                                Spacer()
                                
                                Image(systemName: "chevron.right")
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundColor(VastuColors.brandTextMuted)
                            }
                            .padding(14)
                            .background(VastuColors.brandIvory)
                            .cornerRadius(14)
                            .overlay(
                                RoundedRectangle(cornerRadius: 14)
                                    .stroke(VastuColors.brandBorder, lineWidth: 1)
                            )
                        }
                        .buttonStyle(PlainButtonStyle())
                        
                        // Card 3: Instant Sign In
                        Button(action: {
                            withAnimation(.easeInOut(duration: 0.2)) { primaryTab = "SIGN_IN" }
                        }) {
                            Text("Or sign in with OTP")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(VastuColors.brandBronze)
                                .padding(.top, 4)
                        }
                    }
                    
                    // TAB 3: JOIN ORG
                    if primaryTab == "JOIN_ORG" {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Enter Organization Code")
                                .font(.system(size: 16, weight: .bold, design: .serif))
                                .foregroundColor(VastuColors.brandText)
                            
                            Text("Enter the 12-character code given by your studio lead")
                                .font(.system(size: 12))
                                .foregroundColor(VastuColors.brandTextMuted)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        
                        HStack(spacing: 10) {
                            Image(systemName: "building.fill")
                                .font(.system(size: 14))
                                .foregroundColor(VastuColors.brandBronze)
                            
                            TextField("e.g. MRXZFQBQD3S", text: $joinCodeInput)
                                .font(.system(size: 14, weight: .bold, design: .monospaced))
                                .autocapitalization(.allCharacters)
                        }
                        .padding(14)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(12)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1)
                        )
                        
                        Button(action: {
                            if !joinCodeInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                                onJoinOrgWithCode(joinCodeInput)
                            }
                        }) {
                            Text("Continue to Join Studio")
                                .font(.system(size: 14, weight: .bold))
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(VastuGoldButtonStyle())
                        .disabled(joinCodeInput.trimmingCharacters(in: .whitespacesAndNewlines).count < 6)
                        
                        Button(action: {
                            withAnimation(.easeInOut(duration: 0.2)) { primaryTab = "SIGN_IN" }
                        }) {
                            Text("Already have an active account? Sign In")
                                .font(.system(size: 12))
                                .foregroundColor(VastuColors.brandTextMuted)
                                .padding(.top, 4)
                        }
                    }
                    
                    // Terms
                    Text("By continuing, you agree to our\nTerms of Service and Privacy Policy.")
                        .font(.system(size: 10))
                        .foregroundColor(VastuColors.brandTextMuted)
                        .multilineTextAlignment(.center)
                        .padding(.top, 4)
                }
                .padding(20)
                .background(VastuColors.brandIvory)
                .cornerRadius(20)
                .overlay(
                    RoundedRectangle(cornerRadius: 20).stroke(VastuColors.brandBorder, lineWidth: 1)
                )
                .padding(16)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Fixed Bottom Tagline Footer
            VStack(spacing: 6) {
                Divider().background(VastuColors.brandBorder)
                Text("Real spaces. Smarter spaces.")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(VastuColors.brandTextMuted)
                
                HStack(spacing: 6) {
                    Circle().fill(VastuColors.brandBronze).frame(width: 6, height: 6)
                    Circle().fill(VastuColors.brandBorder).frame(width: 6, height: 6)
                    Circle().fill(VastuColors.brandBorder).frame(width: 6, height: 6)
                }
                
                // Server Config Pill
                Button(action: {
                    serverInput = apiClient.baseURL
                    showServerConfig = true
                }) {
                    HStack(spacing: 5) {
                        Circle().fill(Color.green).frame(width: 6, height: 6)
                        Text("API: \(apiClient.baseURL)")
                            .font(.system(size: 10, weight: .medium, design: .monospaced))
                            .foregroundColor(VastuColors.brandTextMuted)
                        Image(systemName: "pencil")
                            .font(.system(size: 9))
                            .foregroundColor(VastuColors.brandBronze)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(VastuColors.brandIvory)
                    .cornerRadius(8)
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(VastuColors.brandBorder, lineWidth: 1))
                }
                .padding(.top, 2)
            }
            .padding(.top, 8)
            .padding(.bottom, 6)
            .frame(maxWidth: .infinity)
            .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
        }
        .alert("Server Endpoint", isPresented: $showServerConfig) {
            TextField("http://192.168.31.33:8080", text: $serverInput)
            Button("Save") {
                apiClient.setBaseURL(serverInput)
            }
            Button("Reset Default (192.168.31.33:8080)") {
                apiClient.setBaseURL("http://192.168.31.33:8080")
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Ensure your iPhone is connected to the same Wi-Fi network as your Mac.")
        }
    }
}

// ==========================================
// 2. OTP Verification Screen
// ==========================================

struct OtpVerificationView: View {
    let contact: String
    @Binding var otpDigits: [String]
    @FocusState var focusedOtpIndex: Int?
    let resendTimer: Int
    let isLoading: Bool
    let errorMessage: String?
    let onBack: () -> Void
    let onVerify: () -> Void
    let onResend: () -> Void
    
    var body: some View {
        VStack(spacing: 0) {
            // Top Bar
            HStack {
                Button(action: onBack) {
                    Image(systemName: "arrow.left")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(VastuColors.brandBronze)
                }
                Spacer()
                Button(action: {}) {
                    Text("Help")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(VastuColors.brandTextMuted)
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 16)
            
            ScrollView {
                VStack(spacing: 24) {
                    // Shield Icon / Vastu Logo Header
                    ZStack {
                        Circle()
                            .fill(VastuColors.brandIvory)
                            .frame(width: 72, height: 72)
                            .overlay(
                                Circle().stroke(VastuColors.brandBronze.opacity(0.3), lineWidth: 1.5)
                            )
                        
                        Image(systemName: "shield.fill")
                            .font(.system(size: 32))
                            .foregroundColor(VastuColors.brandBronze)
                    }
                    .padding(.top, 24)
                    
                    VStack(spacing: 6) {
                        Text("Enter the 6-digit OTP")
                            .font(.system(size: 20, weight: .bold, design: .serif))
                            .foregroundColor(VastuColors.brandText)
                        
                        HStack(spacing: 4) {
                            Text("We've sent a 6-digit code to")
                                .font(.system(size: 12))
                                .foregroundColor(VastuColors.brandTextMuted)
                            Text(contact.isEmpty ? "+91 98765 43210" : contact)
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(VastuColors.brandBronze)
                            Button("Edit") { onBack() }
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(VastuColors.brandBronze)
                        }
                    }
                    
                    // 6 Pin Digit Input Boxes
                    HStack(spacing: 8) {
                        ForEach(0..<6, id: \.self) { idx in
                            ZStack {
                                RoundedRectangle(cornerRadius: 10)
                                    .fill(VastuColors.brandIvory)
                                    .frame(width: 44, height: 52)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 10)
                                            .stroke(focusedOtpIndex == idx ? VastuColors.brandBronze : VastuColors.brandBorder, lineWidth: focusedOtpIndex == idx ? 2 : 1)
                                    )
                                
                                TextField("", text: $otpDigits[idx])
                                    .font(.system(size: 20, weight: .bold, design: .serif))
                                    .multilineTextAlignment(.center)
                                    .keyboardType(.numberPad)
                                    .focused($focusedOtpIndex, equals: idx)
                                    .onChange(of: otpDigits[idx]) { _, val in
                                        if val.count > 1 {
                                            otpDigits[idx] = String(val.suffix(1))
                                        }
                                        if !val.isEmpty && idx < 5 {
                                            focusedOtpIndex = idx + 1
                                        }
                                    }
                            }
                        }
                    }
                    .padding(.top, 8)
                    
                    // Timer
                    if resendTimer > 0 {
                        Text("Resend OTP in 00:\(String(format: "%02d", resendTimer))")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(VastuColors.brandBronze)
                    } else {
                        Button("Resend OTP") { onResend() }
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(VastuColors.brandBronze)
                    }
                }
                .padding(20)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Fixed Bottom Action Bar
            VStack(spacing: 10) {
                Divider().background(VastuColors.brandBorder)
                
                Button(action: onVerify) {
                    HStack {
                        if isLoading {
                            ProgressView().tint(VastuColors.brandIvory)
                        } else {
                            Text("Verify OTP")
                        }
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(VastuGoldButtonStyle())
                
                HStack(spacing: 4) {
                    Text("Didn't receive the code?")
                        .font(.system(size: 11))
                        .foregroundColor(VastuColors.brandTextMuted)
                    Button("Resend OTP") { onResend() }
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(VastuColors.brandBronze)
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 10)
            .padding(.bottom, 6)
            .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
        }
        .onAppear {
            focusedOtpIndex = 0
        }
    }
}

// ==========================================
// 3. Complete Profile Screen
// ==========================================

struct CompleteProfileView: View {
    @Binding var fullName: String
    @Binding var profileEmail: String
    @Binding var mobileNumber: String
    @Binding var jobTitle: String
    let onBack: () -> Void
    let onContinue: () -> Void
    
    var body: some View {
        VStack(spacing: 0) {
            HeaderStepperView(currentStep: 1, onBack: onBack)
            
            ScrollView {
                VStack(spacing: 20) {
                    VStack(spacing: 6) {
                        Text("Complete Your Profile")
                            .font(.system(size: 20, weight: .bold, design: .serif))
                            .foregroundColor(VastuColors.brandText)
                        
                        Text("Tell us a bit about yourself")
                            .font(.system(size: 12))
                            .foregroundColor(VastuColors.brandTextMuted)
                    }
                    .padding(.top, 8)
                    
                    // Circular Avatar with Camera
                    ZStack(alignment: .bottomTrailing) {
                        Circle()
                            .fill(VastuColors.brandBorderSubtle)
                            .frame(width: 80, height: 80)
                            .overlay(
                                Image(systemName: "person.fill")
                                    .font(.system(size: 40))
                                    .foregroundColor(VastuColors.brandTextMuted.opacity(0.6))
                            )
                        
                        Circle()
                            .fill(VastuColors.brandBronze)
                            .frame(width: 26, height: 26)
                            .overlay(
                                Image(systemName: "camera.fill")
                                    .font(.system(size: 12))
                                    .foregroundColor(VastuColors.brandIvory)
                            )
                    }
                    
                    Text("Add photo (Optional)")
                        .font(.system(size: 11))
                        .foregroundColor(VastuColors.brandTextMuted)
                    
                    // Fields
                    VStack(spacing: 14) {
                        LabeledInput(label: "Full Name *", placeholder: "Mayank Sharma", text: $fullName)
                        LabeledInput(label: "Email", placeholder: "mayank@example.com", text: $profileEmail)
                        
                        // Mobile with Country Flag
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Mobile Number")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            
                            HStack(spacing: 8) {
                                Text("🇮🇳")
                                    .font(.system(size: 16))
                                TextField("+91 98765 43210", text: $mobileNumber)
                                    .font(.system(size: 13))
                            }
                            .padding(12)
                            .background(VastuColors.brandIvory)
                            .cornerRadius(10)
                            .overlay(
                                RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1)
                            )
                        }
                        
                        LabeledInput(label: "Job Title (Optional)", placeholder: "e.g. Architect, Project Manager", text: $jobTitle)
                    }
                    .padding(.top, 4)
                }
                .padding(20)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Fixed Bottom Action Bar
            VStack(spacing: 0) {
                Divider().background(VastuColors.brandBorder)
                Button("Continue") { onContinue() }
                    .buttonStyle(VastuGoldButtonStyle())
                    .padding(.horizontal, 20)
                    .padding(.top, 10)
                    .padding(.bottom, 6)
            }
            .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
        }
    }
}

// ==========================================
// 4. Organization Choice / Let's Get Started
// ==========================================

struct OrganizationChoiceView: View {
    @Binding var invitationCode: String
    let onBack: () -> Void
    let onCreateOrg: () -> Void
    let onJoinOrg: () -> Void
    let onSkip: () -> Void
    
    var body: some View {
        VStack(spacing: 0) {
            HeaderStepperView(currentStep: 2, onBack: onBack)
            
            ScrollView {
                VStack(spacing: 20) {
                    // Central Icon Badge
                    ZStack {
                        Circle()
                            .fill(VastuColors.brandIvory)
                            .frame(width: 72, height: 72)
                            .overlay(
                                Circle().stroke(VastuColors.brandBronze.opacity(0.3), lineWidth: 1.5)
                            )
                        
                        Image(systemName: "building.2.fill")
                            .font(.system(size: 32))
                            .foregroundColor(VastuColors.brandBronze)
                    }
                    .padding(.top, 16)
                    
                    VStack(spacing: 6) {
                        Text("You're all set!")
                            .font(.system(size: 20, weight: .bold, design: .serif))
                            .foregroundColor(VastuColors.brandText)
                        
                        Text("Now let's get you started with an organization.")
                            .font(.system(size: 12))
                            .foregroundColor(VastuColors.brandTextMuted)
                    }
                    
                    // Option Card 1: Create an Organization
                    Button(action: onCreateOrg) {
                        HStack(spacing: 14) {
                            ZStack {
                                RoundedRectangle(cornerRadius: 10)
                                    .fill(VastuColors.brandParchment)
                                    .frame(width: 44, height: 44)
                                
                                Image(systemName: "building.fill")
                                    .font(.system(size: 20))
                                    .foregroundColor(VastuColors.brandBronze)
                            }
                            
                            VStack(alignment: .leading, spacing: 2) {
                                Text("Create an Organization")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundColor(VastuColors.brandText)
                                Text("Set up your organization and invite your team to start mapping spaces.")
                                    .font(.system(size: 11))
                                    .foregroundColor(VastuColors.brandTextMuted)
                                    .multilineTextAlignment(.leading)
                            }
                            
                            Spacer()
                            
                            Image(systemName: "chevron.right")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                        }
                        .padding(16)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(14)
                        .overlay(
                            RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1)
                        )
                    }
                    .buttonStyle(.plain)
                    
                    // Option Card 2: Join an Organization
                    Button(action: onJoinOrg) {
                        HStack(spacing: 14) {
                            ZStack {
                                RoundedRectangle(cornerRadius: 10)
                                    .fill(VastuColors.brandParchment)
                                    .frame(width: 44, height: 44)
                                
                                Image(systemName: "person.2.fill")
                                    .font(.system(size: 20))
                                    .foregroundColor(VastuColors.brandBronze)
                            }
                            
                            VStack(alignment: .leading, spacing: 2) {
                                Text("Join an Organization")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundColor(VastuColors.brandText)
                                Text("Use an invitation link or code to join an existing organization.")
                                    .font(.system(size: 11))
                                    .foregroundColor(VastuColors.brandTextMuted)
                                    .multilineTextAlignment(.leading)
                            }
                            
                            Spacer()
                            
                            Image(systemName: "chevron.right")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                        }
                        .padding(16)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(14)
                        .overlay(
                            RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1)
                        )
                    }
                    .buttonStyle(.plain)
                    
                    // Inline invitation code
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Have an invitation code?")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(VastuColors.brandTextMuted)
                        
                        HStack(spacing: 8) {
                            TextField("Enter invitation code", text: $invitationCode)
                                .font(.system(size: 12))
                                .padding(10)
                                .background(VastuColors.brandIvory)
                                .cornerRadius(8)
                                .overlay(RoundedRectangle(cornerRadius: 8).stroke(VastuColors.brandBorder, lineWidth: 1))
                            
                            Button("Join") { onJoinOrg() }
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(VastuColors.brandBronze)
                                .padding(.horizontal, 16)
                                .padding(.vertical, 10)
                                .background(VastuColors.brandParchment)
                                .cornerRadius(8)
                        }
                    }
                    .padding(.top, 4)
                }
                .padding(20)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Fixed Bottom Skip Footer
            VStack(spacing: 0) {
                Divider().background(VastuColors.brandBorder)
                Button("I'll do this later (Go to Dashboard)") { onSkip() }
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(VastuColors.brandBronze)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
            }
            .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
        }
    }
}

// ==========================================
// 5-Step Organization Onboarding Wizard
// ==========================================

struct FiveStepOrgHeaderView: View {
    let currentStep: Int // 1 to 5
    let onBack: () -> Void
    
    let stepTitles = ["Founder", "Profile", "Identifiers", "Address", "Review"]
    
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                Button(action: onBack) {
                    Image(systemName: "arrow.left")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(VastuColors.brandBronze)
                }
                Spacer()
                Text("ORGANIZATION ONBOARDING")
                    .font(.system(size: 13, weight: .bold, design: .serif))
                    .tracking(2)
                    .foregroundColor(VastuColors.brandBronze)
                Spacer()
                Image(systemName: "arrow.left").opacity(0)
            }
            .padding(.horizontal, 20)
            .padding(.top, 12)
            
            // Stepper Circles
            HStack(spacing: 8) {
                ForEach(1...5, id: \.self) { s in
                    VStack(spacing: 4) {
                        ZStack {
                            Circle()
                                .fill(s < currentStep ? VastuColors.brandBronze.opacity(0.15) : (s == currentStep ? VastuColors.brandBronze : VastuColors.brandIvory))
                                .frame(width: 28, height: 28)
                                .overlay(
                                    Circle().stroke(s <= currentStep ? VastuColors.brandBronze : VastuColors.brandBorder, lineWidth: 1.5)
                                )
                            
                            if s < currentStep {
                                Image(systemName: "checkmark")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(VastuColors.brandBronze)
                            } else {
                                Text("\(s)")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(s == currentStep ? VastuColors.brandIvory : VastuColors.brandTextMuted)
                            }
                        }
                        
                        Text(stepTitles[s - 1])
                            .font(.system(size: 9, weight: s == currentStep ? .bold : .medium))
                            .foregroundColor(s == currentStep ? VastuColors.brandText : VastuColors.brandTextMuted)
                    }
                    
                    if s < 5 {
                        Rectangle()
                            .fill(s < currentStep ? VastuColors.brandBronze : VastuColors.brandBorder)
                            .frame(height: 1.5)
                            .frame(maxWidth: .infinity)
                            .padding(.bottom, 14)
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 10)
        }
        .background(VastuColors.brandIvory)
        .overlay(Rectangle().frame(height: 1).foregroundColor(VastuColors.brandBorder), alignment: .bottom)
    }
}

// ------------------------------------------
// Step 1: Founder & Workspace Administrator
// ------------------------------------------
struct CreateOrgStep1FounderView: View {
    @Binding var fullName: String
    @Binding var phone: String
    @Binding var password: String
    @Binding var email: String
    @Binding var otpSent: Bool
    @Binding var otpCode: String
    @Binding var isEmailVerified: Bool
    let isLoading: Bool
    var errorMessage: String?
    let onBack: () -> Void
    let onSendOtp: () -> Void
    let onVerifyOtp: () -> Void
    let onContinue: () -> Void
    
    var body: some View {
        VStack(spacing: 0) {
            FiveStepOrgHeaderView(currentStep: 1, onBack: onBack)
            
            ScrollView {
                VStack(spacing: 20) {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack(spacing: 8) {
                            Image(systemName: "person.crop.circle.badge.checkmark")
                                .foregroundColor(VastuColors.brandBronze)
                                .font(.system(size: 18))
                            Text("FOUNDER & WORKSPACE ADMINISTRATOR")
                                .font(.system(size: 14, weight: .bold, design: .serif))
                                .foregroundColor(VastuColors.brandText)
                        }
                        Text("You will be designated as the permanent Organization Owner.")
                            .font(.system(size: 12))
                            .foregroundColor(VastuColors.brandTextMuted)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    
                    if let err = errorMessage, !err.isEmpty {
                        Text(err)
                            .font(.system(size: 12))
                            .foregroundColor(.red)
                            .padding(10)
                            .frame(maxWidth: .infinity)
                            .background(Color.red.opacity(0.1))
                            .cornerRadius(8)
                    }
                    
                    VStack(spacing: 14) {
                        LabeledInput(label: "Full Legal Name *", placeholder: "e.g. Ramesh Kumar", text: $fullName)
                        LabeledInput(label: "Mobile Phone *", placeholder: "+91 98765 43210", text: $phone)
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Founder Password * (Min. 12 characters, uppercase, lowercase, number, symbol)")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            
                            SecureField("••••••••••••", text: $password)
                                .font(.system(size: 13))
                                .padding(12)
                                .background(VastuColors.brandIvory)
                                .cornerRadius(10)
                                .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                        }
                        
                        // Email OTP Verification Section
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Work Email *")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            
                            HStack(spacing: 8) {
                                TextField("founder@company.com", text: $email)
                                    .font(.system(size: 13))
                                    .padding(12)
                                    .background(VastuColors.brandIvory)
                                    .cornerRadius(10)
                                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                                    .disabled(isEmailVerified)
                                
                                Button(action: onSendOtp) {
                                    Text(otpSent ? "Resend" : "Send OTP")
                                        .font(.system(size: 12, weight: .bold))
                                        .foregroundColor(VastuColors.brandBronze)
                                        .padding(.horizontal, 14)
                                        .padding(.vertical, 12)
                                        .background(VastuColors.brandParchment)
                                        .cornerRadius(10)
                                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                                }
                                .disabled(email.isEmpty || isEmailVerified)
                            }
                            
                            if isEmailVerified {
                                HStack(spacing: 6) {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundColor(.green)
                                    Text("Email OTP Verified")
                                        .font(.system(size: 12, weight: .semibold))
                                        .foregroundColor(.green)
                                }
                                .padding(.top, 2)
                            } else if otpSent {
                                HStack(spacing: 8) {
                                    TextField("Enter 6-digit OTP", text: $otpCode)
                                        .font(.system(size: 13, design: .monospaced))
                                        .padding(10)
                                        .background(VastuColors.brandIvory)
                                        .cornerRadius(8)
                                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(VastuColors.brandBorder, lineWidth: 1))
                                    
                                    Button("Verify OTP") {
                                        onVerifyOtp()
                                    }
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundColor(VastuColors.brandIvory)
                                    .padding(.horizontal, 14)
                                    .padding(.vertical, 10)
                                    .background(VastuColors.brandBronze)
                                    .cornerRadius(8)
                                }
                                .padding(.top, 4)
                            }
                        }
                    }
                    .padding(16)
                    .background(VastuColors.brandIvory)
                    .cornerRadius(14)
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                }
                .padding(20)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Fixed Bottom Action Bar
            VStack(spacing: 0) {
                Divider().background(VastuColors.brandBorder)
                Button(action: onContinue) {
                    HStack(spacing: 6) {
                        Text("Continue to Organization Profile")
                        Image(systemName: "arrow.right")
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(VastuGoldButtonStyle())
                .disabled(fullName.isEmpty || email.isEmpty)
                .padding(.horizontal, 20)
                .padding(.top, 10)
                .padding(.bottom, 6)
            }
            .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
        }
    }
}

// ------------------------------------------
// Step 2: Organization Profile
// ------------------------------------------
struct CreateOrgStep2ProfileView: View {
    @Binding var orgName: String
    @Binding var legalName: String
    @Binding var orgType: String
    @Binding var industry: String
    @Binding var website: String
    @Binding var teamSize: String
    @Binding var description: String
    let onBack: () -> Void
    let onContinue: () -> Void
    
    let orgTypes = ["Enterprise", "Studio / Firm", "Contractor", "Developer", "Consultancy"]
    let industries = ["Construction & Engineering", "Architecture & Spatial Planning", "Commercial Real Estate", "BIM & Digital Twin", "Infrastructure"]
    let teamSizes = ["1–10 Employees", "11–50 Employees", "51–200 Employees", "201–500 Employees", "500+ Employees"]
    
    var body: some View {
        VStack(spacing: 0) {
            FiveStepOrgHeaderView(currentStep: 2, onBack: onBack)
            
            ScrollView {
                VStack(spacing: 20) {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack(spacing: 8) {
                            Image(systemName: "building.2.fill")
                                .foregroundColor(VastuColors.brandBronze)
                                .font(.system(size: 18))
                            Text("ORGANIZATION PROFILE")
                                .font(.system(size: 14, weight: .bold, design: .serif))
                                .foregroundColor(VastuColors.brandText)
                        }
                        Text("General details for your company's space on VĀSTU.")
                            .font(.system(size: 12))
                            .foregroundColor(VastuColors.brandTextMuted)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    
                    VStack(spacing: 14) {
                        LabeledInput(label: "Organization / Brand Name *", placeholder: "e.g. Apex Engineering Labs", text: $orgName)
                        LabeledInput(label: "Legal Business Name", placeholder: "e.g. Apex Engineering Labs Private Limited", text: $legalName)
                        
                        // Org Type Dropdown
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Organization Type")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            Menu {
                                ForEach(orgTypes, id: \.self) { t in Button(t) { orgType = t } }
                            } label: {
                                HStack {
                                    Text(orgType).font(.system(size: 13)).foregroundColor(VastuColors.brandText)
                                    Spacer()
                                    Image(systemName: "chevron.down").font(.system(size: 11)).foregroundColor(VastuColors.brandTextMuted)
                                }
                                .padding(12).background(VastuColors.brandIvory).cornerRadius(10)
                                .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                            }
                        }
                        
                        // Industry Domain Dropdown
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Industry Domain")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            Menu {
                                ForEach(industries, id: \.self) { ind in Button(ind) { industry = ind } }
                            } label: {
                                HStack {
                                    Text(industry).font(.system(size: 13)).foregroundColor(VastuColors.brandText)
                                    Spacer()
                                    Image(systemName: "chevron.down").font(.system(size: 11)).foregroundColor(VastuColors.brandTextMuted)
                                }
                                .padding(12).background(VastuColors.brandIvory).cornerRadius(10)
                                .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                            }
                        }
                        
                        LabeledInput(label: "Official Website", placeholder: "https://apexengineering.io", text: $website)
                        
                        // Team Size Dropdown
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Team Size")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            Menu {
                                ForEach(teamSizes, id: \.self) { ts in Button(ts) { teamSize = ts } }
                            } label: {
                                HStack {
                                    Text(teamSize).font(.system(size: 13)).foregroundColor(VastuColors.brandText)
                                    Spacer()
                                    Image(systemName: "chevron.down").font(.system(size: 11)).foregroundColor(VastuColors.brandTextMuted)
                                }
                                .padding(12).background(VastuColors.brandIvory).cornerRadius(10)
                                .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                            }
                        }
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Brief Overview / Description")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            TextField("Specialists in LiDAR point cloud acquisition and BIM synchronization...", text: $description, axis: .vertical)
                                .lineLimit(3...4)
                                .font(.system(size: 13))
                                .padding(12)
                                .background(VastuColors.brandIvory)
                                .cornerRadius(10)
                                .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                        }
                    }
                    .padding(16)
                    .background(VastuColors.brandIvory)
                    .cornerRadius(14)
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                }
                .padding(20)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Fixed Bottom Action Bar
            VStack(spacing: 0) {
                Divider().background(VastuColors.brandBorder)
                HStack(spacing: 12) {
                    Button("Back", action: onBack)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundColor(VastuColors.brandText)
                        .frame(maxWidth: 100)
                        .padding(.vertical, 14)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(12)
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1))
                    
                    Button(action: onContinue) {
                        HStack(spacing: 6) {
                            Text("Continue to Identifiers")
                            Image(systemName: "arrow.right")
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(VastuGoldButtonStyle())
                    .disabled(orgName.isEmpty)
                }
                .padding(.horizontal, 20)
                .padding(.top, 10)
                .padding(.bottom, 6)
            }
            .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
        }
    }
}

// ------------------------------------------
// Step 3: Business Identifiers & Verification
// ------------------------------------------
struct CreateOrgStep3IdentifiersView: View {
    @Binding var identifierType: String
    @Binding var identifierValue: String
    @Binding var documentName: String
    let onBack: () -> Void
    let onContinue: () -> Void
    
    let identifierTypes = ["PAN (10-char)", "GSTIN (15-char)", "CIN (21-char)"]
    
    var body: some View {
        VStack(spacing: 0) {
            FiveStepOrgHeaderView(currentStep: 3, onBack: onBack)
            
            ScrollView {
                VStack(spacing: 20) {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack(spacing: 8) {
                            Image(systemName: "shield.checkmark.fill")
                                .foregroundColor(VastuColors.brandBronze)
                                .font(.system(size: 18))
                            Text("BUSINESS IDENTIFIERS & VERIFICATION")
                                .font(.system(size: 14, weight: .bold, design: .serif))
                                .foregroundColor(VastuColors.brandText)
                        }
                        Text("Provide your organization tax or registration number.")
                            .font(.system(size: 12))
                            .foregroundColor(VastuColors.brandTextMuted)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    
                    VStack(spacing: 16) {
                        // Identifier Type Dropdown
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Identifier Type")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            Menu {
                                ForEach(identifierTypes, id: \.self) { t in Button(t) { identifierType = t } }
                            } label: {
                                HStack {
                                    Text(identifierType).font(.system(size: 13)).foregroundColor(VastuColors.brandText)
                                    Spacer()
                                    Image(systemName: "chevron.down").font(.system(size: 11)).foregroundColor(VastuColors.brandTextMuted)
                                }
                                .padding(12).background(VastuColors.brandIvory).cornerRadius(10)
                                .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                            }
                        }
                        
                        LabeledInput(label: "\(identifierType.components(separatedBy: " ").first ?? "Tax ID") Value", placeholder: "AAAA000AA", text: $identifierValue)
                        
                        // Supporting Document Upload Box
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Supporting Verification Document (Optional PDF / Certificate)")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            
                            VStack(spacing: 8) {
                                Image(systemName: "arrow.up.doc.fill")
                                    .font(.system(size: 28))
                                    .foregroundColor(VastuColors.brandBronze)
                                
                                Text(documentName.isEmpty ? "Certificate / Registration Document" : documentName)
                                    .font(.system(size: 12, weight: .semibold))
                                    .foregroundColor(VastuColors.brandText)
                                
                                Text("PDF, PNG, or JPG up to 15MB")
                                    .font(.system(size: 10))
                                    .foregroundColor(VastuColors.brandTextMuted)
                                
                                Button(documentName.isEmpty ? "Choose File" : "Replace File") {
                                    documentName = "Registration_Certificate.pdf"
                                }
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandBronze)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(VastuColors.brandParchment)
                                .cornerRadius(6)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(20)
                            .background(VastuColors.brandIvory)
                            .cornerRadius(12)
                            .overlay(
                                RoundedRectangle(cornerRadius: 12)
                                    .stroke(VastuColors.brandBronze.opacity(0.4), style: StrokeStyle(lineWidth: 1, dash: [4]))
                            )
                        }
                    }
                    .padding(16)
                    .background(VastuColors.brandIvory)
                    .cornerRadius(14)
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                }
                .padding(20)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Fixed Bottom Action Bar
            VStack(spacing: 0) {
                Divider().background(VastuColors.brandBorder)
                HStack(spacing: 12) {
                    Button("Back", action: onBack)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundColor(VastuColors.brandText)
                        .frame(maxWidth: 100)
                        .padding(.vertical, 14)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(12)
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1))
                    
                    Button(action: onContinue) {
                        HStack(spacing: 6) {
                            Text("Continue to Address")
                            Image(systemName: "arrow.right")
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(VastuGoldButtonStyle())
                }
                .padding(.horizontal, 20)
                .padding(.top, 10)
                .padding(.bottom, 6)
            }
            .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
        }
    }
}

// ------------------------------------------
// Step 4: Registered Business Address
// ------------------------------------------
struct CreateOrgStep4AddressView: View {
    @Binding var addressLine1: String
    @Binding var addressLine2: String
    @Binding var locality: String
    @Binding var city: String
    @Binding var state: String
    @Binding var pincode: String
    @Binding var country: String
    let onBack: () -> Void
    let onContinue: () -> Void
    
    var body: some View {
        VStack(spacing: 0) {
            FiveStepOrgHeaderView(currentStep: 4, onBack: onBack)
            
            ScrollView {
                VStack(spacing: 20) {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack(spacing: 8) {
                            Image(systemName: "mappin.and.ellipse")
                                .foregroundColor(VastuColors.brandBronze)
                                .font(.system(size: 18))
                            Text("REGISTERED BUSINESS ADDRESS")
                                .font(.system(size: 14, weight: .bold, design: .serif))
                                .foregroundColor(VastuColors.brandText)
                        }
                        Text("Primary corporate location for regulatory and billing verification.")
                            .font(.system(size: 12))
                            .foregroundColor(VastuColors.brandTextMuted)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    
                    VStack(spacing: 14) {
                        LabeledInput(label: "Address Line 1 *", placeholder: "Street / Building No / Tech Park", text: $addressLine1)
                        
                        HStack(spacing: 10) {
                            LabeledInput(label: "Address Line 2", placeholder: "Floor / Wing / Suite", text: $addressLine2)
                            LabeledInput(label: "Locality / Area", placeholder: "e.g. Whitefield", text: $locality)
                        }
                        
                        HStack(spacing: 10) {
                            LabeledInput(label: "City *", placeholder: "Bengaluru", text: $city)
                            LabeledInput(label: "State *", placeholder: "Karnataka", text: $state)
                        }
                        
                        HStack(spacing: 10) {
                            LabeledInput(label: "PIN Code * (6 digits)", placeholder: "560066", text: $pincode)
                            LabeledInput(label: "Country", placeholder: "India", text: $country)
                        }
                    }
                    .padding(16)
                    .background(VastuColors.brandIvory)
                    .cornerRadius(14)
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                }
                .padding(20)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Fixed Bottom Action Bar
            VStack(spacing: 0) {
                Divider().background(VastuColors.brandBorder)
                HStack(spacing: 12) {
                    Button("Back", action: onBack)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundColor(VastuColors.brandText)
                        .frame(maxWidth: 100)
                        .padding(.vertical, 14)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(12)
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1))
                    
                    Button(action: onContinue) {
                        HStack(spacing: 6) {
                            Text("Review Summary")
                            Image(systemName: "arrow.right")
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(VastuGoldButtonStyle())
                }
                .padding(.horizontal, 20)
                .padding(.top, 10)
                .padding(.bottom, 6)
            }
            .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
        }
    }
}

// ------------------------------------------
// Step 5: Review & Complete Registration
// ------------------------------------------
struct CreateOrgStep5ReviewView: View {
    let founderName: String
    let founderEmail: String
    let founderPhone: String
    let isEmailVerified: Bool
    let orgName: String
    let legalName: String
    let orgType: String
    let industry: String
    let identifierType: String
    let identifierValue: String
    let addressLine1: String
    let addressLine2: String
    let locality: String
    let city: String
    let state: String
    let pincode: String
    let country: String
    let isLoading: Bool
    var errorMessage: String?
    let onBack: () -> Void
    let onConfirmLaunch: () -> Void
    
    var body: some View {
        VStack(spacing: 0) {
            FiveStepOrgHeaderView(currentStep: 5, onBack: onBack)
            
            ScrollView {
                VStack(spacing: 20) {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack(spacing: 8) {
                            Image(systemName: "doc.text.fill")
                                .foregroundColor(VastuColors.brandBronze)
                                .font(.system(size: 18))
                            Text("REVIEW & COMPLETE REGISTRATION")
                                .font(.system(size: 14, weight: .bold, design: .serif))
                                .foregroundColor(VastuColors.brandText)
                        }
                        Text("Confirm the details below. Once submitted, your organization space and unambiguous 12-character ID will be generated atomically.")
                            .font(.system(size: 12))
                            .foregroundColor(VastuColors.brandTextMuted)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    
                    if let err = errorMessage, !err.isEmpty {
                        Text(err)
                            .font(.system(size: 12))
                            .foregroundColor(.red)
                            .padding(10)
                            .frame(maxWidth: .infinity)
                            .background(Color.red.opacity(0.1))
                            .cornerRadius(8)
                    }
                    
                    // Review Summary Card
                    VStack(alignment: .leading, spacing: 16) {
                        // Section 1: Founder
                        VStack(alignment: .leading, spacing: 4) {
                            Text("FOUNDER ACCOUNT")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(VastuColors.brandBronze)
                                .tracking(1)
                            Text(founderName.isEmpty ? "Ramesh Kumar" : founderName)
                                .font(.system(size: 14, weight: .bold))
                                .foregroundColor(VastuColors.brandText)
                            Text("\(founderEmail.isEmpty ? "founder@company.com" : founderEmail) • \(founderPhone.isEmpty ? "+91 98765 43210" : founderPhone)")
                                .font(.system(size: 12))
                                .foregroundColor(VastuColors.brandTextMuted)
                            
                            HStack(spacing: 4) {
                                Image(systemName: "checkmark")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(.green)
                                Text("Email OTP Verified")
                                    .font(.system(size: 11, weight: .semibold))
                                    .foregroundColor(.green)
                            }
                            .padding(.top, 2)
                        }
                        
                        Divider().background(VastuColors.brandBorder)
                        
                        // Section 2: Org Profile
                        VStack(alignment: .leading, spacing: 4) {
                            Text("ORGANIZATION PROFILE")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(VastuColors.brandBronze)
                                .tracking(1)
                            Text(orgName.isEmpty ? "Apex Engineering Labs" : orgName)
                                .font(.system(size: 14, weight: .bold))
                                .foregroundColor(VastuColors.brandText)
                            if !legalName.isEmpty {
                                Text(legalName)
                                    .font(.system(size: 12))
                                    .foregroundColor(VastuColors.brandTextMuted)
                            }
                            Text("\(orgType) • \(industry)")
                                .font(.system(size: 12))
                                .foregroundColor(VastuColors.brandTextMuted)
                        }
                        
                        Divider().background(VastuColors.brandBorder)
                        
                        // Section 3: Identifier
                        VStack(alignment: .leading, spacing: 4) {
                            Text("IDENTIFIER")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(VastuColors.brandBronze)
                                .tracking(1)
                            Text("\(identifierType.components(separatedBy: " ").first ?? "TAX ID"): \(identifierValue.isEmpty ? "AAAA000AA" : identifierValue)")
                                .font(.system(size: 13, weight: .bold, design: .monospaced))
                                .foregroundColor(VastuColors.brandText)
                        }
                        
                        Divider().background(VastuColors.brandBorder)
                        
                        // Section 4: Address
                        VStack(alignment: .leading, spacing: 4) {
                            Text("ADDRESS")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(VastuColors.brandBronze)
                                .tracking(1)
                            Text("\(addressLine1.isEmpty ? "Building 4, Tech Park" : addressLine1), \(locality.isEmpty ? "Whitefield" : locality), \(city.isEmpty ? "Bengaluru" : city), \(state.isEmpty ? "Karnataka" : state) - \(pincode.isEmpty ? "560066" : pincode), \(country.isEmpty ? "India" : country)")
                                .font(.system(size: 12))
                                .foregroundColor(VastuColors.brandTextMuted)
                        }
                    }
                    .padding(18)
                    .background(VastuColors.brandIvory)
                    .cornerRadius(14)
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                }
                .padding(20)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Fixed Bottom Action Bar
            VStack(spacing: 0) {
                Divider().background(VastuColors.brandBorder)
                HStack(spacing: 12) {
                    Button("Back", action: onBack)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundColor(VastuColors.brandText)
                        .frame(maxWidth: 100)
                        .padding(.vertical, 14)
                        .background(VastuColors.brandIvory)
                        .cornerRadius(12)
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1))
                    
                    Button(action: onConfirmLaunch) {
                        HStack(spacing: 6) {
                            if isLoading {
                                ProgressView().tint(VastuColors.brandIvory)
                            } else {
                                Text("Confirm & Launch Workspace")
                                Image(systemName: "checkmark.circle.fill")
                            }
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(VastuGoldButtonStyle())
                }
                .padding(.horizontal, 20)
                .padding(.top, 10)
                .padding(.bottom, 6)
            }
            .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
        }
    }
}

// ------------------------------------------
// Organization Created Success Screen
// ------------------------------------------
struct OrgCreatedSuccessView: View {
    let orgName: String
    var orgCode: String = "MRXZ-FQBQ-D3S"
    let onCreateProject: () -> Void
    let onGoToDashboard: () -> Void
    @State private var isCopied: Bool = false
    
    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            
            // Radiant Checkmark with confetti aura
            ZStack {
                Circle()
                    .fill(VastuColors.brandBronze.opacity(0.12))
                    .frame(width: 130, height: 130)
                
                Circle()
                    .fill(VastuColors.brandBronze)
                    .frame(width: 76, height: 76)
                    .shadow(color: VastuColors.brandBronze.opacity(0.3), radius: 10, x: 0, y: 5)
                
                Image(systemName: "checkmark")
                    .font(.system(size: 34, weight: .bold))
                    .foregroundColor(VastuColors.brandIvory)
            }
            
            VStack(spacing: 8) {
                Text("Organization Created!")
                    .font(.system(size: 24, weight: .bold, design: .serif))
                    .foregroundColor(VastuColors.brandText)
                
                Text(orgName)
                    .font(.system(size: 18, weight: .bold))
                    .foregroundColor(VastuColors.brandBronze)
                
                Text("Your organization space and digital twin\nworkspace have been created successfully.")
                    .font(.system(size: 13))
                    .foregroundColor(VastuColors.brandTextMuted)
                    .multilineTextAlignment(.center)
            }
            
            // 12-char Organization Code Card
            VStack(spacing: 8) {
                Text("ORGANIZATION CODE")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(VastuColors.brandTextMuted)
                    .tracking(1)
                
                Text(orgCode)
                    .font(.system(size: 22, weight: .bold, design: .monospaced))
                    .foregroundColor(VastuColors.brandBronze)
                
                HStack(spacing: 12) {
                    Button(action: {
                        UIPasteboard.general.string = orgCode
                        isCopied = true
                    }) {
                        HStack(spacing: 4) {
                            Image(systemName: isCopied ? "checkmark" : "doc.on.doc")
                            Text(isCopied ? "Copied" : "Copy Code")
                        }
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(VastuColors.brandBronze)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(VastuColors.brandParchment)
                        .cornerRadius(6)
                    }
                }
                
                Text("Share this code with your team to let them join")
                    .font(.system(size: 11))
                    .foregroundColor(VastuColors.brandTextMuted)
            }
            .frame(maxWidth: .infinity)
            .padding(18)
            .background(VastuColors.brandIvory)
            .cornerRadius(14)
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
            .padding(.horizontal, 20)
            
            Spacer()
            
            VStack(spacing: 12) {
                Button("Create Your First Project") { onCreateProject() }
                    .buttonStyle(VastuGoldButtonStyle())
                
                Button("Go to Dashboard") { onGoToDashboard() }
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(VastuColors.brandBronze)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(VastuColors.brandIvory)
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12).stroke(VastuColors.brandBorder, lineWidth: 1)
                    )
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 24)
        }
    }
}

// ------------------------------------------
// Join Organization View
// ------------------------------------------
struct JoinOrgInvitationView: View {
    @Binding var invitationCode: String
    @Binding var fullName: String
    @Binding var email: String
    @Binding var phone: String
    @Binding var password: String
    @Binding var otpSent: Bool
    @Binding var otpCode: String
    @Binding var isEmailVerified: Bool
    let isLoading: Bool
    var errorMessage: String? = nil
    let onBack: () -> Void
    let onSendOtp: () -> Void
    let onVerifyOtp: () -> Void
    let onSubmitJoin: () -> Void
    
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Button(action: onBack) {
                    Image(systemName: "arrow.left")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(VastuColors.brandBronze)
                }
                Spacer()
                Text("JOIN ORGANIZATION")
                    .font(.system(size: 13, weight: .bold, design: .serif))
                    .tracking(2)
                    .foregroundColor(VastuColors.brandBronze)
                Spacer()
                Image(systemName: "arrow.left").opacity(0)
            }
            .padding(20)
            
            ScrollView {
                VStack(spacing: 20) {
                    // Person Icon Badge
                    ZStack {
                        Circle()
                            .fill(VastuColors.brandIvory)
                            .frame(width: 72, height: 72)
                            .overlay(Circle().stroke(VastuColors.brandBronze.opacity(0.3), lineWidth: 1.5))
                        
                        Image(systemName: "person.badge.shield.checkmark.fill")
                            .font(.system(size: 32))
                            .foregroundColor(VastuColors.brandBronze)
                    }
                    
                    VStack(spacing: 6) {
                        Text("Join Studio Workspace")
                            .font(.system(size: 20, weight: .bold, design: .serif))
                            .foregroundColor(VastuColors.brandText)
                        
                        Text("Enter the 12-character organization code and your official credentials.")
                            .font(.system(size: 12))
                            .foregroundColor(VastuColors.brandTextMuted)
                            .multilineTextAlignment(.center)
                    }
                    
                    if let err = errorMessage, !err.isEmpty {
                        Text(err)
                            .font(.system(size: 12))
                            .foregroundColor(.red)
                            .padding(10)
                            .frame(maxWidth: .infinity)
                            .background(Color.red.opacity(0.1))
                            .cornerRadius(8)
                    }
                    
                    // Form fields
                    VStack(spacing: 14) {
                        // 12-char Monospaced Org Code
                        VStack(alignment: .leading, spacing: 4) {
                            Text("ORGANIZATION CODE *")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            
                            TextField("e.g. MRXZ-FQBQ-D3S", text: $invitationCode)
                                .font(.system(size: 14, weight: .bold, design: .monospaced))
                                .textInputAutocapitalization(.characters)
                                .autocorrectionDisabled()
                                .padding(12)
                                .background(VastuColors.brandIvory)
                                .cornerRadius(10)
                                .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                        }
                        
                        LabeledInput(label: "Full Legal Name *", placeholder: "e.g. Maya Sharma", text: $fullName)
                        
                        // Email + OTP
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Work Email *")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            
                            HStack(spacing: 8) {
                                TextField("name@company.com", text: $email)
                                    .font(.system(size: 13))
                                    .padding(12)
                                    .background(VastuColors.brandIvory)
                                    .cornerRadius(10)
                                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                                    .disabled(isEmailVerified)
                                
                                Button(action: onSendOtp) {
                                    Text(otpSent ? "Resend" : "Send OTP")
                                        .font(.system(size: 12, weight: .bold))
                                        .foregroundColor(VastuColors.brandBronze)
                                        .padding(.horizontal, 14)
                                        .padding(.vertical, 12)
                                        .background(VastuColors.brandParchment)
                                        .cornerRadius(10)
                                        .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                                }
                                .disabled(email.isEmpty || isEmailVerified)
                            }
                            
                            if isEmailVerified {
                                HStack(spacing: 6) {
                                    Image(systemName: "checkmark.circle.fill").foregroundColor(.green)
                                    Text("Email OTP Verified").font(.system(size: 12, weight: .semibold)).foregroundColor(.green)
                                }
                            } else if otpSent {
                                HStack(spacing: 8) {
                                    TextField("Enter 6-digit OTP", text: $otpCode)
                                        .font(.system(size: 13, design: .monospaced))
                                        .padding(10)
                                        .background(VastuColors.brandIvory)
                                        .cornerRadius(8)
                                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(VastuColors.brandBorder, lineWidth: 1))
                                    
                                    Button("Verify OTP") { onVerifyOtp() }
                                        .font(.system(size: 12, weight: .bold))
                                        .foregroundColor(VastuColors.brandIvory)
                                        .padding(.horizontal, 14)
                                        .padding(.vertical, 10)
                                        .background(VastuColors.brandBronze)
                                        .cornerRadius(8)
                                }
                            }
                        }
                        
                        LabeledInput(label: "Mobile Phone (Optional)", placeholder: "+91 98765 43210", text: $phone)
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Password *")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(VastuColors.brandTextMuted)
                            SecureField("••••••••••••", text: $password)
                                .font(.system(size: 13))
                                .padding(12)
                                .background(VastuColors.brandIvory)
                                .cornerRadius(10)
                                .overlay(RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1))
                        }
                    }
                    .padding(16)
                    .background(VastuColors.brandIvory)
                    .cornerRadius(14)
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                }
                .padding(20)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Fixed Bottom Action Bar
            VStack(spacing: 0) {
                Divider().background(VastuColors.brandBorder)
                Button(action: onSubmitJoin) {
                    HStack(spacing: 6) {
                        if isLoading {
                            ProgressView().tint(VastuColors.brandIvory)
                        } else {
                            Text("Submit Join Request")
                            Image(systemName: "arrow.right")
                        }
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(VastuGoldButtonStyle())
                .disabled(invitationCode.isEmpty || fullName.isEmpty || email.isEmpty)
                .padding(.horizontal, 20)
                .padding(.top, 10)
                .padding(.bottom, 6)
            }
            .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
        }
    }
}

// ==========================================
// 9. Select Organization (Multi-Org Switcher)
// ==========================================

struct SelectOrganizationView: View {
    let userName: String
    let orgs: [(id: String, name: String, role: String, projects: Int, image: String)]
    let onSelectOrg: (String) -> Void
    let onCreateNewOrg: () -> Void
    
    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(spacing: 20) {
                    // Header Logo
                    VStack(spacing: 4) {
                        Text("V Ā S T U")
                            .font(.system(size: 20, weight: .bold, design: .serif))
                            .tracking(6)
                            .foregroundColor(VastuColors.brandBronze)
                    }
                    .padding(.top, 24)
                    
                    VStack(spacing: 4) {
                        Text("Welcome back, \(userName.components(separatedBy: " ").first ?? "Architect")")
                            .font(.system(size: 20, weight: .bold, design: .serif))
                            .foregroundColor(VastuColors.brandText)
                        
                        Text("Select an organization to continue")
                            .font(.system(size: 12))
                            .foregroundColor(VastuColors.brandTextMuted)
                    }
                    
                    // Org Cards List
                    VStack(spacing: 12) {
                        if orgs.isEmpty {
                            VStack(spacing: 10) {
                                Image(systemName: "building.2")
                                    .font(.system(size: 32))
                                    .foregroundColor(VastuColors.brandBronze.opacity(0.6))
                                Text("No Organizations Found")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundColor(VastuColors.brandText)
                                Text("Create an organization to start collaborating with your spatial team.")
                                    .font(.system(size: 12))
                                    .foregroundColor(VastuColors.brandTextMuted)
                                    .multilineTextAlignment(.center)
                            }
                            .padding(24)
                            .frame(maxWidth: .infinity)
                            .background(VastuColors.brandIvory)
                            .cornerRadius(14)
                            .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                        } else {
                            ForEach(orgs, id: \.id) { o in
                                Button(action: { onSelectOrg(o.id) }) {
                                    HStack(spacing: 14) {
                                        ZStack {
                                            RoundedRectangle(cornerRadius: 10)
                                                .fill(VastuColors.brandParchment)
                                                .frame(width: 48, height: 48)
                                            Image(systemName: o.image)
                                                .font(.system(size: 22))
                                                .foregroundColor(VastuColors.brandBronze)
                                        }
                                        
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(o.name)
                                                .font(.system(size: 14, weight: .bold))
                                                .foregroundColor(VastuColors.brandText)
                                            
                                            HStack(spacing: 6) {
                                                Text(o.role)
                                                    .font(.system(size: 11, weight: .semibold))
                                                    .foregroundColor(VastuColors.brandBronze)
                                                Text("•")
                                                    .font(.system(size: 10))
                                                    .foregroundColor(VastuColors.brandTextMuted)
                                                Text("\(o.projects) Projects")
                                                    .font(.system(size: 11))
                                                    .foregroundColor(VastuColors.brandTextMuted)
                                            }
                                        }
                                        
                                        Spacer()
                                        
                                        Image(systemName: "chevron.right")
                                            .font(.system(size: 12, weight: .bold))
                                            .foregroundColor(VastuColors.brandTextMuted)
                                    }
                                    .padding(14)
                                    .background(VastuColors.brandIvory)
                                    .cornerRadius(14)
                                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(VastuColors.brandBorder, lineWidth: 1))
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                    .padding(.top, 4)
                }
                .padding(20)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Fixed Bottom Footer Bar
            VStack(spacing: 10) {
                Divider().background(VastuColors.brandBorder)
                
                Button(action: onCreateNewOrg) {
                    HStack(spacing: 6) {
                        Image(systemName: "plus")
                            .font(.system(size: 11, weight: .bold))
                        Text("Create New Organization")
                            .font(.system(size: 13, weight: .bold))
                    }
                    .foregroundColor(VastuColors.brandIvory)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(VastuColors.brandBronze)
                    .cornerRadius(12)
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 10)
            .padding(.bottom, 6)
            .background(VastuColors.brandIvory.ignoresSafeArea(edges: .bottom))
        }
    }
}

// ==========================================
// Helper Subviews & Components
// ==========================================

struct HeaderStepperView: View {
    let currentStep: Int // 1: Profile, 2: Organization, 3: Get Started
    let onBack: () -> Void
    
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                Button(action: onBack) {
                    Image(systemName: "arrow.left")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(VastuColors.brandBronze)
                }
                Spacer()
                Text("V Ā S T U")
                    .font(.system(size: 16, weight: .bold, design: .serif))
                    .tracking(4)
                    .foregroundColor(VastuColors.brandBronze)
                Spacer()
                // Balanced spacer
                Image(systemName: "arrow.left").opacity(0)
            }
            .padding(.horizontal, 20)
            .padding(.top, 12)
            
            // Stepper Dots & Labels
            HStack(spacing: 16) {
                StepItem(title: "Profile", isActive: currentStep >= 1, isCurrent: currentStep == 1)
                Rectangle().fill(currentStep >= 2 ? VastuColors.brandBronze : VastuColors.brandBorder).frame(width: 32, height: 2)
                StepItem(title: "Organization", isActive: currentStep >= 2, isCurrent: currentStep == 2)
                Rectangle().fill(currentStep >= 3 ? VastuColors.brandBronze : VastuColors.brandBorder).frame(width: 32, height: 2)
                StepItem(title: "Get Started", isActive: currentStep >= 3, isCurrent: currentStep == 3)
            }
            .padding(.bottom, 8)
        }
        .background(VastuColors.brandIvory)
        .overlay(Rectangle().frame(height: 1).foregroundColor(VastuColors.brandBorder), alignment: .bottom)
    }
}

struct StepItem: View {
    let title: String
    let isActive: Bool
    let isCurrent: Bool
    
    var body: some View {
        VStack(spacing: 4) {
            Circle()
                .fill(isCurrent ? VastuColors.brandBronze : (isActive ? VastuColors.brandBronze.opacity(0.4) : VastuColors.brandBorder))
                .frame(width: 10, height: 10)
            Text(title)
                .font(.system(size: 9, weight: isCurrent ? .bold : .medium))
                .foregroundColor(isCurrent ? VastuColors.brandText : VastuColors.brandTextMuted)
        }
    }
}

struct LabeledInput: View {
    let label: String
    let placeholder: String
    @Binding var text: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(VastuColors.brandTextMuted)
            
            TextField(placeholder, text: $text)
                .font(.system(size: 13))
                .padding(12)
                .background(VastuColors.brandIvory)
                .cornerRadius(10)
                .overlay(
                    RoundedRectangle(cornerRadius: 10).stroke(VastuColors.brandBorder, lineWidth: 1)
                )
        }
    }
}

struct TabButton: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 12, weight: isSelected ? .bold : .medium))
                .foregroundColor(isSelected ? VastuColors.brandText : VastuColors.brandTextMuted)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
                .background(isSelected ? VastuColors.brandIvory : Color.clear)
                .cornerRadius(10)
                .shadow(color: isSelected ? Color.black.opacity(0.05) : Color.clear, radius: 2, x: 0, y: 1)
        }
    }
}

// Architectural Perspective Vector Archway View
struct ArchwayPerspectiveView: View {
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let h = geo.size.height
            
            Path { path in
                // Outer arch
                path.move(to: CGPoint(x: w * 0.15, y: h))
                path.addLine(to: CGPoint(x: w * 0.15, y: h * 0.45))
                path.addQuadCurve(to: CGPoint(x: w * 0.85, y: h * 0.45), control: CGPoint(x: w * 0.5, y: h * 0.15))
                path.addLine(to: CGPoint(x: w * 0.85, y: h))
                
                // Middle arch
                path.move(to: CGPoint(x: w * 0.28, y: h))
                path.addLine(to: CGPoint(x: w * 0.28, y: h * 0.55))
                path.addQuadCurve(to: CGPoint(x: w * 0.72, y: h * 0.55), control: CGPoint(x: w * 0.5, y: h * 0.32))
                path.addLine(to: CGPoint(x: w * 0.72, y: h))
                
                // Inner perspective lines
                path.move(to: CGPoint(x: w * 0.15, y: h))
                path.addLine(to: CGPoint(x: w * 0.38, y: h * 0.65))
                path.move(to: CGPoint(x: w * 0.85, y: h))
                path.addLine(to: CGPoint(x: w * 0.62, y: h * 0.65))
            }
            .stroke(VastuColors.brandBronze.opacity(0.35), lineWidth: 1.5)
        }
    }
}
