"""UI-independent application core: owns receiver, processing, output and profiles."""
from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass

from . import protocol as P
from .opentrack import OpenTrackSender
from .processing import OutputStage, Processor
from .profiles import AXES, Profile, default_profiles, load_profiles, profile_dir, save_profile
from .receiver import Receiver
from .settings import AppSettings


@dataclass
class Status:
    link: str                 # "waiting" | "connected"
    phone_addr: str
    rate_hz: float
    lost: int
    late: int
    face: bool
    paused: bool
    confidence: float
    raw: dict
    out: dict
    gaze: tuple
    eyes_open: bool
    eyes_enabled: bool


def local_ips() -> list[str]:
    """IPv4 addresses of this PC, so the user can type one into the phone if discovery fails."""
    ips: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    try:   # the address used for the default route
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127.") and ip not in ips:
            ips.insert(0, ip)
    except OSError:
        pass
    return ips


class Controller:
    def __init__(self, settings: AppSettings | None = None, data_port: int = P.DATA_PORT,
                 control_port: int = P.CONTROL_PORT):
        self.settings = settings or AppSettings.load()
        self.profiles: dict[str, Profile] = load_profiles()
        name = self.settings.profile if self.settings.profile in self.profiles else "General gaming"
        self.proc = Processor(self.profiles[name])
        self.sender = OpenTrackSender(self.settings.opentrack_host, self.settings.opentrack_port)
        self.stage = OutputStage(self.proc, self.sender.send, rate_hz=self.settings.output_rate_hz)
        self.rx = Receiver(self._on_packet, data_port=data_port, control_port=control_port)
        self.latest: P.TrackingPacket | None = None
        self._first = True
        self._testing = threading.Event()

    # -- lifecycle
    def start(self) -> None:
        self.stage.start()
        self.rx.start()

    def stop(self) -> None:
        self.stage.stop()
        self.rx.stop()
        self.sender.close()

    # -- packets (receiver thread)
    def _on_packet(self, pkt: P.TrackingPacket) -> None:
        self.latest = pkt
        if self.settings.auto_center and (self._first or self.rx.stream_restarted) and pkt.tracking:
            self._first = False
            self.rx.stream_restarted = False
            self.proc.center_on(pkt)
        if self._testing.is_set():
            return                      # a manual output test owns the OpenTrack feed
        self.stage.push(self.proc.process(pkt, smooth=False))

    # -- actions
    def recenter(self) -> None:
        self.proc.recenter()

    def set_paused(self, paused: bool) -> None:
        self.proc.paused = paused
        if paused:
            self.stage.push(None)

    @property
    def paused(self) -> bool:
        return self.proc.paused

    def select_profile(self, name: str) -> Profile:
        p = self.profiles[name]
        self.proc.set_profile(p)
        self.settings.profile = name
        self.settings.save()
        return p

    def save_current(self) -> str:
        return save_profile(self.proc.profile).name

    def duplicate_profile(self, new_name: str) -> Profile:
        src = self.proc.profile
        p = Profile.from_dict(src.to_dict())
        p.name = new_name.strip() or f"{src.name} copy"
        self.profiles[p.name] = p
        save_profile(p)
        return p

    def delete_profile(self, name: str) -> None:
        """Deleting a built-in profile resets it to its default values."""
        builtin = {p.name: p for p in default_profiles()}
        path = profile_dir() / (_safe(name) + ".json")
        if path.exists():
            path.unlink()
        if name in builtin:
            self.profiles[name] = builtin[name]
        else:
            self.profiles.pop(name, None)
        if self.proc.profile.name == name:
            self.select_profile(name if name in self.profiles else "General gaming")

    def set_opentrack_target(self, host: str, port: int) -> None:
        self.settings.opentrack_host = host.strip() or "127.0.0.1"
        self.settings.opentrack_port = int(port)
        self.sender.set_target(self.settings.opentrack_host, self.settings.opentrack_port)
        self.settings.save()

    def output_test(self, seconds: float = 3.0) -> None:
        """User-triggered diagnostic: sweeps yaw +-25 deg into OpenTrack so the output path can be
        verified without the phone. Clearly manual; production tracking never uses synthetic data."""
        if self._testing.is_set():
            return
        self._testing.set()
        self.stage.push(None)

        def run():
            import math
            t0 = time.monotonic()
            try:
                while (t := time.monotonic() - t0) < seconds:
                    self.sender.send(0, 0, 0, 25 * math.sin(2 * math.pi * t / seconds), 0, 0)
                    time.sleep(1 / 60)
                self.sender.send(0, 0, 0, 0, 0, 0)
            finally:
                self._testing.clear()
        threading.Thread(target=run, daemon=True).start()

    @property
    def testing(self) -> bool:
        return self._testing.is_set()

    # -- status snapshot for the UI
    def status(self) -> Status:
        p = self.latest
        connected = self.rx.connected and p is not None
        raw = {a: 0.0 for a in AXES}
        if p is not None:
            raw = {"yaw": p.yaw, "pitch": p.pitch, "roll": p.roll, "x": p.x, "y": p.y, "z": p.z}
        return Status(
            link="connected" if connected else "waiting",
            phone_addr=self.rx.phone_addr[0] if self.rx.phone_addr else "",
            rate_hz=self.rx.rate_hz, lost=self.rx.lost, late=self.rx.out_of_order,
            face=bool(connected and p.tracking), paused=self.proc.paused or bool(p and p.paused),
            confidence=p.confidence if p else 0.0, raw=raw, out=dict(self.proc.last_output),
            gaze=(p.gaze_x, p.gaze_y) if p else (0.0, 0.0),
            eyes_open=bool(p and p.left_open and p.right_open),
            eyes_enabled=bool(p and p.eyes_enabled),
        )


def _safe(name: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")
