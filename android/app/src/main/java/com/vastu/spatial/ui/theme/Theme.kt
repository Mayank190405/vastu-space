package com.vastu.spatial.ui.theme

import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// VĀSTU Warm Architectural Parchment Palette
val BrandParchment = Color(0xFFE3DACA)       // #E3DACA
val BrandIvory = Color(0xFFFAF7F2)           // #FAF7F2
val BrandBronze = Color(0xFF8F6834)          // #8F6834
val BrandBronzeDark = Color(0xFF755427)      // #755427
val BrandBronzeLight = Color(0xFFFAF3E0)     // #FAF3E0
val BrandBorder = Color(0xFFD1C2A5)          // #D1C2A5
val BrandBorderSubtle = Color(0xFFEAE2D3)    // #EAE2D3

// Typography
val BrandText = Color(0xFF1F150D)            // #1F150D Deep Espresso
val BrandTextMuted = Color(0xFF695541)       // #695541 Warm Muted

// Status
val BrandSuccess = Color(0xFF2E7D32)
val BrandWarning = Color(0xFFEF6C00)
val BrandError = Color(0xFFC62828)

// Compatibility aliases for existing screens
val BrandDark = BrandText
val BrandDarkCard = BrandIvory
val BrandGold = BrandBronze
val BrandGoldLight = BrandBronzeLight
val BrandGoldAccent = BrandBronzeDark
val BrandTextPrimary = BrandText

private val VastuColorScheme = lightColorScheme(
    primary = BrandBronze,
    onPrimary = BrandIvory,
    primaryContainer = BrandBronzeLight,
    onPrimaryContainer = BrandText,
    secondary = BrandBronzeDark,
    onSecondary = BrandIvory,
    background = BrandParchment,
    onBackground = BrandText,
    surface = BrandIvory,
    onSurface = BrandText,
    surfaceVariant = Color.White,
    onSurfaceVariant = BrandTextMuted,
    outline = BrandBorder,
    error = BrandError,
    onError = Color.White
)

@Composable
fun VastuTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = VastuColorScheme,
        typography = Typography(),
        content = content
    )
}
