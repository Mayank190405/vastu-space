package com.vastu.spatial.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vastu.spatial.data.api.ApiClient
import com.vastu.spatial.data.model.FloorDto
import com.vastu.spatial.data.model.ProjectDto
import com.vastu.spatial.ui.theme.*
import com.vastu.spatial.ui.qr.QRScannerScreen
import kotlinx.coroutines.launch

import com.vastu.spatial.ui.profile.ProfileScreen

@Composable
fun DashboardScreen(
    onCreateProject: () -> Unit,
    onSelectProjectForCapture: (ProjectDto, FloorDto?) -> Unit,
    onSignOut: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var projects by remember { mutableStateOf<List<ProjectDto>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var selectedTab by remember { mutableStateOf(0) }
    val tokenManager = ApiClient.getTokenManager()
    var selectedOrg by remember { mutableStateOf("Personal Workspace") }
    var showOrgMenu by remember { mutableStateOf(false) }
    var showQRScanner by remember { mutableStateOf(false) }

    fun refreshProjects() {
        isLoading = true
        coroutineScope.launch {
            try {
                val orgResp = ApiClient.service.getMyOrg()
                if (orgResp.isSuccessful && orgResp.body()?.data != null) {
                    val name = orgResp.body()!!.data!!.name
                    if (name.isNotBlank()) selectedOrg = name
                }
            } catch (_: Exception) {}

            try {
                val resp = ApiClient.service.getProjects()
                if (resp.isSuccessful && resp.body()?.data != null) {
                    projects = resp.body()!!.data!!
                }
            } catch (_: Exception) {}
            isLoading = false
        }
    }

    LaunchedEffect(Unit) {
        refreshProjects()
    }

    val scrollState = rememberScrollState()

    Scaffold(
        bottomBar = {
            NavigationBar(
                containerColor = BrandIvory,
                tonalElevation = 4.dp
            ) {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Icon(Icons.Default.Home, contentDescription = "Home") },
                    label = { Text("Home", fontSize = 10.sp, fontWeight = if (selectedTab == 0) FontWeight.Bold else FontWeight.Medium) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = BrandBronze,
                        selectedTextColor = BrandBronze,
                        unselectedIconColor = BrandTextMuted,
                        unselectedTextColor = BrandTextMuted,
                        indicatorColor = BrandParchment
                    )
                )
                NavigationBarItem(
                    selected = selectedTab == 1,
                    onClick = {
                        selectedTab = 1
                        onCreateProject()
                    },
                    icon = { Icon(Icons.Default.List, contentDescription = "Projects") },
                    label = { Text("Projects", fontSize = 10.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = BrandBronze,
                        selectedTextColor = BrandBronze,
                        unselectedIconColor = BrandTextMuted,
                        unselectedTextColor = BrandTextMuted,
                        indicatorColor = BrandParchment
                    )
                )
                NavigationBarItem(
                    selected = selectedTab == 2,
                    onClick = {
                        selectedTab = 2
                        if (projects.isNotEmpty()) {
                            onSelectProjectForCapture(projects.first(), null)
                        } else {
                            onCreateProject()
                        }
                    },
                    icon = { Icon(Icons.Default.PlayArrow, contentDescription = "Captures") },
                    label = { Text("Captures", fontSize = 10.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = BrandBronze,
                        selectedTextColor = BrandBronze,
                        unselectedIconColor = BrandTextMuted,
                        unselectedTextColor = BrandTextMuted,
                        indicatorColor = BrandParchment
                    )
                )
                NavigationBarItem(
                    selected = selectedTab == 3,
                    onClick = { selectedTab = 3 },
                    icon = { Icon(Icons.Default.AccountCircle, contentDescription = "Profile") },
                    label = { Text("Profile", fontSize = 10.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = BrandBronze,
                        selectedTextColor = BrandBronze,
                        unselectedIconColor = BrandTextMuted,
                        unselectedTextColor = BrandTextMuted,
                        indicatorColor = BrandParchment
                    )
                )
            }
        },
        containerColor = BrandParchment
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (selectedTab == 3) {
                ProfileScreen(onSignOut = onSignOut)
            } else {
                // Top App Bar matching Screen 11
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(BrandIvory)
                        .border(1.dp, BrandBorder)
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = { selectedTab = 3 }) {
                        Icon(Icons.Default.AccountCircle, contentDescription = "Profile", tint = BrandBronze)
                    }

                    Spacer(modifier = Modifier.weight(1f))

                    // QR Code Scanner Button
                    IconButton(onClick = { showQRScanner = true }) {
                        Icon(Icons.Default.CameraAlt, contentDescription = "Scan QR Code", tint = BrandText)
                    }

                    // Notification Bell
                    IconButton(onClick = {}) {
                        Icon(Icons.Default.Notifications, contentDescription = "Notifications", tint = BrandText)
                    }

                    // Org Switcher Pill Dropdown
                    Box {
                        Row(
                            modifier = Modifier
                                .clip(RoundedCornerShape(20.dp))
                                .background(BrandIvory)
                                .border(1.dp, BrandBorder, RoundedCornerShape(20.dp))
                                .clickable { showOrgMenu = true }
                                .padding(horizontal = 14.dp, vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.Home, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(14.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(selectedOrg, fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandText)
                            Spacer(modifier = Modifier.width(4.dp))
                            Icon(Icons.Default.ArrowDropDown, contentDescription = null, tint = BrandTextMuted, modifier = Modifier.size(16.dp))
                        }

                        DropdownMenu(
                            expanded = showOrgMenu,
                            onDismissRequest = { showOrgMenu = false }
                        ) {
                            DropdownMenuItem(
                                text = { Text(selectedOrg) },
                                onClick = { showOrgMenu = false }
                            )
                            Divider()
                            DropdownMenuItem(
                                text = { Text("+ Create Project", color = BrandBronze, fontWeight = FontWeight.Bold) },
                                onClick = { showOrgMenu = false; onCreateProject() }
                            )
                        }
                    }

                    Spacer(modifier = Modifier.weight(1f))

                    // Notification Bell
                    Box(contentAlignment = Alignment.TopEnd) {
                        IconButton(onClick = { selectedTab = 3 }) {
                            Icon(Icons.Default.Notifications, contentDescription = "Notifications", tint = BrandText)
                        }
                    }
                }

                // Scrollable Dashboard Body
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(scrollState)
                        .padding(20.dp)
                ) {
                    // Greeting
                    val userGreeting = tokenManager?.getUser()?.fullName ?: "Architect"
                    Text("Good morning,", fontSize = 13.sp, color = BrandTextMuted)
                    Text(userGreeting, fontSize = 22.sp, fontWeight = FontWeight.Bold, color = BrandText)

                    Spacer(modifier = Modifier.height(16.dp))

                    // 4-Metric Grid (Dynamic Zero Fallback)
                    val totalProjects = projects.size
                    val totalSpaces = projects.sumOf { it.totalFloorsCount ?: it.floors?.size ?: 0 }
                    val processingCount = projects.count {
                        val st = (it.status ?: "").lowercase()
                        st == "processing" || st == "in_progress" || st == "capturing"
                    }

                    Row(modifier = Modifier.fillMaxWidth()) {
                        AndroidMetricCard(modifier = Modifier.weight(1f), count = "$totalProjects", label = "Projects", icon = Icons.Default.List)
                        Spacer(modifier = Modifier.width(12.dp))
                        AndroidMetricCard(modifier = Modifier.weight(1f), count = "$totalSpaces", label = "Spaces", icon = Icons.Default.Home)
                    }
                    Spacer(modifier = Modifier.height(12.dp))
                    Row(modifier = Modifier.fillMaxWidth()) {
                        AndroidMetricCard(modifier = Modifier.weight(1f), count = "${if (totalSpaces > 0) totalSpaces else 0}", label = "Captures", icon = Icons.Default.PlayArrow)
                        Spacer(modifier = Modifier.width(12.dp))
                        AndroidMetricCard(modifier = Modifier.weight(1f), count = "$processingCount", label = "Processing", icon = Icons.Default.Person)
                    }

                    Spacer(modifier = Modifier.height(20.dp))

                    // Action Hub Buttons
                    Row(modifier = Modifier.fillMaxWidth()) {
                        Button(
                            onClick = onCreateProject,
                            modifier = Modifier.weight(1f).height(46.dp),
                            shape = RoundedCornerShape(12.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = BrandBronze)
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Create Project", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                        }

                        Spacer(modifier = Modifier.width(12.dp))

                        OutlinedButton(
                            onClick = {
                                if (projects.isNotEmpty()) {
                                    onSelectProjectForCapture(projects.first(), null)
                                } else {
                                    onCreateProject()
                                }
                            },
                            modifier = Modifier.weight(1f).height(46.dp),
                            shape = RoundedCornerShape(12.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, BrandBronze),
                            colors = ButtonDefaults.outlinedButtonColors(containerColor = BrandIvory)
                        ) {
                            Icon(Icons.Default.PlayArrow, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Scan Space", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = BrandBronze)
                        }
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    // Recent Projects Header
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Recent Projects", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = BrandText)
                        Spacer(modifier = Modifier.weight(1f))
                        if (projects.isNotEmpty()) {
                            Text("View All >", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = BrandBronze)
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    // Live Projects (Zero Fallback)
                    if (projects.isEmpty()) {
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(containerColor = BrandIvory),
                            shape = RoundedCornerShape(14.dp),
                            border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
                        ) {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(28.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Home,
                                    contentDescription = null,
                                    tint = BrandBronze.copy(alpha = 0.6f),
                                    modifier = Modifier.size(40.dp)
                                )
                                Spacer(modifier = Modifier.height(12.dp))
                                Text(
                                    text = "No Spatial Projects Yet",
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    fontFamily = androidx.compose.ui.text.font.FontFamily.Serif,
                                    color = BrandText
                                )
                                Spacer(modifier = Modifier.height(6.dp))
                                Text(
                                    text = "Create your first architectural project to upload floor plans and scan 3D spaces.",
                                    fontSize = 12.sp,
                                    color = BrandTextMuted,
                                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                                )
                                Spacer(modifier = Modifier.height(16.dp))
                                Button(
                                    onClick = onCreateProject,
                                    colors = ButtonDefaults.buttonColors(containerColor = BrandBronze),
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Text("Create First Project", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    } else {
                        projects.forEach { p ->
                            AndroidProjectItem(
                                title = p.name,
                                location = p.projectType ?: "Commercial",
                                status = p.status ?: "Ready",
                                statusColor = BrandBronze,
                                onClick = { onSelectProjectForCapture(p, null) }
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                        }
                    }

                    Spacer(modifier = Modifier.height(40.dp))
                }
            }
        }
    }
    
    if (showQRScanner) {
        QRScannerScreen(
            onCodeScanned = { code ->
                handleQRCodeScanned(code, projects, onSelectProjectForCapture)
                showQRScanner = false
            },
            onDismiss = { showQRScanner = false }
        )
    }
}

private fun handleQRCodeScanned(
    code: String,
    projects: List<ProjectDto>,
    onSelectProjectForCapture: (ProjectDto, FloorDto?) -> Unit
) {
    // Parse the QR code to extract session information
    // Expected format: "vastuspatial://capture/{sessionId}?projectId={projectId}"
    // Or session code: "V-{sessionId}"
    
    if (code.startsWith("vastuspatial://capture/")) {
        // Handle deep link format
        val uri = android.net.Uri.parse(code)
        val sessionId = uri.lastPathSegment
        val projectId = uri.getQueryParameter("projectId")
        
        if (sessionId != null && projectId != null) {
            // Find the project and start capture
            val project = projects.find { it.id == projectId }
            if (project != null) {
                onSelectProjectForCapture(project, null)
            }
        }
    } else if (code.startsWith("V-")) {
        // Handle session code format
        val sessionId = code.substring(2)
        // In real implementation, validate session code with backend
        println("Session code scanned: $sessionId")
        // For now, just show alert
    }
}

@Composable
fun AndroidMetricCard(
    modifier: Modifier = Modifier,
    count: String,
    label: String,
    icon: ImageVector
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = BrandIvory),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(BrandParchment),
                contentAlignment = Alignment.Center
            ) {
                Icon(icon, contentDescription = null, tint = BrandBronze, modifier = Modifier.size(18.dp))
            }
            Spacer(modifier = Modifier.width(10.dp))
            Column {
                Text(count, fontSize = 18.sp, fontWeight = FontWeight.Bold, color = BrandText)
                Text(label, fontSize = 11.sp, color = BrandTextMuted)
            }
        }
    }
}

@Composable
fun AndroidProjectItem(
    title: String,
    location: String,
    status: String,
    statusColor: Color,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = BrandIvory),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(42.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(BrandParchment),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Home, contentDescription = null, tint = BrandBronze)
            }

            Spacer(modifier = Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(title, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = BrandText)
                Text(location, fontSize = 11.sp, color = BrandTextMuted)
            }

            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(10.dp))
                    .background(statusColor.copy(alpha = 0.12f))
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(modifier = Modifier.size(6.dp).clip(CircleShape).background(statusColor))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(status, fontSize = 10.sp, fontWeight = FontWeight.Bold, color = statusColor)
                }
            }
        }
    }
}
