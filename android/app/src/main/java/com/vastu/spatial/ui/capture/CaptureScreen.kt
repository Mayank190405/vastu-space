package com.vastu.spatial.ui.capture

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.wifi.WifiManager
import android.os.BatteryManager
import android.os.Build
import android.speech.tts.TextToSpeech
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.view.PreviewView
import androidx.compose.animation.*
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.vastu.spatial.camera.CameraCaptureManager
import com.vastu.spatial.camera.CaptureQualityEngine
import com.vastu.spatial.camera.QualityLevel
import com.vastu.spatial.camera.VideoValidator
import com.vastu.spatial.data.api.ApiClient
import com.vastu.spatial.data.local.LocalCaptureStorageManager
import com.vastu.spatial.data.model.CreateCaptureRequest
import com.vastu.spatial.data.model.FloorDto
import com.vastu.spatial.data.model.ProjectDto
import com.vastu.spatial.sensor.ImuSensorManager
import com.vastu.spatial.sensor.ImuValidator
import com.vastu.spatial.sensor.SensorSyncEngine
import com.vastu.spatial.ui.theme.*
import com.vastu.spatial.util.StorageMonitor
import com.vastu.spatial.worker.ResumableUploadWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun CaptureScreen(
    project: ProjectDto,
    floor: FloorDto? = null,
    onBack: () -> Unit,
    onCaptureComplete: () -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val coroutineScope = rememberCoroutineScope()

    // ----------------------------------------------------
    // 1. Hardware & Engine Managers
    // ----------------------------------------------------
    val cameraManager = remember { CameraCaptureManager(context) }
    val imuManager = remember { ImuSensorManager(context) }
    val qualityEngine = remember { CaptureQualityEngine(context) }
    val storageManager = remember { LocalCaptureStorageManager(context) }

    val isRecording by cameraManager.isRecording.collectAsState()
    val recordedSeconds by cameraManager.recordedDurationSeconds.collectAsState()
    val recordingStartNs by cameraManager.recordingStartTimestampNs.collectAsState()
    val isExposureLocked by cameraManager.isExposureLocked.collectAsState()
    val imuSamples by imuManager.sampleCount.collectAsState()
    val currentSopIndex by qualityEngine.currentSopIndex.collectAsState()
    val qualityFeedback by qualityEngine.qualityFeedback.collectAsState()

    var statusMessage by remember { mutableStateOf("Align camera & follow SOP steps below") }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var availableStorageMB by remember { mutableStateOf(StorageMonitor.getAvailableStorageMB(context.filesDir)) }

    // ----------------------------------------------------
    // 2. Battery & WiFi Telemetry Monitor
    // ----------------------------------------------------
    var batteryLevel by remember { mutableStateOf(100) }
    var isBatteryCharging by remember { mutableStateOf(false) }
    var wifiSignalLevel by remember { mutableStateOf(3) } // 0..4
    var isWifiConnected by remember { mutableStateOf(true) }
    var isDevBatteryBypass by remember { mutableStateOf(false) }

    // Read Battery Status
    DisposableEffect(context) {
        val batteryReceiver = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context?, intent: Intent?) {
                val level = intent?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
                val scale = intent?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
                val status = intent?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
                if (level >= 0 && scale > 0) {
                    batteryLevel = (level * 100) / scale
                }
                isBatteryCharging = status == BatteryManager.BATTERY_STATUS_CHARGING ||
                        status == BatteryManager.BATTERY_STATUS_FULL
            }
        }
        val filter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        context.registerReceiver(batteryReceiver, filter)

        // Read WiFi Status
        val connManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
        val activeNet = connManager?.activeNetwork
        val caps = connManager?.getNetworkCapabilities(activeNet)
        isWifiConnected = caps?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true ||
                caps?.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) == true ||
                caps?.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) == true

        onDispose {
            context.unregisterReceiver(batteryReceiver)
        }
    }

    val isBatteryAllowed = batteryLevel > 80 || isDevBatteryBypass

    // ----------------------------------------------------
    // 3. Text-to-Speech (TTS) Narration Engine
    // ----------------------------------------------------
    var ttsEngine by remember { mutableStateOf<TextToSpeech?>(null) }
    var isSpeakingSop by remember { mutableStateOf(false) }

    DisposableEffect(context) {
        var speech: TextToSpeech? = null
        speech = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                speech?.language = Locale.US
                speech?.setSpeechRate(0.92f)
                ttsEngine = speech
            }
        }
        onDispose {
            ttsEngine?.stop()
            ttsEngine?.shutdown()
        }
    }

    fun speakSopText(text: String) {
        if (isSpeakingSop) {
            ttsEngine?.stop()
            isSpeakingSop = false
        } else {
            ttsEngine?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "SOP_TTS")
            isSpeakingSop = true
            coroutineScope.launch {
                delay(6000)
                isSpeakingSop = false
            }
        }
    }

    // ----------------------------------------------------
    // 4. Permissions Check
    // ----------------------------------------------------
    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }
    var hasAudioPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        )
    }
    var hasLocationPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { perms ->
        hasCameraPermission = perms[Manifest.permission.CAMERA] ?: false
        hasAudioPermission = perms[Manifest.permission.RECORD_AUDIO] ?: false
        hasLocationPermission = perms[Manifest.permission.ACCESS_FINE_LOCATION] ?: false
    }

    LaunchedEffect(Unit) {
        val requiredPerms = mutableListOf(
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT_WATCH) {
            requiredPerms.add(Manifest.permission.BODY_SENSORS)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            requiredPerms.add(Manifest.permission.ACTIVITY_RECOGNITION)
        }
        permissionLauncher.launch(requiredPerms.toTypedArray())
    }

    // ----------------------------------------------------
    // 5. Expandable SOP Drawer State
    // ----------------------------------------------------
    var isSopExpanded by remember { mutableStateOf(false) }

    LaunchedEffect(isRecording) {
        availableStorageMB = StorageMonitor.getAvailableStorageMB(context.filesDir)
    }

    LaunchedEffect(Unit) {
        if (!imuManager.isAvailable()) {
            errorMessage = "Warning: Accelerometer or Gyroscope not detected on this hardware."
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        // Camera Surface Preview
        if (hasCameraPermission) {
            AndroidView(
                factory = { ctx ->
                    PreviewView(ctx).apply {
                        cameraManager.bindCamera(lifecycleOwner, this)
                    }
                },
                modifier = Modifier.fillMaxSize()
            )
        } else {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Default.Warning, contentDescription = null, tint = BrandWarning, modifier = Modifier.size(48.dp))
                    Spacer(modifier = Modifier.height(12.dp))
                    Text("Camera & Sensor Permissions Required", color = Color.White, fontWeight = FontWeight.Bold)
                    Button(
                        onClick = {
                            permissionLauncher.launch(arrayOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO, Manifest.permission.ACCESS_FINE_LOCATION))
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = BrandBronze),
                        modifier = Modifier.padding(top = 12.dp)
                    ) {
                        Text("Grant Permissions", color = Color.White)
                    }
                }
            }
        }

        // ----------------------------------------------------
        // TOP HUD BAR: Back, Project/Timer, WiFi, Battery, Storage
        // ----------------------------------------------------
        Column(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .fillMaxWidth()
                .padding(top = 40.dp, start = 12.dp, end = 12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(
                    onClick = onBack,
                    modifier = Modifier.background(Color(0x80000000), CircleShape),
                    enabled = !isRecording
                ) {
                    Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                }

                // Project & Timer Badge
                Surface(
                    color = Color(0xB31E140C),
                    shape = RoundedCornerShape(20.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, BrandBronze)
                ) {
                    Column(
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = if (floor != null) "${project.name} • ${floor.name}" else project.name,
                            color = BrandBronze,
                            fontWeight = FontWeight.Bold,
                            fontSize = 12.sp
                        )
                        Text(
                            text = if (isRecording) "%02d:%02d".format(recordedSeconds / 60, recordedSeconds % 60) else "00:00",
                            color = if (isRecording) BrandError else Color.White,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 14.sp
                        )
                    }
                }

                // WiFi & Battery & Storage Telemetry Pills
                Row(
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // WiFi Signal Indicator
                    Surface(
                        color = Color(0xB31E140C),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(2.dp)
                        ) {
                            Icon(
                                imageVector = if (isWifiConnected) Icons.Default.Wifi else Icons.Default.WifiOff,
                                contentDescription = "WiFi",
                                tint = if (isWifiConnected) BrandSuccess else BrandError,
                                modifier = Modifier.size(14.dp)
                            )
                        }
                    }

                    // Battery Level Badge (Above 80% Requirement)
                    Surface(
                        color = if (batteryLevel > 80) Color(0xB31E140C) else Color(0xCC7F1D1D),
                        shape = RoundedCornerShape(10.dp),
                        border = androidx.compose.foundation.BorderStroke(
                            1.dp,
                            if (batteryLevel > 80) BrandSuccess else BrandError
                        ),
                        modifier = Modifier.clickable {
                            // Toggle developer bypass if clicked
                            isDevBatteryBypass = !isDevBatteryBypass
                            Toast.makeText(context, if (isDevBatteryBypass) "Dev Battery Bypass ON" else "Strict 80% Rule Active", Toast.LENGTH_SHORT).show()
                        }
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(2.dp)
                        ) {
                            Icon(
                                imageVector = if (isBatteryCharging) Icons.Default.BatteryChargingFull else if (batteryLevel > 80) Icons.Default.BatteryStd else Icons.Default.BatteryAlert,
                                contentDescription = "Battery",
                                tint = if (batteryLevel > 80) BrandSuccess else BrandError,
                                modifier = Modifier.size(14.dp)
                            )
                            Text(
                                text = "$batteryLevel%",
                                color = if (batteryLevel > 80) Color.White else BrandError,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }

                    // AE Lock Toggle
                    IconButton(
                        onClick = { cameraManager.toggleExposureLock(!isExposureLocked) },
                        modifier = Modifier
                            .size(32.dp)
                            .background(Color(0x80000000), CircleShape)
                    ) {
                        Icon(
                            imageVector = if (isExposureLocked) Icons.Default.Lock else Icons.Default.LockOpen,
                            contentDescription = "AE Lock",
                            tint = if (isExposureLocked) BrandBronze else Color.White,
                            modifier = Modifier.size(14.dp)
                        )
                    }
                }
            }

            // ----------------------------------------------------
            // BATTERY GUARD WARNING BANNER (When <= 80%)
            // ----------------------------------------------------
            if (!isBatteryAllowed) {
                Surface(
                    color = Color(0xEB451A03),
                    shape = RoundedCornerShape(10.dp),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFDC2626)),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.BatteryAlert, contentDescription = null, tint = Color(0xFFEF4444), modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "BATTERY GUARD: $batteryLevel% (MINIMUM 80% REQUIRED)",
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                                fontSize = 11.sp
                            )
                            Text(
                                text = "Spatial LiDAR & photogrammetry capture requires > 80% battery to prevent sensor throttling. Connect high-speed charger or tap badge to test.",
                                color = Color.White.copy(alpha = 0.85f),
                                fontSize = 10.sp
                            )
                        }
                    }
                }
            }

            // ----------------------------------------------------
            // EXPANDABLE SOP PROTOCOL DRAWER WITH READ ALOUD (TTS)
            // ----------------------------------------------------
            val currentStep = qualityEngine.sopSteps[currentSopIndex]
            val fullSopSpeech = "Step ${currentStep.index}: ${currentStep.title}. ${currentStep.description}"

            Surface(
                color = Color(0xE61A1009),
                shape = RoundedCornerShape(14.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFF785A3A)),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp)
            ) {
                Column(modifier = Modifier.padding(10.dp)) {
                    // SOP Header with Controls
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.clickable { isSopExpanded = !isSopExpanded }
                        ) {
                            Icon(
                                imageVector = if (isSopExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                                contentDescription = "Expand Guide",
                                tint = BrandBronze,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = "SCANNING GUIDE (${currentStep.index}/${qualityEngine.sopSteps.size})",
                                color = BrandBronze,
                                fontWeight = FontWeight.Bold,
                                fontSize = 11.sp
                            )
                        }

                        // Read Aloud (TTS) Button
                        Surface(
                            color = if (isSpeakingSop) BrandBronze else Color(0x4D966A38),
                            shape = RoundedCornerShape(14.dp),
                            modifier = Modifier.clickable { speakSopText(fullSopSpeech) }
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                Icon(
                                    imageVector = if (isSpeakingSop) Icons.Default.VolumeUp else Icons.Default.SpatialAudio,
                                    contentDescription = "Read Aloud",
                                    tint = Color.White,
                                    modifier = Modifier.size(13.dp)
                                )
                                Text(
                                    text = if (isSpeakingSop) "Playing Audio..." else "Read Aloud",
                                    color = Color.White,
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }
                    }

                    // Collapsed Summary
                    if (!isSopExpanded) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            IconButton(
                                onClick = { qualityEngine.previousSopStep() },
                                enabled = currentSopIndex > 0,
                                modifier = Modifier.size(24.dp)
                            ) {
                                Icon(Icons.Default.ChevronLeft, contentDescription = "Prev", tint = if (currentSopIndex > 0) BrandBronze else Color.Gray)
                            }

                            Column(
                                modifier = Modifier.weight(1f).padding(horizontal = 6.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Text(
                                    text = currentStep.title,
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 11.sp
                                )
                                Text(
                                    text = currentStep.description,
                                    color = BrandGoldLight,
                                    fontSize = 10.sp,
                                    maxLines = 1
                                )
                            }

                            IconButton(
                                onClick = { qualityEngine.nextSopStep() },
                                enabled = currentSopIndex < qualityEngine.sopSteps.size - 1,
                                modifier = Modifier.size(24.dp)
                            ) {
                                Icon(Icons.Default.ChevronRight, contentDescription = "Next", tint = if (currentSopIndex < qualityEngine.sopSteps.size - 1) BrandBronze else Color.Gray)
                            }
                        }
                    }

                    // Expanded Full SOP Guide
                    AnimatedVisibility(
                        visible = isSopExpanded,
                        enter = fadeIn() + expandVertically(),
                        exit = fadeOut() + shrinkVertically()
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 8.dp)
                                .heightIn(max = 200.dp)
                                .verticalScroll(rememberScrollState())
                        ) {
                            qualityEngine.sopSteps.forEachIndexed { idx, step ->
                                val isCurrent = idx == currentSopIndex
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 4.dp)
                                        .background(
                                            if (isCurrent) Color(0x33966A38) else Color.Transparent,
                                            RoundedCornerShape(6.dp)
                                        )
                                        .padding(6.dp),
                                    verticalAlignment = Alignment.Top
                                ) {
                                    Surface(
                                        color = if (isCurrent) BrandBronze else Color.DarkGray,
                                        shape = CircleShape,
                                        modifier = Modifier.size(18.dp)
                                    ) {
                                        Box(contentAlignment = Alignment.Center) {
                                            Text("${step.index}", color = Color.White, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                                        }
                                    }
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Column {
                                        Text(step.title, color = if (isCurrent) BrandBronze else Color.White, fontWeight = FontWeight.Bold, fontSize = 11.sp)
                                        Text(step.description, color = Color.White.copy(alpha = 0.8f), fontSize = 10.sp)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // Live Quality & Motion Guidance HUD
        Column(
            modifier = Modifier
                .align(Alignment.Center)
                .fillMaxWidth()
                .padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            if (isRecording) {
                val badgeColor = when (qualityFeedback.level) {
                    QualityLevel.OPTIMAL -> BrandSuccess
                    QualityLevel.WARNING_MOTION_BLUR -> BrandError
                    QualityLevel.WARNING_INSUFFICIENT_OVERLAP -> BrandWarning
                    QualityLevel.WARNING_LOW_FEATURE_DENSITY -> BrandWarning
                    QualityLevel.WARNING_LOW_LIGHT -> BrandWarning
                    QualityLevel.RESCAN_REQUIRED -> BrandError
                }

                Surface(
                    color = badgeColor.copy(alpha = 0.90f),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.padding(bottom = 12.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = qualityFeedback.title,
                            color = Color.White,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = qualityFeedback.correctiveAction,
                            color = Color.White.copy(alpha = 0.9f),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(top = 2.dp)
                        )
                    }
                }
            }

            // Crosshair Reticle
            Box(
                modifier = Modifier
                    .size(140.dp)
                    .border(
                        1.dp,
                        if (isRecording) BrandBronze.copy(alpha = 0.5f) else Color.White.copy(alpha = 0.3f),
                        CircleShape
                    )
            )
        }

        // ----------------------------------------------------
        // BOTTOM CONTROLS HUD: Telemetry, Shutter, Battery Lock
        // ----------------------------------------------------
        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .background(Color(0xCC1A1009))
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            if (errorMessage != null) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(bottom = 8.dp)
                ) {
                    Icon(Icons.Default.Warning, contentDescription = "Error", tint = BrandError, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = errorMessage!!,
                        color = BrandError,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
            } else {
                Text(
                    text = if (isRecording) "Recording RGB + 100Hz IMU (${imuSamples} samples)" else if (!isBatteryAllowed) "Recording locked: Battery must be > 80%" else statusMessage,
                    color = if (!isBatteryAllowed) Color(0xFFEF4444) else BrandGoldLight,
                    fontSize = 12.sp,
                    fontWeight = if (!isBatteryAllowed) FontWeight.Bold else FontWeight.Normal,
                    modifier = Modifier.padding(bottom = 12.dp)
                )
            }

            // Record / Stop Shutter
            IconButton(
                onClick = {
                    if (!isRecording) {
                        if (!isBatteryAllowed) {
                            errorMessage = "Battery charge must exceed 80% to begin spatial scanning."
                            return@IconButton
                        }

                        errorMessage = null
                        if (!StorageMonitor.hasSufficientStorage(200, context.filesDir)) {
                            errorMessage = "Cannot start scan: Less than 200MB free disk space"
                            return@IconButton
                        }

                        val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
                        val sessionDir = storageManager.createCaptureDirectory(timeStamp)
                        val videoFile = File(sessionDir, "rgb_video.mp4")
                        val imuFile = File(sessionDir, "imu_stream.csv")

                        imuManager.startRecording(imuFile)
                        cameraManager.startRecording(
                            outputFile = videoFile,
                            onVideoSaved = { savedVideo ->
                                imuManager.stopRecording()
                                statusMessage = "Packaging local capture & indexing chunks..."

                                val videoValidation = VideoValidator.validateVideo(savedVideo)
                                if (!videoValidation.isValid) {
                                    errorMessage = videoValidation.errorMessage ?: "Video validation failed"
                                    return@startRecording
                                }

                                val imuValidation = ImuValidator.validateImuFile(imuFile)
                                if (!imuValidation.isValid) {
                                    errorMessage = imuValidation.errorMessage ?: "IMU validation failed"
                                    return@startRecording
                                }

                                val syncManifest = SensorSyncEngine.generateSyncManifest(
                                    sessionName = "Scan_$timeStamp",
                                    videoValidation = videoValidation,
                                    imuValidation = imuValidation,
                                    videoStartTimestampNs = recordingStartNs,
                                    imuFile = imuFile,
                                    outputDir = sessionDir
                                )

                                val manifestFile = File(sessionDir, "sync_manifest.json")

                                coroutineScope.launch {
                                    try {
                                        val intrinsics = cameraManager.extractCameraIntrinsics()
                                        val deviceInfo = "${Build.MANUFACTURER} ${Build.MODEL} (Android ${Build.VERSION.RELEASE})"
                                        val sopCoveragePercent = ((currentSopIndex + 1).toDouble() / qualityEngine.sopSteps.size * 100).toInt()
                                        val qualityScore = String.format("%.2f", qualityEngine.getCoverageQualityScore())

                                        val metadataMap = mapOf(
                                            "focal_length_x" to intrinsics.fx,
                                            "focal_length_y" to intrinsics.fy,
                                            "resolution_width" to videoValidation.width,
                                            "resolution_height" to videoValidation.height,
                                            "duration_ms" to videoValidation.durationMs,
                                            "bitrate" to videoValidation.bitrate,
                                            "frame_rate" to videoValidation.frameRate,
                                            "imu_rate_hz" to imuValidation.averageFrequencyHz,
                                            "imu_total_samples" to imuValidation.totalSamples,
                                            "imu_is_monotonic" to imuValidation.isMonotonic,
                                            "sync_quality" to syncManifest.syncQuality,
                                            "sop_completed_steps" to (currentSopIndex + 1),
                                            "sop_coverage_percent" to sopCoveragePercent,
                                            "capture_quality_score" to qualityScore,
                                            "battery_at_capture_start" to batteryLevel,
                                            "wifi_status" to isWifiConnected
                                        )

                                        val req = CreateCaptureRequest(
                                            projectId = project.id,
                                            name = "Scan_$timeStamp",
                                            captureType = "video_rgb_imu",
                                            deviceInfo = deviceInfo,
                                            metadata = metadataMap
                                        )

                                        val resp = ApiClient.service.createCapture(req)
                                        if (resp.isSuccessful && resp.body()?.data != null) {
                                            val captureDto = resp.body()!!.data!!

                                            storageManager.packageAndIndexCapture(
                                                captureId = captureDto.id,
                                                projectId = project.id,
                                                sessionName = captureDto.name,
                                                sessionDir = sessionDir,
                                                videoFile = savedVideo,
                                                imuFile = imuFile,
                                                manifestFile = manifestFile,
                                                metadataMap = metadataMap
                                            )

                                            ResumableUploadWorker.enqueue(
                                                context = context,
                                                captureId = captureDto.id,
                                                filePath = savedVideo.absolutePath
                                            )

                                            onCaptureComplete()
                                        } else {
                                            errorMessage = resp.body()?.error ?: "Failed to register capture session"
                                        }
                                    } catch (e: Exception) {
                                        errorMessage = "Error registering capture: ${e.localizedMessage}"
                                    }
                                }
                            },
                            onError = { err ->
                                imuManager.stopRecording()
                                errorMessage = err
                            }
                        )
                    } else {
                        cameraManager.stopRecording()
                    }
                },
                enabled = isBatteryAllowed || isRecording,
                modifier = Modifier
                    .size(72.dp)
                    .background(
                        if (isRecording) BrandError else if (!isBatteryAllowed) Color.Gray else BrandBronze,
                        CircleShape
                    )
            ) {
                Icon(
                    imageVector = if (isRecording) Icons.Default.Stop else if (!isBatteryAllowed) Icons.Default.Lock else Icons.Default.FiberManualRecord,
                    contentDescription = if (isRecording) "Stop Scan" else if (!isBatteryAllowed) "Battery Locked" else "Start Scan",
                    tint = if (isRecording) Color.White else if (!isBatteryAllowed) Color.LightGray else BrandDark,
                    modifier = Modifier.size(36.dp)
                )
            }
        }
    }
}
