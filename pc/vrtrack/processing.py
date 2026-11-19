"""Turns raw phone pose into the values sent to OpenTrack."""
from __future__ import annotations

import math
import threading

from .profiles import AXES, Profile
from .protocol import TrackingPacket


def shape_axis(v: float, sens: float, dead: float, vmax: float, curve: float, invert: bool) -> float:
    """dead zone -> response curve -> sensitivity -> invert -> clamp."""
    mag = abs(v)
    if mag <= dead:
        return 0.0
    mag -= dead
    if vmax > 0 and curve != 1.0 and mag < vmax:
        mag = vmax * (mag / vmax) ** curve
    mag *= sens
    if vmax > 0:
        mag = min(mag, vmax)
    out = math.copysign(mag, v)
    return -out if invert else out


class Processor:
    """Thread-safe: GUI mutates profile/recenter, receiver thread calls process()."""

    def __init__(self, profile: Profile | None = None):
        self._lock = threading.Lock()
        self.profile = profile or Profile()
        self._offset = {a: 0.0 for a in AXES}
        self._smoothed: dict[str, float] | None = None
        self._last_raw = {a: 0.0 for a in AXES}
        self.last_output = {a: 0.0 for a in AXES}
        self.paused = False

    def set_profile(self, p: Profile) -> None:
        with self._lock:
            self.profile = p

    def recenter(self) -> None:
        """Make the current head pose the new centre."""
        with self._lock:
            self._offset = dict(self._last_raw)
            self._smoothed = None

    def center_on(self, pkt: TrackingPacket) -> None:
        """Make the pose in `pkt` the centre (used when tracking starts)."""
        with self._lock:
            self._last_raw = {"yaw": pkt.yaw, "pitch": pkt.pitch, "roll": pkt.roll,
                              "x": pkt.x, "y": pkt.y, "z": pkt.z}
            self._offset = dict(self._last_raw)
            self._smoothed = None

    def offset(self, axis: str) -> float:
        with self._lock:
            return self._offset[axis]

    def reset_center(self) -> None:
        with self._lock:
            self._offset = {a: 0.0 for a in AXES}
            self._smoothed = None

    def process(self, pkt: TrackingPacket, smooth: bool = True) -> dict[str, float] | None:
        """Return the pose to send, or None if nothing should be sent (paused / not tracking).

        When tracking is lost nothing is sent, so OpenTrack keeps the last valid pose
        instead of receiving invented values.
        """
        with self._lock:
            if self.paused or not pkt.tracking:
                return None
            p = self.profile
            raw = {"yaw": pkt.yaw, "pitch": pkt.pitch, "roll": pkt.roll,
                   "x": pkt.x, "y": pkt.y, "z": pkt.z}
            self._last_raw = dict(raw)
            out = {a: shape_axis(raw[a] - self._offset[a], p.sensitivity[a], p.deadzone[a],
                                 p.max_value[a], p.curve, bool(p.invert[a])) for a in AXES}
            if p.eye_tracking and pkt.eyes_enabled:
                out["yaw"] += pkt.gaze_x * p.eye_sensitivity * (-1 if p.invert["yaw"] else 1)
                out["pitch"] += pkt.gaze_y * p.eye_sensitivity * (-1 if p.invert["pitch"] else 1)
            if not smooth:           # a fixed-rate OutputStage does the smoothing
                self.last_output = dict(out)
                return dict(out)
            s = min(max(p.smoothing, 0.0), 0.95)
            if self._smoothed is None or s == 0.0:
                self._smoothed = dict(out)
            else:
                self._smoothed = {a: s * self._smoothed[a] + (1 - s) * out[a] for a in AXES}
            self.last_output = dict(self._smoothed)
            return dict(self._smoothed)


class OutputStage:
    """Sends to OpenTrack at a fixed rate (default 120 Hz), independent of the phone's packet rate.

    The phone delivers ~15-30 poses/s; sending only when one arrives makes the game view step.
    Here poses are linearly interpolated one packet-interval behind real time (adds ~1 packet of
    latency, removes the stepping), then lightly low-pass filtered per the profile's smoothing.
    Only real measured poses are used; nothing is extrapolated or invented.
    """

    def __init__(self, processor: Processor, send, rate_hz: float = 120.0):
        import time as _t
        self._time = _t.monotonic
        self.proc = processor
        self.send = send
        self.period = 1.0 / rate_hz
        self._lock = threading.Lock()
        self._samples: list[tuple[float, dict]] = []   # (arrival time, pose)
        self._cur: dict[str, float] | None = None
        self._active = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def push(self, pose: dict[str, float] | None) -> None:
        """pose=None means paused / face lost: stop sending, keep OpenTrack on its last pose."""
        now = self._time()
        with self._lock:
            if pose is None:
                self._active = False
                self._samples.clear()
                self._cur = None
                return
            self._active = True
            self._samples.append((now, pose))
            if len(self._samples) > 6:
                self._samples.pop(0)

    def _target(self, now: float):
        with self._lock:
            smp = list(self._samples)
            active = self._active
        if not active or not smp:
            return None
        if len(smp) == 1:
            return smp[0][1]
        gaps = [b[0] - a[0] for a, b in zip(smp, smp[1:])]
        delay = min(max(sum(gaps) / len(gaps), 0.015), 0.15)
        rt = now - delay
        if rt >= smp[-1][0]:
            return smp[-1][1]
        for (t0, p0), (t1, p1) in zip(smp, smp[1:]):
            if t0 <= rt <= t1:
                k = (rt - t0) / (t1 - t0) if t1 > t0 else 1.0
                return {a: p0[a] + (p1[a] - p0[a]) * k for a in AXES}
        return smp[0][1]

    def _run(self):
        import sys
        import time as _t
        if sys.platform == "win32":
            try:   # 1 ms timer resolution so a 120 Hz loop really runs at 120 Hz
                import ctypes
                ctypes.windll.winmm.timeBeginPeriod(1)
            except Exception:
                pass
        nxt = last = self._time()
        while not self._stop.is_set():
            nxt += self.period
            delay = nxt - self._time()
            if delay > 0:
                _t.sleep(delay)
            else:
                nxt = self._time()          # fell behind: resync instead of bursting
            now = self._time()
            dt, last = max(now - last, 1e-4), now
            tgt = self._target(now)
            if tgt is None:
                continue
            tau = 0.01 + 0.12 * min(max(self.proc.profile.smoothing, 0.0), 0.95)
            if self._cur is None:
                self._cur = dict(tgt)
            else:
                a = 1.0 - math.exp(-dt / tau)
                self._cur = {k: self._cur[k] + (tgt[k] - self._cur[k]) * a for k in AXES}
            self.proc.last_output = dict(self._cur)
            c = self._cur
            self.send(c["x"], c["y"], c["z"], c["yaw"], c["pitch"], c["roll"])
