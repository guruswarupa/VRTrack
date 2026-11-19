package com.vrtrack.tracker

import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Mirror of pc/vrtrack/protocol.py. Keep both in sync. */
object Protocol {
    const val DATA_PORT = 4243
    const val CONTROL_PORT = 4244
    const val PACKET_SIZE = 54

    const val FLAG_LEFT_OPEN = 1
    const val FLAG_RIGHT_OPEN = 2
    const val FLAG_TRACKING = 4
    const val FLAG_PAUSED = 8
    const val FLAG_EYES_ENABLED = 16

    val DISCOVER_REQUEST = "VRTD?".toByteArray()
    val DISCOVER_REPLY_PREFIX = "VRTD!".toByteArray()
    val PING_PREFIX = "VRTP".toByteArray()

    fun newBuffer(): ByteBuffer = ByteBuffer.allocate(PACKET_SIZE).order(ByteOrder.LITTLE_ENDIAN)

    /** Writes one tracking packet into [b] (reused between calls, no allocation). */
    fun encode(
        b: ByteBuffer, seq: Int, timestampUs: Long, flags: Int,
        yaw: Float, pitch: Float, roll: Float, x: Float, y: Float, z: Float,
        gazeX: Float, gazeY: Float, confidence: Float,
    ) {
        b.clear()
        b.put('V'.code.toByte()).put('R'.code.toByte()).put('T'.code.toByte()).put('K'.code.toByte())
        b.put(1.toByte()).put(flags.toByte())
        b.putInt(seq).putLong(timestampUs)
        b.putFloat(yaw).putFloat(pitch).putFloat(roll)
        b.putFloat(x).putFloat(y).putFloat(z)
        b.putFloat(gazeX).putFloat(gazeY).putFloat(confidence)
    }
}
