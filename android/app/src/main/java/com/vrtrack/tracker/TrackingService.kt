package com.vrtrack.tracker

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

/** Keeps camera + tracking alive while the screen is off or another app is in front. */
class TrackingService : LifecycleService() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        instance = this
        when (intent?.action) {
            ACTION_RECENTER -> { engine?.recenter(); return START_NOT_STICKY }
            ACTION_PAUSE -> {
                engine?.let { it.paused = !it.paused }
                updateNotification(TrackerState.ui.value); return START_NOT_STICKY
            }
        }
        if (intent?.action == ACTION_STOP) {
            wakeLock?.let { if (it.isHeld) it.release() }; wakeLock = null
            engine?.stop(); stopForeground(STOP_FOREGROUND_REMOVE); stopSelf()
            return START_NOT_STICKY
        }
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CH, "Tracking", NotificationManager.IMPORTANCE_LOW).apply {
            lockscreenVisibility = Notification.VISIBILITY_PUBLIC
        })
        val n = buildNotification(TrackerState.ui.value)
        if (Build.VERSION.SDK_INT >= 29)
            startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA)
        else startForeground(1, n)
        if (wakeLock == null) {
            wakeLock = getSystemService(android.os.PowerManager::class.java)
                .newWakeLock(android.os.PowerManager.PARTIAL_WAKE_LOCK, "vrtrack:tracking").apply { acquire() }
        }
        val e = engine ?: TrackingEngine(applicationContext).also { engine = it }
        e.start(this)
        if (statusJob == null) statusJob = lifecycleScope.launch {
            var last = ""
            TrackerState.ui.collect { ui ->
                val key = statusText(ui)
                if (key != last) { last = key; updateNotification(ui) }
            }
        }
        return START_NOT_STICKY
    }

    private var statusJob: kotlinx.coroutines.Job? = null

    private fun statusText(ui: UiState): String {
        val face = when { ui.paused -> "Paused"; ui.face -> "Face OK"; else -> "No face" }
        val pc = when (ui.link) {
            Link.CONNECTED -> "PC ${ui.host} ${ui.latencyMs} ms"
            Link.SEARCHING -> "searching PC…"
            Link.LOST -> "PC connection lost"
        }
        return "$face · ${ui.fps} fps · $pc"
    }

    private fun action(name: String, label: String, code: Int): NotificationCompat.Action {
        val pi = PendingIntent.getService(this, code, Intent(this, TrackingService::class.java).setAction(name),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        return NotificationCompat.Action.Builder(0, label, pi).build()
    }

    private fun buildNotification(ui: UiState): Notification {
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        return NotificationCompat.Builder(this, CH)
            .setContentTitle("VRTrack tracking")
            .setContentText(statusText(ui))
            .setSmallIcon(R.drawable.ic_stat_vrtrack)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)   // readable on the lock screen
            .setOnlyAlertOnce(true).setOngoing(true).setContentIntent(open)
            .addAction(action(ACTION_RECENTER, "Recenter", 1))
            .addAction(action(ACTION_PAUSE, if (ui.paused) "Resume" else "Pause", 2))
            .addAction(action(ACTION_STOP, "Stop", 3))
            .build()
    }

    private fun updateNotification(ui: UiState) {
        getSystemService(NotificationManager::class.java).notify(1, buildNotification(ui))
    }

    private var wakeLock: android.os.PowerManager.WakeLock? = null

    override fun onDestroy() {
        wakeLock?.let { if (it.isHeld) it.release() }; wakeLock = null
        engine?.stop(); engine = null; instance = null
        super.onDestroy()
    }

    companion object {
        const val ACTION_STOP = "stop"
        const val ACTION_RECENTER = "recenter"
        const val ACTION_PAUSE = "pause"
        private const val CH = "tracking"
        @Volatile var engine: TrackingEngine? = null
        @Volatile private var instance: TrackingService? = null
        fun lifecycleOwnerOrNull(): androidx.lifecycle.LifecycleOwner? = instance

        fun start(ctx: Context) {
            ContextCompat_startForeground(ctx, Intent(ctx, TrackingService::class.java))
        }

        fun stop(ctx: Context) {
            ctx.startService(Intent(ctx, TrackingService::class.java).setAction(ACTION_STOP))
        }

        private fun ContextCompat_startForeground(ctx: Context, i: Intent) =
            androidx.core.content.ContextCompat.startForegroundService(ctx, i)
    }
}
