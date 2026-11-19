"""Wire protocol between the Android app and the PC companion.

Tracking data (phone -> PC, UDP, DATA_PORT), little-endian, 54 bytes:
    4s  magic "VRTK"
    B   version (1)
    B   flags  (see FLAG_*)
    I   sequence number (wraps at 2**32)
    Q   phone monotonic timestamp, microseconds
    9f  yaw, pitch, roll (deg), x, y, z (cm), gazeX, gazeY (-1..1), confidence (0..1)

Control (UDP, CONTROL_PORT):
    phone -> broadcast  b"VRTD?"            discovery request
    PC -> phone         b"VRTD!" + JSON     {"name": str, "dataPort": int}
    phone -> PC         b"VRTP" + 8 bytes   ping (opaque payload)
    PC -> phone         b"VRTP" + 8 bytes   pong (same payload echoed)
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

DATA_PORT = 4243
CONTROL_PORT = 4244
OPENTRACK_PORT = 4242  # OpenTrack "UDP over network" default input port

MAGIC = b"VRTK"
VERSION = 1
_FMT = struct.Struct("<4sBBIQ9f")
PACKET_SIZE = _FMT.size  # 54

FLAG_LEFT_OPEN = 1
FLAG_RIGHT_OPEN = 2
FLAG_TRACKING = 4   # a face is currently being tracked
FLAG_PAUSED = 8
FLAG_EYES_ENABLED = 16

DISCOVER_REQUEST = b"VRTD?"
DISCOVER_REPLY_PREFIX = b"VRTD!"
PING_PREFIX = b"VRTP"


@dataclass
class TrackingPacket:
    seq: int
    timestamp_us: int
    yaw: float
    pitch: float
    roll: float
    x: float
    y: float
    z: float
    gaze_x: float = 0.0
    gaze_y: float = 0.0
    confidence: float = 0.0
    flags: int = 0

    @property
    def tracking(self) -> bool:
        return bool(self.flags & FLAG_TRACKING) and not self.paused

    @property
    def paused(self) -> bool:
        return bool(self.flags & FLAG_PAUSED)

    @property
    def left_open(self) -> bool:
        return bool(self.flags & FLAG_LEFT_OPEN)

    @property
    def right_open(self) -> bool:
        return bool(self.flags & FLAG_RIGHT_OPEN)

    @property
    def eyes_enabled(self) -> bool:
        return bool(self.flags & FLAG_EYES_ENABLED)

    def pack(self) -> bytes:
        return _FMT.pack(MAGIC, VERSION, self.flags, self.seq & 0xFFFFFFFF, self.timestamp_us,
                         self.yaw, self.pitch, self.roll, self.x, self.y, self.z,
                         self.gaze_x, self.gaze_y, self.confidence)

    @staticmethod
    def unpack(data: bytes) -> "TrackingPacket | None":
        """Return None for anything that is not a valid v1 tracking packet."""
        if len(data) != PACKET_SIZE:
            return None
        magic, ver, flags, seq, ts, yaw, pitch, roll, x, y, z, gx, gy, conf = _FMT.unpack(data)
        if magic != MAGIC or ver != VERSION:
            return None
        vals = (yaw, pitch, roll, x, y, z, gx, gy, conf)
        if any(v != v or abs(v) > 1e6 for v in vals):  # NaN / absurd
            return None
        return TrackingPacket(seq, ts, yaw, pitch, roll, x, y, z, gx, gy, conf, flags)


def seq_is_newer(new: int, last: int) -> bool:
    """Wrap-aware comparison: True if `new` is ahead of `last`."""
    return 0 < ((new - last) & 0xFFFFFFFF) < 0x80000000
