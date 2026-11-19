package com.vrtrack.tracker.ui

import android.content.Intent
import android.provider.Settings as AndroidSettings
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vrtrack.tracker.Link
import com.vrtrack.tracker.Settings
import com.vrtrack.tracker.UiState

@Composable
fun SettingsScreen(s: Settings, ui: UiState, onChange: (Settings) -> Unit) {
    val ctx = LocalContext.current
    var host by remember(s.host) { mutableStateOf(s.host) }
    var port by remember(s.port) { mutableStateOf(s.port.toString()) }
    val version = remember {
        runCatching { ctx.packageManager.getPackageInfo(ctx.packageName, 0).versionName }.getOrNull() ?: "?"
    }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Settings", fontSize = 24.sp, fontWeight = FontWeight.SemiBold, color = Palette.Text)

        AppCard {
            SectionTitle("PC connection")
            Hint("Leave the address empty and the phone finds your PC automatically (on Wi-Fi or USB tethering). " +
                "If it can't, type the PC address shown in the VRTrack desktop app → Setup.")
            OutlinedTextField(host, { host = it }, label = { Text("PC address (optional)") }, singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri))
            OutlinedTextField(port, { port = it.filter(Char::isDigit).take(5) }, label = { Text("Data port") },
                singleLine = true, modifier = Modifier.fillMaxWidth(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number))
            SecondaryButton("Apply and test connection", {
                onChange(s.copy(host = host.trim(), port = port.toIntOrNull()?.coerceIn(1, 65535) ?: s.port))
            })
            val (txt, col) = when {
                !ui.running -> "Start tracking to test the connection" to Palette.Muted
                ui.link == Link.CONNECTED -> "Connected to ${ui.host} · ${ui.latencyMs} ms" to Palette.Good
                ui.link == Link.SEARCHING -> "Searching for the PC…" to Palette.Warn
                else -> "Connection lost — retrying" to Palette.Bad
            }
            Text(txt, color = col, fontSize = 14.sp)
        }

        AppCard {
            SectionTitle("Camera")
            Hint("Lower resolution and 30 fps use less battery and are usually just as accurate.")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Settings.RESOLUTIONS.forEachIndexed { i, (w, h) ->
                    FilterChip(s.resolutionIndex == i, { onChange(s.copy(resolutionIndex = i)) }, label = { Text("${w}×$h") })
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Settings.FPS_OPTIONS.forEach { f ->
                    FilterChip(s.fps == f, { onChange(s.copy(fps = f)) }, label = { Text("$f fps") })
                }
            }
        }

        AppCard {
            SectionTitle("Tracking")
            SwitchRow("Eye tracking", "Gaze and blink detection. Head tracking works without it. " +
                "Restart tracking after changing.", s.eyeTracking) { onChange(s.copy(eyeTracking = it)) }
            Hint("Sensitivity, dead zones, smoothing, curves and per-game profiles are set in the PC app.")
        }

        AppCard {
            SectionTitle("Keep tracking in the background")
            Hint("Tracking runs in a foreground service, so it continues with the screen off. Some phones stop " +
                "background apps to save battery. If tracking stops during long sessions, exclude VRTrack from " +
                "battery optimisation.")
            SecondaryButton("Open battery optimisation settings", {
                runCatching {
                    ctx.startActivity(Intent(AndroidSettings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                }
            })
        }

        AppCard {
            SectionTitle("Privacy")
            Hint("Camera frames are analysed on this phone and are never stored or uploaded. Only head-pose numbers " +
                "are sent to your PC over your local network. No accounts, ads, analytics or internet connection needed.")
            Hint("VRTrack $version")
        }
    }
}
