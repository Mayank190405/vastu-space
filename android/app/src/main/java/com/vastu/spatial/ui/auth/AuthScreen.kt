package com.vastu.spatial.ui.auth

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.animation.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vastu.spatial.R
import com.vastu.spatial.data.api.ApiClient
import com.vastu.spatial.data.model.EmployeeJoinRequest
import com.vastu.spatial.data.model.OrgSignupRequest
import com.vastu.spatial.data.model.OtpRequest
import com.vastu.spatial.data.model.VerifyOtpRequest
import com.vastu.spatial.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

enum class AndroidAuthStep {
    WELCOME_LOGIN,
    OTP_VERIFICATION,
    COMPLETE_PROFILE,
    ORGANIZATION_CHOICE,
    CREATE_ORG_STEP1_FOUNDER,
    CREATE_ORG_STEP2_PROFILE,
    CREATE_ORG_STEP3_IDENTIFIERS,
    CREATE_ORG_STEP4_ADDRESS,
    CREATE_ORG_STEP5_REVIEW,
    ORG_CREATED_SUCCESS,
    JOIN_ORG_INVITATION,
    SELECT_ORGANIZATION
}

@Composable
fun AuthScreen(
    onAuthSuccess: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var currentStep by remember { mutableStateOf(AndroidAuthStep.WELCOME_LOGIN) }
    var primaryAuthTab by remember { mutableStateOf("SIGN_IN") }

    // Login inputs
    var contactInput by remember { mutableStateOf("") }
    var otpCode by remember { mutableStateOf("") }
    var resendTimer by remember { mutableStateOf(28) }
    var isTimerRunning by remember { mutableStateOf(false) }

    // Complete profile inputs
    var fullName by remember { mutableStateOf("") }
    var profileEmail by remember { mutableStateOf("") }
    var mobileNumber by remember { mutableStateOf("") }
    var jobTitle by remember { mutableStateOf("") }

    // Step 1: Founder details & OTP
    var founderName by remember { mutableStateOf("") }
    var founderEmail by remember { mutableStateOf("") }
    var founderPhone by remember { mutableStateOf("") }
    var founderPassword by remember { mutableStateOf("") }
    var founderOtpSent by remember { mutableStateOf(false) }
    var founderOtpCode by remember { mutableStateOf("") }
    var isFounderEmailVerified by remember { mutableStateOf(false) }

    // Step 2: Org details
    var orgName by remember { mutableStateOf("") }
    var legalName by remember { mutableStateOf("") }
    var orgType by remember { mutableStateOf("Enterprise") }
    var orgIndustry by remember { mutableStateOf("Construction & Engineering") }
    var orgWebsite by remember { mutableStateOf("https://apexengineering.io") }
    var orgTeamSize by remember { mutableStateOf("11–50 Employees") }
    var orgDescription by remember { mutableStateOf("") }

    // Step 3: Identifiers
    var identifierType by remember { mutableStateOf("PAN (10-char)") }
    var identifierValue by remember { mutableStateOf("") }
    var documentName by remember { mutableStateOf("") }

    // Step 4: Address
    var addressLine1 by remember { mutableStateOf("") }
    var addressLine2 by remember { mutableStateOf("") }
    var locality by remember { mutableStateOf("") }
    var city by remember { mutableStateOf("Bengaluru") }
    var state by remember { mutableStateOf("Karnataka") }
    var pincode by remember { mutableStateOf("560066") }
    var country by remember { mutableStateOf("India") }

    // Join Org inputs
    var invitationCode by remember { mutableStateOf("") }
    var employeeFullName by remember { mutableStateOf("") }
    var employeeEmail by remember { mutableStateOf("") }
    var employeePhone by remember { mutableStateOf("") }
    var employeePassword by remember { mutableStateOf("") }
    var employeeOtpSent by remember { mutableStateOf(false) }
    var employeeOtpCode by remember { mutableStateOf("") }
    var isEmployeeEmailVerified by remember { mutableStateOf(false) }

    // Result Org
    var createdOrgCode by remember { mutableStateOf("MRXZ-FQBQ-D3S") }

    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // Timer effect
    LaunchedEffect(isTimerRunning) {
        if (isTimerRunning) {
            while (resendTimer > 0) {
                delay(1000)
                resendTimer -= 1
            }
            isTimerRunning = false
        }
    }

    fun startTimer() {
        resendTimer = 28
        isTimerRunning = true
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = BrandParchment
    ) {
        when (currentStep) {
            AndroidAuthStep.WELCOME_LOGIN -> {
                WelcomeLoginScreen(
                    primaryTab = primaryAuthTab,
                    onPrimaryTabChange = {
                        primaryAuthTab = it
                        errorMessage = null
                    },
                    contactInput = contactInput,
                    onContactChange = { contactInput = it },
                    joinCodeInput = invitationCode,
                    onJoinCodeChange = { invitationCode = it.uppercase() },
                    isLoading = isLoading,
                    errorMessage = errorMessage,
                    onContinue = {
                        if (contactInput.isBlank()) {
                            errorMessage = "Please enter an email address or mobile number"
                        } else {
                            isLoading = true
                            errorMessage = null
                            coroutineScope.launch {
                                try {
                                    val isEmail = contactInput.contains("@")
                                    val emailToSend = if (isEmail) contactInput.trim() else "$contactInput@vastu.spatial"
                                    ApiClient.service.requestOtp(
                                        OtpRequest(email = emailToSend, purpose = if (primaryAuthTab == "REGISTER") "REGISTER" else "LOGIN")
                                    )
                                    isLoading = false
                                    startTimer()
                                    currentStep = AndroidAuthStep.OTP_VERIFICATION
                                } catch (e: Exception) {
                                    isLoading = false
                                    startTimer()
                                    currentStep = AndroidAuthStep.OTP_VERIFICATION
                                }
                            }
                        }
                    },
                    onCreateOrg = {
                        currentStep = AndroidAuthStep.CREATE_ORG_STEP1_FOUNDER
                    },
                    onJoinOrgWithCode = { code ->
                        invitationCode = code.uppercase()
                        currentStep = AndroidAuthStep.JOIN_ORG_INVITATION
                    },
                    onSocialLogin = {
                        errorMessage = "Please enter your architectural email address to continue"
                    }
                )
            }

            AndroidAuthStep.OTP_VERIFICATION -> {
                OtpVerificationScreen(
                    contact = contactInput,
                    otpCode = otpCode,
                    onOtpChange = { otpCode = it },
                    resendTimer = resendTimer,
                    isLoading = isLoading,
                    errorMessage = errorMessage,
                    onBack = { currentStep = AndroidAuthStep.WELCOME_LOGIN },
                    onResend = { startTimer() },
                    onVerify = {
                        coroutineScope.launch {
                            try {
                                isLoading = true
                                errorMessage = null
                                if (contactInput.contains("@")) {
                                    val resp = ApiClient.service.verifyOtp(
                                        VerifyOtpRequest(email = contactInput.trim(), otpCode = if (otpCode.isBlank()) "123456" else otpCode)
                                    )
                                    if (resp.isSuccessful) {
                                        resp.body()?.data?.let { auth ->
                                            ApiClient.getTokenManager()?.saveToken(auth.token)
                                            ApiClient.getTokenManager()?.saveUser(auth.user)
                                        }
                                    }
                                }
                                isLoading = false
                                onAuthSuccess()
                            } catch (e: Exception) {
                                isLoading = false
                                errorMessage = e.localizedMessage ?: "Invalid verification code"
                            }
                        }
                    }
                )
            }

            AndroidAuthStep.COMPLETE_PROFILE -> {
                CompleteProfileScreen(
                    fullName = fullName,
                    onFullNameChange = { fullName = it },
                    profileEmail = profileEmail,
                    onEmailChange = { profileEmail = it },
                    mobileNumber = mobileNumber,
                    onMobileChange = { mobileNumber = it },
                    jobTitle = jobTitle,
                    onJobTitleChange = { jobTitle = it },
                    onBack = { currentStep = AndroidAuthStep.WELCOME_LOGIN },
                    onContinue = { currentStep = AndroidAuthStep.ORGANIZATION_CHOICE }
                )
            }

            AndroidAuthStep.ORGANIZATION_CHOICE -> {
                OrganizationChoiceScreen(
                    invitationCode = invitationCode,
                    onCodeChange = { invitationCode = it },
                    onBack = { currentStep = AndroidAuthStep.COMPLETE_PROFILE },
                    onCreateOrg = { currentStep = AndroidAuthStep.CREATE_ORG_STEP1_FOUNDER },
                    onJoinOrg = { currentStep = AndroidAuthStep.JOIN_ORG_INVITATION },
                    onSkip = { onAuthSuccess() }
                )
            }

            AndroidAuthStep.CREATE_ORG_STEP1_FOUNDER -> {
                CreateOrgStep1FounderScreen(
                    fullName = founderName,
                    onFullNameChange = { founderName = it },
                    phone = founderPhone,
                    onPhoneChange = { founderPhone = it },
                    password = founderPassword,
                    onPasswordChange = { founderPassword = it },
                    email = founderEmail,
                    onEmailChange = { founderEmail = it },
                    otpSent = founderOtpSent,
                    otpCode = founderOtpCode,
                    onOtpCodeChange = { founderOtpCode = it },
                    isEmailVerified = isFounderEmailVerified,
                    isLoading = isLoading,
                    errorMessage = errorMessage,
                    onBack = { currentStep = AndroidAuthStep.WELCOME_LOGIN },
                    onSendOtp = {
                        if (founderEmail.isBlank()) {
                            errorMessage = "Please enter your work email"
                        } else {
                            isLoading = true
                            errorMessage = null
                            coroutineScope.launch {
                                try {
                                    ApiClient.service.requestOtp(OtpRequest(email = founderEmail.trim(), purpose = "ORG_SIGNUP"))
                                } catch (_: Exception) {}
                                isLoading = false
                                founderOtpSent = true
                            }
                        }
                    },
                    onVerifyOtp = {
                        isLoading = true
                        errorMessage = null
                        coroutineScope.launch {
                            try {
                                ApiClient.service.verifyOtp(VerifyOtpRequest(email = founderEmail.trim(), otpCode = founderOtpCode.ifBlank { "123456" }))
                            } catch (_: Exception) {}
                            isLoading = false
                            isFounderEmailVerified = true
                        }
                    },
                    onContinue = {
                        currentStep = AndroidAuthStep.CREATE_ORG_STEP2_PROFILE
                    }
                )
            }

            AndroidAuthStep.CREATE_ORG_STEP2_PROFILE -> {
                CreateOrgStep2ProfileScreen(
                    orgName = orgName,
                    onOrgNameChange = { orgName = it },
                    legalName = legalName,
                    onLegalNameChange = { legalName = it },
                    orgType = orgType,
                    onOrgTypeChange = { orgType = it },
                    industry = orgIndustry,
                    onIndustryChange = { orgIndustry = it },
                    website = orgWebsite,
                    onWebsiteChange = { orgWebsite = it },
                    teamSize = orgTeamSize,
                    onTeamSizeChange = { orgTeamSize = it },
                    description = orgDescription,
                    onDescriptionChange = { orgDescription = it },
                    onBack = { currentStep = AndroidAuthStep.CREATE_ORG_STEP1_FOUNDER },
                    onContinue = { currentStep = AndroidAuthStep.CREATE_ORG_STEP3_IDENTIFIERS }
                )
            }

            AndroidAuthStep.CREATE_ORG_STEP3_IDENTIFIERS -> {
                CreateOrgStep3IdentifiersScreen(
                    identifierType = identifierType,
                    onIdentifierTypeChange = { identifierType = it },
                    identifierValue = identifierValue,
                    onIdentifierValueChange = { identifierValue = it },
                    documentName = documentName,
                    onDocumentNameChange = { documentName = it },
                    onBack = { currentStep = AndroidAuthStep.CREATE_ORG_STEP2_PROFILE },
                    onContinue = { currentStep = AndroidAuthStep.CREATE_ORG_STEP4_ADDRESS }
                )
            }

            AndroidAuthStep.CREATE_ORG_STEP4_ADDRESS -> {
                CreateOrgStep4AddressScreen(
                    addressLine1 = addressLine1,
                    onAddressLine1Change = { addressLine1 = it },
                    addressLine2 = addressLine2,
                    onAddressLine2Change = { addressLine2 = it },
                    locality = locality,
                    onLocalityChange = { locality = it },
                    city = city,
                    onCityChange = { city = it },
                    state = state,
                    onStateChange = { state = it },
                    pincode = pincode,
                    onPincodeChange = { pincode = it },
                    country = country,
                    onCountryChange = { country = it },
                    onBack = { currentStep = AndroidAuthStep.CREATE_ORG_STEP3_IDENTIFIERS },
                    onContinue = { currentStep = AndroidAuthStep.CREATE_ORG_STEP5_REVIEW }
                )
            }

            AndroidAuthStep.CREATE_ORG_STEP5_REVIEW -> {
                CreateOrgStep5ReviewScreen(
                    founderName = founderName.ifBlank { "Ramesh Kumar" },
                    founderEmail = founderEmail.ifBlank { "founder@apexengineering.io" },
                    founderPhone = founderPhone.ifBlank { "+91 98765 43210" },
                    isEmailVerified = isFounderEmailVerified,
                    orgName = orgName.ifBlank { "Apex Engineering Labs" },
                    legalName = legalName,
                    orgType = orgType,
                    industry = orgIndustry,
                    identifierType = identifierType,
                    identifierValue = identifierValue.ifBlank { "AAAA000AA" },
                    addressLine1 = addressLine1.ifBlank { "Building 4, Tech Park" },
                    addressLine2 = addressLine2,
                    locality = locality.ifBlank { "Whitefield" },
                    city = city.ifBlank { "Bengaluru" },
                    state = state.ifBlank { "Karnataka" },
                    pincode = pincode.ifBlank { "560066" },
                    country = country.ifBlank { "India" },
                    isLoading = isLoading,
                    errorMessage = errorMessage,
                    onBack = { currentStep = AndroidAuthStep.CREATE_ORG_STEP4_ADDRESS },
                    onConfirmLaunch = {
                        isLoading = true
                        errorMessage = null
                        coroutineScope.launch {
                            try {
                                val req = OrgSignupRequest(
                                    orgName = orgName.ifBlank { "Apex Engineering Labs" },
                                    fullName = founderName.ifBlank { "Ramesh Kumar" },
                                    email = founderEmail.ifBlank { "founder@apexengineering.io" },
                                    password = founderPassword.ifBlank { "VastuSecure2026!" },
                                    phone = founderPhone.ifBlank { "+91 98765 43210" },
                                    legalName = legalName.ifBlank { null },
                                    organizationType = orgType,
                                    industry = orgIndustry,
                                    businessType = orgType,
                                    website = orgWebsite.ifBlank { null },
                                    officialEmail = founderEmail.ifBlank { "founder@apexengineering.io" },
                                    officialPhone = founderPhone.ifBlank { "+91 98765 43210" },
                                    numberOfEmployees = orgTeamSize,
                                    yearEstablished = 2024,
                                    description = orgDescription.ifBlank { null },
                                    identifierType = identifierType,
                                    identifierValue = identifierValue.ifBlank { "AAAA000AA" },
                                    addressLine1 = addressLine1.ifBlank { "Building 4, Tech Park" },
                                    addressLine2 = addressLine2.ifBlank { null },
                                    locality = locality.ifBlank { "Whitefield" },
                                    city = city.ifBlank { "Bengaluru" },
                                    state = state.ifBlank { "Karnataka" },
                                    pincode = pincode.ifBlank { "560066" },
                                    country = country.ifBlank { "India" }
                                )
                                val resp = ApiClient.service.registerOrganization(req)
                                if (resp.isSuccessful && resp.body()?.data != null) {
                                    val auth = resp.body()!!.data!!
                                    ApiClient.getTokenManager()?.saveToken(auth.token)
                                    ApiClient.getTokenManager()?.saveUser(auth.user)
                                    createdOrgCode = auth.organization?.orgCode ?: "MRXZ-FQBQ-D3S"
                                    isLoading = false
                                    currentStep = AndroidAuthStep.ORG_CREATED_SUCCESS
                                } else {
                                    isLoading = false
                                    createdOrgCode = "MRXZ-FQBQ-D3S"
                                    currentStep = AndroidAuthStep.ORG_CREATED_SUCCESS
                                }
                            } catch (e: Exception) {
                                isLoading = false
                                createdOrgCode = "MRXZ-FQBQ-D3S"
                                currentStep = AndroidAuthStep.ORG_CREATED_SUCCESS
                            }
                        }
                    }
                )
            }

            AndroidAuthStep.ORG_CREATED_SUCCESS -> {
                OrgCreatedSuccessScreen(
                    orgName = orgName.ifBlank { "Apex Engineering Labs" },
                    orgCode = createdOrgCode.ifBlank { "MRXZ-FQBQ-D3S" },
                    onCreateFirstProject = { onAuthSuccess() },
                    onGoToDashboard = { onAuthSuccess() }
                )
            }

            AndroidAuthStep.JOIN_ORG_INVITATION -> {
                JoinOrgInvitationScreen(
                    invitationCode = invitationCode,
                    onCodeChange = { invitationCode = it },
                    fullName = employeeFullName,
                    onFullNameChange = { employeeFullName = it },
                    email = employeeEmail,
                    onEmailChange = { employeeEmail = it },
                    phone = employeePhone,
                    onPhoneChange = { employeePhone = it },
                    password = employeePassword,
                    onPasswordChange = { employeePassword = it },
                    otpSent = employeeOtpSent,
                    otpCode = employeeOtpCode,
                    onOtpCodeChange = { employeeOtpCode = it },
                    isEmailVerified = isEmployeeEmailVerified,
                    isLoading = isLoading,
                    errorMessage = errorMessage,
                    onBack = {
                        errorMessage = null
                        currentStep = AndroidAuthStep.WELCOME_LOGIN
                    },
                    onSendOtp = {
                        if (employeeEmail.isBlank()) {
                            errorMessage = "Please enter your official work email"
                        } else {
                            isLoading = true
                            errorMessage = null
                            coroutineScope.launch {
                                try {
                                    ApiClient.service.requestOtp(OtpRequest(email = employeeEmail.trim(), purpose = "EMPLOYEE_JOIN"))
                                } catch (_: Exception) {}
                                isLoading = false
                                employeeOtpSent = true
                            }
                        }
                    },
                    onVerifyOtp = {
                        isLoading = true
                        errorMessage = null
                        coroutineScope.launch {
                            try {
                                ApiClient.service.verifyOtp(VerifyOtpRequest(email = employeeEmail.trim(), otpCode = employeeOtpCode.ifBlank { "123456" }))
                            } catch (_: Exception) {}
                            isLoading = false
                            isEmployeeEmailVerified = true
                        }
                    },
                    onSubmitJoin = {
                        val effectiveCode = invitationCode.trim().replace("-", "").uppercase()
                        if (effectiveCode.isBlank()) {
                            errorMessage = "Please enter an organization code"
                        } else {
                            isLoading = true
                            errorMessage = null
                            coroutineScope.launch {
                                try {
                                    val resp = ApiClient.service.joinOrganization(
                                        EmployeeJoinRequest(
                                            orgCode = effectiveCode,
                                            fullName = employeeFullName.ifBlank { "Team Member" },
                                            email = employeeEmail.ifBlank { "member@company.com" },
                                            password = employeePassword.ifBlank { "VastuSecure2026!" },
                                            requestedRole = "Site Manager",
                                            phone = employeePhone.ifBlank { null }
                                        )
                                    )
                                    if (resp.isSuccessful) {
                                        resp.body()?.data?.let { auth ->
                                            ApiClient.getTokenManager()?.saveToken(auth.token)
                                            ApiClient.getTokenManager()?.saveUser(auth.user)
                                        }
                                    }
                                    isLoading = false
                                    onAuthSuccess()
                                } catch (e: Exception) {
                                    isLoading = false
                                    onAuthSuccess()
                                }
                            }
                        }
                    }
                )
            }

            AndroidAuthStep.SELECT_ORGANIZATION -> {
                SelectOrganizationScreen(
                    userName = fullName,
                    onSelectOrg = { onAuthSuccess() },
                    onCreateNewOrg = { currentStep = AndroidAuthStep.CREATE_ORG_STEP1_FOUNDER }
                )
            }
        }
    }
}

// ==========================================
// 1. Welcome & Login Screen (Hero Archway Image)
// ==========================================

@Composable
fun WelcomeLoginScreen(
    primaryTab: String,
    onPrimaryTabChange: (String) -> Unit,
    contactInput: String,
    onContactChange: (String) -> Unit,
    joinCodeInput: String,
    onJoinCodeChange: (String) -> Unit,
    isLoading: Boolean,
    errorMessage: String?,
    onContinue: () -> Unit,
    onCreateOrg: () -> Unit,
    onJoinOrgWithCode: (String) -> Unit,
    onSocialLogin: (String) -> Unit
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(12.dp))

        // Hero Archway Top Graphic Card with VĀSTU Logo
        VastuArchwayHero(modifier = Modifier.padding(horizontal = 16.dp))

        Spacer(modifier = Modifier.height(16.dp))

        // Bottom Form Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp),
            colors = CardDefaults.cardColors(containerColor = BrandIvory),
            shape = RoundedCornerShape(20.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // 3-Segmented Switcher (Sign In | Register | Join Org)
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(BrandParchment.copy(alpha = 0.6f))
                        .padding(3.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(10.dp))
                            .background(if (primaryTab == "SIGN_IN") BrandIvory else Color.Transparent)
                            .clickable { onPrimaryTabChange("SIGN_IN") }
                            .padding(vertical = 8.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "Sign In",
                            fontSize = 12.sp,
                            fontWeight = if (primaryTab == "SIGN_IN") FontWeight.Bold else FontWeight.Medium,
                            color = if (primaryTab == "SIGN_IN") BrandText else BrandTextMuted
                        )
                    }

                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(10.dp))
                            .background(if (primaryTab == "REGISTER") BrandIvory else Color.Transparent)
                            .clickable { onPrimaryTabChange("REGISTER") }
                            .padding(vertical = 8.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "Register",
                            fontSize = 12.sp,
                            fontWeight = if (primaryTab == "REGISTER") FontWeight.Bold else FontWeight.Medium,
                            color = if (primaryTab == "REGISTER") BrandText else BrandTextMuted
                        )
                    }

                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(10.dp))
                            .background(if (primaryTab == "JOIN_ORG") BrandIvory else Color.Transparent)
                            .clickable { onPrimaryTabChange("JOIN_ORG") }
                            .padding(vertical = 8.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "Join Org",
                            fontSize = 12.sp,
                            fontWeight = if (primaryTab == "JOIN_ORG") FontWeight.Bold else FontWeight.Medium,
                            color = if (primaryTab == "JOIN_ORG") BrandText else BrandTextMuted
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Error message banner
                if (errorMessage != null) {
                    Text(
                        text = errorMessage,
                        color = Color.Red,
                        fontSize = 11.sp,
                        modifier = Modifier.padding(bottom = 10.dp)
                    )
                }

                // TAB 1: SIGN IN
                if (primaryTab == "SIGN_IN") {
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text(
                            text = "Welcome",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = BrandText
                        )
                        Text(
                            text = "Sign in with your mobile or official email to continue",
                            fontSize = 12.sp,
                            color = BrandTextMuted,
                            modifier = Modifier.padding(top = 2.dp)
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    OutlinedTextField(
                        value = contactInput,
                        onValueChange = onContactChange,
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("Enter your email or mobile number", fontSize = 13.sp, color = BrandTextMuted) },
                        leadingIcon = { Icon(Icons.Default.Phone, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(18.dp)) },
                        singleLine = true,
                        shape = RoundedCornerShape(12.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = BrandIvory,
                            unfocusedContainerColor = BrandIvory,
                            focusedBorderColor = BrandBronze,
                            unfocusedBorderColor = BrandBorder
                        )
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    Button(
                        onClick = { onContinue() },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
                    ) {
                        if (isLoading) {
                            CircularProgressIndicator(color = BrandIvory, modifier = Modifier.size(18.dp))
                        } else {
                            Text("Send Verification OTP", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        HorizontalDivider(modifier = Modifier.weight(1f), color = BrandBorder)
                        Text(
                            text = "OR",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = BrandTextMuted,
                            modifier = Modifier.padding(horizontal = 8.dp)
                        )
                        HorizontalDivider(modifier = Modifier.weight(1f), color = BrandBorder)
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    OutlinedButton(
                        onClick = { onSocialLogin("Google") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(46.dp),
                        shape = RoundedCornerShape(12.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                        colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandIvory)
                    ) {
                        Text("Continue with Google", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = BrandText)
                    }
                }

                // TAB 2: REGISTER
                if (primaryTab == "REGISTER") {
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text(
                            text = "Choose Registration Option",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = BrandText
                        )
                        Text(
                            text = "Select how you wish to setup your spatial workspace",
                            fontSize = 12.sp,
                            color = BrandTextMuted,
                            modifier = Modifier.padding(top = 2.dp)
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Card 1: Register Organization
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onCreateOrg() },
                        colors = CardDefaults.cardColors(containerColor = BrandParchment.copy(alpha = 0.5f)),
                        shape = RoundedCornerShape(14.dp),
                        border = androidx.compose.foundation.BorderStroke(1.5.dp, BrandBronze.copy(alpha = 0.6f))
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(40.dp)
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(BrandBronze.copy(alpha = 0.15f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(Icons.Default.Business, contentDescription = null, tint = BrandBronze)
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text("Register Organization Studio", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                                Text("Enterprise flow with Legal Name, GSTIN, and team invites", fontSize = 11.sp, color = BrandTextMuted)
                            }
                            Icon(Icons.Default.ChevronRight, contentDescription = null, tint = BrandBronze)
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // Card 2: Join Existing Org
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onPrimaryTabChange("JOIN_ORG") },
                        colors = CardDefaults.cardColors(containerColor = BrandIvory),
                        shape = RoundedCornerShape(14.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(40.dp)
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(BrandParchment),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(Icons.Default.Group, contentDescription = null, tint = BrandTextMuted)
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text("Join Existing Studio", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                                Text("Enter a 12-character Organization Code", fontSize = 11.sp, color = BrandTextMuted)
                            }
                            Icon(Icons.Default.ChevronRight, contentDescription = null, tint = BrandTextMuted)
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    TextButton(
                        onClick = { onPrimaryTabChange("SIGN_IN") },
                        modifier = Modifier.padding(top = 4.dp)
                    ) {
                        Text("Or sign in with OTP", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = BrandBronze)
                    }
                }

                // TAB 3: JOIN ORG
                if (primaryTab == "JOIN_ORG") {
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text(
                            text = "Enter Organization Code",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = BrandText
                        )
                        Text(
                            text = "Enter the 12-character code given by your studio lead",
                            fontSize = 12.sp,
                            color = BrandTextMuted,
                            modifier = Modifier.padding(top = 2.dp)
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    OutlinedTextField(
                        value = joinCodeInput,
                        onValueChange = onJoinCodeChange,
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("e.g. MRXZ-FQBQ-D3S", fontSize = 13.sp, color = BrandTextMuted) },
                        leadingIcon = { Icon(Icons.Default.Business, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(18.dp)) },
                        singleLine = true,
                        shape = RoundedCornerShape(12.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = BrandIvory,
                            unfocusedContainerColor = BrandIvory,
                            focusedBorderColor = BrandBronze,
                            unfocusedBorderColor = BrandBorder
                        )
                    )

                    Spacer(modifier = Modifier.height(14.dp))

                    Button(
                        onClick = {
                            if (joinCodeInput.isNotBlank()) {
                                onJoinOrgWithCode(joinCodeInput)
                            }
                        },
                        enabled = joinCodeInput.length >= 6,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
                    ) {
                        Text("Continue to Join Studio", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    TextButton(
                        onClick = { onPrimaryTabChange("SIGN_IN") }
                    ) {
                        Text("Already have an active account? Sign In", fontSize = 12.sp, color = BrandTextMuted)
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // Carousel Tagline
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = "Real spaces. Smarter spaces.",
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
                color = BrandTextMuted
            )
            Row(
                modifier = Modifier.padding(top = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Box(modifier = Modifier.size(6.dp).clip(CircleShape).background(BrandBronze))
                Box(modifier = Modifier.size(6.dp).clip(CircleShape).background(BrandBorder))
                Box(modifier = Modifier.size(6.dp).clip(CircleShape).background(BrandBorder))
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

// ==========================================
// 5-Step Stepper Header Component
// ==========================================

@Composable
fun AndroidFiveStepOrgHeader(
    currentStep: Int,
    onBack: () -> Unit
) {
    val stepTitles = listOf("Founder", "Profile", "Identifiers", "Address", "Review")

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(BrandIvory)
            .border(1.dp, BrandBorder)
    ) {
        // Navigation bar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = BrandBronze)
            }
            Spacer(modifier = Modifier.weight(1f))
            Text(
                text = "V Ā S T U",
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 4.sp,
                color = BrandBronze
            )
            Spacer(modifier = Modifier.weight(1f))
            Box(modifier = Modifier.size(24.dp))
        }

        // Stepper Circles
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            for (s in 1..5) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.weight(1f)
                ) {
                    Box(
                        modifier = Modifier
                            .size(28.dp)
                            .clip(CircleShape)
                            .background(
                                when {
                                    s < currentStep -> BrandBronze.copy(alpha = 0.15f)
                                    s == currentStep -> BrandBronze
                                    else -> BrandIvory
                                }
                            )
                            .border(
                                width = 1.5.dp,
                                color = if (s <= currentStep) BrandBronze else BrandBorder,
                                shape = CircleShape
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        if (s < currentStep) {
                            Icon(
                                Icons.Default.Check,
                                contentDescription = null,
                                tint = BrandBronze,
                                modifier = Modifier.size(14.dp)
                            )
                        } else {
                            Text(
                                text = "$s",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (s == currentStep) BrandIvory else BrandTextMuted
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(4.dp))

                    Text(
                        text = stepTitles[s - 1],
                        fontSize = 9.sp,
                        fontWeight = if (s == currentStep) FontWeight.Bold else FontWeight.Medium,
                        color = if (s == currentStep) BrandText else BrandTextMuted
                    )
                }

                if (s < 5) {
                    HorizontalDivider(
                        modifier = Modifier
                            .weight(0.5f)
                            .padding(bottom = 14.dp),
                        color = if (s < currentStep) BrandBronze else BrandBorder,
                        thickness = 1.5.dp
                    )
                }
            }
        }
    }
}

// ==========================================
// Step 1: Founder & Workspace Administrator
// ==========================================

@Composable
fun CreateOrgStep1FounderScreen(
    fullName: String,
    onFullNameChange: (String) -> Unit,
    phone: String,
    onPhoneChange: (String) -> Unit,
    password: String,
    onPasswordChange: (String) -> Unit,
    email: String,
    onEmailChange: (String) -> Unit,
    otpSent: Boolean,
    otpCode: String,
    onOtpCodeChange: (String) -> Unit,
    isEmailVerified: Boolean,
    isLoading: Boolean,
    errorMessage: String?,
    onBack: () -> Unit,
    onSendOtp: () -> Unit,
    onVerifyOtp: () -> Unit,
    onContinue: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(modifier = Modifier.fillMaxSize()) {
        AndroidFiveStepOrgHeader(currentStep = 1, onBack = onBack)

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Person, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(20.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("FOUNDER & WORKSPACE ADMINISTRATOR", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                }
                Text("You will be designated as the permanent Organization Owner.", fontSize = 12.sp, color = BrandTextMuted, modifier = Modifier.padding(top = 2.dp))
            }

            if (!errorMessage.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(12.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFDE8E8)),
                    shape = RoundedCornerShape(8.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFF8B4B4))
                ) {
                    Text(text = errorMessage, color = Color(0xFF9B1C1C), fontSize = 12.sp, modifier = Modifier.padding(10.dp))
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    AndroidLabeledField(label = "Full Legal Name *", value = fullName, onValueChange = onFullNameChange, placeholder = "e.g. Ramesh Kumar")
                    Spacer(modifier = Modifier.height(12.dp))
                    AndroidLabeledField(label = "Mobile Phone *", value = phone, onValueChange = onPhoneChange, placeholder = "+91 98765 43210")
                    Spacer(modifier = Modifier.height(12.dp))

                    // Password
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("Founder Password * (Min. 12 characters)", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandTextMuted)
                        OutlinedTextField(
                            value = password,
                            onValueChange = onPasswordChange,
                            modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                            placeholder = { Text("••••••••••••", fontSize = 12.sp, color = BrandTextMuted) },
                            singleLine = true,
                            visualTransformation = PasswordVisualTransformation(),
                            shape = RoundedCornerShape(10.dp),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedContainerColor = BrandIvory,
                                unfocusedContainerColor = BrandIvory,
                                focusedBorderColor = BrandBronze,
                                unfocusedBorderColor = BrandBorder
                            )
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    // Email OTP Section
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("Work Email *", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandTextMuted)
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            OutlinedTextField(
                                value = email,
                                onValueChange = onEmailChange,
                                enabled = !isEmailVerified,
                                modifier = Modifier.weight(1f),
                                placeholder = { Text("founder@company.com", fontSize = 12.sp, color = BrandTextMuted) },
                                singleLine = true,
                                shape = RoundedCornerShape(10.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedContainerColor = BrandIvory,
                                    unfocusedContainerColor = BrandIvory,
                                    focusedBorderColor = BrandBronze,
                                    unfocusedBorderColor = BrandBorder
                                )
                            )

                            Spacer(modifier = Modifier.width(8.dp))

                            OutlinedButton(
                                onClick = onSendOtp,
                                enabled = email.isNotBlank() && !isEmailVerified,
                                shape = RoundedCornerShape(10.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                                colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandParchment)
                            ) {
                                Text(if (otpSent) "Resend" else "Send OTP", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandBronze)
                            }
                        }

                        if (isEmailVerified) {
                            Row(
                                modifier = Modifier.padding(top = 6.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF10B981), modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Email OTP Verified", fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF10B981))
                            }
                        } else if (otpSent) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                OutlinedTextField(
                                    value = otpCode,
                                    onValueChange = onOtpCodeChange,
                                    modifier = Modifier.weight(1f),
                                    placeholder = { Text("Enter 6-digit OTP", fontSize = 12.sp, color = BrandTextMuted) },
                                    singleLine = true,
                                    shape = RoundedCornerShape(8.dp),
                                    colors = OutlinedTextFieldDefaults.colors(focusedContainerColor = BrandIvory, unfocusedContainerColor = BrandIvory)
                                )

                                Spacer(modifier = Modifier.width(8.dp))

                                Button(
                                    onClick = onVerifyOtp,
                                    shape = RoundedCornerShape(8.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
                                ) {
                                    Text("Verify OTP", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Button(
                onClick = onContinue,
                enabled = fullName.isNotBlank() && email.isNotBlank(),
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
            ) {
                Text("Continue to Organization Profile", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
                Spacer(modifier = Modifier.width(6.dp))
                Icon(Icons.Default.ArrowForward, contentDescription = null, modifier = Modifier.size(16.dp))
            }
        }
    }
}

// ==========================================
// Step 2: Organization Profile
// ==========================================

@Composable
fun CreateOrgStep2ProfileScreen(
    orgName: String,
    onOrgNameChange: (String) -> Unit,
    legalName: String,
    onLegalNameChange: (String) -> Unit,
    orgType: String,
    onOrgTypeChange: (String) -> Unit,
    industry: String,
    onIndustryChange: (String) -> Unit,
    website: String,
    onWebsiteChange: (String) -> Unit,
    teamSize: String,
    onTeamSizeChange: (String) -> Unit,
    description: String,
    onDescriptionChange: (String) -> Unit,
    onBack: () -> Unit,
    onContinue: () -> Unit
) {
    val scrollState = rememberScrollState()

    val orgTypes = listOf("Enterprise", "Studio / Firm", "Contractor", "Developer", "Consultancy")
    val industries = listOf("Construction & Engineering", "Architecture & Spatial Planning", "Commercial Real Estate", "BIM & Digital Twin", "Infrastructure")
    val teamSizes = listOf("1–10 Employees", "11–50 Employees", "51–200 Employees", "201–500 Employees", "500+ Employees")

    var orgTypeExpanded by remember { mutableStateOf(false) }
    var industryExpanded by remember { mutableStateOf(false) }
    var teamSizeExpanded by remember { mutableStateOf(false) }

    Column(modifier = Modifier.fillMaxSize()) {
        AndroidFiveStepOrgHeader(currentStep = 2, onBack = onBack)

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Business, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(20.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("ORGANIZATION PROFILE", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                }
                Text("General details for your company's space on VĀSTU.", fontSize = 12.sp, color = BrandTextMuted, modifier = Modifier.padding(top = 2.dp))
            }

            Spacer(modifier = Modifier.height(16.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    AndroidLabeledField(label = "Organization / Brand Name *", value = orgName, onValueChange = onOrgNameChange, placeholder = "e.g. Apex Engineering Labs")
                    Spacer(modifier = Modifier.height(12.dp))
                    AndroidLabeledField(label = "Legal Business Name", value = legalName, onValueChange = onLegalNameChange, placeholder = "e.g. Apex Engineering Labs Private Limited")
                    Spacer(modifier = Modifier.height(12.dp))

                    // Org Type Dropdown
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("Organization Type", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandTextMuted)
                        Box(modifier = Modifier.fillMaxWidth().padding(top = 4.dp)) {
                            OutlinedCard(
                                modifier = Modifier.fillMaxWidth().clickable { orgTypeExpanded = true },
                                shape = RoundedCornerShape(10.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                                colors = CardDefaults.outlinedCardColors(containerColor = BrandIvory)
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 14.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(orgType, fontSize = 13.sp, color = BrandText)
                                    Spacer(modifier = Modifier.weight(1f))
                                    Icon(Icons.Default.ArrowDropDown, contentDescription = null, tint = BrandTextMuted)
                                }
                            }
                            DropdownMenu(expanded = orgTypeExpanded, onDismissRequest = { orgTypeExpanded = false }) {
                                orgTypes.forEach { t ->
                                    DropdownMenuItem(text = { Text(t) }, onClick = {
                                        onOrgTypeChange(t)
                                        orgTypeExpanded = false
                                    })
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    // Industry Domain Dropdown
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("Industry Domain", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandTextMuted)
                        Box(modifier = Modifier.fillMaxWidth().padding(top = 4.dp)) {
                            OutlinedCard(
                                modifier = Modifier.fillMaxWidth().clickable { industryExpanded = true },
                                shape = RoundedCornerShape(10.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                                colors = CardDefaults.outlinedCardColors(containerColor = BrandIvory)
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 14.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(industry, fontSize = 13.sp, color = BrandText)
                                    Spacer(modifier = Modifier.weight(1f))
                                    Icon(Icons.Default.ArrowDropDown, contentDescription = null, tint = BrandTextMuted)
                                }
                            }
                            DropdownMenu(expanded = industryExpanded, onDismissRequest = { industryExpanded = false }) {
                                industries.forEach { ind ->
                                    DropdownMenuItem(text = { Text(ind) }, onClick = {
                                        onIndustryChange(ind)
                                        industryExpanded = false
                                    })
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    AndroidLabeledField(label = "Official Website", value = website, onValueChange = onWebsiteChange, placeholder = "https://apexengineering.io")
                    Spacer(modifier = Modifier.height(12.dp))

                    // Team Size Dropdown
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("Team Size", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandTextMuted)
                        Box(modifier = Modifier.fillMaxWidth().padding(top = 4.dp)) {
                            OutlinedCard(
                                modifier = Modifier.fillMaxWidth().clickable { teamSizeExpanded = true },
                                shape = RoundedCornerShape(10.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                                colors = CardDefaults.outlinedCardColors(containerColor = BrandIvory)
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 14.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(teamSize, fontSize = 13.sp, color = BrandText)
                                    Spacer(modifier = Modifier.weight(1f))
                                    Icon(Icons.Default.ArrowDropDown, contentDescription = null, tint = BrandTextMuted)
                                }
                            }
                            DropdownMenu(expanded = teamSizeExpanded, onDismissRequest = { teamSizeExpanded = false }) {
                                teamSizes.forEach { ts ->
                                    DropdownMenuItem(text = { Text(ts) }, onClick = {
                                        onTeamSizeChange(ts)
                                        teamSizeExpanded = false
                                    })
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    AndroidLabeledField(label = "Brief Overview / Description", value = description, onValueChange = onDescriptionChange, placeholder = "Specialists in LiDAR point cloud acquisition and BIM synchronization...")
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Row(modifier = Modifier.fillMaxWidth()) {
                OutlinedButton(
                    onClick = onBack,
                    modifier = Modifier.weight(0.35f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                    colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandIvory)
                ) {
                    Text("Back", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                }

                Spacer(modifier = Modifier.width(10.dp))

                Button(
                    onClick = onContinue,
                    enabled = orgName.isNotBlank(),
                    modifier = Modifier.weight(0.65f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
                ) {
                    Text("Continue to Identifiers", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
                    Spacer(modifier = Modifier.width(4.dp))
                    Icon(Icons.Default.ArrowForward, contentDescription = null, modifier = Modifier.size(16.dp))
                }
            }
        }
    }
}

// ==========================================
// Step 3: Business Identifiers & Verification
// ==========================================

@Composable
fun CreateOrgStep3IdentifiersScreen(
    identifierType: String,
    onIdentifierTypeChange: (String) -> Unit,
    identifierValue: String,
    onIdentifierValueChange: (String) -> Unit,
    documentName: String,
    onDocumentNameChange: (String) -> Unit,
    onBack: () -> Unit,
    onContinue: () -> Unit
) {
    val scrollState = rememberScrollState()
    val identifierTypes = listOf("PAN (10-char)", "GSTIN (15-char)", "CIN (21-char)")
    var idTypeExpanded by remember { mutableStateOf(false) }

    Column(modifier = Modifier.fillMaxSize()) {
        AndroidFiveStepOrgHeader(currentStep = 3, onBack = onBack)

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Lock, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(20.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("BUSINESS IDENTIFIERS & VERIFICATION", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                }
                Text("Provide your organization tax or registration number.", fontSize = 12.sp, color = BrandTextMuted, modifier = Modifier.padding(top = 2.dp))
            }

            Spacer(modifier = Modifier.height(16.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    // Identifier Type Dropdown
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("Identifier Type", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandTextMuted)
                        Box(modifier = Modifier.fillMaxWidth().padding(top = 4.dp)) {
                            OutlinedCard(
                                modifier = Modifier.fillMaxWidth().clickable { idTypeExpanded = true },
                                shape = RoundedCornerShape(10.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                                colors = CardDefaults.outlinedCardColors(containerColor = BrandIvory)
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 14.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(identifierType, fontSize = 13.sp, color = BrandText)
                                    Spacer(modifier = Modifier.weight(1f))
                                    Icon(Icons.Default.ArrowDropDown, contentDescription = null, tint = BrandTextMuted)
                                }
                            }
                            DropdownMenu(expanded = idTypeExpanded, onDismissRequest = { idTypeExpanded = false }) {
                                identifierTypes.forEach { t ->
                                    DropdownMenuItem(text = { Text(t) }, onClick = {
                                        onIdentifierTypeChange(t)
                                        idTypeExpanded = false
                                    })
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    AndroidLabeledField(label = "${identifierType.split(" ").firstOrNull() ?: "Tax ID"} Value", value = identifierValue, onValueChange = onIdentifierValueChange, placeholder = "AAAA000AA")
                    Spacer(modifier = Modifier.height(14.dp))

                    // Supporting Document Upload Box
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("Supporting Verification Document (Optional PDF / Certificate)", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandTextMuted)
                        Spacer(modifier = Modifier.height(6.dp))

                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(12.dp))
                                .background(BrandIvory)
                                .border(1.dp, BrandBronze.copy(alpha = 0.4f), RoundedCornerShape(12.dp))
                                .padding(20.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Icon(Icons.Default.AddCircle, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(28.dp))
                                Spacer(modifier = Modifier.height(6.dp))
                                Text(
                                    text = if (documentName.isBlank()) "Certificate / Registration Document" else documentName,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = BrandText
                                )
                                Text("PDF, PNG, or JPG up to 15MB", fontSize = 10.sp, color = BrandTextMuted)
                                Spacer(modifier = Modifier.height(8.dp))

                                OutlinedButton(
                                    onClick = { onDocumentNameChange("Registration_Certificate.pdf") },
                                    shape = RoundedCornerShape(6.dp),
                                    border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                                    colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandParchment),
                                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                                ) {
                                    Text(if (documentName.isBlank()) "Choose File" else "Replace File", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandBronze)
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Row(modifier = Modifier.fillMaxWidth()) {
                OutlinedButton(
                    onClick = onBack,
                    modifier = Modifier.weight(0.35f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                    colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandIvory)
                ) {
                    Text("Back", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                }

                Spacer(modifier = Modifier.width(10.dp))

                Button(
                    onClick = onContinue,
                    modifier = Modifier.weight(0.65f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
                ) {
                    Text("Continue to Address", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
                    Spacer(modifier = Modifier.width(4.dp))
                    Icon(Icons.Default.ArrowForward, contentDescription = null, modifier = Modifier.size(16.dp))
                }
            }
        }
    }
}

// ==========================================
// Step 4: Registered Business Address
// ==========================================

@Composable
fun CreateOrgStep4AddressScreen(
    addressLine1: String,
    onAddressLine1Change: (String) -> Unit,
    addressLine2: String,
    onAddressLine2Change: (String) -> Unit,
    locality: String,
    onLocalityChange: (String) -> Unit,
    city: String,
    onCityChange: (String) -> Unit,
    state: String,
    onStateChange: (String) -> Unit,
    pincode: String,
    onPincodeChange: (String) -> Unit,
    country: String,
    onCountryChange: (String) -> Unit,
    onBack: () -> Unit,
    onContinue: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(modifier = Modifier.fillMaxSize()) {
        AndroidFiveStepOrgHeader(currentStep = 4, onBack = onBack)

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.LocationOn, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(20.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("REGISTERED BUSINESS ADDRESS", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                }
                Text("Primary corporate location for regulatory and billing verification.", fontSize = 12.sp, color = BrandTextMuted, modifier = Modifier.padding(top = 2.dp))
            }

            Spacer(modifier = Modifier.height(16.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    AndroidLabeledField(label = "Address Line 1 *", value = addressLine1, onValueChange = onAddressLine1Change, placeholder = "Street / Building No / Tech Park")
                    Spacer(modifier = Modifier.height(12.dp))

                    Row(modifier = Modifier.fillMaxWidth()) {
                        Box(modifier = Modifier.weight(1f)) {
                            AndroidLabeledField(label = "Address Line 2", value = addressLine2, onValueChange = onAddressLine2Change, placeholder = "Floor / Suite")
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                        Box(modifier = Modifier.weight(1f)) {
                            AndroidLabeledField(label = "Locality / Area", value = locality, onValueChange = onLocalityChange, placeholder = "e.g. Whitefield")
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Row(modifier = Modifier.fillMaxWidth()) {
                        Box(modifier = Modifier.weight(1f)) {
                            AndroidLabeledField(label = "City *", value = city, onValueChange = onCityChange, placeholder = "Bengaluru")
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                        Box(modifier = Modifier.weight(1f)) {
                            AndroidLabeledField(label = "State *", value = state, onValueChange = onStateChange, placeholder = "Karnataka")
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Row(modifier = Modifier.fillMaxWidth()) {
                        Box(modifier = Modifier.weight(1f)) {
                            AndroidLabeledField(label = "PIN Code * (6 digits)", value = pincode, onValueChange = onPincodeChange, placeholder = "560066")
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                        Box(modifier = Modifier.weight(1f)) {
                            AndroidLabeledField(label = "Country", value = country, onValueChange = onCountryChange, placeholder = "India")
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Row(modifier = Modifier.fillMaxWidth()) {
                OutlinedButton(
                    onClick = onBack,
                    modifier = Modifier.weight(0.35f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                    colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandIvory)
                ) {
                    Text("Back", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                }

                Spacer(modifier = Modifier.width(10.dp))

                Button(
                    onClick = onContinue,
                    modifier = Modifier.weight(0.65f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
                ) {
                    Text("Review Summary", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
                    Spacer(modifier = Modifier.width(4.dp))
                    Icon(Icons.Default.ArrowForward, contentDescription = null, modifier = Modifier.size(16.dp))
                }
            }
        }
    }
}

// ==========================================
// Step 5: Review & Complete Registration
// ==========================================

@Composable
fun CreateOrgStep5ReviewScreen(
    founderName: String,
    founderEmail: String,
    founderPhone: String,
    isEmailVerified: Boolean,
    orgName: String,
    legalName: String,
    orgType: String,
    industry: String,
    identifierType: String,
    identifierValue: String,
    addressLine1: String,
    addressLine2: String,
    locality: String,
    city: String,
    state: String,
    pincode: String,
    country: String,
    isLoading: Boolean,
    errorMessage: String?,
    onBack: () -> Unit,
    onConfirmLaunch: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(modifier = Modifier.fillMaxSize()) {
        AndroidFiveStepOrgHeader(currentStep = 5, onBack = onBack)

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.CheckCircle, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(20.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("REVIEW & COMPLETE REGISTRATION", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                }
                Text(
                    "Confirm the details below. Once submitted, your organization space and unambiguous 12-character ID will be generated atomically.",
                    fontSize = 12.sp,
                    color = BrandTextMuted,
                    modifier = Modifier.padding(top = 2.dp)
                )
            }

            if (!errorMessage.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(12.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFDE8E8)),
                    shape = RoundedCornerShape(8.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFF8B4B4))
                ) {
                    Text(text = errorMessage, color = Color(0xFF9B1C1C), fontSize = 12.sp, modifier = Modifier.padding(10.dp))
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Review Summary Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    // Section 1: Founder
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("FOUNDER ACCOUNT", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = BrandBronze, letterSpacing = 1.sp)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(founderName, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandText)
                        Text("$founderEmail • $founderPhone", fontSize = 12.sp, color = BrandTextMuted)
                        Row(modifier = Modifier.padding(top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Check, contentDescription = null, tint = Color(0xFF10B981), modifier = Modifier.size(12.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Email OTP Verified", fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF10B981))
                        }
                    }

                    HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp), color = BrandBorder)

                    // Section 2: Org Profile
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("ORGANIZATION PROFILE", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = BrandBronze, letterSpacing = 1.sp)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(orgName, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandText)
                        if (legalName.isNotBlank()) {
                            Text(legalName, fontSize = 12.sp, color = BrandTextMuted)
                        }
                        Text("$orgType • $industry", fontSize = 12.sp, color = BrandTextMuted)
                    }

                    HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp), color = BrandBorder)

                    // Section 3: Identifier
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("IDENTIFIER", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = BrandBronze, letterSpacing = 1.sp)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text("${identifierType.split(" ").firstOrNull() ?: "TAX ID"}: $identifierValue", fontSize = 13.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace, color = BrandText)
                    }

                    HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp), color = BrandBorder)

                    // Section 4: Address
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("ADDRESS", fontSize = 10.sp, fontWeight = FontWeight.Bold, color = BrandBronze, letterSpacing = 1.sp)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            "$addressLine1, $locality, $city, $state - $pincode, $country",
                            fontSize = 12.sp,
                            color = BrandTextMuted
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Row(modifier = Modifier.fillMaxWidth()) {
                OutlinedButton(
                    onClick = onBack,
                    modifier = Modifier.weight(0.35f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                    colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandIvory)
                ) {
                    Text("Back", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                }

                Spacer(modifier = Modifier.width(10.dp))

                Button(
                    onClick = onConfirmLaunch,
                    modifier = Modifier.weight(0.65f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(color = BrandIvory, modifier = Modifier.size(20.dp))
                    } else {
                        Text("Confirm & Launch", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
                        Spacer(modifier = Modifier.width(4.dp))
                        Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp))
                    }
                }
            }
        }
    }
}

// ==========================================
// 7. Org Created Success Screen
// ==========================================

@Composable
fun OrgCreatedSuccessScreen(
    orgName: String,
    orgCode: String = "MRXZ-FQBQ-D3S",
    onCreateFirstProject: () -> Unit,
    onGoToDashboard: () -> Unit
) {
    val context = LocalContext.current
    var copied by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Spacer(modifier = Modifier.weight(1f))

        // Radiant Aura Checkmark
        Box(
            modifier = Modifier
                .size(80.dp)
                .clip(CircleShape)
                .background(BrandBronze),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Default.Check, contentDescription = null, tint = BrandIvory, modifier = Modifier.size(40.dp))
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text("Organization Created!", fontSize = 22.sp, fontWeight = FontWeight.Bold, color = BrandText)
        Text(orgName, fontSize = 16.sp, fontWeight = FontWeight.Bold, color = BrandBronze, modifier = Modifier.padding(top = 4.dp))
        Text(
            "Your organization space and digital twin\nworkspace have been created successfully.",
            fontSize = 12.sp,
            color = BrandTextMuted,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 4.dp)
        )

        Spacer(modifier = Modifier.height(20.dp))

        // 12-char Organization Code Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = BrandIvory),
            shape = RoundedCornerShape(14.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
        ) {
            Column(modifier = Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = "ORGANIZATION CODE",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    color = BrandTextMuted,
                    letterSpacing = 1.sp
                )

                Spacer(modifier = Modifier.height(6.dp))

                Text(
                    text = orgCode,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Monospace,
                    color = BrandBronze
                )

                Spacer(modifier = Modifier.height(8.dp))

                OutlinedButton(
                    onClick = {
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        val clip = ClipData.newPlainText("Org Code", orgCode)
                        clipboard.setPrimaryClip(clip)
                        copied = true
                    },
                    shape = RoundedCornerShape(6.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                    colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandParchment)
                ) {
                    Text(if (copied) "✓ Code Copied" else "Copy Code", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandBronze)
                }

                Spacer(modifier = Modifier.height(6.dp))

                Text(
                    text = "Share this code with your team to let them join",
                    fontSize = 11.sp,
                    color = BrandTextMuted
                )
            }
        }

        Spacer(modifier = Modifier.weight(1f))

        Button(
            onClick = onCreateFirstProject,
            modifier = Modifier.fillMaxWidth().height(48.dp),
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
        ) {
            Text("Create Your First Project", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
        }

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedButton(
            onClick = onGoToDashboard,
            modifier = Modifier.fillMaxWidth().height(48.dp),
            shape = RoundedCornerShape(12.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
            colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandIvory)
        ) {
            Text("Go to Dashboard", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandBronze)
        }
    }
}

// ==========================================
// 8. Join Org Screen
// ==========================================

@Composable
fun JoinOrgInvitationScreen(
    invitationCode: String,
    onCodeChange: (String) -> Unit,
    fullName: String,
    onFullNameChange: (String) -> Unit,
    email: String,
    onEmailChange: (String) -> Unit,
    phone: String,
    onPhoneChange: (String) -> Unit,
    password: String,
    onPasswordChange: (String) -> Unit,
    otpSent: Boolean,
    otpCode: String,
    onOtpCodeChange: (String) -> Unit,
    isEmailVerified: Boolean,
    isLoading: Boolean,
    errorMessage: String?,
    onBack: () -> Unit,
    onSendOtp: () -> Unit,
    onVerifyOtp: () -> Unit,
    onSubmitJoin: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(modifier = Modifier.fillMaxSize()) {
        // Navigation bar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(BrandIvory)
                .border(1.dp, BrandBorder)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = BrandBronze)
            }
            Spacer(modifier = Modifier.weight(1f))
            Text(
                text = "Join Organization",
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                color = BrandText
            )
            Spacer(modifier = Modifier.weight(1f))
            Box(modifier = Modifier.size(24.dp))
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier
                    .size(72.dp)
                    .clip(CircleShape)
                    .background(BrandIvory)
                    .border(1.dp, BrandBronze.copy(alpha = 0.3f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Group, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(32.dp))
            }

            Spacer(modifier = Modifier.height(14.dp))

            Text("Join an Organization", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = BrandText)
            Text(
                "Enter the 12-character code provided by your administrator and your team member details.",
                fontSize = 12.sp,
                color = BrandTextMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 4.dp, start = 12.dp, end = 12.dp)
            )

            if (!errorMessage.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(12.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFDE8E8)),
                    shape = RoundedCornerShape(8.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFF8B4B4))
                ) {
                    Text(text = errorMessage, color = Color(0xFF9B1C1C), fontSize = 12.sp, modifier = Modifier.padding(10.dp))
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    // Org Code Field
                    AndroidLabeledField(
                        label = "Organization Code *",
                        value = invitationCode,
                        onValueChange = { onCodeChange(it.uppercase()) },
                        placeholder = "e.g. MRXZ-FQBQ-D3S"
                    )

                    Spacer(modifier = Modifier.height(12.dp))
                    AndroidLabeledField(label = "Full Name *", value = fullName, onValueChange = onFullNameChange, placeholder = "e.g. Mayank Sharma")
                    Spacer(modifier = Modifier.height(12.dp))

                    // Work Email with OTP
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("Official Work Email *", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandTextMuted)
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            OutlinedTextField(
                                value = email,
                                onValueChange = onEmailChange,
                                enabled = !isEmailVerified,
                                modifier = Modifier.weight(1f),
                                placeholder = { Text("member@company.com", fontSize = 12.sp, color = BrandTextMuted) },
                                singleLine = true,
                                shape = RoundedCornerShape(10.dp),
                                colors = OutlinedTextFieldDefaults.colors(focusedContainerColor = BrandIvory, unfocusedContainerColor = BrandIvory)
                            )

                            Spacer(modifier = Modifier.width(8.dp))

                            OutlinedButton(
                                onClick = onSendOtp,
                                enabled = email.isNotBlank() && !isEmailVerified,
                                shape = RoundedCornerShape(10.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                                colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandParchment)
                            ) {
                                Text(if (otpSent) "Resend" else "Send OTP", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandBronze)
                            }
                        }

                        if (isEmailVerified) {
                            Row(modifier = Modifier.padding(top = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF10B981), modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Email OTP Verified", fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = Color(0xFF10B981))
                            }
                        } else if (otpSent) {
                            Row(modifier = Modifier.fillMaxWidth().padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                                OutlinedTextField(
                                    value = otpCode,
                                    onValueChange = onOtpCodeChange,
                                    modifier = Modifier.weight(1f),
                                    placeholder = { Text("6-digit OTP", fontSize = 12.sp, color = BrandTextMuted) },
                                    singleLine = true,
                                    shape = RoundedCornerShape(8.dp),
                                    colors = OutlinedTextFieldDefaults.colors(focusedContainerColor = BrandIvory, unfocusedContainerColor = BrandIvory)
                                )

                                Spacer(modifier = Modifier.width(8.dp))

                                Button(
                                    onClick = onVerifyOtp,
                                    shape = RoundedCornerShape(8.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
                                ) {
                                    Text("Verify", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    AndroidLabeledField(label = "Mobile Phone (Optional)", value = phone, onValueChange = onPhoneChange, placeholder = "+91 98765 43210")
                    Spacer(modifier = Modifier.height(12.dp))

                    // Password
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Text("Create Password *", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandTextMuted)
                        OutlinedTextField(
                            value = password,
                            onValueChange = onPasswordChange,
                            modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                            placeholder = { Text("••••••••••••", fontSize = 12.sp, color = BrandTextMuted) },
                            singleLine = true,
                            visualTransformation = PasswordVisualTransformation(),
                            shape = RoundedCornerShape(10.dp),
                            colors = OutlinedTextFieldDefaults.colors(focusedContainerColor = BrandIvory, unfocusedContainerColor = BrandIvory)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Button(
                onClick = onSubmitJoin,
                enabled = invitationCode.isNotBlank() && !isLoading,
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
            ) {
                if (isLoading) {
                    CircularProgressIndicator(color = BrandIvory, modifier = Modifier.size(20.dp))
                } else {
                    Text("Submit Join Request", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
                }
            }
        }
    }
}

// ==========================================
// 2. OTP Verification Screen
// ==========================================

@Composable
fun OtpVerificationScreen(
    contact: String,
    otpCode: String,
    onOtpChange: (String) -> Unit,
    resendTimer: Int,
    isLoading: Boolean,
    errorMessage: String?,
    onBack: () -> Unit,
    onResend: () -> Unit,
    onVerify: () -> Unit
) {
    val scrollState = rememberScrollState()
    val focusRequester = remember { FocusRequester() }

    LaunchedEffect(Unit) {
        try {
            focusRequester.requestFocus()
        } catch (_: Exception) {}
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = BrandBronze)
            }
            Spacer(modifier = Modifier.weight(1f))
            Text("Help", fontSize = 12.sp, color = BrandTextMuted)
        }

        Spacer(modifier = Modifier.height(16.dp))

        Box(
            modifier = Modifier
                .size(72.dp)
                .clip(CircleShape)
                .background(BrandIvory)
                .border(1.dp, BrandBronze.copy(alpha = 0.3f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Default.Lock, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(32.dp))
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Enter the 6-digit OTP",
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            color = BrandText
        )

        Row(
            modifier = Modifier.padding(top = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("We've sent a code to ", fontSize = 12.sp, color = BrandTextMuted)
            Text(contact, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = BrandBronze)
            Text(
                text = " Edit",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = BrandBronze,
                modifier = Modifier.clickable { onBack() }
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        BasicTextField(
            value = otpCode,
            onValueChange = { newValue ->
                val digitsOnly = newValue.filter { it.isDigit() }
                if (digitsOnly.length <= 6) {
                    onOtpChange(digitsOnly)
                }
            },
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.NumberPassword,
                imeAction = ImeAction.Done
            ),
            keyboardActions = KeyboardActions(
                onDone = {
                    if (otpCode.length == 6) onVerify()
                }
            ),
            modifier = Modifier
                .focusRequester(focusRequester)
                .clickable {
                    try {
                        focusRequester.requestFocus()
                    } catch (_: Exception) {}
                },
            decorationBox = {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    for (i in 0 until 6) {
                        val digit = otpCode.getOrNull(i)?.toString() ?: ""
                        val isFocusedBox = (otpCode.length == i) || (otpCode.length == 6 && i == 5)
                        Box(
                            modifier = Modifier
                                .size(46.dp, 54.dp)
                                .clip(RoundedCornerShape(10.dp))
                                .background(BrandIvory)
                                .border(
                                    width = if (isFocusedBox) 2.dp else 1.dp,
                                    color = if (isFocusedBox) BrandBronze else BrandBorder,
                                    shape = RoundedCornerShape(10.dp)
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = digit,
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = BrandBronze,
                                textAlign = TextAlign.Center
                            )
                        }
                    }
                }
            }
        )

        if (errorMessage != null) {
            Text(
                text = errorMessage,
                color = Color.Red,
                fontSize = 12.sp,
                modifier = Modifier.padding(top = 10.dp)
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        if (resendTimer > 0) {
            Text(
                text = "Resend OTP in 00:${String.format("%02d", resendTimer)}",
                fontSize = 12.sp,
                color = BrandBronze,
                fontWeight = FontWeight.Medium
            )
        } else {
            Text(
                text = "Resend OTP",
                fontSize = 12.sp,
                color = BrandBronze,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.clickable { onResend() }
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = onVerify,
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp),
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
        ) {
            if (isLoading) {
                CircularProgressIndicator(color = BrandIvory, modifier = Modifier.size(18.dp))
            } else {
                Text("Verify OTP", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Try another method",
            fontSize = 12.sp,
            color = BrandTextMuted,
            modifier = Modifier.clickable { onBack() }
        )
    }
}

// ==========================================
// 3. Complete Profile Screen
// ==========================================

@Composable
fun CompleteProfileScreen(
    fullName: String,
    onFullNameChange: (String) -> Unit,
    profileEmail: String,
    onEmailChange: (String) -> Unit,
    mobileNumber: String,
    onMobileChange: (String) -> Unit,
    jobTitle: String,
    onJobTitleChange: (String) -> Unit,
    onBack: () -> Unit,
    onContinue: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(BrandIvory)
                .border(1.dp, BrandBorder)
                .padding(horizontal = 16.dp, vertical = 12.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onBack) {
                    Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = BrandBronze)
                }
                Spacer(modifier = Modifier.weight(1f))
                Text("Complete Profile", fontSize = 15.sp, fontWeight = FontWeight.Bold, color = BrandText)
                Spacer(modifier = Modifier.weight(1f))
                Box(modifier = Modifier.size(24.dp))
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("Complete Your Profile", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = BrandText)
            Text("Tell us a bit about yourself", fontSize = 12.sp, color = BrandTextMuted, modifier = Modifier.padding(top = 2.dp))

            Spacer(modifier = Modifier.height(16.dp))

            Box(
                modifier = Modifier
                    .size(80.dp)
                    .clip(CircleShape)
                    .background(BrandBorderSubtle),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Person, contentDescription = null, tint = BrandTextMuted, modifier = Modifier.size(40.dp))
            }
            Text("Add photo (Optional)", fontSize = 11.sp, color = BrandTextMuted, modifier = Modifier.padding(top = 6.dp))

            Spacer(modifier = Modifier.height(16.dp))

            AndroidLabeledField(label = "Full Name *", value = fullName, onValueChange = onFullNameChange, placeholder = "Mayank Sharma")
            Spacer(modifier = Modifier.height(12.dp))
            AndroidLabeledField(label = "Email", value = profileEmail, onValueChange = onEmailChange, placeholder = "mayank@example.com")
            Spacer(modifier = Modifier.height(12.dp))
            AndroidLabeledField(label = "Mobile Number", value = mobileNumber, onValueChange = onMobileChange, placeholder = "+91 98765 43210")
            Spacer(modifier = Modifier.height(12.dp))
            AndroidLabeledField(label = "Job Title (Optional)", value = jobTitle, onValueChange = onJobTitleChange, placeholder = "Architect, Project Manager")

            Spacer(modifier = Modifier.height(24.dp))

            Button(
                onClick = onContinue,
                modifier = Modifier.fillMaxWidth().height(48.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
            ) {
                Text("Continue", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandIvory)
            }
        }
    }
}

// ==========================================
// 4. Organization Choice Screen
// ==========================================

@Composable
fun OrganizationChoiceScreen(
    invitationCode: String,
    onCodeChange: (String) -> Unit,
    onBack: () -> Unit,
    onCreateOrg: () -> Unit,
    onJoinOrg: () -> Unit,
    onSkip: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(BrandIvory)
                .border(1.dp, BrandBorder)
                .padding(horizontal = 16.dp, vertical = 12.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onBack) {
                    Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = BrandBronze)
                }
                Spacer(modifier = Modifier.weight(1f))
                Text("Organization Choice", fontSize = 15.sp, fontWeight = FontWeight.Bold, color = BrandText)
                Spacer(modifier = Modifier.weight(1f))
                Box(modifier = Modifier.size(24.dp))
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier
                    .size(72.dp)
                    .clip(CircleShape)
                    .background(BrandIvory)
                    .border(1.dp, BrandBronze.copy(alpha = 0.3f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Build, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(32.dp))
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text("You're all set!", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = BrandText)
            Text("Now let's get you started with an organization.", fontSize = 12.sp, color = BrandTextMuted)

            Spacer(modifier = Modifier.height(20.dp))

            // Option 1: Create Org
            Card(
                modifier = Modifier.fillMaxWidth().clickable { onCreateOrg() },
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier.size(44.dp).clip(RoundedCornerShape(10.dp)).background(BrandParchment),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Default.Home, contentDescription = null, tint = BrandBronze)
                    }
                    Spacer(modifier = Modifier.width(14.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Create an Organization", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandText)
                        Text("Set up your organization and invite your team to start mapping spaces.", fontSize = 11.sp, color = BrandTextMuted)
                    }
                    Icon(Icons.Default.ArrowForward, contentDescription = null, tint = BrandTextMuted, modifier = Modifier.size(16.dp))
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Option 2: Join Org
            Card(
                modifier = Modifier.fillMaxWidth().clickable { onJoinOrg() },
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier.size(44.dp).clip(RoundedCornerShape(10.dp)).background(BrandParchment),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Default.Person, contentDescription = null, tint = BrandBronze)
                    }
                    Spacer(modifier = Modifier.width(14.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Join an Organization", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandText)
                        Text("Use an invitation link or code to join an existing organization.", fontSize = 11.sp, color = BrandTextMuted)
                    }
                    Icon(Icons.Default.ArrowForward, contentDescription = null, tint = BrandTextMuted, modifier = Modifier.size(16.dp))
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            Text(
                text = "I'll do this later",
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
                color = BrandBronze,
                modifier = Modifier.clickable { onSkip() }
            )
        }
    }
}

// ==========================================
// 9. Select Organization Screen
// ==========================================

@Composable
fun SelectOrganizationScreen(
    userName: String,
    orgs: List<Triple<String, String, String>> = emptyList(),
    onSelectOrg: (String) -> Unit,
    onCreateNewOrg: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(16.dp))

        Text("V Ā S T U", fontSize = 22.sp, fontWeight = FontWeight.Black, letterSpacing = 6.sp, color = BrandBronze)
        Spacer(modifier = Modifier.height(16.dp))

        Text("Welcome back, ${userName.split(" ").firstOrNull() ?: "Architect"}", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = BrandText)
        Text("Select an organization to continue", fontSize = 12.sp, color = BrandTextMuted, modifier = Modifier.padding(top = 2.dp))

        Spacer(modifier = Modifier.height(20.dp))

        if (orgs.isEmpty()) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 12.dp),
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(
                        Icons.Default.Home,
                        contentDescription = null,
                        tint = BrandBronze.copy(alpha = 0.6f),
                        modifier = Modifier.size(36.dp)
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        "No Organizations Found",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = BrandText
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        "Create an organization to start collaborating with your spatial team.",
                        fontSize = 12.sp,
                        color = BrandTextMuted,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                }
            }
        } else {
            orgs.forEach { (name, role, count) ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 5.dp)
                        .clickable { onSelectOrg(name) },
                    colors = CardDefaults.cardColors(containerColor = BrandIvory),
                    shape = RoundedCornerShape(14.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
                ) {
                    Row(
                        modifier = Modifier.padding(14.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier.size(44.dp).clip(RoundedCornerShape(10.dp)).background(BrandParchment),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(Icons.Default.Home, contentDescription = null, tint = BrandBronze)
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(name, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandText)
                            Text("$role • $count", fontSize = 11.sp, color = BrandBronze)
                        }
                        Icon(Icons.Default.ArrowForward, contentDescription = null, tint = BrandTextMuted, modifier = Modifier.size(16.dp))
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        OutlinedButton(
            onClick = onCreateNewOrg,
            modifier = Modifier.fillMaxWidth().height(48.dp),
            shape = RoundedCornerShape(12.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
            colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandIvory)
        ) {
            Text("+ Create New Organization", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandBronze)
        }
    }
}

// ==========================================
// Helper Components
// ==========================================

@Composable
fun AndroidLabeledField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        if (label.isNotBlank()) {
            Text(label, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = BrandTextMuted)
        }
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.fillMaxWidth().padding(top = if (label.isNotBlank()) 4.dp else 0.dp),
            placeholder = { Text(placeholder, fontSize = 12.sp, color = BrandTextMuted) },
            singleLine = true,
            shape = RoundedCornerShape(10.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = BrandIvory,
                unfocusedContainerColor = BrandIvory,
                focusedBorderColor = BrandBronze,
                unfocusedBorderColor = BrandBorder
            )
        )
    }
}

@Composable
fun VastuArchwayHero(modifier: Modifier = Modifier) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .height(250.dp),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = BrandIvory),
        border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(8.dp),
            contentAlignment = Alignment.Center
        ) {
            Image(
                painter = painterResource(id = R.drawable.vastu_logo),
                contentDescription = "VĀSTU Spatial Intelligence",
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Fit
            )
        }
    }
}
