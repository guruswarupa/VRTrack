package com.vrtrack.tracker

import android.os.SystemClock
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.SocketTimeoutException
import java.nio.ByteBuffer

enum class Link { SEARCHING, CONNECTED, LOST }

/**
 * UDP link to the PC: tracking stream, auto discovery (broadcast), ping/pong for latency,
 * and automatic recovery after network interruptions.
 */
class NetworkClient(private val onStatus: (Link, String, Int) -> Unit) {
    @Volatile private var target: InetAddress? = null
    @Volatile private var dataPort = Protocol.DATA_PORT
    @Volatile private var manual = false
    @Volatile private var running = false
    @Volatile private var lastPongMs = 0L
    @Volatile private var latencyMs = -1
    private var thread: Thread? = null

    private val dataSock = DatagramSocket()
    private val dataPacket = DatagramPacket(ByteArray(Protocol.PACKET_SIZE), Protocol.PACKET_SIZE)
    private val buf: ByteBuffer = Protocol.newBuffer()
    private var seq = 0

    fun start(host: String, port: Int) {
        stop()
        manual = host.isNotBlank()
        dataPort = port
        target = null
        if (manual) target = runCatching { InetAddress.getByName(host.trim()) }.getOrNull()
        running = true
        thread = Thread(::controlLoop, "vrtrack-control").also { it.isDaemon = true; it.start() }
    }

    fun stop() {
        running = false
        thread?.join(1500)
        thread = null
    }

    fun close() { stop(); dataSock.close() }

    /** Called per tracking frame from the camera/MediaPipe thread. No allocation. */
    fun sendPose(flags: Int, p: Pose, gx: Float, gy: Float, conf: Float) {
        val t = target ?: return
        Protocol.encode(buf, seq++, SystemClock.elapsedRealtimeNanos() / 1000, flags,
            p.yaw, p.pitch, p.roll, p.x, p.y, p.z, gx, gy, conf)
        System.arraycopy(buf.array(), 0, dataPacket.data, 0, Protocol.PACKET_SIZE)
        dataPacket.setAddress(t)
        dataPacket.port = dataPort
        try {
            dataSock.send(dataPacket)
            if (seq % 120 == 1) android.util.Log.i("VRTrack", "sent seq=$seq to ${t.hostAddress}:$dataPort")
        } catch (e: Exception) {
            if (seq % 120 == 1) android.util.Log.w("VRTrack", "udp send failed: $e")
        }
    }

    private fun controlLoop() {
        val sock = DatagramSocket().apply { soTimeout = 300; broadcast = true }
        val rx = DatagramPacket(ByteArray(256), 256)
        var lastPing = 0L
        var lastDiscover = 0L
        val ping = ByteArray(12)
        System.arraycopy(Protocol.PING_PREFIX, 0, ping, 0, 4)
        try {
            while (running) {
                val now = SystemClock.elapsedRealtime()
                val t = target
                if (t == null || (!manual && now - lastPongMs > REDISCOVER_MS && lastPongMs != 0L)) {
                    if (!manual && now - lastDiscover > 1000) {
                        lastDiscover = now
                        if (lastPongMs != 0L && now - lastPongMs > REDISCOVER_MS) target = null
                        // Broadcast on every interface (Wi-Fi, USB tethering, ...), not just the default route.
                        for (b in broadcastAddresses()) runCatching {
                            sock.send(DatagramPacket(Protocol.DISCOVER_REQUEST, Protocol.DISCOVER_REQUEST.size,
                                b, Protocol.CONTROL_PORT))
                        }
                    }
                } else if (now - lastPing > 500) {
                    lastPing = now
                    java.nio.ByteBuffer.wrap(ping, 4, 8).putLong(SystemClock.elapsedRealtimeNanos())
                    runCatching { sock.send(DatagramPacket(ping, ping.size, t, Protocol.CONTROL_PORT)) }
                }
                try {
                    sock.receive(rx)
                    handle(rx)
                } catch (_: SocketTimeoutException) { }
                catch (_: Exception) { Thread.sleep(200) }
                report(SystemClock.elapsedRealtime())
            }
        } finally { sock.close() }
    }

    private fun broadcastAddresses(): List<InetAddress> = runCatching {
        java.net.NetworkInterface.getNetworkInterfaces().toList()
            .filter { it.isUp && !it.isLoopback }
            .flatMap { it.interfaceAddresses }
            .mapNotNull { it.broadcast }
    }.getOrDefault(emptyList())

    private fun handle(p: DatagramPacket) {
        val d = p.data
        val n = p.length
        if (n >= 5 && startsWith(d, Protocol.DISCOVER_REPLY_PREFIX)) {
            val json = runCatching { JSONObject(String(d, 5, n - 5)) }.getOrNull() ?: return
            dataPort = json.optInt("dataPort", Protocol.DATA_PORT)
            target = p.address
            lastPongMs = SystemClock.elapsedRealtime()
        } else if (n == 12 && startsWith(d, Protocol.PING_PREFIX)) {
            val sent = ByteBuffer.wrap(d, 4, 8).long
            latencyMs = ((SystemClock.elapsedRealtimeNanos() - sent) / 2_000_000L).toInt().coerceAtLeast(0)
            lastPongMs = SystemClock.elapsedRealtime()
        }
    }

    private fun startsWith(d: ByteArray, prefix: ByteArray) =
        d.size >= prefix.size && prefix.indices.all { d[it] == prefix[it] }

    private fun report(now: Long) {
        val t = target
        val link = when {
            t == null -> Link.SEARCHING
            now - lastPongMs < 2000 && lastPongMs != 0L -> Link.CONNECTED
            else -> Link.LOST
        }
        onStatus(link, t?.hostAddress ?: "", latencyMs)
    }

    private companion object { const val REDISCOVER_MS = 6000L }
}
