package com.vrtrack.tracker.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vrtrack.tracker.CalStep
import com.vrtrack.tracker.Settings
import com.vrtrack.tracker.TrackingService
import com.vrtrack.tracker.UiState

@Composable
fun CalibrationScreen(ui: UiState, onStartTracking: () -> Unit) {
    val ctx = LocalContext.current
    val eyes = Settings.load(ctx).eyeTracking
    val engine = TrackingService.engine
    val steps = if (eyes) listOf(CalStep.NEUTRAL, CalStep.LEFT, CalStep.RIGHT, CalStep.UP, CalStep.DOWN)
    else listOf(CalStep.NEUTRAL)
    val active = ui.calStep != CalStep.IDLE && ui.calStep != CalStep.DONE

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Calibration", fontSize = 24.sp, fontWeight = FontWeight.SemiBold, color = Palette.Text)
        Hint("Calibration records your neutral head position so the view starts straight ahead. " +
            if (eyes) "It also measures how far your eyes move when you look at each edge of the monitor."
            else "Gaze calibration is skipped because eye tracking is off (Settings → Tracking).")

        if (!ui.running) {
            AppCard {
                SectionTitle("Start tracking first")
                Hint("Calibration uses the live camera, so tracking has to be running.")
                PrimaryButton("Start tracking", onStartTracking, Modifier.fillMaxWidth())
            }
            return@Column
        }

        AppCard {
            SectionTitle(
                if (active) "Step ${steps.indexOf(ui.calStep).coerceAtLeast(0) + 1} of ${steps.size}"
                else if (ui.calStep == CalStep.DONE || ui.calibrated) "Calibrated" else "Ready")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                steps.forEachIndexed { i, s ->
                    val done = ui.calStep == CalStep.DONE || (active && i < steps.indexOf(ui.calStep))
                    val cur = active && s == ui.calStep
                    Box(Modifier.weight(1f).height(6.dp).clip(CircleShape).background(
                        if (done) Palette.Good else if (cur) Palette.Accent else Palette.Border))
                }
            }
            Text(
                when {
                    active -> ui.calStep.prompt
                    ui.calStep == CalStep.DONE -> "Calibration complete. Press Recenter any time to re-zero your position."
                    else -> "Sit in your normal driving position, look straight at the monitor and keep your head still."
                },
                fontSize = 17.sp, color = Palette.Text, lineHeight = 24.sp)
            if (active) {
                LinearProgressIndicator(progress = { ui.calProgress }, modifier = Modifier.fillMaxWidth())
                if (!ui.face) Text("Face not visible — move into view", color = Palette.Warn, fontSize = 14.sp)
                SecondaryButton("Cancel", { engine?.cancelCalibration() })
            } else {
                PrimaryButton(if (ui.calibrated) "Recalibrate" else "Start calibration",
                    { engine?.startCalibration() }, Modifier.fillMaxWidth())
            }
        }

        AppCard {
            SectionTitle("Tips")
            Hint("• Mount the phone just below or beside the monitor, facing you.\n" +
                "• Keep your whole face in view with even lighting and no strong backlight.\n" +
                "• Recenter (Track tab or notification) whenever the view drifts off-centre.")
        }
    }
}
