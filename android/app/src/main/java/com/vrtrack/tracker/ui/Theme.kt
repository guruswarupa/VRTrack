package com.vrtrack.tracker.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

object Palette {
    val Bg = Color(0xFF101319)
    val Surface = Color(0xFF171B23)
    val Surface2 = Color(0xFF1F242E)
    val Border = Color(0xFF2A303C)
    val Text = Color(0xFFE8EBF2)
    val Muted = Color(0xFF8B93A7)
    val Accent = Color(0xFF4DA3FF)
    val Good = Color(0xFF43D19E)
    val Warn = Color(0xFFFFC857)
    val Bad = Color(0xFFFF6B6B)
}

private val Scheme = darkColorScheme(
    primary = Palette.Accent, onPrimary = Color(0xFF06121F),
    background = Palette.Bg, onBackground = Palette.Text,
    surface = Palette.Surface, onSurface = Palette.Text,
    surfaceVariant = Palette.Surface2, onSurfaceVariant = Palette.Muted,
    outline = Palette.Border, error = Palette.Bad,
    secondaryContainer = Color(0xFF2B5F99), onSecondaryContainer = Color.White,
)

/** The app is dark-only on purpose: it is used next to a monitor in a dim room. */
@Composable
fun VRTrackTheme(content: @Composable () -> Unit) {
    @Suppress("UNUSED_VARIABLE") val unused = isSystemInDarkTheme()
    MaterialTheme(colorScheme = Scheme, content = content)
}
