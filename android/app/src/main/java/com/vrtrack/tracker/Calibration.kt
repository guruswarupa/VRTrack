package com.vrtrack.tracker

import android.content.Context
import kotlin.math.abs

/** Result of the calibration wizard. All values are measured, never defaulted silently. */
data class CalibrationProfile(
    val yaw: Float, val pitch: Float, val roll: Float,
    val x: Float, val y: Float, val z: Float,
    val gazeCx: Float, val gazeCy: Float,
    val extLeft: Float, val extRight: Float, val extUp: Float, val extDown: Float,
    val signX: Float, val signY: Float,
    /** True only if the gaze steps (look left/right/up/down) were actually measured. */
    val gazeMeasured: Boolean = false,
) {
    /** raw gaze ratio -> -1..1 (left/down negative, right/up positive) */
    fun normGazeX(raw: Float): Float {
        if (!gazeMeasured) return 0f
        val d = signX * (raw - gazeCx)
        return (if (d >= 0) d / extRight else d / extLeft).coerceIn(-1f, 1f)
    }

    fun normGazeY(raw: Float): Float {
        if (!gazeMeasured) return 0f
        val d = signY * (raw - gazeCy)
        return (if (d >= 0) d / extUp else d / extDown).coerceIn(-1f, 1f)
    }

    fun save(ctx: Context) {
        ctx.getSharedPreferences("calib", Context.MODE_PRIVATE).edit().apply {
            listOf(yaw, pitch, roll, x, y, z, gazeCx, gazeCy, extLeft, extRight, extUp, extDown, signX, signY, if (gazeMeasured) 1f else 0f)
                .forEachIndexed { i, v -> putFloat("v$i", v) }
        }.apply()
    }

    companion object {
        fun load(ctx: Context): CalibrationProfile? {
            val p = ctx.getSharedPreferences("calib", Context.MODE_PRIVATE)
            if (!p.contains("v13")) return null
            val v = FloatArray(15) { p.getFloat("v$it", 0f) }
            return CalibrationProfile(v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7],
                v[8], v[9], v[10], v[11], v[12], v[13], gazeMeasured = v[14] > 0.5f)
        }
    }
}

enum class CalStep(val prompt: String) {
    IDLE(""),
    NEUTRAL("Sit in your normal driving position, look at the monitor, keep your head neutral"),
    LEFT("Keep your head still. Look at the LEFT edge of the monitor"),
    RIGHT("Keep your head still. Look at the RIGHT edge of the monitor"),
    UP("Keep your head still. Look at the TOP edge of the monitor"),
    DOWN("Keep your head still. Look at the BOTTOM edge of the monitor"),
    DONE("Calibration complete"),
}

/** Time-driven calibration: each step settles, then averages samples while a face is tracked. */
class Calibrator(private val onDone: (CalibrationProfile) -> Unit) {
    private var withGaze = false
    var step = CalStep.IDLE
        private set
    private var stepStartMs = 0L
    private var n = 0
    private val acc = FloatArray(8) // yaw pitch roll x y z gx gy
    private val means = HashMap<CalStep, FloatArray>()

    val active get() = step != CalStep.IDLE && step != CalStep.DONE
    val progress: Float
        get() = if (!active) 0f else ((nowMs() - stepStartMs - SETTLE_MS).coerceAtLeast(0) / SAMPLE_MS.toFloat()).coerceAtMost(1f)

    private fun nowMs() = android.os.SystemClock.elapsedRealtime()

    /** [withGaze]: also measure left/right/up/down gaze (only useful when eye tracking is enabled). */
    fun start(withGaze: Boolean) {
        this.withGaze = withGaze
        means.clear()
        enter(CalStep.NEUTRAL)
    }

    fun cancel() { step = CalStep.IDLE }

    private fun enter(s: CalStep) {
        step = s; stepStartMs = nowMs(); n = 0; acc.fill(0f)
    }

    /** Call once per frame with a tracked face. */
    fun feed(p: Pose, rawGx: Float, rawGy: Float) {
        if (!active) return
        val t = nowMs() - stepStartMs
        if (t < SETTLE_MS) return
        if (n > 0 || t < SETTLE_MS + SAMPLE_MS) {
            acc[0] += p.yaw; acc[1] += p.pitch; acc[2] += p.roll
            acc[3] += p.x; acc[4] += p.y; acc[5] += p.z
            acc[6] += rawGx; acc[7] += rawGy; n++
        }
        if (t >= SETTLE_MS + SAMPLE_MS && n >= MIN_SAMPLES) {
            means[step] = FloatArray(8) { acc[it] / n }
            val next = when (step) {
                CalStep.NEUTRAL -> if (withGaze) CalStep.LEFT else CalStep.DONE
                CalStep.LEFT -> CalStep.RIGHT
                CalStep.RIGHT -> CalStep.UP
                CalStep.UP -> CalStep.DOWN
                else -> CalStep.DONE
            }
            if (next == CalStep.DONE) { finish(); step = CalStep.DONE } else enter(next)
        }
    }

    private fun finish() {
        val c = means[CalStep.NEUTRAL]!!
        val l = means[CalStep.LEFT]
        val r = means[CalStep.RIGHT]
        val u = means[CalStep.UP]
        val d = means[CalStep.DOWN]
        val minExt = 0.01f
        if (l == null || r == null || u == null || d == null) {
            onDone(CalibrationProfile(c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7],
                minExt, minExt, minExt, minExt, 1f, 1f, gazeMeasured = false))
            return
        }
        onDone(CalibrationProfile(
            c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7],
            extLeft = maxOf(abs(l[6] - c[6]), minExt), extRight = maxOf(abs(r[6] - c[6]), minExt),
            extUp = maxOf(abs(u[7] - c[7]), minExt), extDown = maxOf(abs(d[7] - c[7]), minExt),
            signX = if (r[6] >= l[6]) 1f else -1f, signY = if (u[7] >= d[7]) 1f else -1f,
            gazeMeasured = true,
        ))
    }

    private companion object {
        const val SETTLE_MS = 1000L
        const val SAMPLE_MS = 1500L
        const val MIN_SAMPLES = 10
    }
}
