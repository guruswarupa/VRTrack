package com.vrtrack.tracker

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.cos
import kotlin.math.sin

class PoseMathTest {
    /** Column-major 4x4 with rotation about Y (yaw) and a translation. */
    private fun yawMatrix(deg: Double, tx: Float = 0f, ty: Float = 0f, tz: Float = 0f): FloatArray {
        val r = Math.toRadians(deg)
        val c = cos(r).toFloat(); val s = sin(r).toFloat()
        return floatArrayOf(
            c, 0f, -s, 0f,
            0f, 1f, 0f, 0f,
            s, 0f, c, 0f,
            tx, ty, tz, 1f)
    }

    @Test
    fun identityIsZero() {
        val p = Pose()
        assertTrue(PoseMath.fromMatrix(yawMatrix(0.0), p))
        assertEquals(0f, p.yaw, 1e-4f); assertEquals(0f, p.pitch, 1e-4f); assertEquals(0f, p.roll, 1e-4f)
    }

    @Test
    fun recoversYawAndTranslation() {
        val p = Pose()
        assertTrue(PoseMath.fromMatrix(yawMatrix(30.0, 1f, 2f, -50f), p))
        assertEquals(30f, p.yaw, 1e-2f)
        assertEquals(0f, p.pitch, 1e-2f)
        assertEquals(1f, p.x, 1e-4f); assertEquals(2f, p.y, 1e-4f); assertEquals(-50f, p.z, 1e-4f)
    }

    @Test
    fun ignoresUniformScale() {
        val m = yawMatrix(20.0)
        for (i in intArrayOf(0, 1, 2, 4, 5, 6, 8, 9, 10)) m[i] *= 3f
        val p = Pose()
        assertTrue(PoseMath.fromMatrix(m, p))
        assertEquals(20f, p.yaw, 1e-2f)
    }

    @Test
    fun rejectsDegenerateMatrices() {
        assertFalse(PoseMath.fromMatrix(FloatArray(16), Pose()))
        assertFalse(PoseMath.fromMatrix(FloatArray(4), Pose()))
    }
}
