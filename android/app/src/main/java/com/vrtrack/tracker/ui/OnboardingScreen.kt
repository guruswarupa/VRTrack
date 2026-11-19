package com.vrtrack.tracker.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private data class Page(val title: String, val body: String)

private val PAGES = listOf(
    Page("Head tracking from your phone",
        "VRTrack turns your phone's front camera into a head tracker for sim racing and flight sims. " +
            "The camera is analysed on this phone only: no video is stored or uploaded, and no account or " +
            "internet connection is needed."),
    Page("Set up your PC",
        "1. Install the VRTrack desktop app and OpenTrack on your PC.\n" +
            "2. In OpenTrack choose Input “UDP over network”, Output “freetrack 2.0 Enhanced”, then press Start.\n" +
            "3. Connect the phone and PC to the same Wi-Fi, or use USB tethering.\n" +
            "4. Start VRTrack on the PC. The phone finds it automatically."),
    Page("Allow camera access",
        "VRTrack needs the camera to see your head, and a notification so tracking can keep running with the " +
            "screen off. Both stay on your phone."),
)

@Composable
fun OnboardingScreen(onFinish: () -> Unit) {
    var page by remember { mutableIntStateOf(0) }
    val p = PAGES[page]
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.SpaceBetween) {
        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Spacer(Modifier.height(24.dp))
            Text("VRTrack", fontSize = 14.sp, color = Palette.Accent, fontWeight = FontWeight.SemiBold)
            Text(p.title, fontSize = 28.sp, fontWeight = FontWeight.SemiBold, color = Palette.Text, lineHeight = 34.sp)
            Text(p.body, fontSize = 16.sp, color = Palette.Muted, lineHeight = 24.sp)
        }
        Column(verticalArrangement = Arrangement.spacedBy(16.dp), modifier = Modifier.padding(top = 32.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically) {
                PAGES.indices.forEach { i ->
                    Box(Modifier.padding(4.dp).size(if (i == page) 10.dp else 8.dp).clip(CircleShape)
                        .background(if (i == page) Palette.Accent else Palette.Border))
                }
            }
            PrimaryButton(if (page == PAGES.lastIndex) "Allow and continue" else "Next", {
                if (page == PAGES.lastIndex) onFinish() else page++
            }, Modifier.fillMaxWidth())
            if (page > 0) SecondaryButton("Back", { page-- }, Modifier.fillMaxWidth())
        }
    }
}
