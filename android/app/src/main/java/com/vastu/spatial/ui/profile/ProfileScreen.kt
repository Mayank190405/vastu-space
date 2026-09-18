package com.vastu.spatial.ui.profile

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vastu.spatial.data.api.ApiClient
import com.vastu.spatial.data.model.OrganizationDto
import com.vastu.spatial.data.model.UserDto
import com.vastu.spatial.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun ProfileScreen(
    onSignOut: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val tokenManager = ApiClient.getTokenManager()

    var currentUser by remember { mutableStateOf(tokenManager?.getUser()) }
    var currentOrg by remember { mutableStateOf<OrganizationDto?>(null) }
    var currentRole by remember { mutableStateOf("Owner") }
    var isRefreshing by remember { mutableStateOf(false) }
    var showSignOutDialog by remember { mutableStateOf(false) }
    var isCodeCopied by remember { mutableStateOf(false) }

    fun refreshProfile() {
        coroutineScope.launch {
            isRefreshing = true
            try {
                val profileResp = ApiClient.service.getMe()
                if (profileResp.isSuccessful) {
                    val data = profileResp.body()?.data
                    if (data?.user != null) {
                        currentUser = data.user
                        tokenManager?.saveUser(data.user)
                    }
                    if (data?.activeOrg != null) {
                        currentOrg = data.activeOrg
                    }
                    if (data?.activeRole != null) {
                        currentRole = data.activeRole
                    }
                }
            } catch (_: Exception) {}

            try {
                val orgResp = ApiClient.service.getMyOrg()
                if (orgResp.isSuccessful && orgResp.body()?.data != null) {
                    currentOrg = orgResp.body()?.data
                }
            } catch (_: Exception) {}
            isRefreshing = false
        }
    }

    LaunchedEffect(Unit) {
        refreshProfile()
    }

    if (showSignOutDialog) {
        AlertDialog(
            onDismissRequest = { showSignOutDialog = false },
            title = {
                Text(
                    text = "Sign Out",
                    fontFamily = FontFamily.Serif,
                    fontWeight = FontWeight.Bold,
                    color = BrandText
                )
            },
            text = {
                Text(
                    text = "Are you sure you want to sign out of VĀSTU Spatial? Your local scans will remain secure on this device.",
                    color = BrandTextMuted,
                    fontSize = 14.sp
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        showSignOutDialog = false
                        tokenManager?.clear()
                        onSignOut()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFC0392B))
                ) {
                    Text("Sign Out", color = Color.White, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showSignOutDialog = false }) {
                    Text("Cancel", color = BrandTextMuted)
                }
            },
            containerColor = BrandIvory,
            shape = RoundedCornerShape(16.dp)
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BrandParchment)
    ) {
        // Top Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(BrandIvory)
                .border(1.dp, BrandBorder)
                .padding(horizontal = 20.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "ACCOUNT & PROFILE",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 2.sp,
                    color = BrandBronze
                )
                Text(
                    text = "Spatial Identity",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Serif,
                    color = BrandText
                )
            }

            IconButton(
                onClick = { refreshProfile() },
                modifier = Modifier
                    .size(38.dp)
                    .clip(CircleShape)
                    .background(BrandIvory)
                    .border(1.dp, BrandBorder, CircleShape)
            ) {
                Icon(
                    imageVector = Icons.Default.Refresh,
                    contentDescription = "Refresh Profile",
                    tint = BrandBronze,
                    modifier = Modifier.size(18.dp)
                )
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // User Monogram Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(18.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Avatar Circle
                    Box(
                        modifier = Modifier
                            .size(64.dp)
                            .clip(CircleShape)
                            .background(BrandParchment)
                            .border(2.dp, BrandBronze, CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        val initials = currentUser?.fullName
                            ?.split(" ")
                            ?.filter { it.isNotBlank() }
                            ?.take(2)
                            ?.map { it.first().uppercase() }
                            ?.joinToString("")
                            ?: "V"
                        Text(
                            text = initials,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Serif,
                            color = BrandBronze
                        )
                    }

                    Spacer(modifier = Modifier.width(16.dp))

                    Column(modifier = Modifier.weight(1f)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = currentUser?.fullName ?: "Authenticated User",
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Serif,
                                color = BrandText
                            )

                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(6.dp))
                                    .background(BrandBronze.copy(alpha = 0.12f))
                                    .padding(horizontal = 8.dp, vertical = 3.dp)
                            ) {
                                Text(
                                    text = (currentRole.ifBlank { currentUser?.role ?: "ADMIN" }).uppercase(),
                                    fontSize = 9.sp,
                                    fontWeight = FontWeight.Bold,
                                    fontFamily = FontFamily.Monospace,
                                    color = BrandBronze
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(2.dp))

                        Text(
                            text = currentUser?.email ?: "No email linked",
                            fontSize = 13.sp,
                            color = BrandTextMuted
                        )

                        if (!currentUser?.phone.isNullOrBlank()) {
                            Text(
                                text = currentUser?.phone ?: "",
                                fontSize = 12.sp,
                                color = BrandTextMuted
                            )
                        }
                    }
                }
            }

            // Organization Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.Home,
                            contentDescription = "Organization",
                            tint = BrandBronze,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "ACTIVE ORGANIZATION",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            letterSpacing = 1.5.sp,
                            color = BrandTextMuted
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    if (currentOrg != null) {
                        Text(
                            text = currentOrg?.name ?: "",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Serif,
                            color = BrandText
                        )
                        if (!currentOrg?.businessType.isNullOrBlank()) {
                            Text(
                                text = currentOrg?.businessType ?: "",
                                fontSize = 12.sp,
                                color = BrandTextMuted
                            )
                        }

                        if (!currentOrg?.orgCode.isNullOrBlank()) {
                            Spacer(modifier = Modifier.height(14.dp))
                            Divider(color = BrandBorder)
                            Spacer(modifier = Modifier.height(14.dp))

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column {
                                    Text(
                                        text = "ORGANIZATION CODE",
                                        fontSize = 9.sp,
                                        fontWeight = FontWeight.Bold,
                                        fontFamily = FontFamily.Monospace,
                                        color = BrandTextMuted
                                    )
                                    Text(
                                        text = currentOrg?.orgCode ?: "",
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.Bold,
                                        fontFamily = FontFamily.Monospace,
                                        color = BrandBronze
                                    )
                                }

                                Button(
                                    onClick = {
                                        val orgCode = currentOrg?.orgCode ?: ""
                                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                        val clip = ClipData.newPlainText("Org Code", orgCode)
                                        clipboard.setPrimaryClip(clip)
                                        isCodeCopied = true
                                        Toast.makeText(context, "Organization code copied", Toast.LENGTH_SHORT).show()
                                    },
                                    colors = ButtonDefaults.buttonColors(containerColor = BrandParchment),
                                    border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder),
                                    shape = RoundedCornerShape(8.dp),
                                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp)
                                ) {
                                    Icon(
                                        imageVector = if (isCodeCopied) Icons.Default.Check else Icons.Default.Share,
                                        contentDescription = "Copy",
                                        tint = BrandBronze,
                                        modifier = Modifier.size(12.dp)
                                    )
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(
                                        text = if (isCodeCopied) "Copied" else "Copy Code",
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = BrandBronze
                                    )
                                }
                            }
                        }
                    } else {
                        Text(
                            text = "Personal Workspace",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold,
                            fontFamily = FontFamily.Serif,
                            color = BrandText
                        )
                        Text(
                            text = "Individual spatial mapping account",
                            fontSize = 12.sp,
                            color = BrandTextMuted,
                            modifier = Modifier.padding(top = 2.dp)
                        )
                    }
                }
            }

            // Spatial Capabilities Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.Settings,
                            contentDescription = "Sensors",
                            tint = BrandBronze,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "DEVICE SPATIAL HARDWARE",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            letterSpacing = 1.5.sp,
                            color = BrandTextMuted
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    AndroidCapabilityRow(
                        icon = Icons.Default.Place,
                        title = "ARCore Depth API",
                        subtitle = "Hardware synchronized structural depth mapping",
                        isActive = true
                    )

                    Spacer(modifier = Modifier.height(10.dp))
                    Divider(color = BrandBorder)
                    Spacer(modifier = Modifier.height(10.dp))

                    AndroidCapabilityRow(
                        icon = Icons.Default.LocationOn,
                        title = "GPS Geolocation Precision",
                        subtitle = "High accuracy WGS-84 coordinate anchor",
                        isActive = true
                    )

                    Spacer(modifier = Modifier.height(10.dp))
                    Divider(color = BrandBorder)
                    Spacer(modifier = Modifier.height(10.dp))

                    AndroidCapabilityRow(
                        icon = Icons.Default.Refresh,
                        title = "6-DOF IMU Motion Fusion",
                        subtitle = "Continuous hardware gyroscope and accelerometer",
                        isActive = true
                    )
                }
            }

            // Control Plane & Cloud Sync
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = BrandIvory),
                border = androidx.compose.foundation.BorderStroke(1.dp, BrandBorder)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "CONTROL PLANE",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            letterSpacing = 1.5.sp,
                            color = BrandTextMuted
                        )

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(6.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFF27AE60))
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = "Connected",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF27AE60)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = ApiClient.baseUrl,
                        fontSize = 12.sp,
                        fontFamily = FontFamily.Monospace,
                        color = BrandTextMuted
                    )
                }
            }

            // Sign Out Button
            OutlinedButton(
                onClick = { showSignOutDialog = true },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.outlinedButtonColors(
                    containerColor = BrandIvory,
                    contentColor = Color(0xFFC0392B)
                ),
                border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFC0392B).copy(alpha = 0.35f))
            ) {
                Icon(
                    imageVector = Icons.Default.ExitToApp,
                    contentDescription = "Sign Out",
                    modifier = Modifier.size(16.dp),
                    tint = Color(0xFFC0392B)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Sign Out of VĀSTU Spatial",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFC0392B)
                )
            }

            Spacer(modifier = Modifier.height(40.dp))
        }
    }
}

@Composable
private fun AndroidCapabilityRow(
    icon: ImageVector,
    title: String,
    subtitle: String,
    isActive: Boolean = true
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = title,
            tint = if (isActive) BrandBronze else BrandTextMuted,
            modifier = Modifier.size(20.dp)
        )

        Spacer(modifier = Modifier.width(12.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = BrandText
            )
            Text(
                text = subtitle,
                fontSize = 11.sp,
                color = BrandTextMuted
            )
        }

        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(4.dp))
                .background(if (isActive) Color(0xFF27AE60).copy(alpha = 0.12f) else Color.Gray.copy(alpha = 0.12f))
                .padding(horizontal = 6.dp, vertical = 2.dp)
        ) {
            Text(
                text = if (isActive) "Active" else "N/A",
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace,
                color = if (isActive) Color(0xFF27AE60) else BrandTextMuted
            )
        }
    }
}
