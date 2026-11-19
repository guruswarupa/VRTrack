package com.vrtrack.tracker

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Test
import java.io.File

/** The Python PC app is tested against the same fixture file (protocol/test_vectors.json). */
class ProtocolTest {
    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it) }

    @Test
    fun encodesIdenticallyToPython() {
        val root = JSONObject(File("../../protocol/test_vectors.json").readText())
        assertEquals(Protocol.PACKET_SIZE, root.getInt("packet_size"))
        val cases = root.getJSONArray("cases")
        for (i in 0 until cases.length()) {
            val c = cases.getJSONObject(i)
            val b = Protocol.newBuffer()
            Protocol.encode(
                b, c.getLong("seq").toInt(), c.getLong("timestamp_us"), c.getInt("flags"),
                c.getDouble("yaw").toFloat(), c.getDouble("pitch").toFloat(), c.getDouble("roll").toFloat(),
                c.getDouble("x").toFloat(), c.getDouble("y").toFloat(), c.getDouble("z").toFloat(),
                c.getDouble("gaze_x").toFloat(), c.getDouble("gaze_y").toFloat(), c.getDouble("confidence").toFloat())
            assertEquals(c.getString("name"), c.getString("hex"), hex(b.array()))
        }
    }
}
