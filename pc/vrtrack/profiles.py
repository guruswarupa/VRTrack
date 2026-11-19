"""Per-game tracking profiles, stored as JSON in ~/.vrtrack/profiles."""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

AXES = ("yaw", "pitch", "roll", "x", "y", "z")


def _per_axis(v: float) -> dict:
    return {a: v for a in AXES}


@dataclass
class Profile:
    name: str = "General gaming"
    sensitivity: dict = field(default_factory=lambda: _per_axis(1.0))
    deadzone: dict = field(default_factory=lambda: {"yaw": 1.0, "pitch": 1.0, "roll": 1.0,
                                                    "x": 0.3, "y": 0.3, "z": 0.3})  # deg / cm
    max_value: dict = field(default_factory=lambda: {"yaw": 90.0, "pitch": 60.0, "roll": 45.0,
                                                     "x": 20.0, "y": 20.0, "z": 20.0})  # deg / cm
    invert: dict = field(default_factory=lambda: {a: False for a in AXES})
    curve: float = 1.0          # 1 = linear, >1 = gentler near centre, steeper at the edges
    smoothing: float = 0.3      # 0 = none .. 0.95 = heavy
    eye_tracking: bool = False  # add gaze to yaw/pitch
    eye_sensitivity: float = 15.0   # degrees of view per full gaze deflection

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Profile":
        base = Profile()
        for f in fields(Profile):
            if f.name not in d:
                continue
            v = d[f.name]
            cur = getattr(base, f.name)
            if isinstance(cur, dict) and isinstance(v, dict):
                for k, x in v.items():
                    if k in AXES:
                        cur[k] = bool(x) if isinstance(cur[k], bool) else float(x)
            elif isinstance(cur, bool):
                setattr(base, f.name, bool(v))
            elif isinstance(cur, float):
                setattr(base, f.name, float(v))
            elif isinstance(cur, str):
                setattr(base, f.name, str(v))
        return base


def default_profiles() -> list[Profile]:
    ac = Profile(name="Assetto Corsa", smoothing=0.35)
    acc = Profile(name="Assetto Corsa Competizione", smoothing=0.35)
    ets = Profile(name="ETS2", smoothing=0.4)
    ats = Profile(name="ATS", smoothing=0.4)
    for p in (ets, ats):  # truck cabs: wider look-around
        p.sensitivity.update(yaw=1.3, pitch=1.1)
    profiles = [Profile(), ac, acc, ets, ats]
    for p in profiles:   # the phone faces you, so its yaw/pitch signs are opposite to the game's (seen in ETS2)
        p.invert["yaw"] = True
        p.invert["pitch"] = True
    return profiles


def profile_dir() -> Path:
    return Path(os.environ.get("VRTRACK_HOME", Path.home() / ".vrtrack")) / "profiles"


def _fname(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") + ".json"


def save_profile(p: Profile, directory: Path | None = None) -> Path:
    d = directory or profile_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / _fname(p.name)
    path.write_text(json.dumps(p.to_dict(), indent=2))
    return path


def load_profiles(directory: Path | None = None) -> dict[str, Profile]:
    """Defaults first, then anything saved on disk overrides/adds."""
    out = {p.name: p for p in default_profiles()}
    d = directory or profile_dir()
    if d.is_dir():
        for f in sorted(d.glob("*.json")):
            try:
                p = Profile.from_dict(json.loads(f.read_text()))
                out[p.name] = p
            except (OSError, ValueError):
                continue
    return out
