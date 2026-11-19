package com.vrtrack.tracker

import org.junit.Assert.assertEquals
import org.junit.Test

class CalibrationProfileTest {
    private fun profile(measured: Boolean, signX: Float = 1f) = CalibrationProfile(
        0f, 0f, 0f, 0f, 0f, 0f, gazeCx = 0.1f, gazeCy = 0f,
        extLeft = 0.2f, extRight = 0.4f, extUp = 0.1f, extDown = 0.1f,
        signX = signX, signY = 1f, gazeMeasured = measured)

    @Test
    fun gazeIsNormalisedPerSide() {
        val p = profile(true)
        assertEquals(0f, p.normGazeX(0.1f), 1e-6f)
        assertEquals(1f, p.normGazeX(0.5f), 1e-6f)    // right edge
        assertEquals(-1f, p.normGazeX(-0.1f), 1e-6f)  // left edge
        assertEquals(1f, p.normGazeX(5f), 1e-6f)      // clamped
    }

    @Test
    fun invertedSensorSignIsHandled() {
        val p = profile(true, signX = -1f)
        assertEquals(1f, p.normGazeX(-0.3f), 1e-6f)
    }

    @Test
    fun unmeasuredGazeIsNeverInvented() {
        val p = profile(false)
        assertEquals(0f, p.normGazeX(0.5f), 0f)
        assertEquals(0f, p.normGazeY(0.5f), 0f)
    }
}
