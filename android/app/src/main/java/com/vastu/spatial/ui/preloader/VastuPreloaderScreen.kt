package com.vastu.spatial.ui.preloader

import androidx.compose.animation.core.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vastu.spatial.R
import com.vastu.spatial.ui.theme.BrandBronze
import com.vastu.spatial.ui.theme.BrandIvory
import com.vastu.spatial.ui.theme.BrandParchment
import com.vastu.spatial.ui.theme.BrandTextMuted
import kotlinx.coroutines.delay

@Composable
fun VastuPreloaderScreen(
    targetMessage: String = "Welcome to VĀSTU Control Plane",
    onFinish: () -> Unit
) {
    var statusText by remember { mutableStateOf("Securing workspace tokens...") }
    var progress by remember { mutableFloatStateOf(0.15f) }

    // Infinite pulsing & rotation transitions
    val infiniteTransition = rememberInfiniteTransition(label = "preloader")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 0.95f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )

    val rotationAngle by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(4000, easing = LinearEasing)
        ),
        label = "rotation"
    )

    // Telemetry progression
    LaunchedEffect(Unit) {
        delay(400)
        statusText = "Authenticating organization workspace..."
        progress = 0.40f
        delay(500)
        statusText = "Synchronizing digital twin coordinates..."
        progress = 0.70f
        delay(500)
        statusText = "Initializing spatial coordinate engine..."
        progress = 0.90f
        delay(400)
        statusText = targetMessage
        progress = 1.0f
        delay(400)
        onFinish()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(BrandParchment),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier.padding(32.dp)
        ) {
            // Rotating Compass Halo & Breathing Logo
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier.size(140.dp)
            ) {
                // Rotating outer halo
                Box(
                    modifier = Modifier
                        .size(136.dp)
                        .rotate(rotationAngle)
                        .border(
                            width = 2.dp,
                            brush = Brush.sweepGradient(
                                listOf(
                                    BrandBronze.copy(alpha = 0.9f),
                                    Color.Transparent,
                                    BrandBronze.copy(alpha = 0.4f),
                                    Color.Transparent,
                                    BrandBronze.copy(alpha = 0.9f)
                                )
                            ),
                            shape = CircleShape
                        )
                )

                // Central Card with Vastu Logo
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(100.dp)
                        .scale(pulseScale)
                        .clip(CircleShape)
                        .background(BrandIvory)
                        .border(1.5.dp, BrandBronze.copy(alpha = 0.5f), CircleShape)
                        .padding(14.dp)
                ) {
                    Image(
                        painter = painterResource(id = R.drawable.vastu_logo),
                        contentDescription = "VĀSTU",
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.fillMaxSize()
                    )
                }
            }

            Spacer(modifier = Modifier.height(28.dp))

            // Brand Typography
            Text(
                text = "V Ā S T U",
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Serif,
                color = BrandBronze,
                letterSpacing = 6.sp
            )

            Text(
                text = "Spatial Intelligence Platform",
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
                color = BrandTextMuted,
                letterSpacing = 1.5.sp,
                modifier = Modifier.padding(top = 4.dp)
            )

            Spacer(modifier = Modifier.height(36.dp))

            // Telemetry progress bar
            Box(
                modifier = Modifier
                    .width(220.dp)
                    .height(3.dp)
                    .background(BrandBronze.copy(alpha = 0.15f), shape = CircleShape)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth(progress)
                        .fillMaxHeight()
                        .background(BrandBronze, shape = CircleShape)
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Dynamic Status Text
            Text(
                text = statusText,
                fontSize = 12.sp,
                fontWeight = FontWeight.Normal,
                color = BrandTextMuted,
                textAlign = TextAlign.Center
            )
        }
    }
}
