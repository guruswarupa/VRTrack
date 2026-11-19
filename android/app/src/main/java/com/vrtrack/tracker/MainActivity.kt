package com.vrtrack.tracker

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.content.res.Configuration
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.vrtrack.tracker.ui.CalibrationScreen
import com.vrtrack.tracker.ui.OnboardingScreen
import com.vrtrack.tracker.ui.Palette
import com.vrtrack.tracker.ui.SettingsScreen
import com.vrtrack.tracker.ui.TrackScreen
import com.vrtrack.tracker.ui.VRTrackTheme

class MainActivity : ComponentActivity() {
    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        TrackingService.engine?.updateRotation()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // `am start --ez autostart true` begins tracking without touching the UI (camera permission required).
        if (intent?.getBooleanExtra("autostart", false) == true &&
            checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
            TrackingService.start(this)
        setContent {
            VRTrackTheme {
                Surface(Modifier.fillMaxSize(), color = Palette.Bg) { App() }
            }
        }
    }
}

private enum class Tab(val label: String, val glyph: String) {
    TRACK("Track", "◉"), CALIBRATE("Calibrate", "⌖"), SETTINGS("Settings", "⚙")
}

private fun onboarded(ctx: Context) =
    ctx.getSharedPreferences("app", Context.MODE_PRIVATE).getBoolean("onboarded", false)

private fun setOnboarded(ctx: Context) =
    ctx.getSharedPreferences("app", Context.MODE_PRIVATE).edit().putBoolean("onboarded", true).apply()

@Composable
private fun App() {
    val ctx = LocalContext.current
    val ui by TrackerState.ui.collectAsStateWithLifecycle()
    var tab by remember { mutableStateOf(Tab.TRACK) }
    var settings by remember { mutableStateOf(Settings.load(ctx)) }
    var showOnboarding by remember { mutableStateOf(!onboarded(ctx)) }
    val landscape = LocalConfiguration.current.orientation == Configuration.ORIENTATION_LANDSCAPE

    val perms = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { r ->
        if (r[Manifest.permission.CAMERA] == true) TrackingService.start(ctx)
    }
    fun startTracking() {
        val need = buildList {
            add(Manifest.permission.CAMERA)
            if (Build.VERSION.SDK_INT >= 33) add(Manifest.permission.POST_NOTIFICATIONS)
        }
        perms.launch(need.toTypedArray())
    }

    if (showOnboarding) {
        OnboardingScreen {
            setOnboarded(ctx)
            showOnboarding = false
            startTracking()
        }
        return
    }

    val content = @Composable {
        when (tab) {
            Tab.TRACK -> TrackScreen(ui, ::startTracking)
            Tab.CALIBRATE -> CalibrationScreen(ui, ::startTracking)
            Tab.SETTINGS -> SettingsScreen(settings, ui) { s ->
                settings = s
                val engine = TrackingService.engine
                if (engine != null) engine.applySettings(s, TrackingService.lifecycleOwnerOrNull()) else s.save(ctx)
            }
        }
    }

    if (landscape) {
        Row(Modifier.fillMaxSize().safeDrawingPadding()) {
            NavigationRail(containerColor = Palette.Surface) {
                Tab.entries.forEach { t ->
                    NavigationRailItem(selected = tab == t, onClick = { tab = t },
                        icon = { Text(t.glyph) }, label = { Text(t.label) })
                }
            }
            content()
        }
    } else {
        Scaffold(
            containerColor = Palette.Bg,
            bottomBar = {
                NavigationBar(containerColor = Palette.Surface) {
                    Tab.entries.forEach { t ->
                        NavigationBarItem(
                            selected = tab == t, onClick = { tab = t },
                            icon = { Text(t.glyph) }, label = { Text(t.label) },
                            colors = NavigationBarItemDefaults.colors(indicatorColor = Palette.Accent.copy(alpha = 0.25f)))
                    }
                }
            },
        ) { pad -> Box(Modifier.padding(pad)) { content() } }
    }
}
