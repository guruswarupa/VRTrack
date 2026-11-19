package com.vrtrack.tracker.ui

import android.content.res.Configuration
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.vrtrack.tracker.CalStep
import com.vrtrack.tracker.Link
import com.vrtrack.tracker.TrackingEngine
import com.vrtrack.tracker.TrackingService
import com.vrtrack.tracker.UiState
import kotlin.math.sin

@Composable
fun TrackScreen(ui: UiState, onStart: () -> Unit) {
    val ctx = LocalContext.current
    val landscape = LocalConfiguration.current.orientation == Configuration.ORIENTATION_LANDSCAPE
    val engine = TrackingService.engine

    val controls = @Composable {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            StatusGrid(ui)
            if (ui.error != null) {
                AppCard { Text(ui.error, color = Palette.Bad, fontSize = 14.sp) }
            }
            CalibrationBanner(ui, engine)
            if (!ui.running) {
                PrimaryButton("Start tracking", onStart, Modifier.fillMaxWidth())
                Hint("Tracking keeps running when the screen is off. Turn the screen off while you play for the " +
                    "best frame rate and battery life.")
            } else {
                PrimaryButton("Stop tracking", { TrackingService.stop(ctx) }, Modifier.fillMaxWidth(), danger = true)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    SecondaryButton("Recenter", { engine?.recenter() }, Modifier.weight(1f))
                    SecondaryButton(if (ui.paused) "Resume" else "Pause", {
                        engine?.let { it.paused = !it.paused }
                    }, Modifier.weight(1f))
                }
            }
            LiveValues(ui)
        }
    }

    if (landscape) {
        Row(Modifier.fillMaxSize().padding(16.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            CameraPreview(ui, Modifier.weight(1f).fillMaxHeight())
            Column(Modifier.weight(1f).verticalScroll(rememberScrollState())) { controls() }
        }
    } else {
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) {
            CameraPreview(ui, Modifier.fillMaxWidth())
            controls()
        }
    }
}

@Composable
private fun StatusGrid(ui: UiState) {
    val pc = when {
        !ui.running -> "Off" to Color.Gray
        ui.link == Link.CONNECTED -> "${ui.host} · ${ui.latencyMs} ms" to Palette.Good
        ui.link == Link.SEARCHING -> "Searching…" to Palette.Warn
        else -> "Connection lost" to Palette.Bad
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            StatTile("Face", if (ui.face) "Tracked" else if (ui.running) "Not seen" else "—",
                if (ui.face) Palette.Good else if (ui.running) Palette.Bad else Color.Gray, Modifier.weight(1f))
            StatTile("Quality", if (ui.face) "${(ui.confidence * 100).toInt()}%" else "—", Palette.Accent, Modifier.weight(1f))
            StatTile("FPS", if (ui.running) ui.fps.toString() else "—", Palette.Accent, Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            StatTile("PC", pc.first, pc.second, Modifier.weight(2f))
            StatTile("Calibration", if (ui.calibrated) "Done" else "Needed",
                if (ui.calibrated) Palette.Good else Palette.Warn, Modifier.weight(1.2f))
        }
    }
}

@Composable
private fun CalibrationBanner(ui: UiState, engine: TrackingEngine?) {
    if (ui.calStep == CalStep.IDLE || ui.calStep == CalStep.DONE) return
    AppCard {
        SectionTitle("Calibrating")
        Text(ui.calStep.prompt, fontSize = 15.sp, color = Palette.Text)
        LinearProgressIndicator(progress = { ui.calProgress }, modifier = Modifier.fillMaxWidth())
        SecondaryButton("Cancel", { engine?.cancelCalibration() })
    }
}

@Composable
private fun LiveValues(ui: UiState) {
    AppCard {
        SectionTitle("Live values")
        Text(
            "yaw %7.1f°   x %6.1f cm\npitch %5.1f°   y %6.1f cm\nroll %6.1f°   z %6.1f cm".format(
                ui.yaw, ui.x, ui.pitch, ui.y, ui.roll, ui.z),
            fontFamily = FontFamily.Monospace, fontSize = 13.sp, color = Palette.Text, lineHeight = 20.sp)
        if (ui.gazeX != 0f || ui.gazeY != 0f) {
            Text("gaze %5.2f %5.2f   eyes %s".format(ui.gazeX, ui.gazeY, if (ui.leftOpen && ui.rightOpen) "open" else "blink"),
                fontFamily = FontFamily.Monospace, fontSize = 13.sp, color = Palette.Muted)
        }
    }
}

@Composable
fun CameraPreview(ui: UiState, modifier: Modifier = Modifier) {
    val owner = LocalLifecycleOwner.current
    val ctx = LocalContext.current
    val view = remember {
        PreviewView(ctx).apply {
            implementationMode = PreviewView.ImplementationMode.PERFORMANCE
            scaleType = PreviewView.ScaleType.FIT_CENTER
        }
    }

    // The camera always belongs to the foreground service, so tracking survives screen-off.
    // The preview is attached only while this screen is visible.
    DisposableEffect(ui.running, owner) {
        val e = TrackingService.engine
        val svc = TrackingService.lifecycleOwnerOrNull()
        val obs = LifecycleEventObserver { _, ev ->
            if (e != null && svc != null) when (ev) {
                Lifecycle.Event.ON_START -> e.bind(svc, view.surfaceProvider)
                Lifecycle.Event.ON_STOP -> e.bind(svc, null)
                else -> {}
            }
        }
        if (ui.running) owner.lifecycle.addObserver(obs)
        onDispose {
            owner.lifecycle.removeObserver(obs)
            if (e != null && svc != null && ui.running) e.bind(svc, null)
        }
    }

    val screenH = LocalConfiguration.current.screenHeightDp
    BoxWithConstraints(modifier.clip(RoundedCornerShape(16.dp)).background(Color.Black).clipToBounds(),
        contentAlignment = Alignment.Center) {
        // Keep the whole preview on screen: cap its height (40% of the screen in portrait).
        val cap = if (maxHeight == Dp.Infinity) (screenH * 0.4f).dp else maxHeight
        val h = minOf(maxWidth.value / ui.frameAspect, cap.value).dp
        Box(Modifier.size(h * ui.frameAspect, h)) {
            AndroidView({ view }, Modifier.fillMaxSize())
            Canvas(Modifier.fillMaxSize()) {
                val lm = ui.landmarks
                if (lm.isEmpty()) return@Canvas
                fun pt(i: Int) = Offset((1f - lm[i * 2]) * size.width, lm[i * 2 + 1] * size.height) // mirrored like the preview
                val oval = TrackingEngine.OVAL_COUNT
                val eyes = TrackingEngine.EYE_COUNT
                val iris = TrackingEngine.IRIS_COUNT
                for (i in 0 until oval) drawCircle(Color(0x884DA3FF), 3f, pt(i))
                for (i in oval until oval + eyes) drawCircle(Palette.Good, 3.5f, pt(i))
                for (i in oval + eyes until oval + eyes + iris) drawCircle(Palette.Warn, 3f, pt(i))
                val nose = pt(oval + eyes + iris)
                val len = size.width * 0.18f
                drawLine(Color.White, nose, Offset(
                    nose.x - sin(Math.toRadians(ui.yaw.toDouble())).toFloat() * len,
                    nose.y - sin(Math.toRadians(ui.pitch.toDouble())).toFloat() * len), 4f)
            }
        }
        Text(
            if (!ui.running) "Preview off — start tracking" else if (ui.face) "Face detected" else "No face",
            Modifier.align(Alignment.TopStart).padding(12.dp),
            color = if (ui.face) Palette.Good else if (ui.running) Palette.Bad else Palette.Muted, fontSize = 12.sp)
    }
}
