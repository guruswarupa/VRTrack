"""OpenTrack "UDP over network" output.

OpenTrack's UDP input expects 6 little-endian doubles: X, Y, Z (cm), Yaw, Pitch, Roll (deg)
sent to its listening port (default 4242). In OpenTrack choose Input = "UDP over network".
OpenTrack then provides the FreeTrack / TrackIR-compatible output for games.
"""
from __future__ import annotations

import socket
import struct

_FMT = struct.Struct("<6d")


def pack_opentrack(x: float, y: float, z: float, yaw: float, pitch: float, roll: float) -> bytes:
    return _FMT.pack(x, y, z, yaw, pitch, roll)


class OpenTrackSender:
    def __init__(self, host: str = "127.0.0.1", port: int = 4242):
        self.addr = (host, port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def set_target(self, host: str, port: int) -> None:
        self.addr = (host, port)

    def send(self, x, y, z, yaw, pitch, roll) -> None:
        try:
            self._sock.sendto(pack_opentrack(x, y, z, yaw, pitch, roll), self.addr)
        except OSError:
            pass  # OpenTrack not running / network down: ignore, keep tracking alive

    def close(self) -> None:
        self._sock.close()
