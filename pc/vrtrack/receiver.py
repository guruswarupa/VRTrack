"""UDP receiver: tracking data, discovery replies and ping echo."""
from __future__ import annotations

import json
import socket
import threading
import time
from typing import Callable

from . import protocol as P

STREAM_TIMEOUT_S = 1.0


class Receiver:
    def __init__(self, on_packet: Callable[[P.TrackingPacket], None],
                 name: str = "VRTrack PC", data_port: int = P.DATA_PORT,
                 control_port: int = P.CONTROL_PORT, bind: str = "0.0.0.0"):
        self.on_packet = on_packet
        self.name = name
        self.data_port = data_port
        self.control_port = control_port
        self.bind = bind
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._socks: list[socket.socket] = []
        self._last_seq: int | None = None
        self.received = 0
        self.lost = 0
        self.out_of_order = 0
        self.invalid = 0
        self.last_rx_time = 0.0
        self.phone_addr: tuple[str, int] | None = None
        self.stream_restarted = False   # set when a stream resumes after silence; consumer clears it
        self._rate_times: list[float] = []

    @property
    def connected(self) -> bool:
        return self.last_rx_time > 0 and time.monotonic() - self.last_rx_time < 1.0

    @property
    def rate_hz(self) -> float:
        now = time.monotonic()
        self._rate_times = [t for t in self._rate_times if now - t < 1.0]
        return float(len(self._rate_times))

    def start(self) -> None:
        for port, target in ((self.data_port, self._data_loop), (self.control_port, self._control_loop)):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.bind, port))
            s.settimeout(0.2)
            self._socks.append(s)
            t = threading.Thread(target=target, args=(s,), daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout=1.0)
        for s in self._socks:
            s.close()

    def handle_datagram(self, data: bytes, addr) -> None:
        pkt = P.TrackingPacket.unpack(data)
        if pkt is None:
            self.invalid += 1
            return
        now = time.monotonic()
        # The phone app restarted (sequence numbers begin again at 0) if the stream was silent
        # for a while: accept it as a fresh stream instead of rejecting it as "late".
        if self.last_rx_time and now - self.last_rx_time > STREAM_TIMEOUT_S:
            self._last_seq = None
            self.stream_restarted = True
        if self._last_seq is not None:
            if not P.seq_is_newer(pkt.seq, self._last_seq):
                self.out_of_order += 1   # late or duplicate: never move backwards
                return
            gap = (pkt.seq - self._last_seq) & 0xFFFFFFFF
            if gap > 1:
                self.lost += gap - 1
        self._last_seq = pkt.seq
        self.received += 1
        self.last_rx_time = now
        self._rate_times.append(now)
        self.phone_addr = (addr[0], addr[1])
        self.on_packet(pkt)

    def _data_loop(self, sock: socket.socket) -> None:
        while not self._stop.is_set():
            try:
                data, addr = sock.recvfrom(256)
            except TimeoutError:
                continue
            except OSError:
                return
            self.handle_datagram(data, addr)

    def _control_loop(self, sock: socket.socket) -> None:
        reply = P.DISCOVER_REPLY_PREFIX + json.dumps(
            {"name": self.name, "dataPort": self._socks[0].getsockname()[1]}).encode()
        while not self._stop.is_set():
            try:
                data, addr = sock.recvfrom(256)
            except TimeoutError:
                continue
            except OSError:
                return
            try:
                if data == P.DISCOVER_REQUEST:
                    sock.sendto(reply, addr)
                elif data.startswith(P.PING_PREFIX) and len(data) <= 32:
                    sock.sendto(data, addr)   # echo for RTT measurement on the phone
            except OSError:
                pass
