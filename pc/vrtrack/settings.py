"""Application settings (not per-game tuning; that lives in profiles)."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path


def app_dir() -> Path:
    return Path(os.environ.get("VRTRACK_HOME", Path.home() / ".vrtrack"))


@dataclass
class AppSettings:
    profile: str = "General gaming"
    opentrack_host: str = "127.0.0.1"
    opentrack_port: int = 4242
    auto_center: bool = True          # centre on the current pose whenever tracking (re)starts
    minimize_to_tray: bool = False    # closing the window keeps tracking running in the tray
    start_minimized: bool = False
    output_rate_hz: int = 120

    @staticmethod
    def path() -> Path:
        return app_dir() / "settings.json"

    @classmethod
    def load(cls) -> "AppSettings":
        s = cls()
        try:
            d = json.loads(cls.path().read_text())
        except (OSError, ValueError):
            return s
        for f in fields(cls):
            if f.name in d and isinstance(d[f.name], type(getattr(s, f.name))):
                setattr(s, f.name, d[f.name])
        s.opentrack_port = min(max(int(s.opentrack_port), 1), 65535)
        s.output_rate_hz = min(max(int(s.output_rate_hz), 30), 250)
        return s

    def save(self) -> None:
        p = self.path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2))
