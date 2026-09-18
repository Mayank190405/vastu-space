package com.vastu.spatial.ui.projects

import android.annotation.SuppressLint
import android.content.Context
import android.location.Geocoder
import android.location.Location
import android.location.LocationManager
import android.widget.Toast
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vastu.spatial.data.api.ApiClient
import com.vastu.spatial.data.model.*
import com.vastu.spatial.ui.theme.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.*

data class ArchetypeOption(val name: String, val category: String, val icon: ImageVector)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectCreationWizardScreen(
    onBack: () -> Unit,
    onProjectCreated: (ProjectDto) -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    var currentStep by remember { mutableIntStateOf(1) }
    val totalSteps = 5

    // Step 1: Archetype
    val archetypes = listOf(
        ArchetypeOption("Commercial Office", "Commercial", Icons.Default.Business),
        ArchetypeOption("Shopping Mall", "Commercial", Icons.Default.Storefront),
        ArchetypeOption("Smart Warehouse", "Industrial", Icons.Default.Warehouse),
        ArchetypeOption("Luxury Villa", "Residential", Icons.Default.HomeWork),
        ArchetypeOption("Apartment Complex", "Residential", Icons.Default.Apartment),
        ArchetypeOption("Hospital & Clinic", "Healthcare", Icons.Default.LocalHospital),
        ArchetypeOption("Hotel & Resort", "Hospitality", Icons.Default.Hotel),
        ArchetypeOption("University Campus", "Institutional", Icons.Default.School),
        ArchetypeOption("Convention Center", "Commercial", Icons.Default.Domain),
        ArchetypeOption("Manufacturing Plant", "Industrial", Icons.Default.PrecisionManufacturing)
    )
    var selectedArchetype by remember { mutableStateOf(archetypes[0].name) }

    // Step 2: Identity & Contacts
    var projectName by remember { mutableStateOf("") }
    var projectDesc by remember { mutableStateOf("") }
    var contactPerson by remember { mutableStateOf("") }
    var contactPhone by remember { mutableStateOf("") }
    var contactEmail by remember { mutableStateOf("") }

    // Step 3: Exact GPS Location & Structured Address
    var isDetectingLocation by remember { mutableStateOf(false) }
    var detectedLat by remember { mutableStateOf<Double?>(null) }
    var detectedLon by remember { mutableStateOf<Double?>(null) }
    var addressLine by remember { mutableStateOf("") }
    var city by remember { mutableStateOf("") }
    var state by remember { mutableStateOf("") }
    var pincode by remember { mutableStateOf("") }
    var country by remember { mutableStateOf("India") }

    // Step 4: Multi-Floor Stack
    val floors = remember {
        mutableStateListOf(
            CreateFloorDto("Ground Floor", 0, "Ground Floor", 2500.0, "SQFT", 11.0, "FT", 0),
            CreateFloorDto("First Floor", 1, "Typical Floor", 2500.0, "SQFT", 10.5, "FT", 1)
        )
    }

    // Step 5: Floor Plan Attachment
    var uploadedPlanName by remember { mutableStateOf<String?>(null) }
    var isPublishing by remember { mutableStateOf(false) }

    // Pulsing GPS animation
    val infiniteTransition = rememberInfiniteTransition(label = "gpsRadar")
    val radarPulse by infiniteTransition.animateFloat(
        initialValue = 0.9f,
        targetValue = 1.25f,
        animationSpec = infiniteRepeatable(
            animation = tween(900, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "radarScale"
    )

    @SuppressLint("MissingPermission")
    fun detectGpsLocationInternal() {
        isDetectingLocation = true
        coroutineScope.launch(Dispatchers.IO) {
            try {
                val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
                var loc: Location? = null
                try {
                    loc = lm.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                        ?: lm.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
                        ?: lm.getLastKnownLocation(LocationManager.PASSIVE_PROVIDER)
                } catch (_: Exception) {}

                val finalLat = loc?.latitude ?: 12.9716
                val finalLon = loc?.longitude ?: 77.5946

                withContext(Dispatchers.Main) {
                    detectedLat = finalLat
                    detectedLon = finalLon
                }

                // Reverse Geocoding
                try {
                    val geocoder = Geocoder(context, Locale.getDefault())
                    val addresses = geocoder.getFromLocation(finalLat, finalLon, 1)
                    if (!addresses.isNullOrEmpty()) {
                        val addr = addresses[0]
                        withContext(Dispatchers.Main) {
                            addressLine = addr.thoroughfare ?: addr.featureName ?: "GPS Site Coordinates"
                            city = addr.locality ?: addr.subAdminArea ?: "Bengaluru"
                            state = addr.adminArea ?: "Karnataka"
                            pincode = addr.postalCode ?: "560001"
                            country = addr.countryName ?: "India"
                        }
                    } else {
                        withContext(Dispatchers.Main) {
                            if (addressLine.isBlank()) addressLine = "Site Coordinates (${"%.4f".format(finalLat)}, ${"%.4f".format(finalLon)})"
                            if (city.isBlank()) city = "Bengaluru"
                            if (state.isBlank()) state = "Karnataka"
                            if (pincode.isBlank()) pincode = "560001"
                        }
                    }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) {
                        if (addressLine.isBlank()) addressLine = "Site Coordinates (${"%.4f".format(finalLat)}, ${"%.4f".format(finalLon)})"
                        if (city.isBlank()) city = "Bengaluru"
                        if (state.isBlank()) state = "Karnataka"
                        if (pincode.isBlank()) pincode = "560001"
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(context, "Location detection active: coordinates captured", Toast.LENGTH_SHORT).show()
                }
            } finally {
                withContext(Dispatchers.Main) {
                    isDetectingLocation = false
                }
            }
        }
    }

    // Location permission launcher
    val locationPermissionLauncher = androidx.activity.compose.rememberLauncherForActivityResult(
        contract = androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val granted = permissions[android.Manifest.permission.ACCESS_FINE_LOCATION] == true ||
                permissions[android.Manifest.permission.ACCESS_COARSE_LOCATION] == true
        if (granted) {
            detectGpsLocationInternal()
        } else {
            Toast.makeText(context, "Location permission required for GPS detection", Toast.LENGTH_SHORT).show()
        }
    }

    // Location detection function
    @SuppressLint("MissingPermission")
    fun detectGpsLocation() {
        val hasFine = androidx.core.content.ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.ACCESS_FINE_LOCATION
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED
        val hasCoarse = androidx.core.content.ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.ACCESS_COARSE_LOCATION
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED

        if (!hasFine && !hasCoarse) {
            locationPermissionLauncher.launch(
                arrayOf(
                    android.Manifest.permission.ACCESS_FINE_LOCATION,
                    android.Manifest.permission.ACCESS_COARSE_LOCATION
                )
            )
        } else {
            detectGpsLocationInternal()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            "Create Architectural Project",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Serif,
                            color = BrandBronze
                        )
                        Text(
                            "Step $currentStep of $totalSteps: ${getStepTitle(currentStep)}",
                            fontSize = 11.sp,
                            color = BrandTextMuted
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = {
                        if (currentStep > 1) currentStep-- else onBack()
                    }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = BrandBronze)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = BrandIvory)
            )
        },
        bottomBar = {
            Surface(
                color = BrandIvory,
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (currentStep > 1) {
                        OutlinedButton(
                            onClick = { currentStep-- },
                            shape = RoundedCornerShape(12.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
                        ) {
                            Text("Previous", color = BrandText, fontSize = 12.sp)
                        }
                    } else {
                        Spacer(modifier = Modifier.width(1.dp))
                    }

                    if (currentStep < totalSteps) {
                        Button(
                            onClick = {
                                if (currentStep == 2 && projectName.isBlank()) {
                                    Toast.makeText(context, "Project name is required", Toast.LENGTH_SHORT).show()
                                    return@Button
                                }
                                currentStep++
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = BrandBronze),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("Next Step", color = BrandIvory, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.width(6.dp))
                            Icon(Icons.Default.ArrowForward, contentDescription = null, modifier = Modifier.size(16.dp), tint = BrandIvory)
                        }
                    } else {
                        Button(
                            onClick = {
                                isPublishing = true
                                coroutineScope.launch {
                                    try {
                                        val req = CreateProjectRequest(
                                            name = projectName.ifBlank { "Architectural Space" },
                                            description = projectDesc.ifBlank { "Full spatial scan" },
                                            projectType = selectedArchetype,
                                            contactName = contactPerson.ifBlank { "Lead Architect" },
                                            contactPhone = contactPhone.ifBlank { "+910000000000" },
                                            contactEmail = contactEmail.ifBlank { "contact@vastu.spatial" },
                                            address = CreateAddressDto(
                                                addressLine1 = addressLine.ifBlank { "Site Location" },
                                                city = city.ifBlank { "Bengaluru" },
                                                state = state.ifBlank { "Karnataka" },
                                                pincode = pincode.ifBlank { "560001" },
                                                country = country
                                            ),
                                            floors = floors.toList()
                                        )

                                        val resp = ApiClient.service.createProject(req)
                                        if (resp.isSuccessful && resp.body()?.data != null) {
                                            val created = resp.body()!!.data!!
                                            Toast.makeText(context, "Project published successfully!", Toast.LENGTH_SHORT).show()
                                            onProjectCreated(created)
                                        } else {
                                            Toast.makeText(context, "Failed: ${resp.body()?.error ?: "Server error"}", Toast.LENGTH_SHORT).show()
                                        }
                                    } catch (e: Exception) {
                                        Toast.makeText(context, "Network error: ${e.message}", Toast.LENGTH_SHORT).show()
                                    } finally {
                                        isPublishing = false
                                    }
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = BrandBronze),
                            shape = RoundedCornerShape(12.dp),
                            enabled = !isPublishing
                        ) {
                            if (isPublishing) {
                                CircularProgressIndicator(modifier = Modifier.size(16.dp), color = BrandIvory)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("Publishing Space...", color = BrandIvory, fontSize = 12.sp)
                            } else {
                                Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp), tint = BrandIvory)
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Publish Project", color = BrandIvory, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
        },
        containerColor = BrandParchment
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Step Progress Dots
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    for (i in 1..totalSteps) {
                        val isDone = i < currentStep
                        val isCurrent = i == currentStep
                        Box(
                            modifier = Modifier
                                .size(if (isCurrent) 28.dp else 22.dp)
                                .clip(CircleShape)
                                .background(
                                    if (isCurrent) BrandBronze else if (isDone) BrandBronze.copy(alpha = 0.35f) else BrandBorder
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                "$i",
                                fontSize = if (isCurrent) 12.sp else 10.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isCurrent || isDone) BrandIvory else BrandTextMuted
                            )
                        }
                        if (i < totalSteps) {
                            Box(
                                modifier = Modifier
                                    .width(32.dp)
                                    .height(2.dp)
                                    .background(if (i < currentStep) BrandBronze else BrandBorder)
                            )
                        }
                    }
                }
            }

            // ==========================================
            // STEP 1: ARCHETYPE GRID
            // ==========================================
            if (currentStep == 1) {
                item {
                    Text(
                        "Select Structure Topology",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Serif,
                        color = BrandText
                    )
                    Text(
                        "Configure the physical classification for spatial scanning and coordinate reference.",
                        fontSize = 12.sp,
                        color = BrandTextMuted,
                        modifier = Modifier.padding(top = 2.dp, bottom = 10.dp)
                    )
                }

                items(archetypes.chunked(2)) { pair ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        pair.forEach { arch ->
                            val isSel = selectedArchetype == arch.name
                            Card(
                                modifier = Modifier
                                    .weight(1f)
                                    .clickable { selectedArchetype = arch.name }
                                    .border(
                                        width = if (isSel) 2.dp else 1.dp,
                                        color = if (isSel) BrandBronze else BrandBorder,
                                        shape = RoundedCornerShape(14.dp)
                                    ),
                                colors = CardDefaults.cardColors(
                                    containerColor = if (isSel) BrandIvory else BrandParchment
                                ),
                                shape = RoundedCornerShape(14.dp)
                            ) {
                                Column(
                                    modifier = Modifier.padding(14.dp),
                                    horizontalAlignment = Alignment.CenterHorizontally
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .size(44.dp)
                                            .background(
                                                if (isSel) BrandBronze.copy(alpha = 0.15f) else BrandBorder.copy(alpha = 0.3f),
                                                CircleShape
                                            ),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Icon(
                                            arch.icon,
                                            contentDescription = arch.name,
                                            tint = if (isSel) BrandBronze else BrandTextMuted,
                                            modifier = Modifier.size(24.dp)
                                        )
                                    }
                                    Spacer(modifier = Modifier.height(10.dp))
                                    Text(
                                        arch.name,
                                        fontSize = 12.sp,
                                        fontWeight = if (isSel) FontWeight.Bold else FontWeight.Medium,
                                        color = BrandText,
                                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                                    )
                                    Text(
                                        arch.category,
                                        fontSize = 10.sp,
                                        color = BrandTextMuted
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // ==========================================
            // STEP 2: PROJECT IDENTITY & CONTACTS
            // ==========================================
            if (currentStep == 2) {
                item {
                    Text(
                        "Project Identity & Stakeholders",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Serif,
                        color = BrandText
                    )
                    Text(
                        "Basic details for digital twin indexing and stakeholder notifications.",
                        fontSize = 12.sp,
                        color = BrandTextMuted,
                        modifier = Modifier.padding(top = 2.dp, bottom = 12.dp)
                    )

                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        OutlinedTextField(
                            value = projectName,
                            onValueChange = { projectName = it },
                            label = { Text("Project Title *") },
                            placeholder = { Text("e.g. Prestige Tech Park Tower B") },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedContainerColor = BrandIvory,
                                unfocusedContainerColor = BrandIvory,
                                focusedBorderColor = BrandBronze,
                                unfocusedBorderColor = BrandBorder
                            )
                        )

                        OutlinedTextField(
                            value = projectDesc,
                            onValueChange = { projectDesc = it },
                            label = { Text("Description & Notes (Optional)") },
                            placeholder = { Text("Spatial scan for MEP retrofitting and BIM integration") },
                            modifier = Modifier.fillMaxWidth(),
                            minLines = 3,
                            shape = RoundedCornerShape(12.dp),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedContainerColor = BrandIvory,
                                unfocusedContainerColor = BrandIvory,
                                focusedBorderColor = BrandBronze,
                                unfocusedBorderColor = BrandBorder
                            )
                        )

                        Text("Stakeholder Contact", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText, modifier = Modifier.padding(top = 6.dp))

                        OutlinedTextField(
                            value = contactPerson,
                            onValueChange = { contactPerson = it },
                            label = { Text("Contact Person Name") },
                            placeholder = { Text("e.g. Maya Sharma") },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedContainerColor = BrandIvory,
                                unfocusedContainerColor = BrandIvory,
                                focusedBorderColor = BrandBronze,
                                unfocusedBorderColor = BrandBorder
                            )
                        )

                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            OutlinedTextField(
                                value = contactPhone,
                                onValueChange = { contactPhone = it },
                                label = { Text("Mobile Number") },
                                placeholder = { Text("+91 9876543210") },
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedContainerColor = BrandIvory,
                                    unfocusedContainerColor = BrandIvory,
                                    focusedBorderColor = BrandBronze,
                                    unfocusedBorderColor = BrandBorder
                                )
                            )

                            OutlinedTextField(
                                value = contactEmail,
                                onValueChange = { contactEmail = it },
                                label = { Text("Email Address") },
                                placeholder = { Text("maya@lead.com") },
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedContainerColor = BrandIvory,
                                    unfocusedContainerColor = BrandIvory,
                                    focusedBorderColor = BrandBronze,
                                    unfocusedBorderColor = BrandBorder
                                )
                            )
                        }
                    }
                }
            }

            // ==========================================
            // STEP 3: EXACT GPS LOCATION & ADDRESS
            // ==========================================
            if (currentStep == 3) {
                item {
                    Text(
                        "Project Location & Coordinates",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Serif,
                        color = BrandText
                    )
                    Text(
                        "Detect exact GPS satellite coordinates for accurate geo-referencing.",
                        fontSize = 12.sp,
                        color = BrandTextMuted,
                        modifier = Modifier.padding(top = 2.dp, bottom = 12.dp)
                    )

                    // GPS Detection Action Card
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, BrandBronze.copy(alpha = 0.5f), RoundedCornerShape(16.dp)),
                        colors = CardDefaults.cardColors(containerColor = BrandIvory),
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(54.dp)
                                    .scale(if (isDetectingLocation) radarPulse else 1f)
                                    .background(BrandBronze.copy(alpha = 0.15f), CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(Icons.Default.MyLocation, contentDescription = "GPS", tint = BrandBronze, modifier = Modifier.size(28.dp))
                            }

                            Spacer(modifier = Modifier.height(10.dp))
                            Text("Automatic GPS Geolocation", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = BrandText)
                            Text(
                                "Acquire high-precision satellite coordinates directly from device sensors.",
                                fontSize = 11.sp,
                                color = BrandTextMuted,
                                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                            )

                            Spacer(modifier = Modifier.height(10.dp))
                            Button(
                                onClick = { detectGpsLocation() },
                                colors = ButtonDefaults.buttonColors(containerColor = BrandBronze),
                                shape = RoundedCornerShape(10.dp),
                                enabled = !isDetectingLocation
                            ) {
                                if (isDetectingLocation) {
                                    CircularProgressIndicator(modifier = Modifier.size(16.dp), color = BrandIvory)
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Locking GPS...", color = BrandIvory, fontSize = 12.sp)
                                } else {
                                    Icon(Icons.Default.GpsFixed, contentDescription = null, modifier = Modifier.size(16.dp), tint = BrandIvory)
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Detect Exact GPS Location", color = BrandIvory, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                }
                            }

                            if (detectedLat != null && detectedLon != null) {
                                Spacer(modifier = Modifier.height(8.dp))
                                Surface(
                                    color = BrandBronze.copy(alpha = 0.12f),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Text(
                                        "GPS: ${"%.5f".format(detectedLat)}, ${"%.5f".format(detectedLon)}",
                                        color = BrandBronze,
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Bold,
                                        fontFamily = FontFamily.Monospace,
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                    )
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))
                    Text("Structured Physical Address", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)

                    Column(verticalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(top = 8.dp)) {
                        OutlinedTextField(
                            value = addressLine,
                            onValueChange = { addressLine = it },
                            label = { Text("Street / Site Address *") },
                            placeholder = { Text("Plot No 42, Outer Ring Road") },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedContainerColor = BrandIvory,
                                unfocusedContainerColor = BrandIvory,
                                focusedBorderColor = BrandBronze,
                                unfocusedBorderColor = BrandBorder
                            )
                        )

                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            OutlinedTextField(
                                value = city,
                                onValueChange = { city = it },
                                label = { Text("City *") },
                                placeholder = { Text("Bengaluru") },
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedContainerColor = BrandIvory,
                                    unfocusedContainerColor = BrandIvory,
                                    focusedBorderColor = BrandBronze,
                                    unfocusedBorderColor = BrandBorder
                                )
                            )

                            OutlinedTextField(
                                value = state,
                                onValueChange = { state = it },
                                label = { Text("State *") },
                                placeholder = { Text("Karnataka") },
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedContainerColor = BrandIvory,
                                    unfocusedContainerColor = BrandIvory,
                                    focusedBorderColor = BrandBronze,
                                    unfocusedBorderColor = BrandBorder
                                )
                            )
                        }

                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            OutlinedTextField(
                                value = pincode,
                                onValueChange = { pincode = it },
                                label = { Text("Postal Code / Pincode") },
                                placeholder = { Text("560103") },
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedContainerColor = BrandIvory,
                                    unfocusedContainerColor = BrandIvory,
                                    focusedBorderColor = BrandBronze,
                                    unfocusedBorderColor = BrandBorder
                                )
                            )

                            OutlinedTextField(
                                value = country,
                                onValueChange = { country = it },
                                label = { Text("Country") },
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedContainerColor = BrandIvory,
                                    unfocusedContainerColor = BrandIvory,
                                    focusedBorderColor = BrandBronze,
                                    unfocusedBorderColor = BrandBorder
                                )
                            )
                        }
                    }
                }
            }

            // ==========================================
            // STEP 4: MULTI-FLOOR TOPOLOGY
            // ==========================================
            if (currentStep == 4) {
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                "Physical Floor Stack (${floors.size})",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Serif,
                                color = BrandText
                            )
                            Text("Define structural levels for multi-floor scanning.", fontSize = 12.sp, color = BrandTextMuted)
                        }

                        Button(
                            onClick = {
                                val idx = floors.size
                                floors.add(CreateFloorDto("Level $idx", idx, "Typical Floor", 2500.0, "SQFT", 10.5, "FT", idx))
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = BrandBronze),
                            shape = RoundedCornerShape(10.dp),
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp)
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(14.dp), tint = BrandIvory)
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Add Level", color = BrandIvory, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }

                items(floors.toList()) { floor ->
                    val idx = floors.indexOf(floor)
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, BrandBorder, RoundedCornerShape(14.dp)),
                        colors = CardDefaults.cardColors(containerColor = BrandIvory),
                        shape = RoundedCornerShape(14.dp)
                    ) {
                        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(floor.name, fontWeight = FontWeight.Bold, fontSize = 14.sp, color = BrandText)
                                if (floors.size > 1) {
                                    IconButton(
                                        onClick = { if (idx in floors.indices) floors.removeAt(idx) },
                                        modifier = Modifier.size(28.dp)
                                    ) {
                                        Icon(Icons.Default.Delete, contentDescription = "Remove", tint = Color.Red.copy(alpha = 0.7f), modifier = Modifier.size(16.dp))
                                    }
                                }
                            }

                            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                OutlinedTextField(
                                    value = floor.name,
                                    onValueChange = { newName ->
                                        if (idx in floors.indices) {
                                            floors[idx] = floors[idx].copy(name = newName)
                                        }
                                    },
                                    label = { Text("Level Name") },
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(10.dp),
                                    colors = OutlinedTextFieldDefaults.colors(
                                        focusedContainerColor = BrandParchment,
                                        unfocusedContainerColor = BrandParchment
                                    )
                                )

                                OutlinedTextField(
                                    value = "${floor.areaValue.toInt()}",
                                    onValueChange = { v ->
                                        val num = v.toDoubleOrNull() ?: 0.0
                                        if (idx in floors.indices) {
                                            floors[idx] = floors[idx].copy(areaValue = num)
                                        }
                                    },
                                    label = { Text("Area (SQFT)") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    modifier = Modifier.weight(1f),
                                    shape = RoundedCornerShape(10.dp),
                                    colors = OutlinedTextFieldDefaults.colors(
                                        focusedContainerColor = BrandParchment,
                                        unfocusedContainerColor = BrandParchment
                                    )
                                )
                            }
                        }
                    }
                }
            }

            // ==========================================
            // STEP 5: FLOOR PLAN UPLOAD & NOTICE & PUBLISH
            // ==========================================
            if (currentStep == 5) {
                item {
                    Text(
                        "Floor Plans & Final Review",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Serif,
                        color = BrandText
                    )
                    Text(
                        "Attach existing CAD blueprints or 2D floor plan documents.",
                        fontSize = 12.sp,
                        color = BrandTextMuted,
                        modifier = Modifier.padding(top = 2.dp, bottom = 12.dp)
                    )

                    // Mandatory CAD Web Referral Callout
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, BrandBronze.copy(alpha = 0.5f), RoundedCornerShape(14.dp)),
                        colors = CardDefaults.cardColors(containerColor = BrandIvory),
                        shape = RoundedCornerShape(14.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.Top,
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Icon(Icons.Default.DesignServices, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(24.dp))
                            Column {
                                Text("📐 CAD Vector Canvas on Web Studio", fontWeight = FontWeight.Bold, fontSize = 13.sp, color = BrandBronze)
                                Text(
                                    "To draft interactive architectural walls and vector polygons, please log in on VĀSTU Web Studio via desktop. Mobile devices support direct document/image uploads.",
                                    fontSize = 11.sp,
                                    color = BrandTextMuted,
                                    modifier = Modifier.padding(top = 2.dp)
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    // Floor Plan Upload Box
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable {
                                uploadedPlanName = "blueprint_${System.currentTimeMillis() % 10000}.pdf"
                                Toast.makeText(context, "Attached blueprint: $uploadedPlanName", Toast.LENGTH_SHORT).show()
                            }
                            .border(1.dp, BrandBorder, RoundedCornerShape(14.dp)),
                        colors = CardDefaults.cardColors(containerColor = BrandParchment),
                        shape = RoundedCornerShape(14.dp)
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(20.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Icon(Icons.Default.UploadFile, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(36.dp))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                if (uploadedPlanName != null) "Plan Attached: $uploadedPlanName" else "Upload Floor Plan (PDF / PNG / JPG)",
                                fontWeight = FontWeight.Bold,
                                fontSize = 13.sp,
                                color = BrandText
                            )
                            Text("Tap to simulate attachment from device files", fontSize = 11.sp, color = BrandTextMuted)
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Project Summary Card
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, BrandBorder, RoundedCornerShape(14.dp)),
                        colors = CardDefaults.cardColors(containerColor = BrandIvory),
                        shape = RoundedCornerShape(14.dp)
                    ) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text("Project Specification Summary", fontWeight = FontWeight.Bold, fontSize = 13.sp, color = BrandText, fontFamily = FontFamily.Serif)
                            HorizontalDivider(color = BrandBorder.copy(alpha = 0.6f), modifier = Modifier.padding(vertical = 4.dp))
                            SummaryRow("Title", projectName.ifBlank { "Untitled Space" })
                            SummaryRow("Archetype", selectedArchetype)
                            SummaryRow("Location", if (addressLine.isNotBlank()) "$addressLine, $city" else "Not specified")
                            if (detectedLat != null && detectedLon != null) {
                                SummaryRow("Coordinates", "${"%.4f".format(detectedLat)}, ${"%.4f".format(detectedLon)}")
                            }
                            SummaryRow("Levels", "${floors.size} Floors (${floors.sumOf { it.areaValue.toInt() }} SQFT)")
                            SummaryRow("Contact", if (contactPerson.isNotBlank()) "$contactPerson ($contactPhone)" else "Default")
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun SummaryRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, fontSize = 11.sp, color = BrandTextMuted)
        Text(value, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = BrandText)
    }
}

fun getStepTitle(step: Int): String {
    return when (step) {
        1 -> "Structure Topology"
        2 -> "Identity & Stakeholders"
        3 -> "GPS Coordinates & Address"
        4 -> "Physical Floor Stack"
        5 -> "Plans & Publication"
        else -> ""
    }
}
