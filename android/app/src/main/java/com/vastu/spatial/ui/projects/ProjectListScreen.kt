package com.vastu.spatial.ui.projects

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material.icons.filled.Layers
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vastu.spatial.data.api.ApiClient
import com.vastu.spatial.data.model.CreateAddressDto
import com.vastu.spatial.data.model.CreateFloorDto
import com.vastu.spatial.data.model.CreateProjectRequest
import com.vastu.spatial.data.model.FloorDto
import com.vastu.spatial.data.model.ProjectDto
import com.vastu.spatial.ui.theme.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectListScreen(
    onSelectProjectForCapture: (ProjectDto, FloorDto?) -> Unit,
    onSignOut: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var projects by remember { mutableStateOf<List<ProjectDto>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }

    // Project creation state
    var showCreateDialog by remember { mutableStateOf(false) }
    var newProjectName by remember { mutableStateOf("") }
    var newProjectType by remember { mutableStateOf("Building") }
    var newProjectDesc by remember { mutableStateOf("") }
    var contactName by remember { mutableStateOf("") }
    var contactEmail by remember { mutableStateOf("") }
    var contactPhone by remember { mutableStateOf("") }
    var addressLine by remember { mutableStateOf("") }
    var city by remember { mutableStateOf("") }
    var state by remember { mutableStateOf("") }
    var pincode by remember { mutableStateOf("") }
    val floorList = remember {
        mutableStateListOf(
            CreateFloorDto("Ground Floor", 0, "Standard", 2400.0, "SQFT", 10.5, "FT", 0)
        )
    }
    var isSubmitting by remember { mutableStateOf(false) }
    var createError by remember { mutableStateOf<String?>(null) }

    // Floor selection for capture
    var projectForCapture by remember { mutableStateOf<ProjectDto?>(null) }
    var availableFloors by remember { mutableStateOf<List<FloorDto>>(emptyList()) }
    var isLoadingFloors by remember { mutableStateOf(false) }
    var showFloorSelectionDialog by remember { mutableStateOf(false) }

    val supportedTypes = listOf(
        "Building", "Mall", "Office", "Warehouse", "Hospital",
        "Hotel", "Campus", "Convention Centre", "Villa", "Apartment Complex"
    )

    val loadProjects = {
        coroutineScope.launch {
            isLoading = true
            try {
                val resp = ApiClient.service.getProjects()
                if (resp.isSuccessful && resp.body()?.data != null) {
                    projects = resp.body()!!.data!!
                }
            } catch (e: Exception) {
                e.printStackTrace()
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(Unit) {
        loadProjects()
    }

    val openCaptureFloorPicker: (ProjectDto) -> Unit = { project ->
        projectForCapture = project
        availableFloors = emptyList()
        isLoadingFloors = true
        showFloorSelectionDialog = true

        coroutineScope.launch {
            try {
                val resp = ApiClient.service.getFloors(project.id)
                if (resp.isSuccessful && resp.body()?.data != null) {
                    availableFloors = resp.body()!!.data!!
                }
            } catch (e: Exception) {
                e.printStackTrace()
            } finally {
                isLoadingFloors = false
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        "Spatial Projects",
                        fontWeight = FontWeight.Bold,
                        color = BrandBronze,
                        fontSize = 18.sp
                    )
                },
                actions = {
                    IconButton(onClick = {
                        ApiClient.getTokenManager()?.clear()
                        onSignOut()
                    }) {
                        Icon(Icons.Default.ExitToApp, contentDescription = "Sign Out", tint = BrandTextMuted)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = BrandIvory
                )
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showCreateDialog = true },
                containerColor = BrandBronze,
                contentColor = BrandIvory
            ) {
                Icon(Icons.Default.Add, contentDescription = "New Project")
            }
        },
        containerColor = BrandParchment
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.align(Alignment.Center),
                    color = BrandBronze
                )
            } else if (projects.isEmpty()) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Icon(
                        Icons.Default.Layers,
                        contentDescription = null,
                        tint = BrandBronze,
                        modifier = Modifier.size(56.dp)
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        "No Projects Yet",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = BrandText
                    )
                    Text(
                        "Create your first architectural project to begin scanning floors and spatial structures.",
                        color = BrandTextMuted,
                        fontSize = 14.sp,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                        modifier = Modifier.padding(top = 8.dp)
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Button(
                        onClick = { showCreateDialog = true },
                        colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
                    ) {
                        Text("Create First Project", color = BrandIvory, fontWeight = FontWeight.Bold)
                    }
                }
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    items(projects) { project ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .border(1.dp, BrandBorder, RoundedCornerShape(14.dp)),
                            shape = RoundedCornerShape(14.dp),
                            colors = CardDefaults.cardColors(containerColor = BrandIvory),
                            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                        ) {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(16.dp)
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.Top
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = project.name,
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 16.sp,
                                            color = BrandText
                                        )
                                        project.projectType?.let { pType ->
                                            Text(
                                                text = pType.uppercase(),
                                                fontSize = 10.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = BrandBronze,
                                                modifier = Modifier
                                                    .padding(top = 2.dp)
                                                    .background(BrandBronzeLight, RoundedCornerShape(4.dp))
                                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                                            )
                                        }
                                    }

                                    Button(
                                        onClick = { openCaptureFloorPicker(project) },
                                        colors = ButtonDefaults.buttonColors(containerColor = BrandBronze),
                                        shape = RoundedCornerShape(8.dp),
                                        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 8.dp)
                                    ) {
                                        Icon(
                                            Icons.Default.Videocam,
                                            contentDescription = "Capture",
                                            tint = BrandIvory,
                                            modifier = Modifier.size(16.dp)
                                        )
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text("Capture", color = BrandIvory, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                    }
                                }

                                if (!project.description.isNullOrBlank()) {
                                    Text(
                                        text = project.description,
                                        fontSize = 13.sp,
                                        color = BrandTextMuted,
                                        maxLines = 2,
                                        modifier = Modifier.padding(top = 8.dp)
                                    )
                                }

                                Spacer(modifier = Modifier.height(10.dp))

                                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                                    project.totalFloorsCount?.let { count ->
                                        if (count > 0) {
                                            Text(
                                                text = "$count Floors",
                                                fontSize = 12.sp,
                                                fontWeight = FontWeight.Medium,
                                                color = BrandTextMuted
                                            )
                                        }
                                    }
                                    project.totalAreaSqft?.let { area ->
                                        if (area > 0) {
                                            Text(
                                                text = "${area.toInt()} SQFT",
                                                fontSize = 12.sp,
                                                fontWeight = FontWeight.Medium,
                                                color = BrandTextMuted
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ==========================================
    // FLOOR SELECTION DIALOG FOR CAPTURE
    // ==========================================
    if (showFloorSelectionDialog) {
        AlertDialog(
            onDismissRequest = { showFloorSelectionDialog = false },
            containerColor = BrandIvory,
            title = {
                Column {
                    Text(
                        projectForCapture?.name ?: "Select Floor",
                        color = BrandText,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )
                    Text(
                        "Select the floor level you are scanning:",
                        color = BrandTextMuted,
                        fontSize = 12.sp
                    )
                }
            },
            text = {
                if (isLoadingFloors) {
                    Box(modifier = Modifier.fillMaxWidth().height(100.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(color = BrandBronze)
                    }
                } else if (availableFloors.isEmpty()) {
                    Column(
                        modifier = Modifier.fillMaxWidth().padding(8.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("No floors found for this project.", color = BrandTextMuted, fontSize = 13.sp)
                        Spacer(modifier = Modifier.height(12.dp))
                        Button(
                            onClick = {
                                showFloorSelectionDialog = false
                                projectForCapture?.let { onSelectProjectForCapture(it, null) }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
                        ) {
                            Text("Capture on Default Level", color = BrandIvory, fontWeight = FontWeight.Bold)
                        }
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxWidth().heightIn(max = 300.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(availableFloors) { floor ->
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable {
                                        showFloorSelectionDialog = false
                                        projectForCapture?.let { onSelectProjectForCapture(it, floor) }
                                    },
                                shape = RoundedCornerShape(8.dp),
                                colors = CardDefaults.cardColors(containerColor = Color.White),
                                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorderSubtle)
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth().padding(12.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column {
                                        Text(floor.name, fontWeight = FontWeight.Bold, color = BrandText, fontSize = 14.sp)
                                        Text(
                                            "${floor.floorType} • ${floor.areaValue?.toInt() ?: 0} ${floor.areaUnit ?: "SQFT"}",
                                            color = BrandTextMuted,
                                            fontSize = 12.sp
                                        )
                                    }
                                    Text("Select →", color = BrandBronze, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showFloorSelectionDialog = false }) {
                    Text("Cancel", color = BrandTextMuted)
                }
            }
        )
    }

    // ==========================================
    // CREATE PROJECT DIALOG
    // ==========================================
    if (showCreateDialog) {
        AlertDialog(
            onDismissRequest = { if (!isSubmitting) showCreateDialog = false },
            containerColor = BrandIvory,
            title = {
                Text("Create New Project", color = BrandText, fontWeight = FontWeight.Bold, fontSize = 18.sp)
            },
            text = {
                val dialogScrollState = rememberScrollState()
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(max = 420.dp)
                        .verticalScroll(dialogScrollState)
                ) {
                    CustomInputField(value = newProjectName, onValueChange = { newProjectName = it }, label = "Project Name *")
                    Spacer(modifier = Modifier.height(10.dp))
                    CustomInputField(value = newProjectType, onValueChange = { newProjectType = it }, label = "Project Type (e.g. Building, Mall, Office)")
                    Spacer(modifier = Modifier.height(10.dp))
                    CustomInputField(value = newProjectDesc, onValueChange = { newProjectDesc = it }, label = "Description (Optional)")
                    Spacer(modifier = Modifier.height(10.dp))
                    CustomInputField(value = contactName, onValueChange = { contactName = it }, label = "Contact Person")
                    Spacer(modifier = Modifier.height(10.dp))
                    CustomInputField(value = contactPhone, onValueChange = { contactPhone = it }, label = "Contact Mobile", keyboardType = KeyboardType.Phone)
                    Spacer(modifier = Modifier.height(10.dp))
                    CustomInputField(value = contactEmail, onValueChange = { contactEmail = it }, label = "Contact Email", keyboardType = KeyboardType.Email)
                    Spacer(modifier = Modifier.height(10.dp))
                    CustomInputField(value = addressLine, onValueChange = { addressLine = it }, label = "Street Address")
                    Spacer(modifier = Modifier.height(10.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Box(modifier = Modifier.weight(1f)) {
                            CustomInputField(value = city, onValueChange = { city = it }, label = "City")
                        }
                        Box(modifier = Modifier.weight(1f)) {
                            CustomInputField(value = state, onValueChange = { state = it }, label = "State")
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Floors (${floorList.size})", fontWeight = FontWeight.Bold, color = BrandText, fontSize = 13.sp)
                        TextButton(onClick = {
                            val count = floorList.size
                            floorList.add(CreateFloorDto("Floor $count", count, "Standard", 2400.0, "SQFT", 10.5, "FT", count))
                        }) {
                            Text("+ Add Floor", color = BrandBronze, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                        }
                    }

                    floorList.forEachIndexed { idx, fl ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp)
                                .background(Color.White, RoundedCornerShape(6.dp))
                                .border(1.dp, BrandBorderSubtle, RoundedCornerShape(6.dp))
                                .padding(8.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(fl.name, fontSize = 12.sp, color = BrandText, fontWeight = FontWeight.SemiBold)
                            if (floorList.size > 1) {
                                IconButton(
                                    onClick = { floorList.removeAt(idx) },
                                    modifier = Modifier.size(24.dp)
                                ) {
                                    Icon(Icons.Default.Close, contentDescription = "Remove", tint = BrandError, modifier = Modifier.size(16.dp))
                                }
                            }
                        }
                    }

                    createError?.let { err ->
                        Text(err, color = BrandError, fontSize = 12.sp, modifier = Modifier.padding(top = 8.dp))
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (newProjectName.isNotBlank()) {
                            isSubmitting = true
                            createError = null

                            val req = CreateProjectRequest(
                                name = newProjectName.trim(),
                                description = newProjectDesc.ifBlank { null },
                                projectType = newProjectType.trim(),
                                contactName = contactName.ifBlank { "Site Lead" },
                                contactPhone = contactPhone.ifBlank { "+910000000000" },
                                contactEmail = contactEmail.ifBlank { "contact@project.internal" },
                                address = CreateAddressDto(
                                    addressLine1 = addressLine.ifBlank { "Site Address" },
                                    city = city.ifBlank { "Bengaluru" },
                                    state = state.ifBlank { "Karnataka" },
                                    pincode = pincode.ifBlank { "560001" },
                                    country = "India"
                                ),
                                floors = floorList.toList()
                            )

                            coroutineScope.launch {
                                try {
                                    val resp = ApiClient.service.createProject(req)
                                    if (resp.isSuccessful) {
                                        showCreateDialog = false
                                        newProjectName = ""
                                        newProjectDesc = ""
                                        loadProjects()
                                    } else {
                                        createError = resp.body()?.error ?: "Failed to create project"
                                    }
                                } catch (e: Exception) {
                                    createError = e.localizedMessage ?: "Failed to create project"
                                } finally {
                                    isSubmitting = false
                                }
                            }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = BrandBronze),
                    enabled = !isSubmitting && newProjectName.isNotBlank()
                ) {
                    if (isSubmitting) {
                        CircularProgressIndicator(color = BrandIvory, modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                    } else {
                        Text("Publish Project", color = BrandIvory, fontWeight = FontWeight.Bold)
                    }
                }
            },
            dismissButton = {
                TextButton(onClick = { showCreateDialog = false }, enabled = !isSubmitting) {
                    Text("Cancel", color = BrandTextMuted)
                }
            }
        )
    }
}

@Composable
fun CustomInputField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    placeholder: String = "",
    keyboardType: KeyboardType = KeyboardType.Text
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(text = label, color = BrandTextMuted, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.fillMaxWidth().padding(top = 3.dp),
            placeholder = { Text(placeholder.ifEmpty { label }, color = BrandTextMuted, fontSize = 12.sp) },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
            shape = RoundedCornerShape(8.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = BrandIvory,
                unfocusedContainerColor = BrandIvory,
                focusedBorderColor = BrandBronze,
                unfocusedBorderColor = BrandBorder
            )
        )
    }
}
