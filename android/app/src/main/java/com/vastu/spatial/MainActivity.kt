package com.vastu.spatial

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import com.vastu.spatial.data.api.ApiClient
import com.vastu.spatial.data.model.FloorDto
import com.vastu.spatial.data.model.ProjectDto
import com.vastu.spatial.ui.auth.AuthScreen
import com.vastu.spatial.ui.capture.CaptureScreen
import com.vastu.spatial.ui.dashboard.DashboardScreen
import com.vastu.spatial.ui.preloader.VastuPreloaderScreen
import com.vastu.spatial.ui.projects.ProjectCreationWizardScreen
import com.vastu.spatial.ui.theme.BrandParchment
import com.vastu.spatial.ui.theme.VastuTheme

sealed class Screen {
    object Auth : Screen()
    data class Preloader(val target: Screen = Dashboard) : Screen()
    object Dashboard : Screen()
    object CreateProject : Screen()
    data class Capture(val project: ProjectDto, val floor: FloorDto? = null) : Screen()
}

class MainActivity : ComponentActivity() {

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { _ -> }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Request camera, audio, and high-accuracy GPS location permissions
        val requiredPermissions = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
        val missing = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            permissionLauncher.launch(missing.toTypedArray())
        }

        setContent {
            VastuTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = BrandParchment
                ) {
                    val tokenManager = ApiClient.getTokenManager()
                    val destination: Screen = if (tokenManager?.getToken() != null) {
                        Screen.Dashboard
                    } else {
                        Screen.Auth
                    }
                    val initialScreen: Screen = Screen.Preloader(destination)

                    var currentScreen by remember { mutableStateOf(initialScreen) }

                    when (val screen = currentScreen) {
                        is Screen.Auth -> {
                            AuthScreen(
                                onAuthSuccess = {
                                    currentScreen = Screen.Preloader(Screen.Dashboard)
                                }
                            )
                        }
                        is Screen.Preloader -> {
                            VastuPreloaderScreen(
                                onFinish = {
                                    currentScreen = screen.target
                                }
                            )
                        }
                        is Screen.Dashboard -> {
                            DashboardScreen(
                                onCreateProject = {
                                    currentScreen = Screen.CreateProject
                                },
                                onSelectProjectForCapture = { project, floor ->
                                    currentScreen = Screen.Capture(project, floor)
                                },
                                onSignOut = {
                                    currentScreen = Screen.Auth
                                }
                            )
                        }
                        is Screen.CreateProject -> {
                            ProjectCreationWizardScreen(
                                onBack = {
                                    currentScreen = Screen.Dashboard
                                },
                                onProjectCreated = { _ ->
                                    currentScreen = Screen.Dashboard
                                }
                            )
                        }
                        is Screen.Capture -> {
                            CaptureScreen(
                                project = screen.project,
                                floor = screen.floor,
                                onBack = {
                                    currentScreen = Screen.Dashboard
                                },
                                onCaptureComplete = {
                                    currentScreen = Screen.Dashboard
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}
