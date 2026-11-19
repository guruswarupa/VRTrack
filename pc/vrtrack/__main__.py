"""Entry point: GUI by default, `--headless` for console-only operation."""
import argparse
import sys
import time

from . import __version__
from . import protocol as P
from .controller import Controller
from .settings import AppSettings


def run_headless(args) -> int:
    settings = AppSettings.load()
    settings.opentrack_host, settings.opentrack_port = args.opentrack_host, args.opentrack_port
    if args.profile:
        settings.profile = args.profile
    c = Controller(settings)
    if settings.profile not in c.profiles:
        print(f"Unknown profile {settings.profile!r}. Available: {', '.join(c.profiles)}")
        return 2
    c.start()
    print(f"VRTrack {__version__}: listening on UDP {P.DATA_PORT} (data) / {P.CONTROL_PORT} (control); "
          f"profile {settings.profile!r}; OpenTrack -> {args.opentrack_host}:{args.opentrack_port}")
    try:
        while True:
            time.sleep(1)
            s = c.status()
            print(f"\r{s.link:9s} {s.rate_hz:4.0f} Hz lost={s.lost} late={s.late} "
                  f"yaw={s.out['yaw']:6.1f} pitch={s.out['pitch']:6.1f}   ", end="", flush=True)
    except KeyboardInterrupt:
        c.stop()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="vrtrack", description="Phone head tracking companion for OpenTrack")
    ap.add_argument("--headless", action="store_true", help="no window, console status only")
    ap.add_argument("--profile", default=None, help="profile name (default: last used)")
    ap.add_argument("--opentrack-host", default=None)
    ap.add_argument("--opentrack-port", type=int, default=None)
    ap.add_argument("--minimized", action="store_true", help="start minimised (to the tray if available)")
    ap.add_argument("--version", action="version", version=f"vrtrack {__version__}")
    args = ap.parse_args(argv)
    st = AppSettings.load()
    args.opentrack_host = args.opentrack_host or st.opentrack_host
    args.opentrack_port = args.opentrack_port or st.opentrack_port
    if args.headless:
        return run_headless(args)
    from .ui.app import run_gui
    return run_gui(args)


if __name__ == "__main__":
    sys.exit(main())
