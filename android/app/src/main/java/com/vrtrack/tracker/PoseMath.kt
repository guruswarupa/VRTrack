package com.vrtrack.tracker

import kotlin.math.asin
import kotlin.math.atan2
import kotlin.math.sqrt

/** Head pose from MediaPipe's facial transformation matrix (4x4, column-major). */
class Pose {
    var yaw = 0f; var pitch = 0f; var roll = 0f   // degrees
    var x = 0f; var y = 0f; var z = 0f            // centimetres (camera space)
}

object PoseMath {
    private const val RAD2DEG = 57.29578f

    /** Fills [out]. Returns false if the matrix is unusable. */
    fun fromMatrix(m: FloatArray, out: Pose): Boolean {
        if (m.size < 16) return false
        // column c, row r -> m[c*4 + r]; normalise columns to strip uniform scale
        val sx = sqrt(m[0] * m[0] + m[1] * m[1] + m[2] * m[2])
        val sy = sqrt(m[4] * m[4] + m[5] * m[5] + m[6] * m[6])
        val sz = sqrt(m[8] * m[8] + m[9] * m[9] + m[10] * m[10])
        if (sx < 1e-6f || sy < 1e-6f || sz < 1e-6f) return false
        val r02 = m[8] / sz
        val r12 = m[9] / sz
        val r22 = m[10] / sz
        val r10 = m[1] / sx
        val r11 = m[5] / sy
        out.yaw = atan2(r02, r22) * RAD2DEG
        out.pitch = asin((-r12).coerceIn(-1f, 1f)) * RAD2DEG
        out.roll = atan2(r10, r11) * RAD2DEG
        out.x = m[12]; out.y = m[13]; out.z = m[14]
        return true
    }
}
