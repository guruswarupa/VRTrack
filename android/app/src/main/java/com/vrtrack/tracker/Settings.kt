package com.vrtrack.tracker

import android.content.Context

data class Settings(
    val host: String = "",            // empty = auto-discover
    val port: Int = Protocol.DATA_PORT,
    val eyeTracking: Boolean = false, // independent of head tracking
    val resolutionIndex: Int = 0,
    val fps: Int = 30,
) {
    companion object {
        val RESOLUTIONS = listOf(640 to 480, 960 to 720, 1280 to 720)
        val FPS_OPTIONS = listOf(30, 60)

        fun load(ctx: Context): Settings {
            val p = ctx.getSharedPreferences("settings", Context.MODE_PRIVATE)
            return Settings(
                p.getString("host", "") ?: "", p.getInt("port", Protocol.DATA_PORT),
                p.getBoolean("eyes", false), p.getInt("res", 0).coerceIn(RESOLUTIONS.indices),
                p.getInt("fps", 30),
            )
        }
    }

    fun save(ctx: Context) {
        ctx.getSharedPreferences("settings", Context.MODE_PRIVATE).edit()
            .putString("host", host).putInt("port", port).putBoolean("eyes", eyeTracking)
            .putInt("res", resolutionIndex).putInt("fps", fps).apply()
    }
}
